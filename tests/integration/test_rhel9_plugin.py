"""
Integration tests for RHEL9Plugin

Tests the complete RHEL 9 plugin functionality including system interaction,
package management, and idempotent behavior as defined in ADR-0028.
"""

import unittest
import tempfile
import shutil
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from plugins.os.rhel9_plugin import RHEL9Plugin
from core.base_plugin import PluginResult, ExecutionContext, SystemState, PluginStatus


class TestRHEL9PluginIntegration(unittest.TestCase):
    """Integration test cases for RHEL9Plugin"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

        # Mock configuration
        self.mock_config = {
            "packages": [
                "bzip2-devel",
                "libffi-devel",
                "wget",
                "vim",
                "podman",
                "ncurses-devel",
                "sqlite-devel",
                "firewalld",
                "make",
                "gcc",
            ],
            "services": ["firewalld", "podman"],
            "repositories": ["epel-release"],
            "python_packages": ["ansible", "requests"],
        }

        # Create execution context
        self.context = ExecutionContext(
            inventory="localhost",
            config=self.mock_config,
            dry_run=True,  # Use dry run for most tests
        )

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("os.path.exists")
    def test_plugin_initialization_rhel9(self, mock_exists, mock_file):
        """Test plugin initialization on RHEL 9 system"""
        mock_exists.return_value = True

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        self.assertEqual(plugin.name, "rhel9_plugin")
        self.assertEqual(plugin.version, "1.0.0")
        self.assertIn("bzip2-devel", plugin.packages)

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='ID="ubuntu"\nVERSION_ID="20.04"',
    )
    def test_plugin_initialization_non_rhel9(self, mock_file):
        """Test plugin initialization on non-RHEL 9 system"""
        plugin = RHEL9Plugin()

        with self.assertRaises(RuntimeError):
            plugin.configure(self.mock_config)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("subprocess.run")
    def test_check_state_packages_installed(self, mock_run, mock_file):
        """Test system state check with packages installed"""
        # Mock rpm command to return installed packages
        mock_run.return_value = Mock(
            returncode=0,
            stdout="bzip2-devel-1.0.8-8.el9.x86_64\nlibffi-devel-3.4.2-8.el9.x86_64\n",
        )

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        state = plugin.check_state()

        self.assertIsInstance(state, SystemState)
        self.assertIn("packages_installed", state.data)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("subprocess.run")
    def test_validate_environment_success(self, mock_run, mock_file):
        """Test successful environment validation"""
        # Mock successful commands
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        result = plugin.validate_environment(self.context)

        self.assertIsInstance(result, PluginResult)
        self.assertTrue(result.success)
        self.assertEqual(result.status, PluginStatus.SUCCESS)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("subprocess.run")
    def test_validate_environment_failure(self, mock_run, mock_file):
        """Test environment validation failure"""
        # Mock failed command
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="Package not found"
        )

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        result = plugin.validate_environment(self.context)

        self.assertIsInstance(result, PluginResult)
        self.assertFalse(result.success)
        self.assertEqual(result.status, PluginStatus.FAILED)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("subprocess.run")
    def test_execute_dry_run(self, mock_run, mock_file):
        """Test plugin execution in dry run mode"""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        # Use dry run context
        dry_run_context = ExecutionContext(
            inventory="localhost", config=self.mock_config, dry_run=True
        )

        result = plugin.execute(dry_run_context)

        self.assertIsInstance(result, PluginResult)
        self.assertTrue(result.success)
        self.assertEqual(result.status, PluginStatus.SUCCESS)
        self.assertIn("dry run", result.message.lower())

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("subprocess.run")
    def test_execute_actual_run(self, mock_run, mock_file):
        """Test plugin execution in actual run mode"""
        # Mock successful package installation
        mock_run.return_value = Mock(returncode=0, stdout="Complete!", stderr="")

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        # Use actual run context
        actual_context = ExecutionContext(
            inventory="localhost", config=self.mock_config, dry_run=False
        )

        result = plugin.execute(actual_context)

        self.assertIsInstance(result, PluginResult)
        self.assertTrue(result.success)
        self.assertEqual(result.status, PluginStatus.SUCCESS)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("subprocess.run")
    def test_idempotent_behavior(self, mock_run, mock_file):
        """Test idempotent behavior - running twice should be safe"""
        # First run - packages not installed
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr="package not installed"),  # check
            Mock(returncode=0, stdout="Complete!", stderr=""),  # install
        ]

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        # First execution
        result1 = plugin.execute(self.context)
        self.assertTrue(result1.success)

        # Second run - packages already installed
        mock_run.side_effect = [
            Mock(returncode=0, stdout="package already installed", stderr=""),  # check
        ]

        # Second execution should be idempotent
        result2 = plugin.execute(self.context)
        self.assertTrue(result2.success)
        self.assertEqual(result2.status, PluginStatus.SUCCESS)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("subprocess.run")
    def test_package_installation_failure(self, mock_run, mock_file):
        """Test handling of package installation failure"""
        # Mock failed package installation
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="No package nonexistent-package available"
        )

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        result = plugin.execute(self.context)

        self.assertIsInstance(result, PluginResult)
        self.assertFalse(result.success)
        self.assertEqual(result.status, PluginStatus.FAILED)
        self.assertIn("package", result.message.lower())

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("subprocess.run")
    def test_service_management(self, mock_run, mock_file):
        """Test service management functionality"""
        # Mock systemctl commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # enable firewalld
            Mock(returncode=0, stdout="", stderr=""),  # start firewalld
            Mock(returncode=0, stdout="", stderr=""),  # enable podman
            Mock(returncode=0, stdout="", stderr=""),  # start podman
        ]

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        result = plugin.execute(self.context)

        self.assertTrue(result.success)
        # Verify systemctl commands were called
        self.assertGreater(mock_run.call_count, 0)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("subprocess.run")
    def test_repository_management(self, mock_run, mock_file):
        """Test repository management functionality"""
        # Mock dnf commands for repository management
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # install epel-release
            Mock(returncode=0, stdout="", stderr=""),  # update package cache
        ]

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        result = plugin.execute(self.context)

        self.assertTrue(result.success)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("subprocess.run")
    def test_python_package_installation(self, mock_run, mock_file):
        """Test Python package installation via pip"""
        # Mock pip commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # pip install ansible
            Mock(returncode=0, stdout="", stderr=""),  # pip install requests
        ]

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        result = plugin.execute(self.context)

        self.assertTrue(result.success)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("subprocess.run")
    def test_cleanup_functionality(self, mock_run, mock_file):
        """Test cleanup functionality"""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        # Test cleanup
        result = plugin.cleanup()

        self.assertIsInstance(result, PluginResult)
        self.assertTrue(result.success)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    def test_configuration_validation(self, mock_file):
        """Test configuration validation"""
        plugin = RHEL9Plugin()

        # Test valid configuration
        valid_config = {
            "packages": ["vim", "git"],
            "services": ["firewalld"],
            "repositories": ["epel-release"],
        }

        plugin.configure(valid_config)
        self.assertEqual(plugin.packages, ["vim", "git"])

        # Test invalid configuration
        invalid_config = {
            "packages": "not_a_list",  # Should be a list
            "services": ["firewalld"],
        }

        with self.assertRaises((TypeError, ValueError)):
            plugin.configure(invalid_config)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("subprocess.run")
    def test_error_handling_and_recovery(self, mock_run, mock_file):
        """Test error handling and recovery mechanisms"""
        # Simulate transient failure followed by success
        mock_run.side_effect = [
            Mock(
                returncode=1, stdout="", stderr="Temporary failure"
            ),  # First attempt fails
            Mock(returncode=0, stdout="Success", stderr=""),  # Retry succeeds
        ]

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        result = plugin.execute(self.context)

        # Plugin should handle the error gracefully
        self.assertIsInstance(result, PluginResult)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("subprocess.run")
    def test_logging_and_monitoring(self, mock_run, mock_file):
        """Test logging and monitoring functionality"""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        with patch.object(plugin.logger, "info") as mock_log_info:
            with patch.object(plugin.logger, "error") as mock_log_error:
                result = plugin.execute(self.context)

                # Verify logging occurred
                self.assertGreater(mock_log_info.call_count, 0)

                # No errors should be logged for successful execution
                self.assertEqual(mock_log_error.call_count, 0)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    def test_plugin_metadata(self, mock_file):
        """Test plugin metadata and information"""
        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        # Check plugin metadata
        self.assertEqual(plugin.name, "rhel9_plugin")
        self.assertEqual(plugin.version, "1.0.0")
        self.assertIsInstance(plugin.dependencies, list)
        self.assertIsInstance(plugin.description, str)

    @patch(
        "builtins.open", new_callable=mock_open, read_data='ID="rhel"\nVERSION_ID="9.2"'
    )
    @patch("subprocess.run")
    def test_integration_with_event_system(self, mock_run, mock_file):
        """Test integration with the event system"""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        plugin = RHEL9Plugin()
        plugin.configure(self.mock_config)

        # Mock event system
        mock_event_system = Mock()
        plugin.event_system = mock_event_system

        result = plugin.execute(self.context)

        # Verify events were emitted (if plugin supports it)
        # This depends on the actual plugin implementation
        self.assertTrue(result.success)


class TestRHEL9PluginSystemIntegration(unittest.TestCase):
    """System-level integration tests for RHEL9Plugin"""

    @unittest.skipUnless(
        os.path.exists("/etc/os-release")
        and "rhel" in open("/etc/os-release").read().lower(),
        "RHEL system required for system integration tests",
    )
    def test_real_system_validation(self):
        """Test plugin on real RHEL system (if available)"""
        plugin = RHEL9Plugin()

        # Use minimal configuration for real system test
        minimal_config = {
            "packages": ["vim"],  # Safe package that should be available
            "services": [],
            "repositories": [],
        }

        plugin.configure(minimal_config)

        # Test validation only (no actual changes)
        context = ExecutionContext(
            inventory="localhost", config=minimal_config, dry_run=True
        )

        result = plugin.validate_environment(context)
        self.assertIsInstance(result, PluginResult)


if __name__ == "__main__":
    unittest.main()
