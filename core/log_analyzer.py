"""
Qubinode Navigator Automated Log Analysis and Error Resolution System

This module provides intelligent log analysis, error pattern recognition,
and automated resolution capabilities for Qubinode Navigator deployments.

Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture
"""

import json
import re
import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
import requests
from collections import Counter
import hashlib


@dataclass
class ErrorPattern:
    """Represents an identified error pattern"""

    pattern_id: str
    error_type: str
    pattern_regex: str
    description: str
    severity: str  # critical, high, medium, low
    frequency: int
    first_seen: str
    last_seen: str
    resolution_steps: List[str]
    ai_analysis: Optional[str] = None


@dataclass
class LogEntry:
    """Represents a parsed log entry"""

    timestamp: str
    event_type: str
    data: Dict[str, Any]
    parsed_timestamp: Optional[datetime.datetime] = None

    def __post_init__(self):
        """Parse timestamp after initialization"""
        try:
            self.parsed_timestamp = datetime.datetime.fromisoformat(self.timestamp)
        except ValueError:
            self.parsed_timestamp = datetime.datetime.now()


@dataclass
class DeploymentSession:
    """Represents a complete deployment session"""

    session_id: str
    start_time: datetime.datetime
    end_time: Optional[datetime.datetime]
    playbook: str
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    errors: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    resolution_status: str  # resolved, pending, failed


@dataclass
class ResolutionRecommendation:
    """Represents an automated resolution recommendation"""

    recommendation_id: str
    error_pattern_id: str
    confidence: float  # 0.0 to 1.0
    resolution_type: str  # automated, manual, escalation
    steps: List[str]
    estimated_time: str
    risk_level: str  # low, medium, high
    ai_rationale: str
    success_probability: float


