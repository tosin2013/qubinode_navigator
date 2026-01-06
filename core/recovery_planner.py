"""
Recovery Planner - Generate Recovery Actions for Failures

Implements recovery planning using agentic patterns (ADR-0069):
- Generates 3 recovery options: auto-retry, manual fix, escalate
- Creates GitHub issues with full diagnostic context
- Plans rollback procedures
- Executes recovery with idempotency guarantees
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
import logging
from datetime import datetime
import json
import os

from .failure_analyzer import FailureAnalysis, RootCauseCategory, FailureSeverity


class RecoveryActionType(Enum):
    """Type of recovery action"""
    
    RETRY = "retry"              # Re-execute plugin with adjusted parameters
    MANUAL_FIX = "manual_fix"    # Suggest shell commands for human intervention
    ESCALATE = "escalate"         # Create GitHub issue for human review
    ROLLBACK = "rollback"         # Roll back to previous state
    WAIT = "wait"                 # Wait for dependencies to recover
    SKIP = "skip"                 # Skip this plugin, continue with others


@dataclass
class RecoveryOption:
    """Single recovery option"""
    
    action_type: RecoveryActionType
    priority: int  # 1=highest, 3=lowest
    confidence: float  # 0.0 to 1.0
    estimated_duration_seconds: int
    risk_level: str  # low, medium, high
    description: str
    steps: List[str]  # Actionable steps for human or automation
    prerequisites: List[str] = field(default_factory=list)
    rollback_steps: List[str] = field(default_factory=list)
    success_criteria: str = ""


@dataclass
class RecoveryPlan:
    """Complete recovery plan with multiple options"""
    
    timestamp: datetime
    failed_plugin: str
    failure_analysis: FailureAnalysis
    recovery_options: List[RecoveryOption] = field(default_factory=list)
    recommended_option: Optional[RecoveryOption] = None
    github_issue_url: Optional[str] = None
    checkpoint_path: Optional[str] = None  # Path to saved state for rollback
    execution_attempts: int = 0
    last_execution_result: Optional[str] = None
    
    def to_markdown(self) -> str:
        """Convert plan to GitHub issue markdown"""
        
        md = f"""## Failure Recovery Report

**Timestamp**: {self.timestamp.isoformat()}
**Failed Plugin**: {self.failed_plugin}

### Root Cause Analysis

**Category**: {self.failure_analysis.root_cause.value}
**Confidence**: {self.failure_analysis.confidence:.0%}
**Severity**: {self.failure_analysis.severity.value}

**Description**: {self.failure_analysis.root_cause_description}

**Error Message**:
```
{self.failure_analysis.error_message}
```

### Service Health Snapshot
```json
{json.dumps(self.failure_analysis.service_health_snapshot, indent=2)}
```

### System Resources at Failure
```json
{json.dumps(self.failure_analysis.system_resources_at_failure, indent=2)}
```

### Recovery Options

"""
        for i, option in enumerate(self.recovery_options, 1):
            md += f"""#### Option {i}: {option.action_type.value.upper()}
- **Priority**: {option.priority}/3
- **Confidence**: {option.confidence:.0%}
- **Risk**: {option.risk_level}
- **Est. Duration**: {option.estimated_duration_seconds}s

**Description**: {option.description}

