"""
Tests for ModelManager
Tests model configuration, hardware detection, and model management
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from model_manager import ModelManager, create_model_manager


class TestModelManagerInit:
    """Test ModelManager initialization"""

    def test_model_manager_creation(self, mock_config):
        """Test creating a ModelManager instance"""
        manager = ModelManager(mock_config)
        assert manager is not None
        assert manager.model_type == "granite-4.0-micro"

    def test_model_manager_default_values(self, mock_config):
        """Test default configuration values"""
        manager = ModelManager(mock_config)

        assert manager.threads == 4
        assert manager.use_gpu is False
        assert manager.gpu_layers == 0
        assert manager.context_length == 4096

    def test_model_manager_env_override(self, mock_config):
        """Test environment variable overrides"""
        with patch.dict(
            os.environ,
            {
                "AI_MODEL_TYPE": "custom-model",
                "AI_THREADS": "8",
                "AI_USE_GPU": "true",
                "AI_GPU_LAYERS": "32",
            },
        ):
            manager = ModelManager(mock_config)

            assert manager.model_type == "custom-model"
            assert manager.threads == 8
            assert manager.use_gpu is True
            assert manager.gpu_layers == 32


class TestModelManagerConfigValue:
    """Test _get_config_value method"""

    def test_get_config_from_env(self, mock_config):
        """Test getting config from environment variable"""
        manager = ModelManager(mock_config)

        with patch.dict(os.environ, {"AI_TEST_KEY": "env_value"}):
            result = manager._get_config_value("test_key", "default")
            assert result == "env_value"

    def test_get_config_from_file(self, mock_config):
        """Test getting config from config file"""
        mock_config["ai_service"]["custom_key"] = "file_value"
        manager = ModelManager(mock_config)

        result = manager._get_config_value("custom_key", "default")
        assert result == "file_value"

    def test_get_config_default(self, mock_config):
        """Test getting default value when not set"""
        manager = ModelManager(mock_config)

        result = manager._get_config_value("nonexistent_key", "default_value")
        assert result == "default_value"

    def test_get_config_env_var_substitution(self, mock_config):
        """Test environment variable substitution in config values"""
        mock_config["ai_service"]["path_with_var"] = "${HOME:-/home/default}/models"
        manager = ModelManager(mock_config)

        with patch.dict(os.environ, {"HOME": "/home/test"}):
            result = manager._get_config_value("path_with_var", "/default/path")
            assert "/home/test/models" in result or "/home/default/models" in result


class TestModelManagerPresets:
    """Test model preset functionality"""

    def test_apply_model_preset(self, mock_config):
        """Test applying model preset"""
        mock_config["ai_service"]["model_presets"] = {
            "granite-4.0-micro": {
                "model_url": "https://example.com/model.gguf",
                "context_length": 8192,
                "recommended_for": "testing",
            }
        }
        manager = ModelManager(mock_config)

        # Preset should be applied
        assert manager.context_length == 8192

    def test_no_preset_available(self, mock_config):
        """Test behavior when no preset is available"""
        mock_config["ai_service"]["model_presets"] = {}
        manager = ModelManager(mock_config)

        # Should use default values
        assert manager.context_length == 4096


class TestModelManagerHardwareDetection:
    """Test hardware capability detection"""

    def test_detect_hardware_no_gpu(self, mock_config):
        """Test hardware detection without GPU"""
        manager = ModelManager(mock_config)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("nvidia-smi not found")

            with patch("builtins.open", MagicMock()) as mock_open:
                mock_open.return_value.__enter__.return_value.readlines.return_value = ["MemTotal:       16000000 kB\n"]

                capabilities = manager.detect_hardware_capabilities()

        assert capabilities["gpu_available"] is False
        assert capabilities["cpu_cores"] > 0

    def test_detect_hardware_with_gpu(self, mock_config):
        """Test hardware detection with GPU"""
        manager = ModelManager(mock_config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="8192",  # 8GB VRAM
            )

            capabilities = manager.detect_hardware_capabilities()

        assert capabilities["gpu_available"] is True
        assert capabilities["gpu_memory_gb"] == 8.0

    def test_hardware_recommendations_gpu(self, mock_config):
        """Test hardware recommendations with GPU"""
        manager = ModelManager(mock_config)

        capabilities = {
            "gpu_available": True,
            "gpu_memory_gb": 8.0,
            "system_memory_gb": 16.0,
            "cpu_cores": 8,
            "recommendations": [],
        }

        manager._generate_hardware_recommendations(capabilities)

        assert len(capabilities["recommendations"]) > 0
        assert any("GPU" in r["reason"] for r in capabilities["recommendations"])

    def test_hardware_recommendations_limited_resources(self, mock_config):
        """Test hardware recommendations with limited resources"""
        manager = ModelManager(mock_config)

        capabilities = {
            "gpu_available": False,
            "gpu_memory_gb": 0,
            "system_memory_gb": 4.0,
            "cpu_cores": 2,
            "recommendations": [],
        }

        manager._generate_hardware_recommendations(capabilities)

        assert len(capabilities["recommendations"]) > 0
        assert any("lightweight" in r["reason"].lower() for r in capabilities["recommendations"])


class TestModelManagerDownload:
    """Test model download functionality"""

    def test_download_model_exists(self, mock_config, tmp_path):
        """Test that download is skipped when model exists"""
        model_path = tmp_path / "models" / "model.gguf"
        model_path.parent.mkdir(parents=True)
        model_path.write_text("model content")

        mock_config["ai_service"]["model_path"] = str(model_path)
        manager = ModelManager(mock_config)
        manager.model_path = str(model_path)

        result = manager.download_model()
        assert result is True

    def test_download_model_no_url(self, mock_config, tmp_path):
        """Test download fails when no URL is configured"""
        model_path = tmp_path / "models" / "nonexistent.gguf"

        mock_config["ai_service"]["model_path"] = str(model_path)
        manager = ModelManager(mock_config)
        manager.model_path = str(model_path)
        manager.model_url = None

        result = manager.download_model()
        assert result is False


class TestModelManagerLlamaServer:
    """Test llama.cpp server management"""

    def test_start_llama_server_model_not_found(self, mock_config, tmp_path):
        """Test error when model file not found"""
        model_path = tmp_path / "nonexistent.gguf"
        mock_config["ai_service"]["model_path"] = str(model_path)
        manager = ModelManager(mock_config)
        manager.model_path = str(model_path)

        with pytest.raises(FileNotFoundError):
            manager.start_llama_server()

    def test_start_llama_server_executable_not_found(self, mock_config, tmp_path):
        """Test error when llama-server not found"""
        model_path = tmp_path / "model.gguf"
        model_path.write_text("model content")

        mock_config["ai_service"]["model_path"] = str(model_path)
        manager = ModelManager(mock_config)
        manager.model_path = str(model_path)

        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                manager.start_llama_server()


class TestModelManagerInfo:
    """Test model information methods"""

    def test_get_model_info(self, mock_config):
        """Test getting model information"""
        manager = ModelManager(mock_config)
        info = manager.get_model_info()

        assert "model_type" in info
        assert "model_path" in info
        assert "use_gpu" in info
        assert "threads" in info
        assert "context_length" in info
        assert "temperature" in info
        assert "max_tokens" in info

    def test_get_model_info_values(self, mock_config):
        """Test model info values are correct"""
        manager = ModelManager(mock_config)
        info = manager.get_model_info()

        assert info["model_type"] == "granite-4.0-micro"
        assert info["use_gpu"] is False
        assert info["threads"] == 4


class TestModelManagerValidation:
    """Test configuration validation"""

    def test_validate_valid_config(self, mock_config, tmp_path):
        """Test validation passes with valid config"""
        model_path = tmp_path / "model.gguf"
        model_path.write_text("model content")

        mock_config["ai_service"]["model_path"] = str(model_path)
        manager = ModelManager(mock_config)
        manager.model_path = str(model_path)

        validation = manager.validate_configuration()

        assert validation["valid"] is True
        assert len(validation["errors"]) == 0

    def test_validate_missing_model(self, mock_config, tmp_path):
        """Test validation fails with missing model and no URL"""
        model_path = tmp_path / "nonexistent.gguf"

        mock_config["ai_service"]["model_path"] = str(model_path)
        manager = ModelManager(mock_config)
        manager.model_path = str(model_path)
        manager.model_url = None

        validation = manager.validate_configuration()

        assert validation["valid"] is False
        assert len(validation["errors"]) > 0

    def test_validate_gpu_warning(self, mock_config):
        """Test GPU warning when nvidia-smi not available"""
        manager = ModelManager(mock_config)
        manager.use_gpu = True
        manager.gpu_layers = 32

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            validation = manager.validate_configuration()

        assert any("nvidia-smi" in w for w in validation["warnings"])


class TestModelManagerFactory:
    """Test factory function"""

    def test_create_model_manager(self, mock_config):
        """Test factory function creates ModelManager"""
        manager = create_model_manager(mock_config)

        assert isinstance(manager, ModelManager)
        assert manager.model_type == "granite-4.0-micro"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
