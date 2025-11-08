#!/usr/bin/env python3
"""
Configuration Manager for Qubinode AI Assistant
Handles configuration loading and management
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration for the AI assistant."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or "/app/config/ai_config.yaml")
        self.config = {}
        self.default_config = self._get_default_config()
    
    async def load_config(self):
        """Load configuration from file and environment."""
        try:
            # Start with defaults
            self.config = self.default_config.copy()
            
            # Load from file if exists
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        self.config.update(file_config)
                        logger.info(f"Loaded config from {self.config_path}")
            else:
                logger.info("Config file not found, using defaults")
            
            # Override with environment variables
            self._load_env_overrides()
            
            # Validate configuration
            self._validate_config()
            
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "ai": {
                "model_name": "granite-4.0-micro",
                "model_path": "/app/models/granite-4.0-micro.gguf",
                "max_tokens": 512,
                "temperature": 0.7,
                "context_size": 2048,
                "threads": os.cpu_count() or 4
            },
            "server": {
                "host": "0.0.0.0",
                "port": 8080,
                "llama_server_port": 8081,
                "log_level": "INFO",
                "timeout": 30
            },
            "features": {
                "diagnostics": True,
                "system_monitoring": True,
                "log_analysis": True,
                "rag_enabled": True
            },
            "security": {
                "enable_auth": False,
                "api_key": None,
                "allowed_hosts": ["*"],
                "rate_limit": 100
            },
            "storage": {
                "models_dir": "/app/models",
                "data_dir": "/app/data",
                "logs_dir": "/app/logs",
                "vector_db_path": "/app/data/chromadb"
            },
            "qubinode": {
                "integration_enabled": True,
                "plugin_framework_path": "/opt/qubinode/core",
                "ansible_callback": True,
                "setup_hooks": True
            }
        }
    
    def _load_env_overrides(self):
        """Load configuration overrides from environment variables."""
        env_mappings = {
            "AI_HOST": ("server", "host"),
            "AI_PORT": ("server", "port"),
            "AI_LOG_LEVEL": ("server", "log_level"),
            "AI_MODEL_PATH": ("ai", "model_path"),
            "AI_MAX_TOKENS": ("ai", "max_tokens"),
            "AI_TEMPERATURE": ("ai", "temperature"),
            "AI_THREADS": ("ai", "threads"),
            "AI_ENABLE_AUTH": ("security", "enable_auth"),
            "AI_API_KEY": ("security", "api_key"),
            "AI_RATE_LIMIT": ("security", "rate_limit"),
            "QUBINODE_INTEGRATION": ("qubinode", "integration_enabled")
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert types appropriately
                if key in ["port", "llama_server_port", "max_tokens", "threads", "rate_limit"]:
                    value = int(value)
                elif key in ["temperature"]:
                    value = float(value)
                elif key in ["enable_auth", "integration_enabled", "ansible_callback", "setup_hooks"]:
                    value = value.lower() in ("true", "1", "yes", "on")
                
                if section not in self.config:
                    self.config[section] = {}
                self.config[section][key] = value
                
                logger.debug(f"Environment override: {env_var} -> {section}.{key} = {value}")
    
    def _validate_config(self):
        """Validate configuration values."""
        # Validate required directories exist or can be created
        for dir_key in ["models_dir", "data_dir", "logs_dir"]:
            dir_path = Path(self.config["storage"][dir_key])
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.warning(f"Cannot create directory {dir_path}: {e}")
        
        # Validate numeric ranges
        if not (1 <= self.config["ai"]["max_tokens"] <= 4096):
            logger.warning("max_tokens should be between 1 and 4096")
        
        if not (0.0 <= self.config["ai"]["temperature"] <= 2.0):
            logger.warning("temperature should be between 0.0 and 2.0")
        
        if not (1 <= self.config["ai"]["threads"] <= 32):
            logger.warning("threads should be between 1 and 32")
    
    def get(self, section: str, key: str = None, default=None):
        """Get configuration value."""
        if key is None:
            return self.config.get(section, default)
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Any):
        """Set configuration value."""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def get_sanitized_config(self) -> Dict[str, Any]:
        """Get configuration with sensitive values removed."""
        sanitized = self.config.copy()
        
        # Remove sensitive information
        if "security" in sanitized and "api_key" in sanitized["security"]:
            if sanitized["security"]["api_key"]:
                sanitized["security"]["api_key"] = "***REDACTED***"
        
        return sanitized
    
    async def save_config(self):
        """Save current configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI-specific configuration."""
        return self.config.get("ai", {})
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server-specific configuration."""
        return self.config.get("server", {})
    
    def get_qubinode_config(self) -> Dict[str, Any]:
        """Get Qubinode integration configuration."""
        return self.config.get("qubinode", {})
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return self.config.get("features", {}).get(feature, False)
