"""
AI Assistant Plugin

Integrates the Qubinode AI Assistant with the plugin framework.
Provides AI-powered system diagnostics, deployment guidance, and troubleshooting.
Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture.
"""

import subprocess
import os
import json
import time
import requests
from typing import Dict, Any, List
from core.base_plugin import (
    QubiNodePlugin,
    PluginResult,
    SystemState,
    ExecutionContext,
    PluginStatus,
)


class AIAssistantPlugin(QubiNodePlugin):
    """
    AI Assistant integration plugin

    Provides AI-powered deployment assistance, system diagnostics,
    and intelligent troubleshooting capabilities for Qubinode Navigator.
    """

    __version__ = "1.0.0"

    def __init__(self, config: Dict[str, Any]):
        """Initialize AI Assistant plugin with configuration"""
        super().__init__(config)

        # Initialize configuration attributes immediately
        self.ai_service_url = self.config.get("ai_service_url", "http://localhost:8080")
        self.container_name = self.config.get("container_name", "qubinode-ai-assistant")
        self.ai_assistant_path = self.config.get(
            "ai_assistant_path", "/root/qubinode_navigator/ai-assistant"
        )
        self.auto_start = self.config.get("auto_start", True)
        self.health_check_timeout = self.config.get("health_check_timeout", 60)
        self.enable_diagnostics = self.config.get("enable_diagnostics", True)
        self.enable_rag = self.config.get("enable_rag", True)

        # Version configuration
        self.container_version = self.config.get("container_version", "latest")
        self.version_strategy = self.config.get(
            "version_strategy", "auto"
        )  # auto, latest, specific, semver

        # Image configuration for different deployment modes (must be set before determining container image)
        self.image_config = {
            "development": {
                "registry": "localhost",
                "image": "qubinode-ai-assistant",
                "tag": self._get_development_tag(),
                "build_required": True,
                "description": "Local development image with debugging tools",
            },
            "production": {
                "registry": "quay.io/takinosh",
                "image": "qubinode-ai-assistant",
                "tag": self._get_production_tag(),
                "build_required": False,
                "description": "Production-ready image from Quay.io registry",
            },
        }

        # Deployment strategy configuration
        self.deployment_mode = self.config.get(
            "deployment_mode", "auto"
        )  # auto, development, production
        self.container_image = self._determine_container_image()

        # AI Assistant capabilities
        self.capabilities = [
            "system_diagnostics",
            "deployment_guidance",
            "troubleshooting_assistance",
            "rag_knowledge_retrieval",
            "kvm_hypervisor_support",
            "ansible_automation_help",
        ]

    def _determine_container_image(self) -> str:
        """Determine which container image to use based on deployment mode"""
        # Check if image is explicitly configured
        if "container_image" in self.config:
            return self.config["container_image"]

        # Auto-detect deployment mode if not specified
        if self.deployment_mode == "auto":
            self.deployment_mode = self._detect_deployment_mode()

        # Get image configuration for the deployment mode
        if self.deployment_mode in self.image_config:
            config = self.image_config[self.deployment_mode]
            return f"{config['registry']}/{config['image']}:{config['tag']}"
        else:
            # Fallback to development mode
            self.logger.warning(
                f"Unknown deployment mode '{self.deployment_mode}', falling back to development"
            )
            self.deployment_mode = "development"
            config = self.image_config["development"]
            return f"{config['registry']}/{config['image']}:{config['tag']}"

    def _get_development_tag(self) -> str:
        """Get appropriate tag for development mode"""
        if self.container_version != "latest":
            return self.container_version

        # Try to read version from VERSION file
        version_file = os.path.join(self.ai_assistant_path, "VERSION")
        if os.path.exists(version_file):
            try:
                with open(version_file, "r") as f:
                    return f.read().strip()
            except Exception:
                pass

        return "latest"

    def _get_production_tag(self) -> str:
        """Get appropriate tag for production mode"""
        if self.container_version != "latest":
            return self.container_version

        # Version strategy handling
        if self.version_strategy == "latest":
            return "latest"
        elif self.version_strategy == "specific":
            # Use configured version or fall back to latest
            return (
                self.container_version
                if self.container_version != "latest"
                else "latest"
            )
        elif self.version_strategy == "semver":
            # Use semantic versioning - prefer stable releases
            return self._get_latest_stable_version()
        else:  # auto
            # Auto strategy: prefer latest stable, fall back to latest
            stable_version = self._get_latest_stable_version()
            return stable_version if stable_version else "latest"

    def _get_latest_stable_version(self) -> str:
        """Get the latest stable version from VERSION file or environment"""
        # Check environment variable for version override
        env_version = os.environ.get("QUBINODE_AI_VERSION")
        if env_version:
            return env_version

        # Try to read version from VERSION file
        version_file = os.path.join(self.ai_assistant_path, "VERSION")
        if os.path.exists(version_file):
            try:
                with open(version_file, "r") as f:
                    version = f.read().strip()
                    # Only return if it's a stable version (no prerelease)
                    if "-" not in version:
                        return version
            except Exception:
                pass

        # Default to latest if no stable version found
        return "latest"

    def _detect_deployment_mode(self) -> str:
        """Auto-detect deployment mode based on environment"""
        # Check environment variables
        env_mode = os.environ.get("QUBINODE_DEPLOYMENT_MODE")
        if env_mode in ["development", "production"]:
            return env_mode

        # Check if we're in a container (production-like)
        if os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"):
            return "production"

        # Check if local development files exist
        if os.path.exists(self.ai_assistant_path) and os.path.exists(
            os.path.join(self.ai_assistant_path, "Dockerfile")
        ):
            return "development"

        # Default to production for safety
        return "production"

    def _initialize_plugin(self) -> None:
        """Initialize AI Assistant plugin resources"""
        self.logger.info(
            f"Initializing AI Assistant plugin in {self.deployment_mode} mode"
        )
        self.logger.info(f"Using container image: {self.container_image}")

    def check_state(self) -> SystemState:
        """Check current AI Assistant state"""
        state_data = {}

        # Check if container exists
        state_data["container_exists"] = self._container_exists()

        # Check if container is running
        state_data["container_running"] = self._container_running()

        # Check if AI service is healthy
        state_data["ai_service_healthy"] = self._ai_service_healthy()

        # Check if RAG system is loaded
        state_data["rag_system_loaded"] = self._rag_system_loaded()

        # Check if diagnostic tools are available
        state_data["diagnostic_tools_available"] = self._diagnostic_tools_available()

        # Check AI assistant directory
        state_data["ai_assistant_directory_exists"] = os.path.exists(
            self.ai_assistant_path
        )

        return SystemState(state_data)

    def get_desired_state(self, context: ExecutionContext) -> SystemState:
        """Get desired AI Assistant state"""
        desired_state = {
            "container_exists": True,
            "container_running": True,
            "ai_service_healthy": True,
            "rag_system_loaded": self.enable_rag,
            "diagnostic_tools_available": self.enable_diagnostics,
            "ai_assistant_directory_exists": True,
        }

        return SystemState(desired_state)

    def apply_changes(
        self,
        current_state: SystemState,
        desired_state: SystemState,
        context: ExecutionContext,
    ) -> PluginResult:
        """Apply changes to achieve desired AI Assistant state"""

        changes_made = []

        try:
            # Ensure AI assistant directory exists
            if not current_state.get("ai_assistant_directory_exists"):
                self.logger.error(
                    f"AI Assistant directory not found: {self.ai_assistant_path}"
                )
                return PluginResult(
                    changed=False,
                    message=f"AI Assistant directory not found: {self.ai_assistant_path}",
                    status=PluginStatus.FAILED,
                )

            # Build or pull container if it doesn't exist
            if not current_state.get("container_exists"):
                if (
                    self.deployment_mode == "development"
                    and self.image_config[self.deployment_mode]["build_required"]
                ):
                    self.logger.info(
                        "Building AI Assistant container for development..."
                    )
                    if self._build_container():
                        changes_made.append("Built AI Assistant container")
                    else:
                        return PluginResult(
                            changed=False,
                            message="Failed to build AI Assistant container",
                            status=PluginStatus.FAILED,
                        )
                else:
                    self.logger.info(
                        f"Pulling AI Assistant container from {self.container_image}..."
                    )
                    if self._pull_container():
                        changes_made.append("Pulled AI Assistant container")
                    else:
                        return PluginResult(
                            changed=False,
                            message="Failed to pull AI Assistant container",
                            status=PluginStatus.FAILED,
                        )

            # Start container if not running
            if not current_state.get("container_running"):
                self.logger.info("Starting AI Assistant container...")
                if self._start_container():
                    changes_made.append("Started AI Assistant container")
                    # Wait for service to initialize
                    time.sleep(10)
                else:
                    return PluginResult(
                        changed=False,
                        message="Failed to start AI Assistant container",
                        status=PluginStatus.FAILED,
                    )

            # Wait for AI service to become healthy
            if not self._wait_for_health():
                return PluginResult(
                    changed=bool(changes_made),
                    message="AI Assistant started but health check failed",
                    status=PluginStatus.FAILED,
                    data={"changes": changes_made},
                )

            # Verify RAG system if enabled
            if self.enable_rag and not current_state.get("rag_system_loaded"):
                if self._setup_rag_system():
                    changes_made.append("Configured RAG system")
                else:
                    self.logger.warning(
                        "RAG system setup failed, continuing without RAG"
                    )

            # Verify diagnostic tools if enabled
            if self.enable_diagnostics and not current_state.get(
                "diagnostic_tools_available"
            ):
                if self._verify_diagnostic_tools():
                    changes_made.append("Verified diagnostic tools")
                else:
                    self.logger.warning("Diagnostic tools verification failed")

            # Get final status
            final_status = self._get_ai_assistant_status()

            message = "AI Assistant is operational"
            if changes_made:
                message = f"AI Assistant configured successfully. Changes: {', '.join(changes_made)}"

            return PluginResult(
                changed=bool(changes_made),
                message=message,
                status=PluginStatus.COMPLETED,
                data={
                    "changes": changes_made,
                    "ai_assistant_status": final_status,
                    "capabilities": self.capabilities,
                    "service_url": self.ai_service_url,
                },
            )

        except Exception as e:
            self.logger.error(f"Failed to apply AI Assistant changes: {e}")
            return PluginResult(
                changed=bool(changes_made),
                message=f"AI Assistant setup failed: {str(e)}",
                status=PluginStatus.FAILED,
                data={"changes": changes_made},
            )

    def _container_exists(self) -> bool:
        """Check if AI Assistant container exists"""
        # Try both docker and podman
        for runtime in ["docker", "podman"]:
            try:
                result = subprocess.run(
                    [runtime, "ps", "-a", "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    containers = json.loads(result.stdout)
                    for container in containers:
                        names = container.get("Names", [])
                        if isinstance(names, list):
                            if any(self.container_name in name for name in names):
                                return True
                        elif isinstance(names, str):
                            if self.container_name in names:
                                return True
                    # If we got here with docker/podman working but no container found
                    return False
            except FileNotFoundError:
                # Runtime not available, try next one
                continue
            except Exception as e:
                self.logger.debug(
                    f"Failed to check container existence with {runtime}: {e}"
                )
                continue

        # Neither docker nor podman worked
        self.logger.error("Neither docker nor podman available for container checks")
        return False

    def _container_running(self) -> bool:
        """Check if AI Assistant container is running"""
        # Try both docker and podman
        for runtime in ["docker", "podman"]:
            try:
                result = subprocess.run(
                    [runtime, "ps", "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    containers = json.loads(result.stdout)
                    for container in containers:
                        names = container.get("Names", [])
                        if isinstance(names, list):
                            if any(self.container_name in name for name in names):
                                return True
                        elif isinstance(names, str):
                            if self.container_name in names:
                                return True
                    # If we got here with docker/podman working but no container found
                    return False
            except FileNotFoundError:
                # Runtime not available, try next one
                continue
            except Exception as e:
                self.logger.debug(
                    f"Failed to check container status with {runtime}: {e}"
                )
                continue

        # Neither docker nor podman worked
        self.logger.error(
            "Neither docker nor podman available for container status checks"
        )
        return False

    def _ai_service_healthy(self) -> bool:
        """Check if AI service is healthy (accept degraded status)"""
        try:
            response = requests.get(f"{self.ai_service_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                return health_data.get("status") in ["healthy", "degraded"]
            elif response.status_code == 503:
                # Check if it's degraded only due to RAG documents
                try:
                    data = response.json()
                    if "detail" in data and isinstance(data["detail"], dict):
                        detail = data["detail"]
                        if detail.get("status") == "degraded":
                            ai_service = detail.get("ai_service", {})
                            warnings = ai_service.get("warnings", [])
                            # Accept degraded status if only RAG documents not loaded
                            if (
                                len(warnings) == 1
                                and "RAG documents not loaded" in warnings[0]
                            ):
                                return True
                except:
                    pass
            return False
        except Exception as e:
            self.logger.debug(f"AI service health check failed: {e}")
            return False

    def _rag_system_loaded(self) -> bool:
        """Check if RAG system is loaded"""
        try:
            response = requests.get(f"{self.ai_service_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                ai_service = health_data.get("ai_service", {})
                rag_service = ai_service.get("components", {}).get("rag_service", {})
                return rag_service.get("documents_loaded", False)
            return False
        except Exception as e:
            self.logger.debug(f"RAG system check failed: {e}")
            return False

    def _diagnostic_tools_available(self) -> bool:
        """Check if diagnostic tools are available"""
        try:
            response = requests.get(
                f"{self.ai_service_url}/diagnostics/tools", timeout=5
            )
            if response.status_code == 200:
                tools_data = response.json()
                return tools_data.get("total_tools", 0) > 0
            return False
        except Exception as e:
            self.logger.debug(f"Diagnostic tools check failed: {e}")
            return False

    def _build_container(self) -> bool:
        """Build AI Assistant container (development mode only)"""
        try:
            self.logger.info("Building AI Assistant container...")

            # Ensure we're in development mode
            if self.deployment_mode != "development":
                self.logger.error(
                    "Container building is only supported in development mode"
                )
                return False

            # Check if AI assistant directory exists
            if not os.path.exists(self.ai_assistant_path):
                self.logger.error(
                    f"AI Assistant directory not found: {self.ai_assistant_path}"
                )
                return False

            # Change to AI assistant directory
            original_cwd = os.getcwd()
            os.chdir(self.ai_assistant_path)

            try:
                result = subprocess.run(
                    ["./scripts/build.sh"],
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minutes timeout
                )

                if result.returncode == 0:
                    self.logger.info("AI Assistant container built successfully")
                    return True
                else:
                    self.logger.error(f"Container build failed: {result.stderr}")
                    return False

            finally:
                os.chdir(original_cwd)

        except Exception as e:
            self.logger.error(f"Failed to build container: {e}")
            return False

    def _pull_container(self) -> bool:
        """Pull AI Assistant container from registry (production mode)"""
        try:
            self.logger.info(f"Pulling container image: {self.container_image}")

            # Try both docker and podman
            for runtime in ["podman", "docker"]:
                try:
                    result = subprocess.run(
                        [runtime, "pull", self.container_image],
                        capture_output=True,
                        text=True,
                        timeout=300,  # 5 minutes timeout
                    )

                    if result.returncode == 0:
                        self.logger.info(
                            f"Container pulled successfully using {runtime}"
                        )
                        return True
                    else:
                        self.logger.debug(
                            f"Failed to pull with {runtime}: {result.stderr}"
                        )
                        continue

                except FileNotFoundError:
                    # Runtime not available, try next one
                    continue
                except Exception as e:
                    self.logger.debug(f"Failed to pull container with {runtime}: {e}")
                    continue

            self.logger.error("Failed to pull container with any available runtime")
            return False

        except Exception as e:
            self.logger.error(f"Failed to pull container: {e}")
            return False

    def _start_container(self) -> bool:
        """Start AI Assistant container"""
        try:
            # Stop existing container if running
            subprocess.run(
                ["podman", "stop", self.container_name], capture_output=True, timeout=30
            )

            # Remove existing container
            subprocess.run(
                ["podman", "rm", self.container_name], capture_output=True, timeout=10
            )

            # Start new container
            result = subprocess.run(
                [
                    "podman",
                    "run",
                    "-d",
                    "-p",
                    "8080:8080",
                    "--name",
                    self.container_name,
                    self.container_image,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self.logger.info("AI Assistant container started successfully")

                # Copy RAG documents if available
                self._copy_rag_documents()

                return True
            else:
                self.logger.error(f"Failed to start container: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to start container: {e}")
            return False

    def _copy_rag_documents(self) -> bool:
        """Copy RAG documents into container"""
        try:
            rag_docs_path = os.path.join(self.ai_assistant_path, "data", "rag-docs")
            if os.path.exists(rag_docs_path):
                result = subprocess.run(
                    [
                        "podman",
                        "cp",
                        rag_docs_path,
                        f"{self.container_name}:/app/data/",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    self.logger.info("RAG documents copied to container")
                    return True
                else:
                    self.logger.warning(
                        f"Failed to copy RAG documents: {result.stderr}"
                    )
            else:
                self.logger.warning(f"RAG documents not found at {rag_docs_path}")
            return False
        except Exception as e:
            self.logger.warning(f"Failed to copy RAG documents: {e}")
            return False

    def _wait_for_health(self) -> bool:
        """Wait for AI service to become healthy"""
        self.logger.info("Waiting for AI Assistant to become healthy...")

        for attempt in range(self.health_check_timeout):
            if self._ai_service_healthy():
                self.logger.info("AI Assistant is healthy")
                return True
            time.sleep(1)

        self.logger.error("AI Assistant health check timeout")
        return False

    def _setup_rag_system(self) -> bool:
        """Setup RAG system"""
        # RAG system should auto-initialize when documents are available
        # Wait a bit longer for RAG to load
        self.logger.info("Waiting for RAG system to initialize...")

        for attempt in range(60):  # 60 seconds timeout
            if self._rag_system_loaded():
                self.logger.info("RAG system loaded successfully")
                return True
            time.sleep(1)

        self.logger.warning("RAG system initialization timeout")
        return False

    def _verify_diagnostic_tools(self) -> bool:
        """Verify diagnostic tools are available"""
        return self._diagnostic_tools_available()

    def _get_ai_assistant_status(self) -> Dict[str, Any]:
        """Get comprehensive AI Assistant status"""
        status = {
            "container_exists": self._container_exists(),
            "container_running": self._container_running(),
            "ai_service_healthy": self._ai_service_healthy(),
            "rag_system_loaded": self._rag_system_loaded(),
            "diagnostic_tools_available": self._diagnostic_tools_available(),
        }

        # Get detailed health info if available
        try:
            response = requests.get(f"{self.ai_service_url}/health", timeout=5)
            if response.status_code == 200:
                status["detailed_health"] = response.json()
        except Exception:
            pass

        return status

    def get_dependencies(self) -> List[str]:
        """AI Assistant has no plugin dependencies"""
        return []

    def validate_config(self) -> bool:
        """Validate AI Assistant plugin configuration"""
        required_paths = [self.ai_assistant_path]

        for path in required_paths:
            if not os.path.exists(path):
                self.logger.error(f"Required path not found: {path}")
                return False

        return True

    def get_health_status(self) -> Dict[str, Any]:
        """Get plugin health status"""
        base_status = super().get_health_status()

        # Add AI Assistant specific status
        base_status.update(
            {
                "ai_service_url": self.ai_service_url,
                "container_name": self.container_name,
                "container_image": self.container_image,
                "container_version": self.container_version,
                "version_strategy": self.version_strategy,
                "deployment_mode": self.deployment_mode,
                "capabilities": self.capabilities,
                "ai_assistant_status": self._get_ai_assistant_status(),
            }
        )

        return base_status

    def is_healthy(self) -> bool:
        """Check if AI Assistant plugin is healthy"""
        try:
            # Check if container exists and is running
            if not self._container_exists():
                return False

            if not self._container_running():
                return False

            # Check if AI service is responding (accept degraded status)
            response = requests.get(f"{self.ai_service_url}/health", timeout=10)

            # Accept both 200 (healthy) and 503 (degraded) as healthy
            if response.status_code == 200:
                return True
            elif response.status_code == 503:
                # Check if it's degraded only due to RAG documents
                try:
                    data = response.json()
                    if "detail" in data and isinstance(data["detail"], dict):
                        detail = data["detail"]
                        if detail.get("status") == "degraded":
                            ai_service = detail.get("ai_service", {})
                            warnings = ai_service.get("warnings", [])
                            # Accept degraded status if only RAG documents not loaded
                            if (
                                len(warnings) == 1
                                and "RAG documents not loaded" in warnings[0]
                            ):
                                return True
                except:
                    pass

            return False

        except Exception as e:
            self.logger.debug(f"Health check failed: {e}")
            return False

    def _cleanup_plugin(self) -> None:
        """Cleanup AI Assistant plugin resources"""
        try:
            # Optionally stop container (configurable)
            if self.config.get("stop_on_cleanup", False):
                subprocess.run(
                    ["podman", "stop", self.container_name],
                    capture_output=True,
                    timeout=30,
                )
                self.logger.info("AI Assistant container stopped")
        except Exception as e:
            self.logger.error(f"Failed to cleanup AI Assistant: {e}")

    # Public API methods for other plugins to use

    def ask_ai(self, question: str, max_tokens: int = 300) -> Dict[str, Any]:
        """
        Ask the AI Assistant a question

        Args:
            question: Question to ask
            max_tokens: Maximum tokens in response

        Returns:
            Dict containing AI response and metadata
        """
        try:
            response = requests.post(
                f"{self.ai_service_url}/chat",
                json={"message": question, "max_tokens": max_tokens},
                timeout=30,
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"AI request failed: {response.status_code}"}

        except Exception as e:
            return {"error": f"AI request failed: {str(e)}"}

    def run_diagnostics(self, tool_name: str = None) -> Dict[str, Any]:
        """
        Run system diagnostics

        Args:
            tool_name: Specific diagnostic tool to run (None for all)

        Returns:
            Dict containing diagnostic results
        """
        try:
            if tool_name:
                url = f"{self.ai_service_url}/diagnostics/tool/{tool_name}"
                payload = {}
            else:
                url = f"{self.ai_service_url}/diagnostics"
                payload = {"include_ai_analysis": True}

            response = requests.post(url, json=payload, timeout=60)

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Diagnostics request failed: {response.status_code}"}

        except Exception as e:
            return {"error": f"Diagnostics request failed: {str(e)}"}

    def get_available_tools(self) -> Dict[str, Any]:
        """
        Get list of available diagnostic tools

        Returns:
            Dict containing available tools
        """
        try:
            response = requests.get(
                f"{self.ai_service_url}/diagnostics/tools", timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Tools request failed: {response.status_code}"}

        except Exception as e:
            return {"error": f"Tools request failed: {str(e)}"}
