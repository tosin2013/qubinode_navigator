"""
Qubinode Navigator Log Analysis Plugin

Provides automated log analysis and error resolution capabilities
for Qubinode Navigator deployments through the plugin framework.

Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.base_plugin import (
    QubiNodePlugin,
    PluginResult,
    PluginStatus,
    SystemState,
    ExecutionContext,
)
from core.log_analyzer import LogAnalyzer


class LogAnalysisPlugin(QubiNodePlugin):
    """
    Log Analysis Plugin for Qubinode Navigator

    Provides automated analysis of deployment logs with AI-powered
    error resolution recommendations and pattern recognition.
    """

    __version__ = "1.0.0"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.description = "Automated log analysis and error resolution for Qubinode Navigator deployments"

        # Configuration
        self.ai_assistant_url = config.get("ai_assistant_url", "http://localhost:8080")
        self.log_directory = config.get("log_directory", "/tmp")
        self.auto_analyze = config.get("auto_analyze", True)
        self.report_directory = config.get(
            "report_directory", "/tmp/log_analysis_reports"
        )

        # Initialize log analyzer
        self.log_analyzer = LogAnalyzer(ai_assistant_url=self.ai_assistant_url)

        # State tracking
        self.analysis_history: List[Dict[str, Any]] = []
        self.last_analysis_time: Optional[datetime] = None

        self.logger = logging.getLogger(__name__)

        # Ensure report directory exists
        Path(self.report_directory).mkdir(parents=True, exist_ok=True)

    def _initialize_plugin(self) -> None:
        """Plugin-specific initialization logic"""
        # Verify log analyzer is working
        if not self.log_analyzer.error_patterns:
            raise RuntimeError("No error patterns loaded")

        # Check if AI Assistant is available
        try:
            import requests

            response = requests.get(f"{self.ai_assistant_url}/health", timeout=5)
            if response.status_code == 200:
                self.logger.info("AI Assistant connection verified")
            else:
                self.logger.warning(
                    "AI Assistant not available - analysis will continue without AI insights"
                )
        except Exception as e:
            self.logger.warning(f"AI Assistant not available: {e}")

        self.logger.info(
            f"Log Analysis Plugin initialized with {len(self.log_analyzer.error_patterns)} error patterns"
        )

    def check_state(self) -> SystemState:
        """Check current system state for idempotency"""
        return self.check_system_state(ExecutionContext())

    def initialize(self) -> bool:
        """Initialize the log analysis plugin"""
        try:
            self.logger.info("Initializing Log Analysis Plugin")
            self._initialize_plugin()
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Log Analysis Plugin: {e}")
            return False

    def check_system_state(self, context: ExecutionContext) -> SystemState:
        """Check system state for log analysis readiness"""
        try:
            state_data = {}

            # Check if log directory exists and is accessible
            log_path = Path(self.log_directory)
            state_data["log_directory_exists"] = log_path.exists()
            state_data["log_directory_is_dir"] = (
                log_path.is_dir() if log_path.exists() else False
            )

            if not log_path.exists():
                state_data["status"] = "needs_configuration"
                return SystemState(state_data)

            if not log_path.is_dir():
                state_data["status"] = "error"
                return SystemState(state_data)

            # Check for recent deployment logs
            log_files = list(log_path.glob("*deployment*.log"))
            state_data["log_files_count"] = len(log_files)

            if not log_files:
                state_data["status"] = "ready"
                return SystemState(state_data)

            # Check if any logs need analysis
            recent_logs = [
                f
                for f in log_files
                if (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).days < 1
            ]
            state_data["recent_logs_count"] = len(recent_logs)

            if recent_logs and self.auto_analyze:
                state_data["status"] = "needs_changes"
            else:
                state_data["status"] = "ready"

            return SystemState(state_data)

        except Exception as e:
            self.logger.error(f"Error checking system state: {e}")
            return SystemState({"status": "error", "error": str(e)})

    def is_idempotent(self) -> bool:
        """Log analysis is idempotent - can be run multiple times safely"""
        return True

    def apply_changes(
        self,
        current_state: SystemState,
        desired_state: SystemState,
        context: ExecutionContext,
    ) -> PluginResult:
        """Apply log analysis changes"""
        try:
            self.logger.info("Starting automated log analysis")

            # Find deployment logs to analyze
            log_files = self._find_deployment_logs()

            if not log_files:
                return PluginResult(
                    changed=False,
                    message="No deployment logs found for analysis",
                    data={"analyzed_files": 0},
                )

            # Analyze each log file
            analysis_results = []
            for log_file in log_files:
                try:
                    result = asyncio.run(self._analyze_log_file(log_file))
                    if result:
                        analysis_results.append(result)
                except Exception as e:
                    self.logger.error(f"Failed to analyze {log_file}: {e}")

            # Generate summary report
            summary_report = self._generate_summary_report(analysis_results)

            # Save summary report
            report_path = self._save_summary_report(summary_report)

            self.last_analysis_time = datetime.now()

            return PluginResult(
                changed=True,
                message=f"Analyzed {len(analysis_results)} deployment logs",
                data={
                    "analyzed_files": len(analysis_results),
                    "total_errors": summary_report.get("total_errors", 0),
                    "critical_issues": summary_report.get("critical_issues", 0),
                    "report_path": str(report_path),
                },
            )

        except Exception as e:
            self.logger.error(f"Failed to apply log analysis changes: {e}")
            return PluginResult(
                changed=False,
                message=f"Log analysis failed: {str(e)}",
                status=PluginStatus.FAILED,
            )

    def cleanup(self) -> bool:
        """Cleanup log analysis resources"""
        try:
            self.logger.info("Cleaning up Log Analysis Plugin")

            # Clean up old analysis reports (keep last 10)
            report_files = sorted(
                Path(self.report_directory).glob("analysis_*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )

            for old_report in report_files[10:]:
                try:
                    old_report.unlink()
                    self.logger.debug(f"Removed old report: {old_report}")
                except Exception as e:
                    self.logger.warning(
                        f"Failed to remove old report {old_report}: {e}"
                    )

            return True

        except Exception as e:
            self.logger.error(f"Failed to cleanup Log Analysis Plugin: {e}")
            return False

    def _find_deployment_logs(self) -> List[Path]:
        """Find deployment log files to analyze"""
        log_path = Path(self.log_directory)

        # Look for various log file patterns
        patterns = ["*deployment*.log", "*qubinode*.log", "ansible*.log"]

        log_files = []
        for pattern in patterns:
            log_files.extend(log_path.glob(pattern))

        # Filter to recent files (last 24 hours) if auto_analyze is enabled
        if self.auto_analyze:
            cutoff_time = datetime.now().timestamp() - (24 * 3600)  # 24 hours ago
            log_files = [f for f in log_files if f.stat().st_mtime > cutoff_time]

        # Remove duplicates and sort by modification time
        unique_files = list(set(log_files))
        unique_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        return unique_files[:5]  # Limit to 5 most recent files

    async def _analyze_log_file(self, log_file: Path) -> Optional[Dict[str, Any]]:
        """Analyze a single log file"""
        try:
            self.logger.info(f"Analyzing log file: {log_file}")

            # Run log analysis
            report = await self.log_analyzer.analyze_log_file(str(log_file))

            if "error" in report:
                self.logger.error(f"Analysis failed for {log_file}: {report['error']}")
                return None

            # Enhance report with file metadata
            report["file_metadata"] = {
                "file_path": str(log_file),
                "file_size": log_file.stat().st_size,
                "modification_time": datetime.fromtimestamp(
                    log_file.stat().st_mtime
                ).isoformat(),
                "analysis_time": datetime.now().isoformat(),
            }

            # Save individual report
            report_file = (
                Path(self.report_directory)
                / f"analysis_{log_file.stem}_{int(datetime.now().timestamp())}.json"
            )
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.info(
                f"Analysis complete for {log_file}, report saved to {report_file}"
            )
            return report

        except Exception as e:
            self.logger.error(f"Failed to analyze {log_file}: {e}")
            return None

    def _generate_summary_report(
        self, analysis_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate summary report from multiple analysis results"""
        summary = {
            "summary_timestamp": datetime.now().isoformat(),
            "total_files_analyzed": len(analysis_results),
            "total_errors": 0,
            "critical_issues": 0,
            "high_priority_issues": 0,
            "pattern_frequency": {},
            "common_recommendations": [],
            "deployment_sessions": [],
        }

        for result in analysis_results:
            # Count errors and issues
            session_summary = result.get("session_summary", {})
            summary["total_errors"] += session_summary.get("failed_tasks", 0)

            # Count pattern severities
            error_analysis = result.get("error_analysis", {})
            for pattern in error_analysis.get("pattern_details", []):
                severity = pattern.get("severity", "unknown")
                pattern_id = pattern.get("pattern_id", "unknown")

                if severity == "critical":
                    summary["critical_issues"] += 1
                elif severity == "high":
                    summary["high_priority_issues"] += 1

                # Track pattern frequency
                if pattern_id not in summary["pattern_frequency"]:
                    summary["pattern_frequency"][pattern_id] = 0
                summary["pattern_frequency"][pattern_id] += 1

            # Collect session info
            summary["deployment_sessions"].append(
                {
                    "session_id": session_summary.get("session_id"),
                    "playbook": session_summary.get("playbook"),
                    "failure_rate": session_summary.get("performance_metrics", {}).get(
                        "failure_rate", 0
                    ),
                    "file_path": result.get("file_metadata", {}).get("file_path"),
                }
            )

        # Generate common recommendations
        summary["common_recommendations"] = self._extract_common_recommendations(
            analysis_results
        )

        return summary

    def _extract_common_recommendations(
        self, analysis_results: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract common recommendations across multiple analyses"""
        recommendation_counts = {}

        for result in analysis_results:
            recommendations = result.get("recommendations", [])
            for rec in recommendations:
                rec_type = rec.get("error_pattern_id", "unknown")
                if rec_type not in recommendation_counts:
                    recommendation_counts[rec_type] = 0
                recommendation_counts[rec_type] += 1

        # Return most common recommendations
        common_recs = []
        for pattern_id, count in sorted(
            recommendation_counts.items(), key=lambda x: x[1], reverse=True
        ):
            if count > 1:  # Appears in multiple analyses
                if pattern_id in self.log_analyzer.error_patterns:
                    pattern = self.log_analyzer.error_patterns[pattern_id]
                    common_recs.append(f"{pattern.description} (seen {count} times)")

        return common_recs[:5]  # Top 5 common recommendations

    def _save_summary_report(self, summary_report: Dict[str, Any]) -> Path:
        """Save summary report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path(self.report_directory) / f"summary_report_{timestamp}.json"

        with open(report_path, "w") as f:
            json.dump(summary_report, f, indent=2, default=str)

        self.logger.info(f"Summary report saved to {report_path}")
        return report_path

    def get_status(self) -> Dict[str, Any]:
        """Get plugin status information"""
        return {
            "plugin_name": self.name,
            "version": self.version,
            "status": "active",
            "ai_assistant_url": self.ai_assistant_url,
            "log_directory": self.log_directory,
            "report_directory": self.report_directory,
            "auto_analyze": self.auto_analyze,
            "error_patterns_loaded": len(self.log_analyzer.error_patterns),
            "last_analysis_time": self.last_analysis_time.isoformat()
            if self.last_analysis_time
            else None,
            "analysis_history_count": len(self.analysis_history),
        }

    def analyze_specific_log(self, log_file_path: str) -> Dict[str, Any]:
        """Analyze a specific log file (public API method)"""
        try:
            return asyncio.run(self.log_analyzer.analyze_log_file(log_file_path))
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    def get_error_patterns(self) -> Dict[str, Any]:
        """Get known error patterns (public API method)"""
        patterns = {}
        for pattern_id, pattern in self.log_analyzer.error_patterns.items():
            patterns[pattern_id] = {
                "description": pattern.description,
                "severity": pattern.severity,
                "error_type": pattern.error_type,
                "frequency": pattern.frequency,
            }
        return patterns
