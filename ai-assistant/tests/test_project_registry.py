"""
Tests for project_registry.py - Source project awareness for DAG creation.

Tests cover:
- ProjectCapability enum
- ProjectEntryPoint and ProjectInfo dataclasses
- ProjectRegistry class methods
- Singleton registry functions
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Set test mode
os.environ["TEST_MODE"] = "true"

from project_registry import (
    ProjectCapability,
    ProjectEntryPoint,
    ProjectInfo,
    ProjectRegistry,
    DEFAULT_PROJECTS,
    get_project_registry,
    find_project_for_task,
    analyze_external_project,
)


class TestProjectCapability:
    """Tests for ProjectCapability enum."""

    def test_all_capabilities_exist(self):
        """Test that all capabilities are defined."""
        assert ProjectCapability.VM_CREATION
        assert ProjectCapability.VM_DELETION
        assert ProjectCapability.OPENSHIFT
        assert ProjectCapability.FREEIPA
        assert ProjectCapability.HARBOR
        assert ProjectCapability.VAULT
        assert ProjectCapability.STEP_CA
        assert ProjectCapability.VYOS
        assert ProjectCapability.DNS
        assert ProjectCapability.REGISTRY
        assert ProjectCapability.GENERIC_DEPLOYMENT

    def test_capability_values(self):
        """Test capability enum values."""
        assert ProjectCapability.VM_CREATION.value == "vm_creation"
        assert ProjectCapability.FREEIPA.value == "freeipa"
        assert ProjectCapability.OPENSHIFT.value == "openshift"


class TestProjectEntryPoint:
    """Tests for ProjectEntryPoint dataclass."""

    def test_entry_point_minimal(self):
        """Test entry point with minimal fields."""
        ep = ProjectEntryPoint(
            name="deploy",
            command="./deploy.sh",
            description="Deploy the service",
        )
        assert ep.name == "deploy"
        assert ep.command == "./deploy.sh"
        assert ep.description == "Deploy the service"
        assert ep.required_params == []
        assert ep.optional_params == []

    def test_entry_point_full(self):
        """Test entry point with all fields."""
        ep = ProjectEntryPoint(
            name="create_vm",
            command="./deploy-vm.sh {profile} {vm_name}",
            description="Create a VM",
            required_params=["profile"],
            optional_params=["vm_name", "memory"],
        )
        assert ep.name == "create_vm"
        assert "profile" in ep.required_params
        assert "memory" in ep.optional_params


class TestProjectInfo:
    """Tests for ProjectInfo dataclass."""

    def test_project_info_minimal(self):
        """Test project info with minimal fields."""
        info = ProjectInfo(
            name="test-project",
            path="/opt/test-project",
        )
        assert info.name == "test-project"
        assert info.path == "/opt/test-project"
        assert info.git_url is None
        assert info.capabilities == []
        assert info.entry_points == {}
        assert info.config_paths == {}
        assert info.description == ""
        assert info.is_available is False

    def test_project_info_full(self):
        """Test project info with all fields."""
        entry_point = ProjectEntryPoint(
            name="deploy",
            command="./deploy.sh",
            description="Deploy",
        )
        info = ProjectInfo(
            name="freeipa-project",
            path="/opt/freeipa",
            git_url="https://github.com/example/freeipa.git",
            capabilities=[ProjectCapability.FREEIPA, ProjectCapability.DNS],
            entry_points={"deploy": entry_point},
            config_paths={"vars": "vars/"},
            description="FreeIPA deployment project",
            is_available=True,
        )
        assert info.name == "freeipa-project"
        assert info.git_url is not None
        assert ProjectCapability.FREEIPA in info.capabilities
        assert "deploy" in info.entry_points
        assert info.is_available is True


class TestDefaultProjects:
    """Tests for default project definitions."""

    def test_qubinode_pipelines_exists(self):
        """Test qubinode-pipelines is defined."""
        assert "qubinode-pipelines" in DEFAULT_PROJECTS

    def test_qubinode_navigator_exists(self):
        """Test qubinode_navigator is defined."""
        assert "qubinode_navigator" in DEFAULT_PROJECTS

    def test_pipelines_has_entry_points(self):
        """Test qubinode-pipelines has expected entry points."""
        pipelines = DEFAULT_PROJECTS["qubinode-pipelines"]
        assert "entry_points" in pipelines
        assert "create_vm" in pipelines["entry_points"]
        assert "deploy_freeipa" in pipelines["entry_points"]

    def test_pipelines_has_capabilities(self):
        """Test qubinode-pipelines has capabilities."""
        pipelines = DEFAULT_PROJECTS["qubinode-pipelines"]
        caps = pipelines["capabilities"]
        assert ProjectCapability.VM_CREATION in caps
        assert ProjectCapability.FREEIPA in caps


class TestProjectRegistry:
    """Tests for ProjectRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return ProjectRegistry()

    @pytest.mark.asyncio
    async def test_registry_initialization(self, registry):
        """Test registry initializes correctly."""
        assert registry._projects == {}
        assert registry._initialized is False

    @pytest.mark.asyncio
    async def test_registry_initialize_loads_defaults(self, registry):
        """Test initialize loads default projects."""
        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = False  # Projects not available on test system

            await registry.initialize()

            assert registry._initialized is True
            assert len(registry._projects) > 0

    @pytest.mark.asyncio
    async def test_registry_initialize_idempotent(self, registry):
        """Test initialize only runs once."""
        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = False

            await registry.initialize()
            count1 = len(registry._projects)

            await registry.initialize()  # Second call
            count2 = len(registry._projects)

            assert count1 == count2

    @pytest.mark.asyncio
    async def test_register_project(self, registry):
        """Test registering a custom project."""
        config = {
            "path": "/opt/custom-project",
            "description": "Custom project for testing",
            "capabilities": [ProjectCapability.VM_CREATION],
            "entry_points": {
                "deploy": {
                    "command": "./deploy.sh",
                    "description": "Deploy",
                    "required_params": [],
                },
            },
        }

        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True

            project = await registry.register_project("custom-project", config)

            assert project.name == "custom-project"
            assert project.is_available is True
            assert ProjectCapability.VM_CREATION in project.capabilities

    @pytest.mark.asyncio
    async def test_register_project_with_string_capabilities(self, registry):
        """Test registering project with string capabilities."""
        config = {
            "path": "/opt/test",
            "capabilities": ["vm_creation", "freeipa"],  # String values
        }

        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = False

            project = await registry.register_project("test", config)

            assert ProjectCapability.VM_CREATION in project.capabilities
            assert ProjectCapability.FREEIPA in project.capabilities

    @pytest.mark.asyncio
    async def test_register_project_alt_paths(self, registry):
        """Test registering project with alternative paths."""
        config = {
            "path": "/opt/primary",
            "alt_paths": ["/opt/secondary", "/opt/tertiary"],
        }

        async def check_path(path):
            # Only secondary path exists
            return path == "/opt/secondary"

        with patch.object(registry, "_check_availability", side_effect=check_path):
            project = await registry.register_project("test", config)

            assert project.path == "/opt/secondary"
            assert project.is_available is True

    @pytest.mark.asyncio
    async def test_check_availability_true(self, registry):
        """Test _check_availability returns True for existing path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await registry._check_availability(tmpdir)
            assert result is True

    @pytest.mark.asyncio
    async def test_check_availability_false(self, registry):
        """Test _check_availability returns False for non-existing path."""
        result = await registry._check_availability("/nonexistent/path/12345")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_project(self, registry):
        """Test getting a project by name."""
        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            await registry.register_project("test-proj", {"path": "/opt/test"})

            project = registry.get_project("test-proj")
            assert project is not None
            assert project.name == "test-proj"

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, registry):
        """Test getting a non-existent project."""
        project = registry.get_project("nonexistent")
        assert project is None

    @pytest.mark.asyncio
    async def test_get_all_projects(self, registry):
        """Test getting all projects."""
        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            await registry.register_project("proj1", {"path": "/opt/proj1"})
            await registry.register_project("proj2", {"path": "/opt/proj2"})

            all_projects = registry.get_all_projects()
            assert len(all_projects) == 2

    @pytest.mark.asyncio
    async def test_get_available_projects(self, registry):
        """Test getting only available projects."""
        async def check_avail(path):
            return path == "/opt/available"

        with patch.object(registry, "_check_availability", side_effect=check_avail):
            await registry.register_project("available", {"path": "/opt/available"})
            await registry.register_project("unavailable", {"path": "/opt/unavailable"})

            available = registry.get_available_projects()
            assert len(available) == 1
            assert available[0].name == "available"

    @pytest.mark.asyncio
    async def test_find_by_capability(self, registry):
        """Test finding projects by capability."""
        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True

            await registry.register_project("freeipa-proj", {
                "path": "/opt/freeipa",
                "capabilities": [ProjectCapability.FREEIPA],
            })
            await registry.register_project("vm-proj", {
                "path": "/opt/vm",
                "capabilities": [ProjectCapability.VM_CREATION],
            })

            freeipa_projects = registry.find_by_capability(ProjectCapability.FREEIPA)
            assert len(freeipa_projects) == 1
            assert freeipa_projects[0].name == "freeipa-proj"

    @pytest.mark.asyncio
    async def test_find_for_task_vm(self, registry):
        """Test finding projects for VM-related task."""
        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True

            await registry.register_project("vm-proj", {
                "path": "/opt/vm",
                "capabilities": [ProjectCapability.VM_CREATION],
            })

            matches = registry.find_for_task("create a centos vm")
            assert len(matches) > 0

    @pytest.mark.asyncio
    async def test_find_for_task_freeipa(self, registry):
        """Test finding projects for FreeIPA task."""
        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True

            await registry.register_project("freeipa-proj", {
                "path": "/opt/freeipa",
                "capabilities": [ProjectCapability.FREEIPA],
            })

            matches = registry.find_for_task("deploy freeipa identity server")
            assert len(matches) > 0

    @pytest.mark.asyncio
    async def test_find_for_task_openshift(self, registry):
        """Test finding projects for OpenShift task."""
        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True

            await registry.register_project("ocp-proj", {
                "path": "/opt/ocp",
                "capabilities": [ProjectCapability.OPENSHIFT],
            })

            matches = registry.find_for_task("deploy kubernetes cluster")
            assert len(matches) > 0

    @pytest.mark.asyncio
    async def test_find_for_task_generic_fallback(self, registry):
        """Test find_for_task falls back to generic deployment."""
        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True

            await registry.register_project("generic", {
                "path": "/opt/generic",
                "capabilities": [ProjectCapability.GENERIC_DEPLOYMENT],
            })

            matches = registry.find_for_task("do something completely unique")
            assert len(matches) > 0


class TestProjectAnalysis:
    """Tests for project analysis functionality."""

    @pytest.fixture
    def registry(self):
        return ProjectRegistry()

    @pytest.mark.asyncio
    async def test_analyze_nonexistent_path(self, registry):
        """Test analyzing a non-existent path."""
        result = await registry.analyze_project("/nonexistent/path/12345")

        assert result["exists"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_analyze_python_project(self, registry):
        """Test analyzing a Python project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a Python project structure
            req_file = Path(tmpdir) / "requirements.txt"
            req_file.write_text("fastapi>=0.100.0\nuvicorn\nredis\n")

            main_file = Path(tmpdir) / "main.py"
            main_file.write_text("# Main app")

            result = await registry.analyze_project(tmpdir)

            assert result["exists"] is True
            assert result["detected_type"] == "python"
            assert "requirements.txt" in result["config_files"]
            assert "fastapi" in result["dependencies"]

    @pytest.mark.asyncio
    async def test_analyze_nodejs_project(self, registry):
        """Test analyzing a Node.js project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_file = Path(tmpdir) / "package.json"
            pkg_file.write_text('{"name": "test-project"}')

            result = await registry.analyze_project(tmpdir)

            assert result["detected_type"] == "nodejs"
            assert "package.json" in result["config_files"]

    @pytest.mark.asyncio
    async def test_analyze_docker_project(self, registry):
        """Test analyzing a Docker project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile = Path(tmpdir) / "Dockerfile"
            dockerfile.write_text("FROM python:3.11")

            result = await registry.analyze_project(tmpdir)

            assert result.get("has_docker") is True
            assert "Dockerfile" in result["config_files"]

    @pytest.mark.asyncio
    async def test_analyze_ansible_project(self, registry):
        """Test analyzing an Ansible project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ansible_cfg = Path(tmpdir) / "ansible.cfg"
            ansible_cfg.write_text("[defaults]\n")

            result = await registry.analyze_project(tmpdir)

            assert result["detected_type"] == "ansible"

    @pytest.mark.asyncio
    async def test_analyze_finds_shell_scripts(self, registry):
        """Test analyzing finds executable shell scripts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            deploy_script = Path(tmpdir) / "deploy.sh"
            deploy_script.write_text("#!/bin/bash\necho 'deploy'")
            deploy_script.chmod(0o755)

            result = await registry.analyze_project(tmpdir)

            entry_points = result["entry_points"]
            assert len(entry_points) > 0


