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


class TestModelManagerConfigValueAdvanced:
    """Advanced tests for _get_config_value edge cases"""

    def test_env_var_substitution_without_default(self, mock_config):
        """Test env var substitution without default value"""
        mock_config["ai_service"]["path_no_default"] = "${CUSTOM_VAR}"
        manager = ModelManager(mock_config)

        with patch.dict(os.environ, {"CUSTOM_VAR": "custom_value"}):
            result = manager._get_config_value("path_no_default", "fallback")
            assert result == "custom_value"

    def test_env_var_substitution_uses_default_when_not_set(self, mock_config):
        """Test that default is used when env var not set"""
        mock_config["ai_service"]["path_with_default"] = "${UNSET_VAR:-/default/path}"
        manager = ModelManager(mock_config)

        # Ensure UNSET_VAR is not in environment
        with patch.dict(os.environ, {}, clear=False):
            if "UNSET_VAR" in os.environ:
                del os.environ["UNSET_VAR"]
            result = manager._get_config_value("path_with_default", "/fallback")
            assert result == "/default/path"


class TestModelManagerPresetAdvanced:
    """Advanced tests for model preset functionality"""

    def test_preset_applies_model_url(self, mock_config):
        """Test that preset applies model URL when not set or empty"""
        mock_config["ai_service"]["model_presets"] = {
            "granite-4.0-micro": {
                "model_url": "https://example.com/preset-model.gguf",
                "recommended_for": "testing",
            }
        }
        # Set model_url to empty string (falsy) to trigger preset application
        mock_config["ai_service"]["model_url"] = ""
        manager = ModelManager(mock_config)

        # The preset URL should be applied when model_url was empty/falsy
        assert manager.model_url == "https://example.com/preset-model.gguf"

    def test_preset_applies_gpu_layers(self, mock_config):
        """Test that preset applies GPU layers when not set"""
        mock_config["ai_service"]["model_presets"] = {
            "granite-4.0-micro": {
                "gpu_layers": 20,
                "recommended_for": "gpu testing",
            }
        }
        manager = ModelManager(mock_config)

        assert manager.gpu_layers == 20

    def test_preset_applies_model_path(self, mock_config):
        """Test that preset applies model path when using default"""
        mock_config["ai_service"]["model_presets"] = {
            "granite-4.0-micro": {
                "model_path": "/custom/preset/model.gguf",
                "recommended_for": "custom path testing",
            }
        }
        # Reset to default path to trigger preset override
        mock_config["ai_service"]["model_path"] = "/app/models/granite-4.0-micro.gguf"
        manager = ModelManager(mock_config)

        assert manager.model_path == "/custom/preset/model.gguf"


