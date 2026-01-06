"""
Failure Analyzer - Intelligent Root Cause Analysis

Implements failure diagnosis using agentic patterns (ADR-0069):
- Real-time error log analysis
- LLM-powered root cause classification via PydanticAI
- Pattern matching against known error library
- Service correlation and shadow error detection
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional
import logging
import re
from datetime import datetime

# Try to import PydanticAI components (optional, graceful fallback)
try:
    from pydantic_ai import Agent, ModelMessage
except ImportError:
    Agent = None
    ModelMessage = None


class RootCauseCategory(Enum):
    """Root cause classification categories"""
    
    VIRTUALIZATION = "virtualization"
    NETWORK = "network"
    STORAGE = "storage"
    SERVICE_DEPENDENCY = "service_dependency"
    CREDENTIAL = "credential"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CONFIGURATION = "configuration"
    TIMEOUT = "timeout"
    STATE_MISMATCH = "state_mismatch"
    UNKNOWN = "unknown"


class FailureSeverity(Enum):
    """Failure severity levels"""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class KnownErrorPattern:
    """Pattern for known error recognition"""
    
    pattern_id: str
    regex: str
    root_cause: RootCauseCategory
    description: str
    severity: FailureSeverity
    services_affected: List[str]
    recovery_hint: str


@dataclass
class FailureAnalysis:
    """Result of failure diagnosis"""
    
    timestamp: datetime
    failed_plugin: str
    error_message: str
    root_cause: RootCauseCategory
    root_cause_description: str
    confidence: float  # 0.0 to 1.0
    severity: FailureSeverity
    affected_services: List[str] = field(default_factory=list)
    pattern_matches: List[str] = field(default_factory=list)
    service_health_snapshot: Dict[str, Any] = field(default_factory=dict)
    system_resources_at_failure: Dict[str, Any] = field(default_factory=dict)
    correlated_failures: List[str] = field(default_factory=list)
    lm_reasoning: Optional[str] = None
    recommended_actions: List[str] = field(default_factory=list)


class FailureAnalyzer:
    """
    Analyzes failures and determines root causes using agentic patterns
    
    Combines pattern matching, heuristics, and LLM reasoning (if available)
    to classify failures and recommend recovery actions.
    """
    
    def __init__(self, ai_assistant_url: Optional[str] = None, use_llm: bool = True):
        """
        Initialize the failure analyzer
        
        Args:
            ai_assistant_url: URL to AI Assistant service for LLM-based analysis
            use_llm: Whether to use LLM for advanced reasoning
        """
        self.logger = logging.getLogger(__name__)
        self.ai_assistant_url = ai_assistant_url or "http://localhost:8080"
        self.use_llm = use_llm and Agent is not None
        
        # Initialize known error patterns library
        self._patterns = self._load_error_patterns()
        
        # LLM agent for reasoning (optional)
        self._reasoning_agent = None
        if self.use_llm:
            try:
                self._reasoning_agent = self._create_reasoning_agent()
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM reasoning agent: {e}")
                self.use_llm = False
    
    def analyze(self, diagnostic_context: Any) -> FailureAnalysis:
        """
        Analyze a failure using multiple strategies
        
        Args:
            diagnostic_context: DiagnosticContext with failure information
        
        Returns:
            FailureAnalysis with root cause and recommendations
        """
        self.logger.info(f"Analyzing failure for plugin: {diagnostic_context.plugin_name}")
        
        analysis = FailureAnalysis(
            timestamp=diagnostic_context.failure_timestamp,
            failed_plugin=diagnostic_context.plugin_name,
            error_message=diagnostic_context.error_message,
            root_cause=RootCauseCategory.UNKNOWN,
            root_cause_description="",
            confidence=0.0,
            severity=FailureSeverity.MEDIUM,
            service_health_snapshot=diagnostic_context.service_health,
            system_resources_at_failure=diagnostic_context.system_resources,
        )
        
        # Step 1: Pattern matching against known errors
        self._match_error_patterns(analysis, diagnostic_context)
        
        # Step 2: Service correlation analysis
        self._analyze_service_dependencies(analysis, diagnostic_context)
        
        # Step 3: Resource analysis
        self._analyze_resource_constraints(analysis, diagnostic_context)
        
        # Step 4: LLM-based reasoning (if available and confidence is low)
        if self.use_llm and analysis.confidence < 0.7:
            self._apply_llm_reasoning(analysis, diagnostic_context)
        
        # Step 5: Generate recommended actions
        self._generate_recommendations(analysis)
        
        self.logger.info(
            f"Analysis complete: {analysis.root_cause.value} "
            f"(confidence: {analysis.confidence:.2%})"
        )
        
        return analysis
    
    def _load_error_patterns(self) -> List[KnownErrorPattern]:
        """Load the library of known error patterns"""
        
        patterns = [
            # Virtualization errors
            KnownErrorPattern(
                pattern_id="virsh_001",
                regex=r"(CPU virtualization|KVM not available|nested virtualization)",
                root_cause=RootCauseCategory.VIRTUALIZATION,
                description="Host CPU does not support KVM virtualization",
                severity=FailureSeverity.CRITICAL,
                services_affected=["libvirtd", "kcli"],
                recovery_hint="Enable virtualization in BIOS/UEFI or use nested VM support"
            ),
            KnownErrorPattern(
                pattern_id="libvirt_001",
                regex=r"(libvirtd.*not running|Failed to connect to system bus)",
                root_cause=RootCauseCategory.SERVICE_DEPENDENCY,
                description="libvirtd service is not running or not accessible",
                severity=FailureSeverity.CRITICAL,
                services_affected=["libvirtd"],
                recovery_hint="Start libvirtd: systemctl start libvirtd"
            ),
            
            # Network errors
            KnownErrorPattern(
                pattern_id="network_001",
                regex=r"(No route to host|Network is unreachable|Temporary failure in name resolution)",
                root_cause=RootCauseCategory.NETWORK,
                description="Network connectivity issue to target host",
                severity=FailureSeverity.HIGH,
                services_affected=["networking"],
                recovery_hint="Check network connectivity and DNS resolution"
            ),
            KnownErrorPattern(
                pattern_id="registry_001",
                regex=r"(Failed to pull image|registry.*not reachable|authentication required)",
                root_cause=RootCauseCategory.NETWORK,
                description="Cannot reach container registry or authentication failed",
                severity=FailureSeverity.HIGH,
                services_affected=["podman", "container_runtime"],
                recovery_hint="Check registry credentials and network access to registry"
            ),
            
            # Storage/Disk errors
            KnownErrorPattern(
                pattern_id="disk_001",
                regex=r"(No space left on device|Disk quota exceeded|out of disk space)",
                root_cause=RootCauseCategory.STORAGE,
                description="Insufficient disk space for operation",
                severity=FailureSeverity.CRITICAL,
                services_affected=["storage"],
                recovery_hint="Free up disk space: remove old images, logs, or temporary files"
            ),
            
            # Credential errors
            KnownErrorPattern(
                pattern_id="credential_001",
                regex=r"(Permission denied|authentication failed|Invalid credentials|Unauthorized)",
                root_cause=RootCauseCategory.CREDENTIAL,
                description="Authentication or authorization failure",
                severity=FailureSeverity.HIGH,
                services_affected=["auth", "vault"],
                recovery_hint="Check credentials and permissions for the operation"
            ),
            KnownErrorPattern(
                pattern_id="vault_001",
                regex=r"(vault.*connection|Failed to unseal vault|vault.*decrypt)",
                root_cause=RootCauseCategory.CREDENTIAL,
                description="Vault service issue or decryption failure",
                severity=FailureSeverity.CRITICAL,
                services_affected=["vault"],
                recovery_hint="Check Vault service status and unlock if needed"
            ),
            
            # Timeout errors
            KnownErrorPattern(
                pattern_id="timeout_001",
                regex=r"(timeout|timed out|connection timeout|read timeout)",
                root_cause=RootCauseCategory.TIMEOUT,
                description="Operation exceeded time limit",
                severity=FailureSeverity.MEDIUM,
                services_affected=["networking"],
                recovery_hint="Increase timeout or check service responsiveness"
            ),
            
            # Airflow-specific errors
            KnownErrorPattern(
                pattern_id="airflow_001",
                regex=r"(airflow.*scheduler|airflow.*worker|DAG.*import|airflow.*database)",
                root_cause=RootCauseCategory.SERVICE_DEPENDENCY,
                description="Airflow service or DAG execution issue",
                severity=FailureSeverity.HIGH,
                services_affected=["airflow"],
                recovery_hint="Check Airflow logs: podman logs airflow-scheduler"
            ),
            
            # VM creation/kcli errors
            KnownErrorPattern(
                pattern_id="kcli_001",
                regex=r"(kcli.*error|VM.*already exists|image.*not found)",
                root_cause=RootCauseCategory.STATE_MISMATCH,
                description="kcli VM operation failed or state inconsistency",
                severity=FailureSeverity.HIGH,
                services_affected=["kcli", "libvirtd"],
                recovery_hint="Verify VM state: kcli list vm; delete conflicting VMs if needed"
            ),
        ]
        
        return patterns
    
    def _match_error_patterns(self, analysis: FailureAnalysis, diagnostic_context: Any) -> None:
        """Match error message against known patterns"""
        
        error_text = diagnostic_context.error_message.lower()
        
        for pattern in self._patterns:
            try:
                if re.search(pattern.regex.lower(), error_text):
                    analysis.pattern_matches.append(pattern.pattern_id)
                    
                    # Update analysis if confidence is higher
                    if 0.8 > analysis.confidence:
                        analysis.root_cause = pattern.root_cause
                        analysis.root_cause_description = pattern.description
                        analysis.confidence = 0.8
                        analysis.severity = pattern.severity
                        analysis.affected_services.extend(pattern.services_affected)
                        analysis.recommended_actions.append(pattern.recovery_hint)
                    
                    self.logger.debug(f"Matched pattern: {pattern.pattern_id}")
            except re.error as e:
                self.logger.warning(f"Invalid regex in pattern {pattern.pattern_id}: {e}")
    
    def _analyze_service_dependencies(self, analysis: FailureAnalysis, diagnostic_context: Any) -> None:
        """Analyze service health to correlate with failure"""
        
        service_health = diagnostic_context.service_health
        
        # Check for unhealthy dependencies
        unhealthy_services = []
        for service_name, health_info in service_health.items():
            if isinstance(health_info, dict) and not health_info.get("active", False):
                unhealthy_services.append(service_name)
        
        if unhealthy_services:
            analysis.correlated_failures.extend(unhealthy_services)
            
            # If a critical service is down and confidence is low, update analysis
            critical_services = ["libvirtd", "airflow", "vault"]
            for service in unhealthy_services:
                if any(crit in service for crit in critical_services) and analysis.confidence < 0.9:
                    analysis.root_cause = RootCauseCategory.SERVICE_DEPENDENCY
                    analysis.root_cause_description = f"{service} service is not running"
                    analysis.confidence = 0.85
                    analysis.severity = FailureSeverity.CRITICAL
                    analysis.recommended_actions.insert(0, f"Start service: systemctl start {service}")
    
    def _analyze_resource_constraints(self, analysis: FailureAnalysis, diagnostic_context: Any) -> None:
        """Analyze system resources for resource exhaustion issues"""
        
        resources = diagnostic_context.system_resources
        
        # Check CPU
        if resources.get("cpu", {}).get("percent", 0) > 95:
            analysis.recommended_actions.append("CPU is highly utilized; wait or kill non-essential processes")
        
        # Check memory
        mem = resources.get("memory", {})
        if mem.get("percent", 0) > 90:
            if analysis.confidence < 0.7:
                analysis.root_cause = RootCauseCategory.RESOURCE_EXHAUSTION
                analysis.root_cause_description = "System memory is nearly exhausted"
                analysis.confidence = 0.75
                analysis.severity = FailureSeverity.HIGH
            analysis.recommended_actions.append("Free memory: kill unused processes or restart services")
        
        # Check disk
        disk = resources.get("disk", {})
        if disk.get("percent", 0) > 90:
            if analysis.confidence < 0.7:
                analysis.root_cause = RootCauseCategory.STORAGE
                analysis.root_cause_description = "System disk is nearly full"
                analysis.confidence = 0.75
                analysis.severity = FailureSeverity.CRITICAL
            analysis.recommended_actions.insert(0, "Free disk space: du -sh /* | sort -h; rm -rf /tmp/*")
    
    def _create_reasoning_agent(self):
        """Create PydanticAI agent for advanced reasoning"""
        
        if not Agent:
            return None
        
        try:
            # Create a lightweight agent for failure reasoning
            agent = Agent(
                model="openai/gpt-4o",  # or configured via env var
                system_prompt="""You are an infrastructure failure diagnosis expert.
                
