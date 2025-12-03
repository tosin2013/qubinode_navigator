"""
Qubinode Navigator Core Framework

This module provides the core plugin framework for Qubinode Navigator,
implementing the modular architecture defined in ADR-0028.
"""

__version__ = "1.0.0"
__author__ = "Qubinode Navigator Team"

from .base_plugin import ExecutionContext, PluginResult, QubiNodePlugin, SystemState
from .config_manager import ConfigManager
from .event_system import EventSystem
from .plugin_manager import PluginManager

__all__ = [
    "PluginManager",
    "EventSystem",
    "ConfigManager",
    "QubiNodePlugin",
    "PluginResult",
    "SystemState",
    "ExecutionContext",
]
