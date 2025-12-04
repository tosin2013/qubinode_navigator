#!/usr/bin/env python3
"""
Model Manager for Qubinode AI Assistant
Handles configurable AI models and hardware optimization
"""

import os
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages AI model configuration and deployment"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ai_config = config.get("ai_service", config.get("ai", {}))
        self.model_presets = self.ai_config.get("model_presets", {})

        # Get model configuration from environment or config
        self.model_type = self._get_config_value("model_type", "granite-4.0-micro")
        self.use_gpu = self._get_config_value("use_gpu", "false").lower() == "true"
        self.gpu_layers = int(self._get_config_value("gpu_layers", "0"))
        self.threads = int(self._get_config_value("threads", "4"))

        # Model paths and URLs
        self.model_path = self._get_config_value("model_path", "/app/models/granite-4.0-micro.gguf")
        self.model_url = self._get_config_value("model_url", None)

        # Server configuration
        self.context_length = int(self._get_config_value("context_length", "4096"))
        self.temperature = float(self._get_config_value("temperature", "0.7"))
        self.max_tokens = int(self._get_config_value("max_tokens", "512"))

        # Apply model preset if available
        self._apply_model_preset()

        logger.info("Model Manager initialized:")
        logger.info(f"  Model Type: {self.model_type}")
        logger.info(f"  GPU Enabled: {self.use_gpu}")
        logger.info(f"  GPU Layers: {self.gpu_layers}")
        logger.info(f"  CPU Threads: {self.threads}")
        logger.info(f"  Model Path: {self.model_path}")

    def _get_config_value(self, key: str, default: str) -> str:
        """Get configuration value from environment or config file"""
        env_key = f"AI_{key.upper()}"

        # First check environment variable directly
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value

        # Then check config file value (should already be processed by config manager)
        config_value = self.ai_config.get(key, default)

        # If config value still contains environment variable syntax, process it
        if isinstance(config_value, str) and "${" in config_value:
            import re

            pattern = r"\$\{([^}]+)\}"

            def replace_var(match):
                var_expr = match.group(1)
                if ":-" in var_expr:
                    var_name, default_value = var_expr.split(":-", 1)
                    return os.getenv(var_name.strip(), default_value.strip())
                else:
                    return os.getenv(var_expr.strip(), default)

            config_value = re.sub(pattern, replace_var, config_value)

        return str(config_value)

    def _apply_model_preset(self):
        """Apply model preset configuration if available"""
        if self.model_type in self.model_presets:
            preset = self.model_presets[self.model_type]

            # Update configuration from preset
            if not self.model_url:
                self.model_url = preset.get("model_url")

            # Update model path if not explicitly set
            if self.model_path == "/app/models/granite-4.0-micro.gguf":
                self.model_path = preset.get("model_path", self.model_path)

            # Update other settings from preset
            if "context_length" in preset:
                self.context_length = preset["context_length"]

            if "gpu_layers" in preset and self.gpu_layers == 0:
                self.gpu_layers = preset.get("gpu_layers", 0)

            logger.info(f"Applied preset for {self.model_type}: {preset.get('recommended_for', 'N/A')}")

    def detect_hardware_capabilities(self) -> Dict[str, Any]:
        """Detect available hardware capabilities"""
        capabilities = {
            "cpu_cores": os.cpu_count() or 4,
            "gpu_available": False,
            "gpu_memory_gb": 0,
            "system_memory_gb": 0,
            "recommendations": [],
        }

        try:
            # Check for NVIDIA GPU
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                gpu_memory_mb = int(result.stdout.strip())
                capabilities["gpu_available"] = True
                capabilities["gpu_memory_gb"] = gpu_memory_mb / 1024
                logger.info(f"NVIDIA GPU detected: {capabilities['gpu_memory_gb']:.1f}GB VRAM")
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            logger.info("No NVIDIA GPU detected or nvidia-smi not available")

        try:
            # Check system memory
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        mem_kb = int(line.split()[1])
                        capabilities["system_memory_gb"] = mem_kb / (1024 * 1024)
                        break
        except (FileNotFoundError, ValueError):
            logger.warning("Could not detect system memory")

        # Generate recommendations
        self._generate_hardware_recommendations(capabilities)

        return capabilities

    def _generate_hardware_recommendations(self, capabilities: Dict[str, Any]):
        """Generate model recommendations based on hardware"""
        recommendations = []

        if capabilities["gpu_available"] and capabilities["gpu_memory_gb"] >= 6:
            recommendations.append(
                {
                    "model": "llama3-8b",
                    "reason": f"GPU with {capabilities['gpu_memory_gb']:.1f}GB VRAM detected - can handle larger models",
                }
            )
        elif capabilities["system_memory_gb"] >= 8:
            recommendations.append(
                {
                    "model": "granite-7b",
                    "reason": f"System has {capabilities['system_memory_gb']:.1f}GB RAM - can handle medium models",
                }
            )
        else:
            recommendations.append(
                {
                    "model": "granite-4.0-micro",
                    "reason": "Limited resources detected - recommend lightweight model",
                }
            )

        capabilities["recommendations"] = recommendations

    def download_model(self) -> bool:
        """Download the configured model if needed"""
        model_path = Path(self.model_path)

        if model_path.exists():
            logger.info(f"Model already exists: {model_path}")
            return True

        if not self.model_url:
            logger.error(f"No model URL configured for {self.model_type}")
            return False

        logger.info(f"Downloading {self.model_type} model from {self.model_url}")

        try:
            # Create models directory
            model_path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare headers for Hugging Face authentication
            headers = {}
            hf_token = os.getenv("HUGGINGFACE_TOKEN")
            if hf_token:
                headers["Authorization"] = f"Bearer {hf_token}"
                logger.info("Using Hugging Face authentication token")

            # Download with progress (follow redirects)
            with httpx.stream(
                "GET",
                self.model_url,
                headers=headers,
                timeout=300,
                follow_redirects=True,
            ) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(model_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if downloaded % (1024 * 1024 * 10) == 0:  # Log every 10MB
                                logger.info(f"Download progress: {progress:.1f}%")

            logger.info(f"Model downloaded successfully: {model_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            if model_path.exists():
                model_path.unlink()  # Clean up partial download
            return False

    def start_llama_server(self) -> subprocess.Popen:
        """Start llama.cpp server with configured parameters"""

        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")

        # Find llama-server executable (try multiple locations for compatibility)
        server_paths = [
            "/usr/local/bin/llama-server",  # Primary location
            "/app/llama.cpp/server",  # Backward compatibility symlink
            "llama-server",  # System PATH
        ]

        server_executable = None
        for path in server_paths:
            if Path(path).exists() or path == "llama-server":
                server_executable = path
                break

        if not server_executable:
            raise FileNotFoundError(f"llama-server executable not found in any of these locations: {server_paths}")

        logger.info(f"Using llama-server executable: {server_executable}")

        # Build llama.cpp server command
        cmd = [
            server_executable,
            "--model",
            self.model_path,
            "--port",
            "8081",
            "--host",
            "0.0.0.0",
            "--ctx-size",
            str(self.context_length),
            "--threads",
            str(self.threads),
            "--log-disable",
        ]

        # Add GPU configuration if enabled
        if self.use_gpu and self.gpu_layers > 0:
            cmd.extend(["--n-gpu-layers", str(self.gpu_layers)])
            logger.info(f"GPU acceleration enabled: {self.gpu_layers} layers")

        logger.info(f"Starting llama.cpp server: {' '.join(cmd)}")

        # Start server process
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Wait for server to start
        max_wait = 30
        for i in range(max_wait):
            try:
                response = httpx.get("http://localhost:8081/health", timeout=2)
                if response.status_code == 200:
                    logger.info("llama.cpp server started successfully")
                    return process
            except httpx.RequestError:
                pass

            time.sleep(1)

        # Server failed to start
        process.terminate()
        stdout, stderr = process.communicate(timeout=5)
        logger.error("Failed to start llama.cpp server")
        logger.error(f"stdout: {stdout}")
        logger.error(f"stderr: {stderr}")
        raise RuntimeError("llama.cpp server failed to start")

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model configuration"""
        return {
            "model_type": self.model_type,
            "model_path": self.model_path,
            "model_url": self.model_url,
            "use_gpu": self.use_gpu,
            "gpu_layers": self.gpu_layers,
            "threads": self.threads,
            "context_length": self.context_length,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "preset_info": self.model_presets.get(self.model_type, {}),
        }

    def validate_configuration(self) -> Dict[str, Any]:
        """Validate the current model configuration"""
        validation = {"valid": True, "warnings": [], "errors": []}

        # Check model file
        if not Path(self.model_path).exists() and not self.model_url:
            validation["errors"].append(f"Model file not found and no download URL: {self.model_path}")
            validation["valid"] = False

        # Check GPU configuration
        if self.use_gpu and self.gpu_layers > 0:
            try:
                subprocess.run(["nvidia-smi"], capture_output=True, timeout=5)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                validation["warnings"].append("GPU acceleration requested but nvidia-smi not available")

        # Check memory requirements
        if self.model_type == "granite-7b" and self.threads > 8:
            validation["warnings"].append("High thread count with large model may cause memory issues")

        return validation


def create_model_manager(config: Dict[str, Any]) -> ModelManager:
    """Factory function to create a model manager"""
    return ModelManager(config)