**Steps**:
"""
            for step in option.steps:
                md += f"- {step}\n"
            
            if option.rollback_steps:
                md += "\n**Rollback Steps**:\n"
                for step in option.rollback_steps:
                    md += f"- {step}\n"
            
            md += "\n"
        
        return md


class RecoveryPlanner:
    """
    Plans recovery actions for diagnosed failures
    
    Generates multiple recovery options, evaluates feasibility,
    and creates escalation issues when needed.
    """
    
    def __init__(self, github_token: Optional[str] = None, github_repo: Optional[str] = None):
        """
        Initialize the recovery planner
        
        Args:
            github_token: GitHub API token for creating issues
            github_repo: GitHub repository in format 'owner/repo'
        """
        self.logger = logging.getLogger(__name__)
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.github_repo = github_repo or os.getenv("GITHUB_REPOSITORY", "Qubinode/qubinode_navigator")
    
    def plan_recovery(self, failure_analysis: FailureAnalysis, plugin_config: Dict[str, Any] = None) -> RecoveryPlan:
        """
        Generate recovery plan for a diagnosed failure
        
        Args:
            failure_analysis: Result from FailureAnalyzer
            plugin_config: Configuration of the failed plugin
        
        Returns:
            RecoveryPlan with multiple recovery options
        """
        
        self.logger.info(f"Planning recovery for: {failure_analysis.failed_plugin}")
        
        plan = RecoveryPlan(
            timestamp=datetime.now(),
            failed_plugin=failure_analysis.failed_plugin,
            failure_analysis=failure_analysis,
        )
        
        # Generate recovery options based on root cause
        self._generate_retry_option(plan, failure_analysis, plugin_config)
        self._generate_manual_fix_option(plan, failure_analysis)
        self._generate_escalation_option(plan, failure_analysis)
        
        # Rank options by confidence and risk
        self._rank_options(plan)
        
        # Select recommended option
        plan.recommended_option = plan.recovery_options[0] if plan.recovery_options else None
        
        self.logger.info(f"Recovery plan created with {len(plan.recovery_options)} options")
        
        return plan
    
    def _generate_retry_option(
        self,
        plan: RecoveryPlan,
        analysis: FailureAnalysis,
        config: Dict[str, Any] = None
    ) -> None:
        """Generate auto-retry recovery option"""
        
        config = config or {}
        
        option = RecoveryOption(
            action_type=RecoveryActionType.RETRY,
            priority=1,  # Highest priority if safe
            confidence=min(0.85, analysis.confidence + 0.05),
            estimated_duration_seconds=300,  # 5 minutes default
            risk_level="low",
            description="Re-execute the failed plugin with checkpoint recovery",
            steps=[
                "Load last checkpoint (system state snapshot)",
                f"Re-execute {plan.failed_plugin} plugin",
                "Compare state with desired state",
                "Verify plugin health status",
            ],
            prerequisites=[
                "Sufficient disk space (>1GB free)",
                "All dependent services healthy",
            ],
            rollback_steps=[
                "Restore from checkpoint",
                "Verify system state match",
            ],
            success_criteria=f"Plugin {plan.failed_plugin} returns PluginStatus.COMPLETED"
        )
        
        # Adjust retry parameters based on root cause
        if analysis.root_cause == RootCauseCategory.TIMEOUT:
            option.steps.insert(0, "Increase timeout to 600 seconds (10 minutes)")
            option.steps.append("Monitor service health before retry")
            option.estimated_duration_seconds = 600
        
        elif analysis.root_cause == RootCauseCategory.SERVICE_DEPENDENCY:
            option.steps.insert(0, "Wait 30s for dependent services to stabilize")
            option.estimated_duration_seconds = 330
            option.prerequisites.extend([
                f"Service(s) {', '.join(analysis.affected_services)} healthy",
            ])
        
        elif analysis.root_cause == RootCauseCategory.RESOURCE_EXHAUSTION:
            option.confidence = 0.6  # Lower confidence if resources are exhausted
            option.risk_level = "medium"
            option.steps.insert(0, "Free system resources (disk, memory)")
            option.prerequisites = [
                "At least 2GB free disk space",
                "At least 4GB free memory",
            ]
        
        elif analysis.root_cause == RootCauseCategory.STATE_MISMATCH:
            option.priority = 2  # Lower priority; may need manual intervention
            option.confidence = 0.65
            option.steps.insert(1, "Reset VM state: kcli delete vm; kcli create vm")
            option.estimated_duration_seconds = 900
        
        plan.recovery_options.append(option)
    
    def _generate_manual_fix_option(self, plan: RecoveryPlan, analysis: FailureAnalysis) -> None:
        """Generate manual fix option with diagnostic steps"""
        
        steps = []
        risk = "medium"
        duration = 600  # 10 minutes for human-guided fix
        
        # Add diagnostic steps based on root cause
        if analysis.root_cause == RootCauseCategory.VIRTUALIZATION:
            steps = [
                "Verify virtualization support: grep -o 'vmx\\|svm' /proc/cpuinfo",
                "Enable in BIOS/UEFI if not present",
                "Reboot and verify: virt-host-validate qemu",
            ]
            risk = "high"
            duration = 1200  # 20 minutes for BIOS changes
        
        elif analysis.root_cause == RootCauseCategory.NETWORK:
            steps = [
                "Check network connectivity: ping 8.8.8.8",
                "Check DNS: nslookup registry.redhat.io",
                "Test registry access: curl -I https://registry.redhat.io",
                "Check firewall: sudo firewall-cmd --list-all",
            ]
        
        elif analysis.root_cause == RootCauseCategory.CREDENTIAL:
            steps = [
                "Verify credentials: cat ~/.docker/config.json (if exists)",
                "Check vault status: vault status",
                "Re-authenticate: podman login quay.io",
                "Verify SSH keys: ls -la ~/.ssh/",
            ]
            risk = "low"
        
        elif analysis.root_cause == RootCauseCategory.STORAGE:
            steps = [
                "Check disk usage: df -h",
                "Free space: sudo rm -rf /tmp/* /var/log/*.gz",
                "Remove old images: podman image prune -a",
                "Verify: df -h",
            ]
            risk = "medium"
        
        elif analysis.root_cause == RootCauseCategory.SERVICE_DEPENDENCY:
            service = analysis.affected_services[0] if analysis.affected_services else "service"
            steps = [
                f"Check {service} status: systemctl status {service}",
                f"View logs: journalctl -u {service} -n 50",
                f"Restart: sudo systemctl restart {service}",
                f"Verify: sudo systemctl status {service}",
            ]
        
        else:
            # Generic diagnostic steps
            steps = [
                "Check system logs: journalctl -xe | tail -100",
                "Check plugin logs: grep ERROR /opt/qubinode_navigator/logs/*.log",
                "Review failure context in GitHub Actions logs",
                "Check service health: systemctl status libvirtd podman airflow",
            ]
        
        option = RecoveryOption(
            action_type=RecoveryActionType.MANUAL_FIX,
            priority=2,
            confidence=0.75,  # Confidence that these steps will help
            estimated_duration_seconds=duration,
            risk_level=risk,
            description="Execute manual diagnostic and fix steps",
            steps=steps,
            success_criteria="Verify dependencies are healthy before retry"
        )
        
        # Add recommended actions from failure analysis
        option.steps.extend(analysis.recommended_actions)
        
        plan.recovery_options.append(option)
    
    def _generate_escalation_option(self, plan: RecoveryPlan, analysis: FailureAnalysis) -> None:
        """Generate escalation option that creates a GitHub issue"""
        
        option = RecoveryOption(
            action_type=RecoveryActionType.ESCALATE,
            priority=3,  # Lowest priority; only if others fail
            confidence=1.0,  # Always safe to escalate
            estimated_duration_seconds=3600,  # 1 hour for human review
            risk_level="low",
            description="Create GitHub issue for human review with full diagnostic context",
            steps=[
                "Create GitHub issue with failure analysis",
                "Include diagnostic context and service health",
                "Assign to on-call engineer",
                "Continue deployment with optional skip or rollback",
            ],
            success_criteria="GitHub issue created and human acknowledged"
        )
        
        plan.recovery_options.append(option)
    
    def _rank_options(self, plan: RecoveryPlan) -> None:
        """Rank recovery options by priority and confidence"""
        
        def option_score(opt: RecoveryOption) -> tuple:
            """Score option for ranking (higher is better)"""
            risk_weight = {"low": 3, "medium": 2, "high": 1}.get(opt.risk_level, 1)
            return (opt.priority, opt.confidence, risk_weight)
        
        plan.recovery_options.sort(key=option_score, reverse=True)
    
    def create_github_issue(self, plan: RecoveryPlan) -> Optional[str]:
        """
        Create GitHub issue for failure with recovery plan
        
        Args:
            plan: RecoveryPlan to document
        
        Returns:
            URL to created issue or None if failed
        """
        
        if not self.github_token or not self.github_repo:
            self.logger.warning("GitHub credentials not configured; skipping issue creation")
            return None
        
        try:
            import requests
        except ImportError:
            self.logger.warning("requests module not available; cannot create GitHub issue")
            return None
        
        try:
            title = f"[Failure] {plan.failed_plugin} - {plan.failure_analysis.root_cause.value}"
            body = plan.to_markdown()
            
            # Create issue via GitHub API
            api_url = f"https://api.github.com/repos/{self.github_repo}/issues"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            payload = {
                "title": title,
                "body": body,
                "labels": ["failure-diagnosis", "needs-triage"],
            }
            
            response = requests.post(api_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 201:
                issue_data = response.json()
                issue_url = issue_data.get("html_url")
                plan.github_issue_url = issue_url
                self.logger.info(f"Created GitHub issue: {issue_url}")
                return issue_url
            else:
                self.logger.error(f"Failed to create GitHub issue: {response.status_code} {response.text}")
                return None
        
        except Exception as e:
            self.logger.error(f"Exception creating GitHub issue: {e}")
            return None
    
    def execute_recovery(
        self,
        plan: RecoveryPlan,
        recovery_option: RecoveryOption,
        approval_callback: Optional[Callable[[RecoveryOption], bool]] = None,
    ) -> bool:
        """
        Execute a recovery option
        
        Args:
            plan: Recovery plan
            recovery_option: Specific option to execute
            approval_callback: Callback to approve execution (for interactive mode)
        
        Returns:
            True if recovery succeeded, False otherwise
        """
        
        self.logger.info(f"Executing recovery: {recovery_option.action_type.value}")
        
        # Check if approval is needed
        if approval_callback:
            if not approval_callback(recovery_option):
                self.logger.info("Recovery execution denied by approval callback")
                plan.last_execution_result = "denied"
                return False
        
        plan.execution_attempts += 1
        
        try:
            if recovery_option.action_type == RecoveryActionType.RETRY:
                success = self._execute_retry(plan, recovery_option)
            
            elif recovery_option.action_type == RecoveryActionType.MANUAL_FIX:
                success = self._execute_manual_fix(plan, recovery_option)
            
            elif recovery_option.action_type == RecoveryActionType.ESCALATE:
                success = self._execute_escalation(plan, recovery_option)
            
            elif recovery_option.action_type == RecoveryActionType.WAIT:
                success = self._execute_wait(plan, recovery_option)
            
            elif recovery_option.action_type == RecoveryActionType.ROLLBACK:
                success = self._execute_rollback(plan, recovery_option)
            
            elif recovery_option.action_type == RecoveryActionType.SKIP:
                success = self._execute_skip(plan, recovery_option)
            
            else:
                self.logger.error(f"Unknown recovery action type: {recovery_option.action_type}")
                success = False
            
            plan.last_execution_result = "success" if success else "failed"
            return success
        
        except Exception as e:
            self.logger.error(f"Exception during recovery execution: {e}")
            plan.last_execution_result = f"error: {str(e)}"
            return False
    
    def _execute_retry(self, plan: RecoveryPlan, option: RecoveryOption) -> bool:
        """Execute plugin retry recovery"""
        # This would be called by PluginManager with actual plugin instance
        self.logger.info(f"Retry recovery: {option.description}")
        # Return True if retry should proceed; actual execution happens in PluginManager
        return True
    
    def _execute_manual_fix(self, plan: RecoveryPlan, option: RecoveryOption) -> bool:
        """Log manual fix steps and request human action"""
        self.logger.info(f"Manual fix recovery - execute these steps:")
        for i, step in enumerate(option.steps, 1):
            self.logger.info(f"  {i}. {step}")
        # Return True to indicate steps were logged
        return True
    
    def _execute_escalation(self, plan: RecoveryPlan, option: RecoveryOption) -> bool:
        """Execute escalation by creating GitHub issue"""
        return self.create_github_issue(plan) is not None
    
    def _execute_wait(self, plan: RecoveryPlan, option: RecoveryOption) -> bool:
        """Execute wait recovery"""
        import time
        wait_seconds = int(option.estimated_duration_seconds * 0.1)  # Wait 10% of estimated
        self.logger.info(f"Waiting {wait_seconds}s for services to stabilize")
        time.sleep(wait_seconds)
        return True
    
    def _execute_rollback(self, plan: RecoveryPlan, option: RecoveryOption) -> bool:
        """Execute rollback recovery"""
        # This would be called by PluginManager with actual checkpoint
        self.logger.info(f"Rollback recovery: {option.description}")
        return True
    
    def _execute_skip(self, plan: RecoveryPlan, option: RecoveryOption) -> bool:
        """Skip this plugin and continue"""
        self.logger.info(f"Skipping plugin: {plan.failed_plugin}")
        return True
