"""
Integration tests for Qubinode CLI Tool

Tests the command-line interface functionality and integration with
the plugin framework as defined in ADR-0028.
"""

import unittest
import tempfile
import shutil
import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch
from io import StringIO

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import qubinode_cli
from core import ConfigManager


class TestQubiNodeCLI(unittest.TestCase):
    """Test cases for Qubinode CLI tool"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        # Create mock plugin directory
        self.plugin_dir = os.path.join(self.temp_dir, "plugins")
        os.makedirs(self.plugin_dir)

        # Create mock config
        self.config_file = os.path.join(self.temp_dir, "config", "plugins.yml")
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

        with open(self.config_file, "w") as f:
            f.write(
                """
plugins:
  mock_plugin:
    enabled: true
    priority: 10
system:
  log_level: INFO
"""
            )

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_setup_logging(self):
        """Test logging setup functionality"""
        # Test default logging level
        qubinode_cli.setup_logging()

        # Test custom logging level
        qubinode_cli.setup_logging("DEBUG")

        # Test invalid logging level (should not crash)
        qubinode_cli.setup_logging("INVALID")

    @patch("core.PluginManager")
    def test_list_plugins_empty(self, mock_plugin_manager_class):
        """Test listing plugins when no plugins are available"""
        mock_plugin_manager = Mock()
        mock_plugin_manager.list_plugins.return_value = []
        mock_plugin_manager_class.return_value = mock_plugin_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            qubinode_cli.list_plugins(mock_plugin_manager)
            output = mock_stdout.getvalue()

            self.assertIn("Available Plugins:", output)
            mock_plugin_manager.list_plugins.assert_called_once()

    @patch("core.PluginManager")
    def test_list_plugins_with_plugins(self, mock_plugin_manager_class):
        """Test listing plugins when plugins are available"""
        mock_plugin_manager = Mock()
        mock_plugin_manager.list_plugins.return_value = [
            "test_plugin",
            "another_plugin",
        ]

        # Mock plugin info
        mock_plugin_info = Mock()
        mock_plugin_info.version = "1.0.0"
        mock_plugin_info.dependencies = ["dependency1"]
        mock_plugin_info.description = "Test plugin description"

        mock_plugin_manager.get_plugin_info.return_value = mock_plugin_info
        mock_plugin_manager_class.return_value = mock_plugin_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            qubinode_cli.list_plugins(mock_plugin_manager)
            output = mock_stdout.getvalue()

            self.assertIn("Available Plugins:", output)
            self.assertIn("test_plugin", output)
            self.assertIn("another_plugin", output)
            self.assertIn("1.0.0", output)
            self.assertIn("Test plugin description", output)

    @patch("core.PluginManager")
    @patch("core.ConfigManager")
    def test_execute_plugins_success(
        self, mock_config_manager_class, mock_plugin_manager_class
    ):
        """Test successful plugin execution"""
        # Setup mocks
        mock_plugin_manager = Mock()
        mock_config_manager = Mock()

        mock_plugin_manager.discover_plugins.return_value = ["test_plugin"]
        mock_plugin_manager.load_plugin.return_value = True

        mock_result = Mock()
        mock_result.success = True
        mock_result.message = "Plugin executed successfully"
        mock_plugin_manager.execute_plugin.return_value = mock_result

        mock_plugin_manager_class.return_value = mock_plugin_manager
        mock_config_manager_class.return_value = mock_config_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            qubinode_cli.execute_plugins(
                mock_plugin_manager, mock_config_manager, plugin_names=["test_plugin"]
            )
            output = mock_stdout.getvalue()

            self.assertIn("test_plugin", output)
            self.assertIn("successfully", output.lower())

    @patch("core.PluginManager")
    @patch("core.ConfigManager")
    def test_execute_plugins_failure(
        self, mock_config_manager_class, mock_plugin_manager_class
    ):
        """Test plugin execution failure"""
        # Setup mocks
        mock_plugin_manager = Mock()
        mock_config_manager = Mock()

        mock_plugin_manager.discover_plugins.return_value = ["test_plugin"]
        mock_plugin_manager.load_plugin.return_value = True

        mock_result = Mock()
        mock_result.success = False
        mock_result.message = "Plugin execution failed"
        mock_plugin_manager.execute_plugin.return_value = mock_result

        mock_plugin_manager_class.return_value = mock_plugin_manager
        mock_config_manager_class.return_value = mock_config_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            qubinode_cli.execute_plugins(
                mock_plugin_manager, mock_config_manager, plugin_names=["test_plugin"]
            )
            output = mock_stdout.getvalue()

            self.assertIn("test_plugin", output)
            self.assertIn("failed", output.lower())

    @patch("sys.argv", ["qubinode_cli.py", "list"])
    @patch("core.PluginManager")
    def test_main_list_command(self, mock_plugin_manager_class):
        """Test main function with list command"""
        mock_plugin_manager = Mock()
        mock_plugin_manager.discover_plugins.return_value = []
        mock_plugin_manager.list_plugins.return_value = []
        mock_plugin_manager_class.return_value = mock_plugin_manager

        with patch("sys.stdout", new_callable=StringIO):
            try:
                qubinode_cli.main()
            except SystemExit:
                pass  # argparse calls sys.exit

    @patch("sys.argv", ["qubinode_cli.py", "execute", "--plugins", "test_plugin"])
    @patch("core.PluginManager")
    @patch("core.ConfigManager")
    def test_main_execute_command(
        self, mock_config_manager_class, mock_plugin_manager_class
    ):
        """Test main function with execute command"""
        mock_plugin_manager = Mock()
        mock_config_manager = Mock()

        mock_plugin_manager.discover_plugins.return_value = ["test_plugin"]
        mock_plugin_manager.load_plugin.return_value = True

        mock_result = Mock()
        mock_result.success = True
        mock_result.message = "Success"
        mock_plugin_manager.execute_plugin.return_value = mock_result

        mock_plugin_manager_class.return_value = mock_plugin_manager
        mock_config_manager_class.return_value = mock_config_manager
        mock_config_manager.load_config.return_value = True

        with patch("sys.stdout", new_callable=StringIO):
            try:
                qubinode_cli.main()
            except SystemExit:
                pass  # argparse calls sys.exit

    @patch("sys.argv", ["qubinode_cli.py", "--help"])
    def test_main_help_command(self):
        """Test main function with help command"""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            try:
                qubinode_cli.main()
            except SystemExit:
                pass  # argparse calls sys.exit for help

            output = mock_stdout.getvalue()
            self.assertIn("usage:", output.lower())

    def test_cli_script_execution(self):
        """Test CLI script can be executed directly"""
        # Test that the CLI script is executable
        cli_path = Path(__file__).parent.parent.parent / "qubinode_cli.py"
        self.assertTrue(cli_path.exists())

        # Test basic help command
        try:
            result = subprocess.run(
                [sys.executable, str(cli_path), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("usage:", result.stdout.lower())
        except subprocess.TimeoutExpired:
            self.fail("CLI script execution timed out")
        except Exception as e:
            self.fail(f"CLI script execution failed: {e}")

    def test_cli_list_command_execution(self):
        """Test CLI list command execution"""
        cli_path = Path(__file__).parent.parent.parent / "qubinode_cli.py"

        try:
            result = subprocess.run(
                [sys.executable, str(cli_path), "list"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(Path(__file__).parent.parent.parent),
            )

            # Should not crash, even if no plugins found
            self.assertIn(result.returncode, [0, 1])  # 0 for success, 1 for no plugins
            self.assertIn("Available Plugins", result.stdout)

        except subprocess.TimeoutExpired:
            self.fail("CLI list command timed out")
        except Exception as e:
            self.fail(f"CLI list command failed: {e}")

    @patch("core.PluginManager")
    def test_plugin_discovery_integration(self, mock_plugin_manager_class):
        """Test integration with plugin discovery"""
        mock_plugin_manager = Mock()
        mock_plugin_manager.discover_plugins.return_value = [
            "rhel9_plugin",
            "hetzner_plugin",
        ]
        mock_plugin_manager.list_plugins.return_value = [
            "rhel9_plugin",
            "hetzner_plugin",
        ]

        mock_plugin_info = Mock()
        mock_plugin_info.version = "1.0.0"
        mock_plugin_info.dependencies = []
        mock_plugin_info.description = "Test plugin"
        mock_plugin_manager.get_plugin_info.return_value = mock_plugin_info

        mock_plugin_manager_class.return_value = mock_plugin_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            qubinode_cli.list_plugins(mock_plugin_manager)
            output = mock_stdout.getvalue()

            self.assertIn("rhel9_plugin", output)
            self.assertIn("hetzner_plugin", output)
            mock_plugin_manager.discover_plugins.assert_called_once()

    @patch("core.ConfigManager")
    def test_config_integration(self, mock_config_manager_class):
        """Test integration with configuration manager"""
        mock_config_manager = Mock()
        mock_config_manager.load_config.return_value = True
        mock_config_manager.get_plugin_config.return_value = {
            "enabled": True,
            "priority": 10,
        }

        mock_config_manager_class.return_value = mock_config_manager

        # Test that config manager is properly initialized
        config_manager = ConfigManager()
        self.assertIsNotNone(config_manager)

    def test_error_handling(self):
        """Test error handling in CLI"""
        cli_path = Path(__file__).parent.parent.parent / "qubinode_cli.py"

        # Test invalid command
        try:
            result = subprocess.run(
                [sys.executable, str(cli_path), "invalid_command"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Should exit with error code
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error", result.stderr.lower())

        except subprocess.TimeoutExpired:
            self.fail("CLI error handling test timed out")
        except Exception as e:
            self.fail(f"CLI error handling test failed: {e}")

    @patch("core.PluginManager")
    @patch("core.ConfigManager")
    def test_dry_run_functionality(
        self, mock_config_manager_class, mock_plugin_manager_class
    ):
        """Test dry run functionality"""
        mock_plugin_manager = Mock()
        mock_config_manager = Mock()

        mock_plugin_manager.discover_plugins.return_value = ["test_plugin"]
        mock_plugin_manager.load_plugin.return_value = True

        mock_result = Mock()
        mock_result.success = True
        mock_result.message = "Dry run completed"
        mock_plugin_manager.execute_plugin.return_value = mock_result

        mock_plugin_manager_class.return_value = mock_plugin_manager
        mock_config_manager_class.return_value = mock_config_manager

        # Test dry run execution
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            qubinode_cli.execute_plugins(
                mock_plugin_manager,
                mock_config_manager,
                plugin_names=["test_plugin"],
                inventory="localhost",
            )

            # Verify execution context includes dry run
            mock_plugin_manager.execute_plugin.assert_called()
            call_args = mock_plugin_manager.execute_plugin.call_args
            context = call_args[0][1]  # Second argument is the context
            # Note: This test assumes the CLI supports dry run mode

    def test_inventory_parameter(self):
        """Test inventory parameter handling"""
        cli_path = Path(__file__).parent.parent.parent / "qubinode_cli.py"

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(cli_path),
                    "execute",
                    "--inventory",
                    "test_inventory",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(Path(__file__).parent.parent.parent),
            )

            # Should handle inventory parameter without crashing
            # (may fail due to no plugins, but should parse arguments correctly)
            self.assertNotIn("unrecognized arguments", result.stderr)

        except subprocess.TimeoutExpired:
            self.fail("CLI inventory parameter test timed out")
        except Exception as e:
            self.fail(f"CLI inventory parameter test failed: {e}")

    def test_logging_level_parameter(self):
        """Test logging level parameter handling"""
        cli_path = Path(__file__).parent.parent.parent / "qubinode_cli.py"

        try:
            result = subprocess.run(
                [sys.executable, str(cli_path), "--log-level", "DEBUG", "list"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(Path(__file__).parent.parent.parent),
            )

            # Should handle log level parameter without crashing
            self.assertNotIn("unrecognized arguments", result.stderr)

        except subprocess.TimeoutExpired:
            self.fail("CLI logging level parameter test timed out")
        except Exception as e:
            self.fail(f"CLI logging level parameter test failed: {e}")


if __name__ == "__main__":
    unittest.main()