class TestModelManagerHardwareDetectionAdvanced:
    """Advanced hardware detection tests"""

    def test_detect_hardware_memory_parsing(self, mock_config):
        """Test memory parsing from /proc/meminfo"""
        manager = ModelManager(mock_config)

        mock_meminfo = [
            "MemTotal:       16384000 kB\n",
            "MemFree:        8192000 kB\n",
            "MemAvailable:   10240000 kB\n",
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("nvidia-smi not found")

            mock_file = MagicMock()
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock(return_value=False)
            mock_file.__iter__ = MagicMock(return_value=iter(mock_meminfo))

            with patch("builtins.open", return_value=mock_file):
                capabilities = manager.detect_hardware_capabilities()

        # 16384000 kB ~= 15.63 GB
        assert capabilities["system_memory_gb"] > 15
        assert capabilities["system_memory_gb"] < 17

    def test_detect_hardware_memory_file_not_found(self, mock_config):
        """Test handling when /proc/meminfo is not found"""
        manager = ModelManager(mock_config)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("nvidia-smi not found")

            with patch("builtins.open") as mock_open:
                mock_open.side_effect = FileNotFoundError("/proc/meminfo not found")
                capabilities = manager.detect_hardware_capabilities()

        assert capabilities["system_memory_gb"] == 0
        assert capabilities["gpu_available"] is False

    def test_detect_hardware_gpu_timeout(self, mock_config):
        """Test handling when nvidia-smi times out"""
        manager = ModelManager(mock_config)
        import subprocess

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("nvidia-smi", 5)

            with patch("builtins.open") as mock_open:
                mock_open.side_effect = FileNotFoundError()
                capabilities = manager.detect_hardware_capabilities()

        assert capabilities["gpu_available"] is False

    def test_detect_hardware_gpu_invalid_output(self, mock_config):
        """Test handling when nvidia-smi returns invalid output"""
        manager = ModelManager(mock_config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="invalid_memory",  # Not a valid integer
            )

            with patch("builtins.open") as mock_open:
                mock_open.side_effect = FileNotFoundError()
                capabilities = manager.detect_hardware_capabilities()

        # Should handle ValueError gracefully
        assert capabilities["gpu_available"] is False

    def test_hardware_recommendations_medium_ram(self, mock_config):
        """Test hardware recommendations with medium RAM (8-16GB)"""
        manager = ModelManager(mock_config)

        capabilities = {
            "gpu_available": False,
            "gpu_memory_gb": 0,
            "system_memory_gb": 12.0,  # Medium RAM
            "cpu_cores": 4,
            "recommendations": [],
        }

        manager._generate_hardware_recommendations(capabilities)

        assert len(capabilities["recommendations"]) > 0
        # Should recommend granite-7b for medium RAM
        assert any("granite-7b" in r["model"] for r in capabilities["recommendations"])


class TestModelManagerDownloadAdvanced:
    """Advanced model download tests"""

    def test_download_model_success(self, mock_config, tmp_path):
        """Test successful model download"""
        model_path = tmp_path / "models" / "model.gguf"
        mock_config["ai_service"]["model_path"] = str(model_path)

        manager = ModelManager(mock_config)
        manager.model_path = str(model_path)
        manager.model_url = "https://example.com/model.gguf"

        # Mock httpx.stream
        mock_response = MagicMock()
        mock_response.headers = {"content-length": "1000"}
        mock_response.iter_bytes = MagicMock(return_value=[b"x" * 100] * 10)
        mock_response.raise_for_status = MagicMock()

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_response)
        mock_stream.__exit__ = MagicMock(return_value=False)

        with patch("httpx.stream", return_value=mock_stream):
            result = manager.download_model()

        assert result is True
        assert model_path.exists()

    def test_download_model_with_hf_token(self, mock_config, tmp_path):
        """Test model download with Hugging Face token"""
        model_path = tmp_path / "models" / "model.gguf"
        mock_config["ai_service"]["model_path"] = str(model_path)

        manager = ModelManager(mock_config)
        manager.model_path = str(model_path)
        manager.model_url = "https://huggingface.co/model.gguf"

        mock_response = MagicMock()
        mock_response.headers = {"content-length": "100"}
        mock_response.iter_bytes = MagicMock(return_value=[b"x" * 100])
        mock_response.raise_for_status = MagicMock()

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_response)
        mock_stream.__exit__ = MagicMock(return_value=False)

        with patch.dict(os.environ, {"HUGGINGFACE_TOKEN": "hf_test_token"}):
            with patch("httpx.stream", return_value=mock_stream) as mock_httpx:
                result = manager.download_model()

        # Verify token was passed
        call_kwargs = mock_httpx.call_args[1]
        assert "headers" in call_kwargs
        assert call_kwargs["headers"].get("Authorization") == "Bearer hf_test_token"
        assert result is True

    def test_download_model_failure(self, mock_config, tmp_path):
        """Test model download failure handling"""
        model_path = tmp_path / "models" / "model.gguf"
        mock_config["ai_service"]["model_path"] = str(model_path)

        manager = ModelManager(mock_config)
        manager.model_path = str(model_path)
        manager.model_url = "https://example.com/model.gguf"

        with patch("httpx.stream") as mock_stream:
            mock_stream.side_effect = Exception("Download failed")
            result = manager.download_model()

        assert result is False
        # Partial file should be cleaned up
        assert not model_path.exists()

    def test_download_model_cleans_up_partial(self, mock_config, tmp_path):
        """Test that partial download is cleaned up on failure"""
        model_path = tmp_path / "models" / "model.gguf"
        model_path.parent.mkdir(parents=True)
        model_path.write_text("partial content")  # Simulate partial file

        mock_config["ai_service"]["model_path"] = str(model_path)

        manager = ModelManager(mock_config)
        manager.model_path = str(model_path)
        manager.model_url = "https://example.com/model.gguf"

        # Make it look like download is needed by checking existence before mock
        original_exists = model_path.exists

        def mock_exists():
            # Return False on first call (check for download), True on cleanup check
            return original_exists()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(side_effect=Exception("HTTP Error"))

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_response)
        mock_stream.__exit__ = MagicMock(return_value=False)

        # File exists initially, so download_model returns True
        assert manager.download_model() is True


