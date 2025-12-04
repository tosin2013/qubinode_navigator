"""
Tests for ConfigManager
Tests configuration loading, environment variable substitution, and validation
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config_manager import ConfigManager


class TestConfigManagerInit:
    """Test ConfigManager initialization"""

    def test_config_manager_creation(self):
        """Test creating a ConfigManager instance"""
        manager = ConfigManager()
        assert manager is not None
        assert manager.config_path == Path("/app/config/ai_config.yaml")

    def test_config_manager_custom_path(self, tmp_path):
        """Test ConfigManager with custom config path"""
        config_path = str(tmp_path / "custom_config.yaml")
        manager = ConfigManager(config_path=config_path)
        assert manager.config_path == Path(config_path)

    def test_default_config_structure(self):
        """Test that default config has required sections"""
        manager = ConfigManager()
        default_config = manager.default_config

        assert "ai" in default_config
        assert "server" in default_config
        assert "features" in default_config
        assert "security" in default_config
        assert "storage" in default_config
        assert "qubinode" in default_config


class TestConfigManagerLoadConfig:
    """Test configuration loading"""

    @pytest.mark.asyncio
    async def test_load_config_defaults_only(self, tmp_path):
        """Test loading config when no file exists"""
        config_path = str(tmp_path / "nonexistent.yaml")
        manager = ConfigManager(config_path=config_path)
        await manager.load_config()

        # Should use defaults
        assert manager.config["ai"]["model_name"] == "granite-4.0-micro"
        assert manager.config["server"]["port"] == 8080

    @pytest.mark.asyncio
    async def test_load_config_from_file(self, temp_config_file):
        """Test loading config from a file"""
        manager = ConfigManager(config_path=temp_config_file)
        await manager.load_config()

        # Values from file should override defaults
        assert manager.config["ai"]["model_name"] == "granite-4.0-micro"
        assert manager.config["server"]["port"] == 8080

    @pytest.mark.asyncio
    async def test_load_config_with_env_override(self, tmp_path):
        """Test environment variable overrides"""
        config_path = str(tmp_path / "config.yaml")
        manager = ConfigManager(config_path=config_path)

        with patch.dict(os.environ, {"AI_PORT": "9090", "AI_LOG_LEVEL": "DEBUG"}):
            await manager.load_config()

        assert manager.config["server"]["port"] == 9090
        assert manager.config["server"]["log_level"] == "DEBUG"


class TestConfigManagerEnvSubstitution:
    """Test environment variable substitution"""

    def test_substitute_simple_env_var(self):
        """Test simple environment variable substitution"""
        manager = ConfigManager()

        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = manager._substitute_env_vars("${TEST_VAR}")
            assert result == "test_value"

    def test_substitute_env_var_with_default(self):
        """Test environment variable with default value"""
        manager = ConfigManager()

        # Variable not set, should use default
        result = manager._substitute_env_vars("${UNSET_VAR:-default_value}")
        assert result == "default_value"

        # Variable set, should use actual value
        with patch.dict(os.environ, {"SET_VAR": "actual_value"}):
            result = manager._substitute_env_vars("${SET_VAR:-default_value}")
            assert result == "actual_value"

    def test_substitute_nested_dict(self):
        """Test environment variable substitution in nested dict"""
        manager = ConfigManager()

        config = {
            "level1": {
                "level2": "${TEST_NESTED:-nested_default}",
                "list": ["${LIST_VAR:-item1}", "item2"],
            }
        }

        result = manager._substitute_env_vars(config)
        assert result["level1"]["level2"] == "nested_default"
        assert result["level1"]["list"][0] == "item1"

    def test_substitute_in_list(self):
        """Test environment variable substitution in list"""
        manager = ConfigManager()

        config = ["${VAR1:-val1}", "${VAR2:-val2}", "static"]
        result = manager._substitute_env_vars(config)

        assert result == ["val1", "val2", "static"]


class TestConfigManagerEnvOverrides:
    """Test environment variable overrides"""

    @pytest.mark.asyncio
    async def test_port_override(self, tmp_path):
        """Test port override from environment"""
        config_path = str(tmp_path / "config.yaml")
        manager = ConfigManager(config_path=config_path)

        with patch.dict(os.environ, {"AI_PORT": "9999"}):
            await manager.load_config()

        assert manager.config["server"]["port"] == 9999

    @pytest.mark.asyncio
    async def test_model_path_override(self, tmp_path):
        """Test model path override from environment"""
        config_path = str(tmp_path / "config.yaml")
        manager = ConfigManager(config_path=config_path)

        with patch.dict(os.environ, {"AI_MODEL_PATH": "/custom/model.gguf"}):
            await manager.load_config()

        assert manager.config["ai"]["model_path"] == "/custom/model.gguf"

    @pytest.mark.asyncio
    async def test_boolean_override(self, tmp_path):
        """Test boolean value override"""
        config_path = str(tmp_path / "config.yaml")
        manager = ConfigManager(config_path=config_path)

        with patch.dict(os.environ, {"AI_ENABLE_AUTH": "true"}):
            await manager.load_config()

        assert manager.config["security"]["enable_auth"] is True

    @pytest.mark.asyncio
    async def test_float_override(self, tmp_path):
        """Test float value override"""
        config_path = str(tmp_path / "config.yaml")
        manager = ConfigManager(config_path=config_path)

        with patch.dict(os.environ, {"AI_TEMPERATURE": "0.9"}):
            await manager.load_config()

        assert manager.config["ai"]["temperature"] == 0.9


class TestConfigManagerValidation:
    """Test configuration validation"""

    @pytest.mark.asyncio
    async def test_validate_max_tokens_warning(self, tmp_path, caplog):
        """Test warning for invalid max_tokens"""
        config_path = str(tmp_path / "config.yaml")
        manager = ConfigManager(config_path=config_path)
        await manager.load_config()

        # Set invalid value
        manager.config["ai"]["max_tokens"] = 10000
        manager._validate_config()

        assert "max_tokens should be between 1 and 4096" in caplog.text

    @pytest.mark.asyncio
    async def test_validate_temperature_warning(self, tmp_path, caplog):
        """Test warning for invalid temperature"""
        config_path = str(tmp_path / "config.yaml")
        manager = ConfigManager(config_path=config_path)
        await manager.load_config()

        # Set invalid value
        manager.config["ai"]["temperature"] = 3.0
        manager._validate_config()

        assert "temperature should be between 0.0 and 2.0" in caplog.text

    @pytest.mark.asyncio
    async def test_validate_threads_warning(self, tmp_path, caplog):
        """Test warning for invalid threads"""
        config_path = str(tmp_path / "config.yaml")
        manager = ConfigManager(config_path=config_path)
        await manager.load_config()

        # Set invalid value
        manager.config["ai"]["threads"] = 100
        manager._validate_config()

        assert "threads should be between 1 and 32" in caplog.text


class TestConfigManagerGetSet:
    """Test get and set methods"""

    def test_get_section(self):
        """Test getting a config section"""
        manager = ConfigManager()
        manager.config = {"ai": {"model_name": "test"}}

        result = manager.get("ai")
        assert result == {"model_name": "test"}

    def test_get_key(self):
        """Test getting a specific key"""
        manager = ConfigManager()
        manager.config = {"ai": {"model_name": "test"}}

        result = manager.get("ai", "model_name")
        assert result == "test"

    def test_get_with_default(self):
        """Test getting with default value"""
        manager = ConfigManager()
        manager.config = {}

        result = manager.get("nonexistent", "key", "default_value")
        assert result == "default_value"

    def test_set_value(self):
        """Test setting a config value"""
        manager = ConfigManager()
        manager.config = {"ai": {}}

        manager.set("ai", "new_key", "new_value")
        assert manager.config["ai"]["new_key"] == "new_value"

    def test_set_new_section(self):
        """Test setting value in new section"""
        manager = ConfigManager()
        manager.config = {}

        manager.set("new_section", "key", "value")
        assert manager.config["new_section"]["key"] == "value"


class TestConfigManagerSanitized:
    """Test sanitized config output"""

    def test_sanitize_api_key(self):
        """Test that API key is redacted"""
        manager = ConfigManager()
        manager.config = {
            "security": {
                "api_key": "secret_key_12345",
                "other_setting": "visible",
            }
        }

        sanitized = manager.get_sanitized_config()
        assert sanitized["security"]["api_key"] == "***REDACTED***"
        assert sanitized["security"]["other_setting"] == "visible"

    def test_sanitize_with_none_api_key(self):
        """Test sanitization when API key is None"""
        manager = ConfigManager()
        manager.config = {"security": {"api_key": None}}

        sanitized = manager.get_sanitized_config()
        assert sanitized["security"]["api_key"] is None


class TestConfigManagerSaveConfig:
    """Test configuration saving"""

    @pytest.mark.asyncio
    async def test_save_config(self, tmp_path):
        """Test saving configuration to file"""
        config_path = tmp_path / "saved_config.yaml"
        manager = ConfigManager(config_path=str(config_path))
        manager.config = {
            "ai": {"model_name": "test-model"},
            "server": {"port": 8080},
        }

        await manager.save_config()

        assert config_path.exists()
        content = config_path.read_text()
        assert "test-model" in content

    @pytest.mark.asyncio
    async def test_save_config_creates_directory(self, tmp_path):
        """Test that save creates parent directories"""
        config_path = tmp_path / "subdir" / "config.yaml"
        manager = ConfigManager(config_path=str(config_path))
        manager.config = {"test": "value"}

        await manager.save_config()

        assert config_path.exists()


class TestConfigManagerHelpers:
    """Test helper methods"""

    def test_get_ai_config(self):
        """Test getting AI configuration"""
        manager = ConfigManager()
        manager.config = {"ai": {"model_name": "test"}}

        result = manager.get_ai_config()
        assert result == {"model_name": "test"}

    def test_get_server_config(self):
        """Test getting server configuration"""
        manager = ConfigManager()
        manager.config = {"server": {"port": 8080}}

        result = manager.get_server_config()
        assert result == {"port": 8080}

    def test_get_qubinode_config(self):
        """Test getting Qubinode configuration"""
        manager = ConfigManager()
        manager.config = {"qubinode": {"enabled": True}}

        result = manager.get_qubinode_config()
        assert result == {"enabled": True}

    def test_is_feature_enabled_true(self):
        """Test checking enabled feature"""
        manager = ConfigManager()
        manager.config = {"features": {"diagnostics": True}}

        assert manager.is_feature_enabled("diagnostics") is True

    def test_is_feature_enabled_false(self):
        """Test checking disabled feature"""
        manager = ConfigManager()
        manager.config = {"features": {"diagnostics": False}}

        assert manager.is_feature_enabled("diagnostics") is False

    def test_is_feature_enabled_missing(self):
        """Test checking missing feature"""
        manager = ConfigManager()
        manager.config = {"features": {}}

        assert manager.is_feature_enabled("nonexistent") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
