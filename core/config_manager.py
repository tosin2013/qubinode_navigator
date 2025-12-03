"""
Configuration Manager

Handles plugin configuration and system-wide settings as defined in ADR-0028.
"""

import os
import yaml
import json
from typing import Dict, Any, List
import logging


class ConfigManager:
    """
    Manages configuration for plugins and system components

    Provides centralized configuration management with support for
    multiple formats and environment-specific overrides.
    """

    def __init__(self, config_file: str = "config/plugins.yml"):
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file
        self._config: Dict[str, Any] = {}
        self._loaded = False

    def load_config(self) -> bool:
        """
        Load configuration from file

        Returns:
            bool: True if configuration loaded successfully
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    if self.config_file.endswith(".json"):
                        self._config = json.load(f)
                    else:
                        self._config = yaml.safe_load(f) or {}
            else:
                self.logger.warning(f"Config file not found: {self.config_file}")
                self._config = self._get_default_config()

            self._apply_environment_overrides()
            self._loaded = True
            self.logger.info(f"Configuration loaded from {self.config_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self._config = self._get_default_config()
            return False

    def save_config(self) -> bool:
        """
        Save current configuration to file

        Returns:
            bool: True if configuration saved successfully
        """
        try:
            # Ensure directory exists
            config_dir = os.path.dirname(self.config_file)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)

            with open(self.config_file, "w") as f:
                if self.config_file.endswith(".json"):
                    json.dump(self._config, f, indent=2)
                else:
                    yaml.dump(self._config, f, default_flow_style=False, indent=2)

            self.logger.info(f"Configuration saved to {self.config_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific plugin

        Args:
            plugin_name: Name of the plugin

        Returns:
            Dict[str, Any]: Plugin configuration
        """
        if not self._loaded:
            self.load_config()

        return self._config.get("plugins", {}).get(plugin_name, {})

    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> None:
        """
        Set configuration for a specific plugin

        Args:
            plugin_name: Name of the plugin
            config: Plugin configuration
        """
        if "plugins" not in self._config:
            self._config["plugins"] = {}

        self._config["plugins"][plugin_name] = config

    def get_global_config(self) -> Dict[str, Any]:
        """Get global system configuration"""
        if not self._loaded:
            self.load_config()

        return self._config.get("global", {})

    def set_global_config(self, config: Dict[str, Any]) -> None:
        """Set global system configuration"""
        self._config["global"] = config

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key path

        Args:
            key: Dot-separated key path (e.g., 'plugins.rhel10_plugin.python_version')
            default: Default value if key not found

        Returns:
            Any: Configuration value
        """
        if not self._loaded:
            self.load_config()

        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value by key path

        Args:
            key: Dot-separated key path
            value: Value to set
        """
        keys = key.split(".")
        config = self._config

        # Navigate to parent
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set value
        config[keys[-1]] = value

    def get_enabled_plugins(self) -> List[str]:
        """Get list of enabled plugins"""
        return self.get("plugins.enabled", [])

    def set_enabled_plugins(self, plugins: List[str]) -> None:
        """Set list of enabled plugins"""
        self.set("plugins.enabled", plugins)

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled"""
        return plugin_name in self.get_enabled_plugins()

    def enable_plugin(self, plugin_name: str) -> None:
        """Enable a plugin"""
        enabled = self.get_enabled_plugins()
        if plugin_name not in enabled:
            enabled.append(plugin_name)
            self.set_enabled_plugins(enabled)

    def disable_plugin(self, plugin_name: str) -> None:
        """Disable a plugin"""
        enabled = self.get_enabled_plugins()
        if plugin_name in enabled:
            enabled.remove(plugin_name)
            self.set_enabled_plugins(enabled)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "global": {
                "log_level": "INFO",
                "plugin_directories": ["plugins"],
                "execution_timeout": 3600,
            },
            "plugins": {"enabled": []},
        }

    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides"""
        # Override with environment variables
        # Format: QUBINODE_CONFIG_<KEY_PATH>=<VALUE>
        prefix = "QUBINODE_CONFIG_"

        for env_var, value in os.environ.items():
            if env_var.startswith(prefix):
                key_path = env_var[len(prefix) :].lower().replace("_", ".")

                # Try to parse as JSON, fall back to string
                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    parsed_value = value

                self.set(key_path, parsed_value)
                self.logger.debug(
                    f"Applied environment override: {key_path} = {parsed_value}"
                )

    def validate_config(self) -> List[str]:
        """
        Validate configuration

        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        errors = []

        # Check required sections
        if "plugins" not in self._config:
            errors.append("Missing 'plugins' section in configuration")

        # Validate plugin configurations
        plugins_config = self._config.get("plugins", {})
        enabled_plugins = plugins_config.get("enabled", [])

        for plugin_name in enabled_plugins:
            if plugin_name not in plugins_config:
                errors.append(f"Enabled plugin '{plugin_name}' has no configuration")

        return errors

    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary"""
        return {
            "config_file": self.config_file,
            "loaded": self._loaded,
            "enabled_plugins": self.get_enabled_plugins(),
            "global_config_keys": list(self.get_global_config().keys()),
            "plugin_count": len(self._config.get("plugins", {}))
            - 1,  # Exclude 'enabled' key
            "validation_errors": self.validate_config(),
        }