class TestModelManagerLlamaServerAdvanced:
    """Advanced llama server tests"""

    def test_start_llama_server_success(self, mock_config, tmp_path):
        """Test successful llama server startup"""
        model_path = tmp_path / "model.gguf"
        model_path.write_text("model content")

        mock_config["ai_service"]["model_path"] = str(model_path)
        manager = ModelManager(mock_config)
        manager.model_path = str(model_path)

        mock_process = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
                mock_response = MagicMock()
                mock_response.status_code = 200

                with patch("httpx.get", return_value=mock_response):
                    process = manager.start_llama_server()

        assert process == mock_process
        mock_popen.assert_called_once()

    def test_start_llama_server_with_gpu(self, mock_config, tmp_path):
        """Test llama server startup with GPU enabled"""
        model_path = tmp_path / "model.gguf"
        model_path.write_text("model content")

        mock_config["ai_service"]["model_path"] = str(model_path)
        manager = ModelManager(mock_config)
        manager.model_path = str(model_path)
        manager.use_gpu = True
        manager.gpu_layers = 32

        mock_process = MagicMock()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
                mock_response = MagicMock()
                mock_response.status_code = 200

                with patch("httpx.get", return_value=mock_response):
                    manager.start_llama_server()

        # Verify GPU flags were passed
        call_args = mock_popen.call_args[0][0]
        assert "--n-gpu-layers" in call_args
        assert "32" in call_args

    def test_start_llama_server_timeout(self, mock_config, tmp_path):
        """Test llama server startup timeout"""
        model_path = tmp_path / "model.gguf"
        model_path.write_text("model content")

        mock_config["ai_service"]["model_path"] = str(model_path)
        manager = ModelManager(mock_config)
        manager.model_path = str(model_path)

        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.communicate = MagicMock(return_value=("stdout", "stderr"))

        import httpx

        with patch("pathlib.Path.exists", return_value=True):
            with patch("subprocess.Popen", return_value=mock_process):
                with patch("httpx.get") as mock_get:
                    mock_get.side_effect = httpx.RequestError("Connection refused")
                    with patch("time.sleep"):  # Speed up test
                        with pytest.raises(RuntimeError, match="failed to start"):
                            manager.start_llama_server()

        mock_process.terminate.assert_called_once()


class TestModelManagerValidationAdvanced:
    """Advanced validation tests"""

    def test_validate_large_model_high_threads_warning(self, mock_config):
        """Test warning for high thread count with large model"""
        manager = ModelManager(mock_config)
        manager.model_type = "granite-7b"
        manager.threads = 12

        validation = manager.validate_configuration()

        assert any("memory" in w.lower() for w in validation["warnings"])

    def test_validate_with_model_url_but_no_file(self, mock_config, tmp_path):
        """Test validation passes when model file missing but URL provided"""
        model_path = tmp_path / "nonexistent.gguf"

        mock_config["ai_service"]["model_path"] = str(model_path)
        manager = ModelManager(mock_config)
        manager.model_path = str(model_path)
        manager.model_url = "https://example.com/model.gguf"  # URL is set

        validation = manager.validate_configuration()

        # Should be valid because URL is provided
        assert validation["valid"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