class TestEnsureProjectAvailable:
    """Tests for ensure_project_available method."""

    @pytest.fixture
    def registry(self):
        return ProjectRegistry()

    @pytest.mark.asyncio
    async def test_ensure_unknown_project_raises(self, registry):
        """Test ensure raises for unknown project."""
        with pytest.raises(ValueError, match="Unknown project"):
            await registry.ensure_project_available("nonexistent")

    @pytest.mark.asyncio
    async def test_ensure_already_available(self, registry):
        """Test ensure returns if already available."""
        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            await registry.register_project("test", {"path": "/opt/test"})

            project = await registry.ensure_project_available("test")
            assert project.is_available is True

    @pytest.mark.asyncio
    async def test_ensure_clones_if_missing(self, registry):
        """Test ensure clones project if missing and clone_if_missing=True."""
        async def check_avail_dynamic(path):
            # Start unavailable, become available after clone
            return registry._projects.get("test", MagicMock()).is_available

        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = False

            await registry.register_project("test", {
                "path": "/opt/test",
                "git_url": "https://github.com/example/test.git",
            })

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                _project = await registry.ensure_project_available("test", clone_if_missing=True)

                mock_run.assert_called_once()
                assert "git" in mock_run.call_args[0][0]


class TestEntryPointAndCommand:
    """Tests for entry point and command formatting."""

    @pytest.fixture
    def registry(self):
        return ProjectRegistry()

    @pytest.mark.asyncio
    async def test_get_entry_point(self, registry):
        """Test getting an entry point."""
        config = {
            "path": "/opt/test",
            "entry_points": {
                "deploy": {
                    "command": "./deploy.sh",
                    "description": "Deploy",
                    "required_params": [],
                },
            },
        }

        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            await registry.register_project("test", config)

            ep = registry.get_entry_point("test", "deploy")
            assert ep is not None
            assert ep.name == "deploy"

    @pytest.mark.asyncio
    async def test_get_entry_point_not_found(self, registry):
        """Test getting non-existent entry point."""
        ep = registry.get_entry_point("nonexistent", "deploy")
        assert ep is None

    @pytest.mark.asyncio
    async def test_format_command(self, registry):
        """Test formatting a command with parameters."""
        config = {
            "path": "/opt/test",
            "entry_points": {
                "create_vm": {
                    "command": "./deploy-vm.sh {profile} {vm_name}",
                    "description": "Create VM",
                    "required_params": ["profile"],
                    "optional_params": ["vm_name"],
                },
            },
        }

        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            await registry.register_project("test", config)

            command = registry.format_command("test", "create_vm", {
                "profile": "centos9stream",
                "vm_name": "test-vm",
            })

            assert command is not None
            assert "centos9stream" in command
            assert "test-vm" in command
            assert "cd /opt/test" in command

    @pytest.mark.asyncio
    async def test_format_command_removes_unsubstituted(self, registry):
        """Test format_command removes unsubstituted parameters."""
        config = {
            "path": "/opt/test",
            "entry_points": {
                "deploy": {
                    "command": "./deploy.sh {required} {optional}",
                    "description": "Deploy",
                    "required_params": ["required"],
                    "optional_params": ["optional"],
                },
            },
        }

        with patch.object(registry, "_check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            await registry.register_project("test", config)

            command = registry.format_command("test", "deploy", {"required": "value"})

            assert "{optional}" not in command
            assert "value" in command


class TestSingletonFunctions:
    """Tests for singleton and convenience functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset the singleton before each test."""
        import project_registry
        project_registry._registry = None
        yield
        project_registry._registry = None

    @pytest.mark.asyncio
    async def test_get_project_registry(self):
        """Test get_project_registry returns initialized registry."""
        with patch("project_registry.ProjectRegistry._check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = False

            registry = await get_project_registry()

            assert registry is not None
            assert registry._initialized is True

    @pytest.mark.asyncio
    async def test_get_project_registry_singleton(self):
        """Test get_project_registry returns same instance."""
        with patch("project_registry.ProjectRegistry._check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = False

            registry1 = await get_project_registry()
            registry2 = await get_project_registry()

            assert registry1 is registry2

    @pytest.mark.asyncio
    async def test_find_project_for_task(self):
        """Test find_project_for_task convenience function."""
        with patch("project_registry.ProjectRegistry._check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True

            projects = await find_project_for_task("deploy freeipa server")

            # Should find at least one project (from defaults)
            assert isinstance(projects, list)

    @pytest.mark.asyncio
    async def test_analyze_external_project(self):
        """Test analyze_external_project convenience function."""
        with patch("project_registry.ProjectRegistry._check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = False

            with tempfile.TemporaryDirectory() as tmpdir:
                result = await analyze_external_project(tmpdir)

                assert result["exists"] is True
                assert result["detected_type"] is not None
