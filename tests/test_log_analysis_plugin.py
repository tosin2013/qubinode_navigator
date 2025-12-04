"""
Tests for Qubinode Navigator Log Analysis Plugin

Tests the log analysis plugin integration with the plugin framework
including automated analysis, error resolution, and reporting capabilities.
"""

import pytest
import unittest.mock as mock
import json
import tempfile
import os
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from plugins.services.log_analysis_plugin import LogAnalysisPlugin
from core.base_plugin import SystemState, ExecutionContext, PluginStatus


class TestLogAnalysisPlugin:
    """Test cases for log analysis plugin functionality"""

    def setup_method(self):
        """Setup test environment"""
        # Create temporary directories
        self.temp_log_dir = tempfile.mkdtemp()
        self.temp_report_dir = tempfile.mkdtemp()

        # Plugin configuration
        self.config = {
            "ai_assistant_url": "http://test:8080",
            "log_directory": self.temp_log_dir,
            "auto_analyze": True,
            "report_directory": self.temp_report_dir,
        }

        # Create plugin instance
        self.plugin = LogAnalysisPlugin(self.config)

        # Create sample log file
        self.sample_log_file = Path(self.temp_log_dir) / "qubinode_deployment.log"
        self._create_sample_log_file()

        # Mock execution context
        self.context = ExecutionContext(inventory="localhost", environment="development", config={}, variables={})

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil

        try:
            shutil.rmtree(self.temp_log_dir)
            shutil.rmtree(self.temp_report_dir)
        except Exception:
            pass

    def _create_sample_log_file(self):
        """Create sample log file for testing"""
        sample_logs = [
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
                "event_type": "deployment_complete",
                "data": {"total_duration": 15.0, "end_time": 1699440015},
            },
        ]

        with open(self.sample_log_file, "w") as f:
            for log_entry in sample_logs:
                f.write(json.dumps(log_entry) + "\n")

    def test_plugin_initialization(self):
        """Test plugin initialization"""
        assert self.plugin.name == "LogAnalysisPlugin"
        assert self.plugin.version == "1.0.0"
        assert self.plugin.ai_assistant_url == "http://test:8080"
        assert self.plugin.log_directory == self.temp_log_dir
        assert self.plugin.auto_analyze is True
        assert self.plugin.report_directory == self.temp_report_dir

        # Check log analyzer is initialized
        assert self.plugin.log_analyzer is not None
        assert len(self.plugin.log_analyzer.error_patterns) > 0

    @mock.patch("requests.get")
    def test_plugin_initialize_with_ai_available(self, mock_get):
        """Test plugin initialization with AI Assistant available"""
        # Mock AI Assistant health check
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.plugin.initialize()

        assert result is True
        mock_get.assert_called_once()

    @mock.patch("requests.get")
    def test_plugin_initialize_with_ai_unavailable(self, mock_get):
        """Test plugin initialization with AI Assistant unavailable"""
        # Mock AI Assistant connection failure
        mock_get.side_effect = Exception("Connection refused")

        result = self.plugin.initialize()

        assert result is True  # Should still initialize without AI
        mock_get.assert_called_once()

    def test_check_system_state_ready(self):
        """Test system state check when ready"""
        state = self.plugin.check_system_state(self.context)

        # Should be needs_changes because we have logs to analyze
        assert state.state_data["status"] == "needs_changes"

    def test_check_system_state_no_logs(self):
        """Test system state check with no logs"""
        # Remove log file
        self.sample_log_file.unlink()

        state = self.plugin.check_system_state(self.context)

        assert state.state_data["status"] == "ready"

    def test_check_system_state_invalid_directory(self):
        """Test system state check with invalid log directory"""
        # Set invalid log directory
        self.plugin.log_directory = "/nonexistent/directory"

        state = self.plugin.check_system_state(self.context)

        assert state.state_data["status"] == "needs_configuration"

    def test_is_idempotent(self):
        """Test plugin idempotency"""
        assert self.plugin.is_idempotent() is True

    def test_find_deployment_logs(self):
        """Test finding deployment logs"""
        logs = self.plugin._find_deployment_logs()

        assert len(logs) == 1
        assert logs[0].name == "qubinode_deployment.log"

    def test_find_deployment_logs_multiple_patterns(self):
        """Test finding logs with multiple patterns"""
        # Create additional log files
        (Path(self.temp_log_dir) / "ansible.log").touch()
        (Path(self.temp_log_dir) / "other_deployment.log").touch()

        logs = self.plugin._find_deployment_logs()

        assert len(logs) >= 2
        log_names = [log.name for log in logs]
        assert "qubinode_deployment.log" in log_names
        assert "ansible.log" in log_names

    @mock.patch("core.log_analyzer.LogAnalyzer.analyze_log_file")
    def test_analyze_specific_log_success(self, mock_analyze):
        """Test analyzing specific log file"""
        # Mock successful analysis
        mock_analyze.return_value = {
            "session_summary": {"session_id": "test123"},
            "error_analysis": {"patterns_identified": 1},
        }

        result = self.plugin.analyze_specific_log(str(self.sample_log_file))

        assert "session_summary" in result
        assert result["session_summary"]["session_id"] == "test123"
        mock_analyze.assert_called_once()

    @mock.patch("core.log_analyzer.LogAnalyzer.analyze_log_file")
    def test_analyze_specific_log_failure(self, mock_analyze):
        """Test analyzing specific log file with failure"""
        # Mock analysis failure
        mock_analyze.side_effect = Exception("Analysis failed")

        result = self.plugin.analyze_specific_log(str(self.sample_log_file))

        assert "error" in result
        assert "Analysis failed" in result["error"]

    def test_get_error_patterns(self):
        """Test getting error patterns"""
        patterns = self.plugin.get_error_patterns()

        assert isinstance(patterns, dict)
        assert len(patterns) > 0

        # Check pattern structure
        for pattern_id, pattern_data in patterns.items():
            assert "description" in pattern_data
            assert "severity" in pattern_data
            assert "error_type" in pattern_data
            assert "frequency" in pattern_data

    def test_get_status(self):
        """Test getting plugin status"""
        status = self.plugin.get_status()

        assert status["plugin_name"] == "LogAnalysisPlugin"
        assert status["version"] == "1.0.0"
        assert status["status"] == "active"
        assert status["ai_assistant_url"] == "http://test:8080"
        assert status["error_patterns_loaded"] > 0

    @mock.patch("core.log_analyzer.LogAnalyzer.analyze_log_file")
    async def test_analyze_log_file_success(self, mock_analyze):
        """Test analyzing log file with success"""
        # Mock successful analysis
        mock_analyze.return_value = {
            "session_summary": {"session_id": "test123"},
            "error_analysis": {"patterns_identified": 1},
        }

        result = await self.plugin._analyze_log_file(self.sample_log_file)

        assert result is not None
        assert "session_summary" in result
        assert "file_metadata" in result

        # Check file metadata
        metadata = result["file_metadata"]
        assert metadata["file_path"] == str(self.sample_log_file)
        assert "file_size" in metadata
        assert "modification_time" in metadata
        assert "analysis_time" in metadata

    @mock.patch("core.log_analyzer.LogAnalyzer.analyze_log_file")
    async def test_analyze_log_file_failure(self, mock_analyze):
        """Test analyzing log file with failure"""
        # Mock analysis failure
        mock_analyze.return_value = {"error": "Analysis failed"}

        result = await self.plugin._analyze_log_file(self.sample_log_file)

        assert result is None

    def test_generate_summary_report(self):
        """Test generating summary report"""
        # Sample analysis results
        analysis_results = [
            {
                "session_summary": {
                    "session_id": "test1",
                    "playbook": "site.yml",
                    "failed_tasks": 2,
                    "performance_metrics": {"failure_rate": 20.0},
                },
                "error_analysis": {
                    "pattern_details": [
                        {
                            "pattern_id": "virtualization_disabled",
                            "severity": "critical",
                        },
                        {"pattern_id": "kcli_install_failure", "severity": "high"},
                    ]
                },
                "recommendations": [
                    {"error_pattern_id": "virtualization_disabled"},
                    {"error_pattern_id": "kcli_install_failure"},
                ],
                "file_metadata": {"file_path": "/tmp/test1.log"},
            },
            {
                "session_summary": {
                    "session_id": "test2",
                    "playbook": "deploy.yml",
                    "failed_tasks": 1,
                    "performance_metrics": {"failure_rate": 10.0},
                },
                "error_analysis": {
                    "pattern_details": [
                        {
                            "pattern_id": "virtualization_disabled",
                            "severity": "critical",
                        }
                    ]
                },
                "recommendations": [{"error_pattern_id": "virtualization_disabled"}],
                "file_metadata": {"file_path": "/tmp/test2.log"},
            },
        ]

        summary = self.plugin._generate_summary_report(analysis_results)

        assert summary["total_files_analyzed"] == 2
        assert summary["total_errors"] == 3  # 2 + 1
        assert summary["critical_issues"] == 2  # Both have critical virtualization issue
        assert summary["high_priority_issues"] == 1  # One kcli issue

        # Check pattern frequency
        assert summary["pattern_frequency"]["virtualization_disabled"] == 2
        assert summary["pattern_frequency"]["kcli_install_failure"] == 1

        # Check deployment sessions
        assert len(summary["deployment_sessions"]) == 2
        assert summary["deployment_sessions"][0]["session_id"] == "test1"
        assert summary["deployment_sessions"][1]["session_id"] == "test2"

    def test_extract_common_recommendations(self):
        """Test extracting common recommendations"""
        analysis_results = [
            {
                "recommendations": [
                    {"error_pattern_id": "virtualization_disabled"},
                    {"error_pattern_id": "kcli_install_failure"},
                ]
            },
            {
                "recommendations": [
                    {"error_pattern_id": "virtualization_disabled"},
                    {"error_pattern_id": "firewall_service_down"},
                ]
            },
        ]

        common_recs = self.plugin._extract_common_recommendations(analysis_results)

        assert len(common_recs) > 0
        # virtualization_disabled should be most common (appears twice)
        assert any("Hardware virtualization" in rec for rec in common_recs)

    @mock.patch("core.log_analyzer.LogAnalyzer.analyze_log_file")
    def test_apply_changes_success(self, mock_analyze):
        """Test applying changes successfully"""
        # Mock successful analysis
        mock_analyze.return_value = {
            "session_summary": {
                "session_id": "test123",
                "failed_tasks": 1,
                "performance_metrics": {"failure_rate": 10.0},
            },
            "error_analysis": {
                "patterns_identified": 1,
                "pattern_details": [{"pattern_id": "virtualization_disabled", "severity": "critical"}],
            },
            "recommendations": [{"error_pattern_id": "virtualization_disabled"}],
        }

        current_state = SystemState({"status": "needs_changes"})
        desired_state = SystemState({"status": "ready"})
        result = self.plugin.apply_changes(current_state, desired_state, self.context)

        assert result.changed is True
        assert result.data["analyzed_files"] == 1
        assert "report_path" in result.data

        # Check that summary report was created
        report_files = list(Path(self.temp_report_dir).glob("summary_report_*.json"))
        assert len(report_files) > 0

    def test_apply_changes_no_logs(self):
        """Test applying changes with no logs"""
        # Remove log file
        self.sample_log_file.unlink()

        current_state = SystemState({"status": "ready"})
        desired_state = SystemState({"status": "ready"})
        result = self.plugin.apply_changes(current_state, desired_state, self.context)

        assert result.changed is False
        assert result.data["analyzed_files"] == 0

    @mock.patch("core.log_analyzer.LogAnalyzer.analyze_log_file")
    def test_apply_changes_analysis_failure(self, mock_analyze):
        """Test applying changes with analysis failure"""
        # Mock analysis failure
        mock_analyze.side_effect = Exception("Analysis failed")

        current_state = SystemState({"status": "needs_changes"})
        desired_state = SystemState({"status": "ready"})
        result = self.plugin.apply_changes(current_state, desired_state, self.context)

        assert result.changed is False
        assert result.status == PluginStatus.FAILED
        assert "Analysis failed" in result.message

    def test_cleanup_success(self):
        """Test successful cleanup"""
        # Create some old report files
        for i in range(15):  # More than the 10 file limit
            report_file = Path(self.temp_report_dir) / f"analysis_old_{i}.json"
            report_file.write_text('{"test": "data"}')
            # Set different modification times
            os.utime(report_file, (1000 + i, 1000 + i))

        result = self.plugin.cleanup()

        assert result is True

        # Check that old files were removed (should keep only 10 newest)
        remaining_files = list(Path(self.temp_report_dir).glob("analysis_*.json"))
        assert len(remaining_files) <= 10

    def test_cleanup_failure(self):
        """Test cleanup with permission errors"""
        # Mock permission error
        with mock.patch("pathlib.Path.unlink", side_effect=PermissionError("Permission denied")):
            # Create a report file
            report_file = Path(self.temp_report_dir) / "analysis_test.json"
            report_file.write_text('{"test": "data"}')

            result = self.plugin.cleanup()

            # Should still return True even with permission errors
            assert result is True

    def test_save_summary_report(self):
        """Test saving summary report"""
        summary_data = {
            "total_files_analyzed": 2,
            "total_errors": 3,
            "critical_issues": 1,
        }

        report_path = self.plugin._save_summary_report(summary_data)

        assert report_path.exists()
        assert report_path.name.startswith("summary_report_")
        assert report_path.suffix == ".json"

        # Verify content
        with open(report_path, "r") as f:
            saved_data = json.load(f)

        assert saved_data["total_files_analyzed"] == 2
        assert saved_data["total_errors"] == 3
        assert saved_data["critical_issues"] == 1


class TestLogAnalysisPluginIntegration:
    """Integration tests for log analysis plugin"""

    @pytest.mark.integration
    def test_full_plugin_workflow(self):
        """Test complete plugin workflow"""
        # This would require actual log files and plugin manager
        # Placeholder for integration testing
        pass

    @pytest.mark.integration
    def test_plugin_manager_integration(self):
        """Test integration with plugin manager"""
        # This would require plugin manager setup
        # Placeholder for integration testing
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
