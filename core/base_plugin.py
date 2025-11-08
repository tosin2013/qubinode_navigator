"""
Base Plugin Classes and Interfaces

Implements the plugin interface specification from ADR-0028 with
idempotency support and comprehensive state management.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging


class PluginStatus(Enum):
    """Plugin execution status"""
    NOT_STARTED = "not_started"
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SystemState:
    """Represents the current state of the system for idempotency checks"""
    
    def __init__(self, state_data: Dict[str, Any] = None):
        self.state_data = state_data or {}
        
    def matches(self, other: 'SystemState') -> bool:
        """Compare system states for idempotency checks"""
        if not isinstance(other, SystemState):
            return False
        return self.state_data == other.state_data
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get state value by key"""
        return self.state_data.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """Set state value by key"""
        self.state_data[key] = value
        
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple state values"""
        self.state_data.update(updates)


@dataclass
class PluginResult:
    """Result of plugin execution"""
    
    def __init__(self, 
                 changed: bool = False, 
                 message: str = "", 
                 data: Dict[str, Any] = None,
                 status: PluginStatus = PluginStatus.COMPLETED,
                 final_state: SystemState = None):
        self.changed = changed
        self.message = message
        self.data = data or {}
        self.status = status
        self.final_state = final_state or SystemState()


@dataclass 
class ExecutionContext:
    """Context information for plugin execution"""
    
    def __init__(self,
                 inventory: str = "localhost",
                 environment: str = "development", 
                 config: Dict[str, Any] = None,
                 variables: Dict[str, Any] = None):
        self.inventory = inventory
        self.environment = environment
        self.config = config or {}
        self.variables = variables or {}


class QubiNodePlugin(ABC):
    """
    Base class for all Qubinode Navigator plugins
    
    Implements the plugin interface specification from ADR-0028
    with idempotency support and comprehensive lifecycle management.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._initialized = False
        
    @property
    def name(self) -> str:
        """Plugin name for identification"""
        return self.__class__.__name__
        
    @property
    def version(self) -> str:
        """Plugin version"""
        return getattr(self, '__version__', '1.0.0')
        
    def initialize(self) -> bool:
        """
        Initialize plugin resources
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self._initialize_plugin()
            self._initialized = True
            self.logger.info(f"Plugin {self.name} initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize plugin {self.name}: {e}")
            return False
            
    @abstractmethod
    def _initialize_plugin(self) -> None:
        """Plugin-specific initialization logic"""
        pass
        
    @abstractmethod
    def check_state(self) -> SystemState:
        """
        Check current system state for idempotency
        
        Returns:
            SystemState: Current state of the system
        """
        pass
        
    def is_idempotent(self) -> bool:
        """
        Verify plugin can be safely re-run
        
        Returns:
            bool: True if plugin is idempotent, False otherwise
        """
        return True
        
    def get_desired_state(self, context: ExecutionContext) -> SystemState:
        """
        Get the desired system state based on context
        
        Args:
            context: Execution context with configuration and variables
            
        Returns:
            SystemState: Desired state of the system
        """
        # Default implementation - plugins should override if needed
        return SystemState()
        
    def execute(self, context: ExecutionContext) -> PluginResult:
        """
        Execute plugin functionality with idempotent behavior
        
        Args:
            context: Execution context with configuration and variables
            
        Returns:
            PluginResult: Result of plugin execution
        """
        if not self._initialized:
            if not self.initialize():
                return PluginResult(
                    changed=False,
                    message=f"Plugin {self.name} initialization failed",
                    status=PluginStatus.FAILED
                )
        
        try:
            # Check current state for idempotency
            current_state = self.check_state()
            desired_state = self.get_desired_state(context)
            
            if current_state.matches(desired_state):
                self.logger.info(f"Plugin {self.name}: System already in desired state")
                return PluginResult(
                    changed=False,
                    message="Already in desired state",
                    status=PluginStatus.SKIPPED,
                    final_state=current_state
                )
            
            # Execute plugin-specific logic
            self.logger.info(f"Plugin {self.name}: Applying changes")
            result = self.apply_changes(current_state, desired_state, context)
            
            # Verify final state
            final_state = self.check_state()
            result.final_state = final_state
            
            self.logger.info(f"Plugin {self.name}: Execution completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Plugin {self.name} execution failed: {e}")
            return PluginResult(
                changed=False,
                message=f"Execution failed: {str(e)}",
                status=PluginStatus.FAILED
            )
            
    @abstractmethod
    def apply_changes(self, 
                     current_state: SystemState, 
                     desired_state: SystemState,
                     context: ExecutionContext) -> PluginResult:
        """
        Apply changes to move from current state to desired state
        
        Args:
            current_state: Current system state
            desired_state: Desired system state  
            context: Execution context
            
        Returns:
            PluginResult: Result of applying changes
        """
        pass
        
    def cleanup(self) -> None:
        """Cleanup plugin resources"""
        try:
            self._cleanup_plugin()
            self.logger.info(f"Plugin {self.name} cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Failed to cleanup plugin {self.name}: {e}")
            
    def _cleanup_plugin(self) -> None:
        """Plugin-specific cleanup logic"""
        pass
        
    def get_dependencies(self) -> List[str]:
        """
        Return list of required plugins
        
        Returns:
            List[str]: List of plugin names this plugin depends on
        """
        return []
        
    def validate_config(self) -> bool:
        """
        Validate plugin configuration
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        return True
        
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get plugin health status
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            'name': self.name,
            'version': self.version,
            'initialized': self._initialized,
            'status': 'healthy' if self._initialized else 'not_initialized'
        }
