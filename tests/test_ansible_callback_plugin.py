"""
Tests for Qubinode Navigator Ansible Callback Plugin

Tests the real-time monitoring callback plugin functionality
including AI Assistant integration and deployment tracking.
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "ansible_plugins" / "callback_plugins"))

# Import the callback plugin
from qubinode_monitoring import CallbackModule


class TestQubiNodeMonitoringCallback:
    """Test cases for Qubinode Navigator monitoring callback plugin"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_log = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        self.temp_log.close()

        # Mock environment variables
        self.env_patcher = patch.dict(
            os.environ,
            {
                "QUBINODE_AI_ASSISTANT_URL": "http://test:8080",
                "QUBINODE_ENABLE_AI_ANALYSIS": "true",
                "QUBINODE_LOG_FILE": self.temp_log.name,
                "QUBINODE_ALERT_THRESHOLD": "2",
            },
        )
        self.env_patcher.start()

        # Create callback instance
        self.callback = CallbackModule()
        self.callback._display = MagicMock()

    def teardown_method(self):
        """Cleanup test environment"""
        self.env_patcher.stop()
        try:
            os.unlink(self.temp_log.name)
        except FileNotFoundError:
            pass

    def test_callback_initialization(self):
        """Test callback plugin initialization"""
        assert self.callback.ai_assistant_url == "http://test:8080"
        assert self.callback.enable_ai_analysis is True
        assert self.callback.log_file == self.temp_log.name
        assert self.callback.alert_threshold == 2
        assert self.callback.failure_count == 0

    def test_log_event_file_writing(self):
        """Test event logging to file"""
        test_data = {"test": "data", "timestamp": "2025-11-08"}

        self.callback._log_event("test_event", test_data)

        # Verify log file content
        with open(self.temp_log.name, "r") as f:
            content = f.read()
            assert "test_event" in content
            assert "test" in content

    @patch("requests.post")
    def test_ai_assistant_integration(self, mock_post):
        """Test AI Assistant integration"""
        # Mock successful AI response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "AI analysis of deployment event",
            "metadata": {"model": "granite-4.0-micro"},
        }
        mock_post.return_value = mock_response

        # Test AI Assistant call
        log_entry = {
            "timestamp": "2025-11-08T10:00:00",
            "event_type": "task_failed",
            "data": {"error": "test error"},
        }

        self.callback._send_to_ai_assistant(log_entry)

        # Verify AI Assistant was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["message"].startswith("Analyze this Qubinode Navigator deployment event")
        assert "deployment_type" in call_args[1]["json"]["context"]

    @patch("requests.post")
    def test_diagnostics_integration(self, mock_post):
        """Test diagnostic tools integration"""
        # Mock diagnostic response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "diagnostics": {"summary": {"successful_tools": 6, "total_tools": 6}},
            "ai_analysis": "System appears healthy with no critical issues detected",
        }
        mock_post.return_value = mock_response

        # Test diagnostics call
        self.callback._run_diagnostics()

        # Verify diagnostics endpoint was called
        mock_post.assert_called_once_with(
            "http://test:8080/diagnostics",
            json={"include_ai_analysis": True},
            timeout=30,
        )

    def test_playbook_start_tracking(self):
        """Test playbook start event tracking"""
        # Mock playbook object
        mock_playbook = MagicMock()
        mock_playbook._file_name = "test_playbook.yml"

        self.callback.v2_playbook_on_start(mock_playbook)

        # Verify tracking
        assert self.callback.deployment_start_time is not None
        self.callback._display.display.assert_called()

    def test_play_start_tracking(self):
        """Test play start event tracking"""
        # Mock play object
        mock_play = MagicMock()
        mock_play.get_name.return_value = "Test Play"
        mock_play.hosts = ["localhost", "testhost"]

        self.callback.v2_playbook_on_play_start(mock_play)

        # Verify tracking
        assert self.callback.current_play == "Test Play"
        self.callback._display.display.assert_called()

    def test_task_start_tracking(self):
        """Test task start event tracking"""
        # Mock task object
        mock_task = MagicMock()
        mock_task.get_name.return_value = "Test Task"

        self.callback.v2_playbook_on_task_start(mock_task, False)

        # Verify tracking
        assert self.callback.current_task == "Test Task"
        assert "Test Task" in self.callback.task_stats
        assert "start_time" in self.callback.task_stats["Test Task"]

    def test_task_success_tracking(self):
        """Test successful task tracking"""
        # Setup task start time
        task_name = "Test Success Task"
        self.callback.task_stats[task_name] = {"start_time": 1000.0}

        # Mock result object
        mock_result = MagicMock()
        mock_result._task.get_name.return_value = task_name
        mock_result._host.get_name.return_value = "localhost"

        with patch("time.time", return_value=1002.0):
            self.callback.v2_runner_on_ok(mock_result)

        # Verify success tracking (no failure count increase)
        assert self.callback.failure_count == 0

    @patch("requests.post")
    def test_task_failure_tracking(self, mock_post):
        """Test task failure tracking and AI integration"""
        # Mock AI response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "AI failure analysis"}
        mock_post.return_value = mock_response

        # Mock failed result
        mock_result = MagicMock()
        mock_result._task.get_name.return_value = "Failed Task"
        mock_result._host.get_name.return_value = "localhost"
        mock_result._result = {
            "msg": "Task failed with error",
            "stderr": "Error details",
        }

        self.callback.v2_runner_on_failed(mock_result)

        # Verify failure tracking
        assert self.callback.failure_count == 1
        self.callback._display.display.assert_called()

    @patch("requests.post")
    def test_alert_threshold_trigger(self, mock_post):
        """Test alert threshold triggering diagnostics"""
        # Mock responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "AI analysis"}
        mock_post.return_value = mock_response

        # Mock failed results to reach threshold
        mock_result = MagicMock()
        mock_result._task.get_name.return_value = "Failed Task"
        mock_result._host.get_name.return_value = "localhost"
        mock_result._result = {"msg": "Error"}

        # Trigger failures to reach threshold (2)
        self.callback.v2_runner_on_failed(mock_result)
        self.callback.v2_runner_on_failed(mock_result)

        # Verify alert threshold was reached and diagnostics called
        assert self.callback.failure_count == 2
        assert mock_post.call_count >= 2  # AI analysis + diagnostics

    def test_unreachable_host_tracking(self):
        """Test unreachable host tracking"""
        # Mock unreachable result
        mock_result = MagicMock()
        mock_result._host.get_name.return_value = "unreachable_host"
        mock_result._result = {"msg": "Host unreachable"}

        self.callback.v2_runner_on_unreachable(mock_result)

        # Verify unreachable tracking
        self.callback._display.display.assert_called()

    @patch("requests.post")
    def test_deployment_completion_summary(self, mock_post):
        """Test deployment completion and summary"""
        # Setup deployment start time
        self.callback.deployment_start_time = 1000.0
        self.callback.failure_count = 1

        # Mock AI response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Final analysis"}
        mock_post.return_value = mock_response

        # Mock stats object
        mock_stats = MagicMock()
        mock_stats.processed = ["localhost"]
        mock_stats.ok = {"localhost": 5}
        mock_stats.changed = {"localhost": 2}
        mock_stats.dark = {"localhost": 0}
        mock_stats.failures = {"localhost": 1}
        mock_stats.skipped = {"localhost": 0}

        with patch("time.time", return_value=1060.0):
            self.callback.v2_playbook_on_stats(mock_stats)

        # Verify completion summary
        self.callback._display.display.assert_called()
        # Should call AI for final analysis due to failures
        mock_post.assert_called()

    def test_performance_monitoring(self):
        """Test performance monitoring for slow tasks"""
        # Setup slow task
        task_name = "Slow Task"
        self.callback.task_stats[task_name] = {"start_time": 1000.0}

        # Mock result for slow task (>60s)
        mock_result = MagicMock()
        mock_result._task.get_name.return_value = task_name
        mock_result._host.get_name.return_value = "localhost"

        with patch("time.time", return_value=1070.0):  # 70 seconds later
            self.callback.v2_runner_on_ok(mock_result)

        # Verify slow task warning was displayed
        display_calls = [call[0][0] for call in self.callback._display.display.call_args_list]
        slow_task_warning = any("Slow task detected" in call for call in display_calls)
        assert slow_task_warning

    def test_configuration_from_environment(self):
        """Test configuration loading from environment variables"""
        with patch.dict(
            os.environ,
            {
                "QUBINODE_AI_ASSISTANT_URL": "http://custom:9090",
                "QUBINODE_ENABLE_AI_ANALYSIS": "false",
                "QUBINODE_ALERT_THRESHOLD": "5",
            },
        ):
            callback = CallbackModule()

            assert callback.ai_assistant_url == "http://custom:9090"
            assert callback.enable_ai_analysis is False
            assert callback.alert_threshold == 5


class TestCallbackPluginIntegration:
    """Integration tests for callback plugin"""

    @pytest.mark.integration
    def test_full_deployment_workflow(self):
        """Test complete deployment workflow simulation"""
        # This would require actual Ansible execution
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
