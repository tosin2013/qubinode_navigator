"""
Tests for Qubinode Navigator Log Analyzer

Tests the automated log analysis and error resolution system
including pattern recognition, AI integration, and recommendation generation.
"""

import json
import os
import sys
import tempfile
import unittest.mock as mock
from datetime import datetime
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.log_analyzer import (
    DeploymentSession,
    ErrorPattern,
    LogAnalyzer,
    LogEntry,
    ResolutionRecommendation,
)


class TestLogAnalyzer:
    """Test cases for log analyzer functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.analyzer = LogAnalyzer(ai_assistant_url="http://test:8080")

        # Create temporary log file
        self.temp_log = tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".log"
        )

        # Sample log entries
        self.sample_logs = [
            {
                "timestamp": "2025-11-08T10:00:00",
                "event_type": "deployment_start",
                "data": {"playbook": "site.yml", "start_time": 1699440000},
            },
            {
                "timestamp": "2025-11-08T10:00:05",
                "event_type": "task_success",
                "data": {
                    "task_name": "Install packages",
                    "host": "localhost",
                    "duration": 2.3,
                },
            },
            {
                "timestamp": "2025-11-08T10:00:10",
                "event_type": "task_failed",
                "data": {
                    "task_name": "Configure KVM",
                    "host": "localhost",
                    "error_msg": "Hardware virtualization not enabled in BIOS (VT-x required)",
                    "stderr": "kvm: disabled by bios",
                },
            },
            {
                "timestamp": "2025-11-08T10:00:15",
                "event_type": "task_failed",
                "data": {
                    "task_name": "Install kcli",
                    "host": "localhost",
                    "error_msg": "kcli installation failed: pip install error - missing python3-dev",
                    "stderr": "error: Microsoft Visual C++ 14.0 is required",
                },
            },
            {
                "timestamp": "2025-11-08T10:00:20",
                "event_type": "deployment_complete",
                "data": {"total_duration": 20.0, "end_time": 1699440020},
            },
        ]

        # Write sample logs to temp file
        for log_entry in self.sample_logs:
            self.temp_log.write(json.dumps(log_entry) + "\n")
        self.temp_log.close()

    def teardown_method(self):
        """Cleanup test environment"""
        try:
            os.unlink(self.temp_log.name)
        except FileNotFoundError:
            pass

    def test_log_analyzer_initialization(self):
        """Test log analyzer initialization"""
        assert self.analyzer.ai_assistant_url == "http://test:8080"
        assert len(self.analyzer.error_patterns) > 0
        assert "virtualization_disabled" in self.analyzer.error_patterns
        assert "kcli_install_failure" in self.analyzer.error_patterns

    def test_error_pattern_loading(self):
        """Test error pattern loading"""
        patterns = self.analyzer.error_patterns

        # Check virtualization pattern
        virt_pattern = patterns["virtualization_disabled"]
        assert virt_pattern.error_type == "hardware"
        assert virt_pattern.severity == "critical"
        assert len(virt_pattern.resolution_steps) > 0

        # Check kcli pattern
        kcli_pattern = patterns["kcli_install_failure"]
        assert kcli_pattern.error_type == "package"
        assert kcli_pattern.severity == "high"

    def test_log_file_parsing(self):
        """Test log file parsing"""
        entries = self.analyzer.parse_log_file(self.temp_log.name)

        assert len(entries) == 5
        assert entries[0].event_type == "deployment_start"
        assert entries[2].event_type == "task_failed"
        assert entries[4].event_type == "deployment_complete"

        # Check parsed timestamp
        assert isinstance(entries[0].parsed_timestamp, datetime)

    def test_deployment_session_analysis(self):
        """Test deployment session analysis"""
        entries = self.analyzer.parse_log_file(self.temp_log.name)
        session = self.analyzer.analyze_deployment_session(entries)

        assert session is not None
        assert session.playbook == "site.yml"
        assert session.total_tasks == 3  # 1 success + 2 failures
        assert session.successful_tasks == 1
        assert session.failed_tasks == 2
        assert len(session.errors) == 2

        # Check performance metrics
        assert "total_duration" in session.performance_metrics
        assert "failure_rate" in session.performance_metrics
        assert session.performance_metrics["failure_rate"] > 0

    def test_error_pattern_identification(self):
        """Test error pattern identification"""
        entries = self.analyzer.parse_log_file(self.temp_log.name)
        session = self.analyzer.analyze_deployment_session(entries)
        error_patterns = self.analyzer.identify_error_patterns(session)

        assert "virtualization_disabled" in error_patterns
        assert "kcli_install_failure" in error_patterns

        # Check pattern frequency updates
        virt_pattern = self.analyzer.error_patterns["virtualization_disabled"]
        assert virt_pattern.frequency > 0
        assert virt_pattern.last_seen != ""

    def test_resolution_recommendation_generation(self):
        """Test resolution recommendation generation"""
        entries = self.analyzer.parse_log_file(self.temp_log.name)
        session = self.analyzer.analyze_deployment_session(entries)
        error_patterns = self.analyzer.identify_error_patterns(session)
        recommendations = self.analyzer.generate_resolution_recommendations(
            session, error_patterns
        )

        assert len(recommendations) > 0

        # Check recommendation structure
        rec = recommendations[0]
        assert hasattr(rec, "recommendation_id")
        assert hasattr(rec, "confidence")
        assert hasattr(rec, "resolution_type")
        assert hasattr(rec, "steps")
        assert len(rec.steps) > 0

        # Check confidence calculation
        assert 0.0 <= rec.confidence <= 1.0

        # Check resolution types
        resolution_types = [r.resolution_type for r in recommendations]
        assert all(
            rt in ["automated", "manual", "escalation"] for rt in resolution_types
        )

    @mock.patch("requests.post")
    def test_ai_analysis_integration(self, mock_post):
        """Test AI analysis integration"""
        # Mock AI response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "Hardware virtualization is disabled. Enable VT-x in BIOS settings."
        }
        mock_post.return_value = mock_response

        entries = self.analyzer.parse_log_file(self.temp_log.name)
        session = self.analyzer.analyze_deployment_session(entries)
        error_patterns = self.analyzer.identify_error_patterns(session)

        # Test AI analysis (async function, so we need to run it)
        import asyncio

        ai_analysis = asyncio.run(
            self.analyzer.generate_ai_analysis(session, error_patterns)
        )

        assert "Hardware virtualization" in ai_analysis
        mock_post.assert_called_once()

    def test_performance_metrics_calculation(self):
        """Test performance metrics calculation"""
        entries = self.analyzer.parse_log_file(self.temp_log.name)
        session = self.analyzer.analyze_deployment_session(entries)

        metrics = session.performance_metrics

        assert "total_duration" in metrics
        assert "average_task_duration" in metrics
        assert "failure_rate" in metrics
        assert "slow_tasks" in metrics

        # Check failure rate calculation
        expected_failure_rate = (2 / 3) * 100  # 2 failures out of 3 tasks
        assert abs(metrics["failure_rate"] - expected_failure_rate) < 0.1

    def test_analysis_report_generation(self):
        """Test comprehensive analysis report generation"""
        entries = self.analyzer.parse_log_file(self.temp_log.name)
        session = self.analyzer.analyze_deployment_session(entries)
        error_patterns = self.analyzer.identify_error_patterns(session)
        recommendations = self.analyzer.generate_resolution_recommendations(
            session, error_patterns
        )

        report = self.analyzer.generate_analysis_report(
            session, error_patterns, recommendations, "AI analysis text"
        )

        # Check report structure
        assert "analysis_timestamp" in report
        assert "session_summary" in report
        assert "error_analysis" in report
        assert "recommendations" in report
        assert "ai_analysis" in report
        assert "next_steps" in report
        assert "prevention_measures" in report

        # Check error analysis
        error_analysis = report["error_analysis"]
        assert error_analysis["patterns_identified"] > 0
        assert len(error_analysis["pattern_details"]) > 0

        # Check recommendations
        assert len(report["recommendations"]) > 0

        # Check next steps and prevention measures
        assert len(report["next_steps"]) > 0
        assert len(report["prevention_measures"]) > 0

    def test_severity_weighting(self):
        """Test severity weighting for recommendations"""
        # Test severity weights
        assert (
            self.analyzer._severity_weight("virtualization_disabled") == 4
        )  # critical
        assert self.analyzer._severity_weight("kcli_install_failure") == 3  # high
        assert self.analyzer._severity_weight("firewall_service_down") == 2  # medium
        assert self.analyzer._severity_weight("nonexistent_pattern") == 0

    def test_time_estimation(self):
        """Test resolution time estimation"""
        pattern = self.analyzer.error_patterns["virtualization_disabled"]
        time_estimate = self.analyzer._estimate_resolution_time(pattern)

        assert isinstance(time_estimate, str)
        assert "minutes" in time_estimate.lower()

    def test_risk_assessment(self):
        """Test risk level assessment"""
        virt_pattern = self.analyzer.error_patterns["virtualization_disabled"]
        kcli_pattern = self.analyzer.error_patterns["kcli_install_failure"]

        virt_risk = self.analyzer._assess_risk_level(virt_pattern)
        kcli_risk = self.analyzer._assess_risk_level(kcli_pattern)

        assert virt_risk in ["low", "medium", "high"]
        assert kcli_risk in ["low", "medium", "high"]

    def test_empty_log_file_handling(self):
        """Test handling of empty log files"""
        empty_log = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        empty_log.close()

        try:
            entries = self.analyzer.parse_log_file(empty_log.name)
            assert len(entries) == 0

            session = self.analyzer.analyze_deployment_session(entries)
            assert session is None
        finally:
            os.unlink(empty_log.name)

    def test_malformed_log_handling(self):
        """Test handling of malformed log entries"""
        malformed_log = tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".log"
        )

        # Write malformed JSON and valid entries
        malformed_log.write("invalid json line\n")
        malformed_log.write(
            '{"timestamp": "2025-11-08T10:00:00", "event_type": "test", "data": {}}\n'
        )
        malformed_log.write("another invalid line\n")
        malformed_log.close()

        try:
            entries = self.analyzer.parse_log_file(malformed_log.name)
            assert len(entries) == 1  # Only valid entry should be parsed
            assert entries[0].event_type == "test"
        finally:
            os.unlink(malformed_log.name)

    def test_pattern_frequency_tracking(self):
        """Test error pattern frequency tracking"""
        # Initial frequency should be 0
        pattern = self.analyzer.error_patterns["virtualization_disabled"]
        initial_frequency = pattern.frequency

        # Analyze logs (should increment frequency)
        entries = self.analyzer.parse_log_file(self.temp_log.name)
        session = self.analyzer.analyze_deployment_session(entries)
        self.analyzer.identify_error_patterns(session)

        # Frequency should have increased
        assert pattern.frequency > initial_frequency
        assert pattern.last_seen != ""

    @mock.patch("requests.post")
    def test_diagnostic_analysis_integration(self, mock_post):
        """Test diagnostic analysis integration"""
        # Mock diagnostic response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "diagnostics": {"summary": {"successful_tools": 6, "total_tools": 6}},
            "ai_analysis": "System appears healthy",
        }
        mock_post.return_value = mock_response

        entries = self.analyzer.parse_log_file(self.temp_log.name)
        session = self.analyzer.analyze_deployment_session(entries)

        # Test diagnostic analysis
        import asyncio

        diagnostics = asyncio.run(self.analyzer.run_diagnostic_analysis(session))

        assert "diagnostics" in diagnostics
        assert "session_context" in diagnostics
        mock_post.assert_called_once()

    def test_next_steps_generation(self):
        """Test next steps generation"""
        entries = self.analyzer.parse_log_file(self.temp_log.name)
        session = self.analyzer.analyze_deployment_session(entries)
        error_patterns = self.analyzer.identify_error_patterns(session)
        recommendations = self.analyzer.generate_resolution_recommendations(
            session, error_patterns
        )

        next_steps = self.analyzer._generate_next_steps(recommendations)

        assert len(next_steps) > 0
        assert any("fix" in step.lower() for step in next_steps)
        assert any("deployment" in step.lower() for step in next_steps)

    def test_prevention_measures_generation(self):
        """Test prevention measures generation"""
        entries = self.analyzer.parse_log_file(self.temp_log.name)
        session = self.analyzer.analyze_deployment_session(entries)
        error_patterns = self.analyzer.identify_error_patterns(session)

        prevention_measures = self.analyzer._generate_prevention_measures(
            error_patterns
        )

        assert len(prevention_measures) > 0
        assert any("validation" in measure.lower() for measure in prevention_measures)
        # Check for either 'monitoring' or 'maintenance' since both are valid prevention measures
        assert any(
            "monitoring" in measure.lower() or "maintenance" in measure.lower()
            for measure in prevention_measures
        )


class TestLogAnalyzerIntegration:
    """Integration tests for log analyzer"""

    @pytest.mark.integration
    def test_full_analysis_workflow(self):
        """Test complete analysis workflow"""
        # This would require actual log files and AI Assistant
        # Placeholder for integration testing
        pass

    @pytest.mark.integration
    def test_ai_assistant_live_integration(self):
        """Test live AI Assistant integration"""
        # This would require running AI Assistant
        # Placeholder for integration testing
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