class LogAnalyzer:
    """
    Automated log analysis and error resolution system

    Provides intelligent analysis of Ansible deployment logs,
    pattern recognition, and AI-powered resolution recommendations.
    """

    def __init__(self, ai_assistant_url: str = "http://localhost:8080"):
        self.logger = logging.getLogger(__name__)
        self.ai_assistant_url = ai_assistant_url

        # Pattern storage
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.deployment_sessions: Dict[str, DeploymentSession] = {}

        # Analysis state
        self.pattern_cache = {}
        self.resolution_history = []

        # Load existing patterns
        self._load_error_patterns()

    def _load_error_patterns(self):
        """Load known error patterns from knowledge base"""
        # Initialize with common Qubinode Navigator error patterns
        common_patterns = [
            {
                "pattern_id": "virtualization_disabled",
                "error_type": "hardware",
                "pattern_regex": r"(virtualization|VT-x|AMD-V).*(not|disabled|unavailable)",
                "description": "Hardware virtualization not enabled in BIOS",
                "severity": "critical",
                "resolution_steps": [
                    "Reboot system and enter BIOS/UEFI setup",
                    "Navigate to CPU or Advanced settings",
                    "Enable Intel VT-x or AMD-V virtualization",
                    "Save settings and reboot",
                    "Verify with: grep -E '(vmx|svm)' /proc/cpuinfo",
                ],
            },
            {
                "pattern_id": "kcli_install_failure",
                "error_type": "package",
                "pattern_regex": r"kcli.*(install|pip).*(failed|error)",
                "description": "kcli installation failure due to missing dependencies",
                "severity": "high",
                "resolution_steps": [
                    "Install Python development headers: dnf install python3-devel",
                    "Update pip: python3 -m pip install --upgrade pip",
                    "Install kcli: pip3 install kcli",
                    "Verify installation: kcli version",
                ],
            },
            {
                "pattern_id": "firewall_service_down",
                "error_type": "service",
                "pattern_regex": r"firewall.*(not running|inactive|failed)",
                "description": "Firewall service not running or configured",
                "severity": "medium",
                "resolution_steps": [
                    "Start firewalld service: systemctl start firewalld",
                    "Enable firewalld: systemctl enable firewalld",
                    "Check status: systemctl status firewalld",
                    "Configure required ports for cockpit: firewall-cmd --add-service=cockpit --permanent",
                    "Reload firewall: firewall-cmd --reload",
                ],
            },
            {
                "pattern_id": "insufficient_disk_space",
                "error_type": "storage",
                "pattern_regex": r"(insufficient|not enough|low).*(disk|space|storage)",
                "description": "Insufficient disk space for VM storage pools",
                "severity": "high",
                "resolution_steps": [
                    "Check disk usage: df -h",
                    "Clean up temporary files: dnf clean all && rm -rf /tmp/*",
                    "Remove old container images: podman system prune -a",
                    "Expand disk or add external storage",
                    "Reconfigure storage pool location if needed",
                ],
            },
            {
                "pattern_id": "python_compatibility",
                "error_type": "compatibility",
                "pattern_regex": r"python.*(3\.12|compatibility|module).*(error|failed)",
                "description": "Python 3.12 compatibility issues with legacy modules",
                "severity": "medium",
                "resolution_steps": [
                    "Check Python version: python3 --version",
                    "Update to compatible package versions",
                    "Use virtual environment: python3 -m venv /opt/qubinode-venv",
                    "Activate venv: source /opt/qubinode-venv/bin/activate",
                    "Install compatible packages in venv",
                ],
            },
        ]

        for pattern_data in common_patterns:
            pattern = ErrorPattern(
                pattern_id=pattern_data["pattern_id"],
                error_type=pattern_data["error_type"],
                pattern_regex=pattern_data["pattern_regex"],
                description=pattern_data["description"],
                severity=pattern_data["severity"],
                frequency=0,
                first_seen="",
                last_seen="",
                resolution_steps=pattern_data["resolution_steps"],
            )
            self.error_patterns[pattern.pattern_id] = pattern

    def parse_log_file(self, log_file_path: str) -> List[LogEntry]:
        """Parse deployment log file into structured entries"""
        entries = []

        try:
            with open(log_file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("="):
                        continue

                    try:
                        log_data = json.loads(line)
                        entry = LogEntry(
                            timestamp=log_data.get("timestamp", ""),
                            event_type=log_data.get("event_type", ""),
                            data=log_data.get("data", {}),
                        )
                        entries.append(entry)
                    except json.JSONDecodeError:
                        # Handle non-JSON log lines
                        self.logger.debug(f"Skipping non-JSON log line: {line}")

        except FileNotFoundError:
            self.logger.error(f"Log file not found: {log_file_path}")
        except Exception as e:
            self.logger.error(f"Error parsing log file: {e}")

        return entries

    def analyze_deployment_session(self, log_entries: List[LogEntry]) -> DeploymentSession:
        """Analyze a complete deployment session"""
        if not log_entries:
            return None

        # Find session boundaries
        start_entry = next((e for e in log_entries if e.event_type == "deployment_start"), None)
        end_entry = next(
            (e for e in reversed(log_entries) if e.event_type == "deployment_complete"),
            None,
        )

        if not start_entry:
            return None

        # Generate session ID
        session_id = hashlib.md5(f"{start_entry.timestamp}_{start_entry.data.get('playbook', 'unknown')}".encode()).hexdigest()[:8]

        # Analyze session metrics
        task_events = [e for e in log_entries if e.event_type in ["task_success", "task_failed"]]
        failed_events = [e for e in log_entries if e.event_type == "task_failed"]

        # Extract errors
        errors = []
        for event in failed_events:
            errors.append(
                {
                    "timestamp": event.timestamp,
                    "task_name": event.data.get("task_name", ""),
                    "host": event.data.get("host", ""),
                    "error_msg": event.data.get("error_msg", ""),
                    "stderr": event.data.get("stderr", ""),
                }
            )

        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(log_entries)

        session = DeploymentSession(
            session_id=session_id,
            start_time=start_entry.parsed_timestamp,
            end_time=end_entry.parsed_timestamp if end_entry else None,
            playbook=start_entry.data.get("playbook", "unknown"),
            total_tasks=len(task_events),
            successful_tasks=len(task_events) - len(failed_events),
            failed_tasks=len(failed_events),
            errors=errors,
            performance_metrics=performance_metrics,
            resolution_status="pending" if errors else "resolved",
        )

        self.deployment_sessions[session_id] = session
        return session

    def _calculate_performance_metrics(self, log_entries: List[LogEntry]) -> Dict[str, Any]:
        """Calculate performance metrics from log entries"""
        metrics = {
            "total_duration": 0,
            "average_task_duration": 0,
            "slow_tasks": [],
            "failure_rate": 0,
        }

        # Find deployment duration
        start_entry = next((e for e in log_entries if e.event_type == "deployment_start"), None)
        end_entry = next(
            (e for e in reversed(log_entries) if e.event_type == "deployment_complete"),
            None,
        )

        if start_entry and end_entry:
            duration = (end_entry.parsed_timestamp - start_entry.parsed_timestamp).total_seconds()
            metrics["total_duration"] = duration

        # Analyze task performance
        task_durations = []
        slow_threshold = 30.0  # seconds

        for entry in log_entries:
            if entry.event_type == "task_success" and "duration" in entry.data:
                duration = entry.data["duration"]
                task_durations.append(duration)

                if duration > slow_threshold:
                    metrics["slow_tasks"].append(
                        {
                            "task_name": entry.data.get("task_name", ""),
                            "duration": duration,
                            "host": entry.data.get("host", ""),
                        }
                    )

        if task_durations:
            metrics["average_task_duration"] = sum(task_durations) / len(task_durations)

        # Calculate failure rate
        total_tasks = len([e for e in log_entries if e.event_type in ["task_success", "task_failed"]])
        failed_tasks = len([e for e in log_entries if e.event_type == "task_failed"])

        if total_tasks > 0:
            metrics["failure_rate"] = (failed_tasks / total_tasks) * 100

        return metrics

    def identify_error_patterns(self, session: DeploymentSession) -> List[str]:
        """Identify error patterns in deployment session"""
        if not session:
            return []

        matched_patterns = []

        for error in session.errors:
            error_text = f"{error.get('error_msg', '')} {error.get('stderr', '')}"

            for pattern_id, pattern in self.error_patterns.items():
                if re.search(pattern.pattern_regex, error_text, re.IGNORECASE):
                    matched_patterns.append(pattern_id)

                    # Update pattern statistics
                    pattern.frequency += 1
                    pattern.last_seen = error["timestamp"]
                    if not pattern.first_seen:
                        pattern.first_seen = error["timestamp"]

        return list(set(matched_patterns))  # Remove duplicates

    async def generate_ai_analysis(self, session: DeploymentSession, error_patterns: List[str]) -> str:
        """Generate AI-powered analysis of deployment issues"""
        try:
            # Prepare context for AI analysis
            context = {
                "session_id": session.session_id,
                "playbook": session.playbook,
                "total_tasks": session.total_tasks,
                "failed_tasks": session.failed_tasks,
                "failure_rate": session.performance_metrics.get("failure_rate", 0),
                "errors": session.errors[:5],  # Limit to first 5 errors
                "identified_patterns": error_patterns,
            }

            # Create AI analysis prompt
            prompt = f"""
            Analyze this Qubinode Navigator deployment session and provide intelligent troubleshooting guidance:

            Deployment Context:
            - Session ID: {session.session_id}
            - Playbook: {session.playbook}
            - Tasks: {session.successful_tasks}/{session.total_tasks} successful
            - Failure Rate: {session.performance_metrics.get("failure_rate", 0):.1f}%

            Identified Error Patterns:
            {", ".join(error_patterns) if error_patterns else "None"}

            Recent Errors:
            {json.dumps(session.errors[:3], indent=2)}

            Please provide:
            1. Root cause analysis
            2. Priority order for addressing issues
            3. Specific resolution steps
            4. Prevention recommendations
            """

            # Send to AI Assistant
            response = requests.post(
                f"{self.ai_assistant_url}/chat",
                json={"message": prompt, "context": context},
                timeout=30,
            )

            if response.status_code == 200:
                ai_response = response.json()
                return ai_response.get("text", "No analysis available")
            else:
                return "AI analysis unavailable"

        except Exception as e:
            self.logger.error(f"Failed to generate AI analysis: {e}")
            return f"AI analysis failed: {str(e)}"

    def generate_resolution_recommendations(self, session: DeploymentSession, error_patterns: List[str]) -> List[ResolutionRecommendation]:
        """Generate automated resolution recommendations"""
        recommendations = []

        for pattern_id in error_patterns:
            if pattern_id not in self.error_patterns:
                continue

            pattern = self.error_patterns[pattern_id]

            # Calculate confidence based on pattern frequency and severity
            confidence = min(0.9, 0.5 + (pattern.frequency * 0.1))
            if pattern.severity == "critical":
                confidence += 0.2
            elif pattern.severity == "high":
                confidence += 0.1

            # Determine resolution type
            resolution_type = "automated" if confidence > 0.8 else "manual"
            if pattern.severity == "critical":
                resolution_type = "escalation"

            # Estimate time and risk
            estimated_time = self._estimate_resolution_time(pattern)
            risk_level = self._assess_risk_level(pattern)

            recommendation = ResolutionRecommendation(
                recommendation_id=f"{session.session_id}_{pattern_id}",
                error_pattern_id=pattern_id,
                confidence=confidence,
                resolution_type=resolution_type,
                steps=pattern.resolution_steps,
                estimated_time=estimated_time,
                risk_level=risk_level,
                ai_rationale=f"Pattern '{pattern.description}' detected with {confidence:.1%} confidence",
                success_probability=confidence * 0.9,
            )

            recommendations.append(recommendation)

        # Sort by confidence and severity
        recommendations.sort(
            key=lambda r: (r.confidence, self._severity_weight(r.error_pattern_id)),
            reverse=True,
        )

        return recommendations

    def _estimate_resolution_time(self, pattern: ErrorPattern) -> str:
        """Estimate time required to resolve error pattern"""
        time_estimates = {
            "critical": "30-60 minutes",
            "high": "15-30 minutes",
            "medium": "5-15 minutes",
            "low": "2-5 minutes",
        }
        return time_estimates.get(pattern.severity, "10-20 minutes")

    def _assess_risk_level(self, pattern: ErrorPattern) -> str:
        """Assess risk level of applying resolution"""
        # Hardware and service changes are higher risk
        if pattern.error_type in ["hardware", "service"]:
            return "medium"
        elif pattern.error_type in ["package", "compatibility"]:
            return "low"
        else:
            return "medium"

    def _severity_weight(self, pattern_id: str) -> int:
        """Get numeric weight for pattern severity"""
        if pattern_id not in self.error_patterns:
            return 0

        severity_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}

        return severity_weights.get(self.error_patterns[pattern_id].severity, 0)

    async def run_diagnostic_analysis(self, session: DeploymentSession) -> Dict[str, Any]:
        """Run comprehensive diagnostic analysis using AI Assistant"""
        try:
            response = requests.post(
                f"{self.ai_assistant_url}/diagnostics",
                json={"include_ai_analysis": True},
                timeout=60,
            )

            if response.status_code == 200:
                diagnostics = response.json()

                # Enhance with session context
                diagnostics["session_context"] = {
                    "session_id": session.session_id,
                    "failure_rate": session.performance_metrics.get("failure_rate", 0),
                    "error_count": session.failed_tasks,
                }

                return diagnostics
            else:
                return {"error": f"Diagnostics failed: {response.status_code}"}

        except Exception as e:
            self.logger.error(f"Failed to run diagnostic analysis: {e}")
            return {"error": f"Diagnostics unavailable: {str(e)}"}

    def generate_analysis_report(
        self,
        session: DeploymentSession,
        error_patterns: List[str],
        recommendations: List[ResolutionRecommendation],
        ai_analysis: str = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""

        report = {
            "analysis_timestamp": datetime.datetime.now().isoformat(),
            "session_summary": asdict(session),
            "error_analysis": {
                "patterns_identified": len(error_patterns),
                "pattern_details": [
                    {
                        "pattern_id": pid,
                        "description": self.error_patterns[pid].description,
                        "severity": self.error_patterns[pid].severity,
                        "frequency": self.error_patterns[pid].frequency,
                    }
                    for pid in error_patterns
                    if pid in self.error_patterns
                ],
            },
            "recommendations": [asdict(rec) for rec in recommendations],
            "ai_analysis": ai_analysis,
            "next_steps": self._generate_next_steps(recommendations),
            "prevention_measures": self._generate_prevention_measures(error_patterns),
        }

        return report

    def _generate_next_steps(self, recommendations: List[ResolutionRecommendation]) -> List[str]:
        """Generate prioritized next steps"""
        if not recommendations:
            return ["No specific issues identified. Monitor future deployments."]

        next_steps = []

        # High-confidence automated fixes first
        auto_recs = [r for r in recommendations if r.resolution_type == "automated" and r.confidence > 0.8]
        if auto_recs:
            next_steps.append(f"Apply automated fixes for {len(auto_recs)} high-confidence issues")

        # Manual interventions
        manual_recs = [r for r in recommendations if r.resolution_type == "manual"]
        if manual_recs:
            next_steps.append(f"Review and apply {len(manual_recs)} manual resolution steps")

        # Escalations
        escalation_recs = [r for r in recommendations if r.resolution_type == "escalation"]
        if escalation_recs:
            next_steps.append(f"Escalate {len(escalation_recs)} critical issues requiring expert intervention")

        next_steps.append("Re-run deployment after applying fixes")
        next_steps.append("Monitor for recurring patterns")

        return next_steps

    def _generate_prevention_measures(self, error_patterns: List[str]) -> List[str]:
        """Generate prevention measures for identified patterns"""
        prevention_measures = []

        pattern_types = [self.error_patterns[pid].error_type for pid in error_patterns if pid in self.error_patterns]
        type_counts = Counter(pattern_types)

        if "hardware" in type_counts:
            prevention_measures.append("Implement pre-deployment hardware validation checks")

        if "package" in type_counts:
            prevention_measures.append("Create dependency validation playbooks")

        if "service" in type_counts:
            prevention_measures.append("Add service health checks to deployment workflow")

        if "storage" in type_counts:
            prevention_measures.append("Implement disk space monitoring and alerts")

        prevention_measures.extend(
            [
                "Regular system updates and maintenance",
                "Automated testing in staging environment",
                "Documentation of environment-specific requirements",
            ]
        )

        return prevention_measures

    async def analyze_log_file(self, log_file_path: str) -> Dict[str, Any]:
        """Complete log analysis workflow"""
        self.logger.info(f"Starting log analysis for: {log_file_path}")

        # Parse log file
        log_entries = self.parse_log_file(log_file_path)
        if not log_entries:
            return {"error": "No valid log entries found"}

        # Analyze deployment session
        session = self.analyze_deployment_session(log_entries)
        if not session:
            return {"error": "Could not identify deployment session"}

        # Identify error patterns
        error_patterns = self.identify_error_patterns(session)

        # Generate recommendations
        recommendations = self.generate_resolution_recommendations(session, error_patterns)

        # Get AI analysis
        ai_analysis = await self.generate_ai_analysis(session, error_patterns)

        # Generate comprehensive report
        report = self.generate_analysis_report(session, error_patterns, recommendations, ai_analysis)

        self.logger.info(f"Analysis complete for session {session.session_id}")
        return report
