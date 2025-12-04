"""
Unit tests for ConfigManager

Tests configuration loading, validation, and environment override functionality
as defined in ADR-0028.
"""

import unittest
import tempfile
import shutil
import os
import sys
import json
import yaml
from pathlib import Path
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.yml")
        self.config_manager = ConfigManager(config_file=self.config_file)

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test ConfigManager initialization"""
        self.assertEqual(self.config_manager.config_file, self.config_file)
        self.assertFalse(self.config_manager._loaded)
        self.assertEqual(self.config_manager._config, {})

    def test_load_config_yaml_success(self):
        """Test successful YAML config loading"""
        config_data = {
            "plugins": {"rhel9_plugin": {"enabled": True, "priority": 10}},
            "system": {"log_level": "INFO"},
        }

        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        result = self.config_manager.load_config()
        self.assertTrue(result)
        self.assertTrue(self.config_manager._loaded)
        self.assertEqual(self.config_manager._config["plugins"]["rhel9_plugin"]["enabled"], True)
        self.assertEqual(self.config_manager._config["system"]["log_level"], "INFO")

    def test_load_config_json_success(self):
        """Test successful JSON config loading"""
        config_data = {"plugins": {"rhel9_plugin": {"enabled": True, "priority": 10}}}

        json_config_file = os.path.join(self.temp_dir, "test_config.json")
        config_manager = ConfigManager(config_file=json_config_file)

        with open(json_config_file, "w") as f:
            json.dump(config_data, f)

        result = config_manager.load_config()
        self.assertTrue(result)
        self.assertTrue(config_manager._loaded)
        self.assertEqual(config_manager._config["plugins"]["rhel9_plugin"]["enabled"], True)

    def test_load_config_file_not_found(self):
        """Test loading config when file doesn't exist"""
        nonexistent_file = os.path.join(self.temp_dir, "nonexistent.yml")
        config_manager = ConfigManager(config_file=nonexistent_file)

        result = config_manager.load_config()
        self.assertTrue(result)  # Should succeed with default config
        self.assertTrue(config_manager._loaded)
        # Should have default config structure
        self.assertIn("plugins", config_manager._config)
        self.assertIn("global", config_manager._config)

    def test_load_config_invalid_yaml(self):
        """Test loading invalid YAML config"""
        with open(self.config_file, "w") as f:
            f.write("invalid: yaml: content: [")

        result = self.config_manager.load_config()
        self.assertFalse(result)
        self.assertFalse(self.config_manager._loaded)

    def test_get_plugin_config_exists(self):
        """Test getting existing plugin configuration"""
        config_data = {
            "plugins": {
                "rhel9_plugin": {
                    "enabled": True,
                    "priority": 10,
                    "settings": {"package_manager": "dnf"},
                }
            }
        }

        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        self.config_manager.load_config()

        plugin_config = self.config_manager.get_plugin_config("rhel9_plugin")
        self.assertIsNotNone(plugin_config)
        self.assertTrue(plugin_config["enabled"])
        self.assertEqual(plugin_config["priority"], 10)
        self.assertEqual(plugin_config["settings"]["package_manager"], "dnf")

    def test_get_plugin_config_not_exists(self):
        """Test getting non-existent plugin configuration"""
        self.config_manager.load_config()

        plugin_config = self.config_manager.get_plugin_config("nonexistent_plugin")
        self.assertEqual(plugin_config, {})

    def test_get_global_config(self):
        """Test getting global configuration"""
        config_data = {
            "global": {
                "log_level": "DEBUG",
                "plugin_directories": ["plugins", "custom_plugins"],
                "execution_timeout": 300,
            }
        }

        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        self.config_manager.load_config()

        global_config = self.config_manager.get_global_config()
        self.assertEqual(global_config["log_level"], "DEBUG")
        self.assertEqual(global_config["plugin_directories"], ["plugins", "custom_plugins"])
        self.assertEqual(global_config["execution_timeout"], 300)

    def test_set_plugin_config(self):
        """Test setting plugin configuration"""
        self.config_manager.load_config()

        new_config = {"enabled": False, "priority": 20, "custom_setting": "test_value"}

        self.config_manager.set_plugin_config("test_plugin", new_config)

        retrieved_config = self.config_manager.get_plugin_config("test_plugin")
        self.assertEqual(retrieved_config, new_config)

    def test_get_set_config_by_key_path(self):
        """Test getting and setting configuration by key path"""
        config_data = {"plugins": {"rhel9_plugin": {"enabled": True, "priority": 10}}}

        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        self.config_manager.load_config()

        # Test get by key path
        enabled = self.config_manager.get("plugins.rhel9_plugin.enabled")
        self.assertTrue(enabled)

        priority = self.config_manager.get("plugins.rhel9_plugin.priority")
        self.assertEqual(priority, 10)

        # Test set by key path
        self.config_manager.set("plugins.rhel9_plugin.new_setting", "new_value")
        new_setting = self.config_manager.get("plugins.rhel9_plugin.new_setting")
        self.assertEqual(new_setting, "new_value")

    def test_save_config_yaml(self):
        """Test saving configuration to YAML file"""
        self.config_manager.load_config()

        self.config_manager.set_plugin_config("test_plugin", {"enabled": True})

        result = self.config_manager.save_config()
        self.assertTrue(result)

        # Verify file was written
        self.assertTrue(os.path.exists(self.config_file))

        # Verify content
        with open(self.config_file, "r") as f:
            saved_data = yaml.safe_load(f)

        self.assertEqual(saved_data["plugins"]["test_plugin"]["enabled"], True)

    def test_save_config_json(self):
        """Test saving configuration to JSON file"""
        json_config_file = os.path.join(self.temp_dir, "test_config.json")
        config_manager = ConfigManager(config_file=json_config_file)

        config_manager.load_config()
        config_manager.set_plugin_config("test_plugin", {"enabled": True})

        result = config_manager.save_config()
        self.assertTrue(result)

        # Verify file was written
        self.assertTrue(os.path.exists(json_config_file))

        # Verify content
        with open(json_config_file, "r") as f:
            saved_data = json.load(f)

        self.assertEqual(saved_data["plugins"]["test_plugin"]["enabled"], True)

    def test_environment_overrides(self):
        """Test environment variable overrides"""
        config_data = {
            "plugins": {"rhel9_plugin": {"enabled": True, "priority": 10}},
            "global": {"log_level": "INFO"},
        }

        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        # Set environment variables
        with patch.dict(
            os.environ,
            {
                "QUBINODE_CONFIG_PLUGINS.RHEL9_PLUGIN.ENABLED": "false",
                "QUBINODE_CONFIG_GLOBAL.LOG_LEVEL": "DEBUG",
            },
        ):
            self.config_manager.load_config()

            # Check overrides were applied
            enabled = self.config_manager.get("plugins.rhel9_plugin.enabled")
            self.assertFalse(enabled)  # Overridden to false

            priority = self.config_manager.get("plugins.rhel9_plugin.priority")
            self.assertEqual(priority, 10)  # Not overridden

            log_level = self.config_manager.get("global.log_level")
            self.assertEqual(log_level, "DEBUG")  # Overridden

    def test_validate_config_valid(self):
        """Test configuration validation with valid config"""
        config_data = {
            "plugins": {"rhel9_plugin": {"enabled": True, "priority": 10}},
            "system": {"log_level": "INFO", "max_concurrent_plugins": 5},
        }

        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        self.config_manager.load_config()

        errors = self.config_manager.validate_config()
        self.assertEqual(len(errors), 0)

    def test_validate_config_invalid(self):
        """Test configuration validation with invalid config"""
        config_data = {
            "plugins": {
                "rhel9_plugin": {
                    "enabled": "not_a_boolean",  # Invalid type
                    "priority": "not_a_number",  # Invalid type
                }
            },
            "system": {
                "log_level": "INVALID_LEVEL"  # Invalid value
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        self.config_manager.load_config()

        errors = self.config_manager.validate_config()
        self.assertGreater(len(errors), 0)

    def test_get_default_config(self):
        """Test default configuration generation"""
        default_config = self.config_manager._get_default_config()

        # Verify default structure
        self.assertIn("plugins", default_config)
        self.assertIn("global", default_config)
        self.assertIn("log_level", default_config["global"])
        self.assertIn("plugin_directories", default_config["global"])
        self.assertIn("execution_timeout", default_config["global"])

    def test_plugin_enable_disable(self):
        """Test plugin enable/disable functionality"""
        self.config_manager.load_config()

        # Test enabling a plugin
        self.config_manager.enable_plugin("test_plugin")
        self.assertTrue(self.config_manager.is_plugin_enabled("test_plugin"))

        # Test disabling a plugin
        self.config_manager.disable_plugin("test_plugin")
        self.assertFalse(self.config_manager.is_plugin_enabled("test_plugin"))


if __name__ == "__main__":
    unittest.main()
