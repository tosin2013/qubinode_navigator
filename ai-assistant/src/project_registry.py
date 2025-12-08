"""
Project Registry: Source project awareness for DAG creation.

This module provides:
- Registry of known projects (qubinode-pipelines, external repos)
- Project analysis for unknown directories
- Entry point discovery
- File structure understanding

Per ADR-0066: Developer Agent DAG Validation and Smart Pipelines
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class ProjectCapability(str, Enum):
    """Capabilities a project can provide."""

    VM_CREATION = "vm_creation"
    VM_DELETION = "vm_deletion"
    OPENSHIFT = "openshift"
    FREEIPA = "freeipa"
    HARBOR = "harbor"
    VAULT = "vault"
    STEP_CA = "step_ca"
    VYOS = "vyos"
    DNS = "dns"
    REGISTRY = "registry"
    GENERIC_DEPLOYMENT = "generic_deployment"


@dataclass
class ProjectEntryPoint:
    """An entry point (script) in a project."""

    name: str
    command: str
    description: str
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)


@dataclass
class ProjectInfo:
    """Information about a registered project."""

    name: str
    path: str
    git_url: Optional[str] = None
    capabilities: List[ProjectCapability] = field(default_factory=list)
    entry_points: Dict[str, ProjectEntryPoint] = field(default_factory=dict)
    config_paths: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    is_available: bool = False  # Set after checking if path exists


# Default project registry
DEFAULT_PROJECTS: Dict[str, Dict[str, Any]] = {
    "qubinode-pipelines": {
        "path": "/opt/qubinode-pipelines",
        "alt_paths": ["/opt/kcli-pipelines", "/root/qubinode-pipelines"],  # Legacy/alternative paths
        "git_url": "https://github.com/Qubinode/qubinode-pipelines.git",
        "description": "Primary infrastructure deployment pipelines for Qubinode",
        "capabilities": [
            ProjectCapability.VM_CREATION,
            ProjectCapability.VM_DELETION,
            ProjectCapability.OPENSHIFT,
            ProjectCapability.FREEIPA,
            ProjectCapability.HARBOR,
            ProjectCapability.VAULT,
            ProjectCapability.STEP_CA,
            ProjectCapability.VYOS,
            ProjectCapability.DNS,
            ProjectCapability.REGISTRY,
        ],
        "entry_points": {
            "create_vm": {
                "command": "./deploy-vm.sh {profile} {vm_name}",
                "description": "Deploy a VM using kcli profile",
                "required_params": ["profile"],
                "optional_params": ["vm_name", "memory", "cpus"],
            },
            "delete_vm": {
                "command": "./destroy-vm.sh {vm_name}",
                "description": "Delete a VM",
                "required_params": ["vm_name"],
            },
            "deploy_freeipa": {
                "command": "./freeipa/deploy-freeipa.sh",
                "description": "Deploy FreeIPA identity server",
                "required_params": [],
                "optional_params": ["domain", "realm"],
            },
            "deploy_harbor": {
                "command": "./harbor/install.sh",
                "description": "Deploy Harbor container registry",
                "required_params": [],
            },
            "deploy_vyos": {
                "command": "./vyos-router/deploy.sh",
                "description": "Deploy VyOS router",
                "required_params": [],
            },
            "deploy_step_ca": {
                "command": "./step-ca-server/deploy.sh",
                "description": "Deploy Step CA certificate authority",
                "required_params": [],
            },
        },
        "config_paths": {
            "profiles": "kcli_profiles/",
            "inventory": "inventory/",
            "vars": "vars/",
        },
    },
    "qubinode_navigator": {
        "path": "/root/qubinode_navigator",
        "git_url": "https://github.com/Qubinode/qubinode_navigator.git",
        "description": "Qubinode Navigator - Airflow-based infrastructure orchestration",
        "capabilities": [
            ProjectCapability.GENERIC_DEPLOYMENT,
        ],
        "entry_points": {
            "trigger_dag": {
                "command": "airflow dags trigger {dag_id} --conf '{conf}'",
                "description": "Trigger an Airflow DAG",
                "required_params": ["dag_id"],
                "optional_params": ["conf"],
            },
        },
        "config_paths": {
            "dags": "airflow/dags/",
            "plugins": "airflow/plugins/",
            "adrs": "docs/adrs/",
        },
    },
}


class ProjectRegistry:
    """
    Registry for managing known and discovered projects.

    Provides:
    - Project lookup by name or capability
    - Project availability checking
    - Dynamic project registration
    - Project analysis for unknown directories
    """

    def __init__(self):
        self._projects: Dict[str, ProjectInfo] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize registry with default projects."""
        if self._initialized:
            return

        for name, config in DEFAULT_PROJECTS.items():
            await self.register_project(name, config)

        self._initialized = True
        logger.info(f"Project registry initialized with {len(self._projects)} projects")

    async def register_project(
        self,
        name: str,
        config: Dict[str, Any],
    ) -> ProjectInfo:
        """
        Register a project in the registry.

        Args:
            name: Project name
            config: Project configuration dict

        Returns:
            ProjectInfo with availability status
        """
        # Parse entry points
        entry_points = {}
        for ep_name, ep_config in config.get("entry_points", {}).items():
            if isinstance(ep_config, dict):
                entry_points[ep_name] = ProjectEntryPoint(
                    name=ep_name,
                    command=ep_config.get("command", ""),
                    description=ep_config.get("description", ""),
                    required_params=ep_config.get("required_params", []),
                    optional_params=ep_config.get("optional_params", []),
                )

        # Parse capabilities
        capabilities = []
        for cap in config.get("capabilities", []):
            if isinstance(cap, ProjectCapability):
                capabilities.append(cap)
            elif isinstance(cap, str):
                try:
                    capabilities.append(ProjectCapability(cap))
                except ValueError:
                    logger.warning(f"Unknown capability: {cap}")

        # Check primary path and alternative paths
        primary_path = config.get("path", "")
        alt_paths = config.get("alt_paths", [])

        actual_path = primary_path
        is_available = await self._check_availability(primary_path)

        # If primary path not available, check alternatives
        if not is_available and alt_paths:
            for alt_path in alt_paths:
                if await self._check_availability(alt_path):
                    actual_path = alt_path
                    is_available = True
                    logger.info(f"Using alternative path for {name}: {alt_path}")
                    break

        project = ProjectInfo(
            name=name,
            path=actual_path,
            git_url=config.get("git_url"),
            description=config.get("description", ""),
            capabilities=capabilities,
            entry_points=entry_points,
            config_paths=config.get("config_paths", {}),
            is_available=is_available,
        )

        self._projects[name] = project
        logger.info(f"Registered project: {name} at {actual_path} (available: {project.is_available})")

        return project

    async def _check_availability(self, path: str) -> bool:
        """Check if a project path exists and is accessible."""
        try:
            return Path(path).exists() and Path(path).is_dir()
        except Exception as e:
            logger.warning(f"Error checking path {path}: {e}")
            return False

    def get_project(self, name: str) -> Optional[ProjectInfo]:
        """Get a project by name."""
        return self._projects.get(name)

    def get_all_projects(self) -> List[ProjectInfo]:
        """Get all registered projects."""
        return list(self._projects.values())

    def get_available_projects(self) -> List[ProjectInfo]:
        """Get only available (path exists) projects."""
        return [p for p in self._projects.values() if p.is_available]

    def find_by_capability(
        self,
        capability: ProjectCapability,
    ) -> List[ProjectInfo]:
        """Find projects that provide a specific capability."""
        return [p for p in self._projects.values() if capability in p.capabilities and p.is_available]

    def find_for_task(self, task_description: str) -> List[ProjectInfo]:
        """
        Find projects that might be able to handle a task.

        Uses keyword matching to identify relevant capabilities.
        """
        task_lower = task_description.lower()

        # Map keywords to capabilities
        keyword_map = {
            "vm": [ProjectCapability.VM_CREATION, ProjectCapability.VM_DELETION],
            "virtual machine": [ProjectCapability.VM_CREATION],
            "centos": [ProjectCapability.VM_CREATION],
            "rhel": [ProjectCapability.VM_CREATION],
            "fedora": [ProjectCapability.VM_CREATION],
            "openshift": [ProjectCapability.OPENSHIFT],
            "ocp": [ProjectCapability.OPENSHIFT],
            "kubernetes": [ProjectCapability.OPENSHIFT],
            "freeipa": [ProjectCapability.FREEIPA],
            "identity": [ProjectCapability.FREEIPA],
            "ldap": [ProjectCapability.FREEIPA],
            "harbor": [ProjectCapability.HARBOR],
            "registry": [ProjectCapability.REGISTRY, ProjectCapability.HARBOR],
            "container registry": [ProjectCapability.HARBOR],
            "vault": [ProjectCapability.VAULT],
            "secrets": [ProjectCapability.VAULT],
            "step ca": [ProjectCapability.STEP_CA],
            "certificate": [ProjectCapability.STEP_CA],
            "vyos": [ProjectCapability.VYOS],
            "router": [ProjectCapability.VYOS],
            "dns": [ProjectCapability.DNS],
        }

        # Find matching capabilities
        matching_caps = set()
        for keyword, caps in keyword_map.items():
            if keyword in task_lower:
                matching_caps.update(caps)

        # Find projects with those capabilities
        matching_projects = []
        for project in self._projects.values():
            if not project.is_available:
                continue

            if matching_caps.intersection(set(project.capabilities)):
                matching_projects.append(project)

        # If no specific match, return projects with generic deployment
        if not matching_projects:
            matching_projects = self.find_by_capability(ProjectCapability.GENERIC_DEPLOYMENT)

        return matching_projects

    async def analyze_project(self, path: str) -> Dict[str, Any]:
        """
        Analyze an unknown project directory to understand its structure.

        Returns:
            Dict with project analysis including:
            - detected_type: Type of project (python, ansible, shell, etc.)
            - entry_points: Discovered scripts/commands
            - config_files: Configuration files found
            - dependencies: Detected dependencies
            - suggestions: Suggestions for DAG creation
        """
        analysis = {
            "path": path,
            "exists": False,
            "detected_type": "unknown",
            "entry_points": [],
            "config_files": [],
            "dependencies": [],
            "suggestions": [],
        }

        project_path = Path(path)
        if not project_path.exists():
            analysis["error"] = f"Path does not exist: {path}"
            return analysis

        analysis["exists"] = True

        # Check for common project indicators
        files = list(project_path.iterdir())
        file_names = [f.name for f in files]

        # Detect project type
        if "requirements.txt" in file_names or "setup.py" in file_names:
            analysis["detected_type"] = "python"
            if "requirements.txt" in file_names:
                analysis["config_files"].append("requirements.txt")
                # Parse dependencies
                try:
                    req_file = project_path / "requirements.txt"
                    deps = req_file.read_text().strip().split("\n")
                    analysis["dependencies"] = [d.split("==")[0].split(">=")[0].strip() for d in deps if d.strip() and not d.startswith("#")]
                except Exception:
                    pass

        if "package.json" in file_names:
            analysis["detected_type"] = "nodejs"
            analysis["config_files"].append("package.json")

        if "Dockerfile" in file_names:
            analysis["has_docker"] = True
            analysis["config_files"].append("Dockerfile")

        if "docker-compose.yml" in file_names or "docker-compose.yaml" in file_names:
            analysis["has_docker_compose"] = True
            compose_file = "docker-compose.yml" if "docker-compose.yml" in file_names else "docker-compose.yaml"
            analysis["config_files"].append(compose_file)

        if "ansible.cfg" in file_names or "playbook.yml" in file_names:
            analysis["detected_type"] = "ansible"
            analysis["config_files"].extend([f for f in file_names if f.endswith(".yml") or f.endswith(".yaml")][:5])

        # Find executable scripts
        for f in files:
            if f.is_file():
                # Check for shell scripts
                if f.name.endswith(".sh"):
                    try:
                        if os.access(f, os.X_OK):
                            analysis["entry_points"].append(
                                {
                                    "name": f.name,
                                    "path": str(f),
                                    "type": "shell",
                                    "executable": True,
                                }
                            )
                    except Exception:
                        pass

                # Check for deploy/install/run scripts
                if f.name.lower() in ["deploy.sh", "install.sh", "run.sh", "start.sh", "main.py", "app.py"]:
                    analysis["entry_points"].append(
                        {
                            "name": f.name,
                            "path": str(f),
                            "type": "entry_point",
                            "primary": True,
                        }
                    )

        # Generate suggestions
        if analysis["entry_points"]:
            primary = next((ep for ep in analysis["entry_points"] if ep.get("primary")), analysis["entry_points"][0])
            analysis["suggestions"].append(f"Use '{primary['name']}' as the main entry point for DAG")

        if analysis.get("has_docker"):
            analysis["suggestions"].append("Project has Dockerfile - consider container-based deployment")

        if analysis.get("has_docker_compose"):
            analysis["suggestions"].append("Project has docker-compose - can use DockerOperator")

        if "redis" in str(analysis["dependencies"]).lower():
            analysis["suggestions"].append("Project uses Redis - ensure Redis is available before deployment")

        if "postgres" in str(analysis["dependencies"]).lower() or "psycopg" in str(analysis["dependencies"]).lower():
            analysis["suggestions"].append("Project uses PostgreSQL - ensure database is available")

        return analysis

    async def ensure_project_available(
        self,
        name: str,
        clone_if_missing: bool = False,
    ) -> ProjectInfo:
        """
        Ensure a project is available, optionally cloning if missing.

        Args:
            name: Project name
            clone_if_missing: Whether to clone from git if not present

        Returns:
            ProjectInfo with updated availability status
        """
        project = self.get_project(name)
        if not project:
            raise ValueError(f"Unknown project: {name}")

        # Recheck availability
        project.is_available = await self._check_availability(project.path)

        if project.is_available:
            return project

        if clone_if_missing and project.git_url:
            logger.info(f"Cloning project {name} from {project.git_url}")
            try:
                import subprocess

                result = subprocess.run(
                    ["git", "clone", project.git_url, project.path],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode == 0:
                    project.is_available = True
                    logger.info(f"Successfully cloned {name} to {project.path}")
                else:
                    logger.error(f"Failed to clone {name}: {result.stderr}")
            except Exception as e:
                logger.error(f"Error cloning {name}: {e}")

        return project

    def get_entry_point(
        self,
        project_name: str,
        entry_point_name: str,
    ) -> Optional[ProjectEntryPoint]:
        """Get a specific entry point from a project."""
        project = self.get_project(project_name)
        if not project:
            return None
        return project.entry_points.get(entry_point_name)

    def format_command(
        self,
        project_name: str,
        entry_point_name: str,
        params: Dict[str, str],
    ) -> Optional[str]:
        """
        Format a command with parameters for execution.

        Args:
            project_name: Name of the project
            entry_point_name: Name of the entry point
            params: Parameters to substitute in the command

        Returns:
            Formatted command string or None if not found
        """
        entry_point = self.get_entry_point(project_name, entry_point_name)
        if not entry_point:
            return None

        project = self.get_project(project_name)
        if not project:
            return None

        # Start with the command template
        command = entry_point.command

        # Substitute parameters
        for key, value in params.items():
            command = command.replace(f"{{{key}}}", str(value))

        # Remove any unsubstituted optional params
        import re

        command = re.sub(r"\{[^}]+\}", "", command)

        # Prepend project path for relative commands
        if command.startswith("./"):
            command = f"cd {project.path} && {command}"

        return command.strip()


# Singleton instance
_registry: Optional[ProjectRegistry] = None


async def get_project_registry() -> ProjectRegistry:
    """Get the singleton project registry instance."""
    global _registry
    if _registry is None:
        _registry = ProjectRegistry()
        await _registry.initialize()
    return _registry


async def find_project_for_task(task_description: str) -> List[ProjectInfo]:
    """Convenience function to find projects for a task."""
    registry = await get_project_registry()
    return registry.find_for_task(task_description)


async def analyze_external_project(path: str) -> Dict[str, Any]:
    """Convenience function to analyze an external project."""
    registry = await get_project_registry()
    return await registry.analyze_project(path)