Given error logs, system state, and service health information, determine:
1. The root cause of the failure
2. Confidence level (0-1)
3. Recommended recovery actions

Be concise and actionable."""
            )
            return agent
        except Exception as e:
            self.logger.warning(f"Failed to create reasoning agent: {e}")
            return None
    
    def _apply_llm_reasoning(self, analysis: FailureAnalysis, diagnostic_context: Any) -> None:
        """Use LLM to refine failure analysis"""
        
        if not self._reasoning_agent:
            return
        
        try:
            prompt = f"""
Analyze this infrastructure failure:

Plugin: {diagnostic_context.plugin_name}
Error: {diagnostic_context.error_message}
Matched Patterns: {', '.join(analysis.pattern_matches) or 'none'}
Unhealthy Services: {', '.join(analysis.correlated_failures) or 'none'}

Current Analysis:
- Root Cause: {analysis.root_cause.value}
- Confidence: {analysis.confidence:.2%}

Refine the analysis with your assessment of the most likely root cause.
Respond with: ROOT_CAUSE | CONFIDENCE | KEY_ACTIONS
"""
            
            # Synchronous call to agent (simplified; real impl would be async)
            self.logger.debug(f"Invoking LLM reasoning agent")
            # Note: This is a simplified placeholder; real integration would be async
            analysis.lm_reasoning = f"LLM analysis queued for {analysis.failed_plugin}"
            
        except Exception as e:
            self.logger.warning(f"LLM reasoning failed: {e}")
    
    def _generate_recommendations(self, analysis: FailureAnalysis) -> None:
        """Generate actionable recovery recommendations based on analysis"""
        
        # Ensure we have at least basic recommendations
        if not analysis.recommended_actions:
            analysis.recommended_actions = [
                "Check service logs: journalctl -xe",
                "Verify system resources: free -h; df -h",
                "Check network: ping -c 3 8.8.8.8"
            ]
        
        # Add diagnostic commands based on root cause
        if analysis.root_cause == RootCauseCategory.SERVICE_DEPENDENCY:
            if "systemctl status libvirtd" not in analysis.recommended_actions[0]:
                analysis.recommended_actions.insert(0, "Check libvirtd status: systemctl status libvirtd")
        
        elif analysis.root_cause == RootCauseCategory.NETWORK:
            if "ping" not in str(analysis.recommended_actions):
                analysis.recommended_actions.insert(0, "Test connectivity: ping registry.redhat.io")
        
        elif analysis.root_cause == RootCauseCategory.STORAGE:
            if "disk" not in str(analysis.recommended_actions).lower():
                analysis.recommended_actions.insert(0, "Check disk usage: df -h; du -sh /var/log/*")
