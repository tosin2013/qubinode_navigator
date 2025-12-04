"""
Tests for Qubinode Navigator Update Manager

Tests the automated update detection system including OS packages,
software components, and Ansible collections with compatibility analysis.
"""

import pytest
import unittest.mock as mock
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.update_manager import (
    UpdateDetector,
    UpdateInfo,
    UpdateBatch,
    CompatibilityMatrix,
)


class TestUpdateDetector:
    """Test cases for update detector functionality"""

    def setup_method(self):
        """Setup test environment"""
        # Create temporary cache directory
        self.temp_cache_dir = tempfile.mkdtemp()

        # Create temporary compatibility file
        self.temp_compat_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
        self.temp_compat_file.write(
            """
podman:
  supported_versions:
    "10": ["4.9.0", "5.0.0"]
    "9": ["4.6.0", "4.9.0"]
  known_issues: []
  test_results:
    "4.9.0": "passed"
    "5.0.0": "needs_testing"
  last_updated: "2025-11-08T00:00:00"
        """
        )
        self.temp_compat_file.close()

        # Update detector configuration
        self.config = {
            "ai_assistant_url": "http://test:8080",
            "cache_directory": self.temp_cache_dir,
            "compatibility_file": self.temp_compat_file.name,
            "check_interval": 3600,
        }

        # Create detector instance
        self.detector = UpdateDetector(self.config)

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil

        try:
            shutil.rmtree(self.temp_cache_dir)
            os.unlink(self.temp_compat_file.name)
        except Exception:
            pass

    def test_detector_initialization(self):
        """Test update detector initialization"""
        assert self.detector.check_interval == 3600
        assert self.detector.ai_assistant_url == "http://test:8080"
        assert Path(self.detector.cache_directory).exists()
        assert len(self.detector.compatibility_matrix) > 0
        assert "podman" in self.detector.compatibility_matrix

    def test_compatibility_matrix_loading(self):
        """Test compatibility matrix loading"""
        matrix = self.detector.compatibility_matrix["podman"]

        assert matrix.component_name == "podman"
        assert "10" in matrix.supported_versions
        assert "4.9.0" in matrix.supported_versions["10"]
        assert matrix.test_results["4.9.0"] == "passed"
        assert matrix.test_results["5.0.0"] == "needs_testing"

    @mock.patch("subprocess.run")
    async def test_get_os_info(self, mock_run):
        """Test OS information detection"""
        # Mock os-release file content
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'ID="centos"\nVERSION_ID="10"\nNAME="CentOS Stream"'

        os_info = await self.detector._get_os_info()

        assert os_info["id"] == "centos"
        assert os_info["version_id"] == "10"
        assert os_info["name"] == "CentOS Stream"

    @mock.patch("subprocess.run")
    async def test_detect_rpm_updates(self, mock_run):
        """Test RPM package update detection"""
        # Mock dnf check-update output
        mock_run.return_value.returncode = 100  # Updates available
        mock_run.return_value.stdout = """
kernel.x86_64                    6.12.1-1.el10                    baseos
podman.x86_64                    5.0.1-1.el10                     appstream
        """

        # Mock current version queries
        with mock.patch.object(self.detector, "_get_rpm_current_version") as mock_version:
            mock_version.side_effect = ["6.12.0-1.el10", "4.9.0-1.el10"]

            updates = await self.detector._detect_rpm_updates()

            assert len(updates) == 2
            assert updates[0].component_name == "kernel"
            assert updates[0].current_version == "6.12.0-1.el10"
            assert updates[0].available_version == "6.12.1-1.el10"
            assert updates[0].component_type == "os_package"

    @mock.patch("subprocess.run")
    async def test_detect_apt_updates(self, mock_run):
        """Test APT package update detection"""
        # Mock apt update and list commands
        mock_run.side_effect = [
            mock.MagicMock(returncode=0),  # apt update
            mock.MagicMock(
                returncode=0,
                stdout="Listing...\nkernel-image/focal-updates 5.15.0-91 amd64 [upgradable from: 5.15.0-90]",
            ),  # apt list
        ]

        # Mock current version query
        with mock.patch.object(self.detector, "_get_apt_current_version") as mock_version:
            mock_version.return_value = "5.15.0-90"

            updates = await self.detector._detect_apt_updates()

            assert len(updates) == 1
            assert updates[0].component_name == "kernel-image"
            assert updates[0].current_version == "5.15.0-90"
            assert updates[0].available_version == "5.15.0-91"

    @mock.patch("subprocess.run")
    async def test_check_podman_updates(self, mock_run):
        """Test Podman update checking"""
        # Mock podman --version output
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "podman version 4.9.0"

        # Mock GitHub API response
        with mock.patch.object(self.detector, "_get_github_latest_release") as mock_github:
            mock_github.return_value = "5.0.1"

            updates = await self.detector._check_podman_updates()

            assert len(updates) == 1
            assert updates[0].component_name == "podman"
            assert updates[0].current_version == "4.9.0"
            assert updates[0].available_version == "5.0.1"
            assert updates[0].component_type == "software"

    @mock.patch("subprocess.run")
    async def test_check_ansible_updates(self, mock_run):
        """Test Ansible update checking"""
        # Mock ansible --version output
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "ansible [core 2.15.0]"

        # Mock PyPI API response
        with mock.patch.object(self.detector, "_get_pypi_latest_version") as mock_pypi:
            mock_pypi.return_value = "2.16.0"

            updates = await self.detector._check_ansible_updates()

            assert len(updates) == 1
            assert updates[0].component_name == "ansible"
            assert updates[0].current_version == "2.15.0"
            assert updates[0].available_version == "2.16.0"

    @mock.patch("subprocess.run")
    async def test_detect_collection_updates(self, mock_run):
        """Test Ansible collection update detection"""
        # Mock ansible-galaxy collection list output
        collections_json = {
            "/usr/share/ansible/collections/ansible_collections": {
                "community.general": {"version": "7.0.0"},
                "ansible.posix": {"version": "1.5.0"},
            }
        }

        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(collections_json)

        # Mock Galaxy API responses
        with mock.patch.object(self.detector, "_get_galaxy_latest_version") as mock_galaxy:
            mock_galaxy.side_effect = ["8.0.0", "1.6.0"]

            updates = await self.detector.detect_collection_updates()

            assert len(updates) == 2
            assert updates[0].component_name == "community.general"
            assert updates[0].current_version == "7.0.0"
            assert updates[0].available_version == "8.0.0"
            assert updates[0].component_type == "collection"

    @mock.patch("requests.get")
    async def test_get_github_latest_release(self, mock_get):
        """Test GitHub latest release fetching"""
        # Mock GitHub API response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tag_name": "v5.0.1"}
        mock_get.return_value = mock_response

        version = await self.detector._get_github_latest_release("containers/podman")

        assert version == "5.0.1"
        mock_get.assert_called_once_with("https://api.github.com/repos/containers/podman/releases/latest", timeout=10)

    @mock.patch("requests.get")
    async def test_get_pypi_latest_version(self, mock_get):
        """Test PyPI latest version fetching"""
        # Mock PyPI API response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {"version": "2.16.0"}}
        mock_get.return_value = mock_response

        version = await self.detector._get_pypi_latest_version("ansible")

        assert version == "2.16.0"
        mock_get.assert_called_once_with("https://pypi.org/pypi/ansible/json", timeout=10)

    @mock.patch("requests.get")
    async def test_get_galaxy_latest_version(self, mock_get):
        """Test Ansible Galaxy latest version fetching"""
        # Mock Galaxy API response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"latest_version": {"version": "8.0.0"}}
        mock_get.return_value = mock_response

        version = await self.detector._get_galaxy_latest_version("community.general")

        assert version == "8.0.0"
        mock_get.assert_called_once_with(
            "https://galaxy.ansible.com/api/v2/collections/community/general/",
            timeout=10,
        )

    async def test_determine_update_severity(self):
        """Test update severity determination"""
        # Security packages should get security severity
        severity = await self.detector._determine_update_severity("kernel", "6.12.1")
        assert severity == "security"

        severity = await self.detector._determine_update_severity("openssl", "3.0.1")
        assert severity == "security"

        # System packages should get important severity
        severity = await self.detector._determine_update_severity("systemd", "255")
        assert severity == "important"

        # Other packages should get moderate severity
        severity = await self.detector._determine_update_severity("some-app", "1.0.1")
        assert severity == "moderate"

    async def test_check_compatibility_with_matrix(self):
        """Test compatibility checking using matrix"""
        # Create test update
        update = UpdateInfo(
            component_type="software",
            component_name="podman",
            current_version="4.9.0",
            available_version="5.0.0",
            severity="moderate",
            description="Test update",
            release_date=datetime.now().isoformat(),
        )

        # Mock OS info
        with mock.patch.object(self.detector, "_get_os_info") as mock_os:
            mock_os.return_value = {"version_id": "10"}

            compatibility = await self.detector.check_compatibility(update)

            # Should return needs_testing based on test_results
            assert compatibility == "needs_testing"

    @mock.patch("requests.post")
    async def test_ai_compatibility_check(self, mock_post):
        """Test AI-powered compatibility checking"""
        # Mock AI response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "This update is compatible with your system."}
        mock_post.return_value = mock_response

        update = UpdateInfo(
            component_type="software",
            component_name="test-app",
            current_version="1.0.0",
            available_version="1.1.0",
            severity="moderate",
            description="Test update",
            release_date=datetime.now().isoformat(),
        )

        result = await self.detector._ai_compatibility_check(update)

        assert result == "compatible"
        mock_post.assert_called_once()

    async def test_create_update_batches(self):
        """Test update batch creation"""
        # Create test updates with different severities
        updates = [
            UpdateInfo(
                component_type="os_package",
                component_name="kernel",
                current_version="6.12.0",
                available_version="6.12.1",
                severity="security",
                description="Security update",
                release_date=datetime.now().isoformat(),
            ),
            UpdateInfo(
                component_type="os_package",
                component_name="glibc",
                current_version="2.38",
                available_version="2.39",
                severity="critical",
                description="Critical update",
                release_date=datetime.now().isoformat(),
            ),
            UpdateInfo(
                component_type="software",
                component_name="podman",
                current_version="4.9.0",
                available_version="5.0.0",
                severity="moderate",
                description="Feature update",
                release_date=datetime.now().isoformat(),
            ),
        ]

        batches = await self.detector.create_update_batches(updates)

        # Should create security, critical, and maintenance batches
        assert len(batches) == 3

        batch_types = [batch.batch_type for batch in batches]
        assert "security" in batch_types
        assert "critical" in batch_types
        assert "maintenance" in batch_types

        # Security batch should contain kernel update
        security_batch = next(b for b in batches if b.batch_type == "security")
        assert len(security_batch.updates) == 1
        assert security_batch.updates[0].component_name == "kernel"
        assert security_batch.requires_reboot is True  # Kernel update requires reboot

    @mock.patch.object(UpdateDetector, "detect_os_updates")
    @mock.patch.object(UpdateDetector, "detect_software_updates")
    @mock.patch.object(UpdateDetector, "detect_collection_updates")
    @mock.patch.object(UpdateDetector, "check_compatibility")
    async def test_run_full_update_check(self, mock_compat, mock_collections, mock_software, mock_os):
        """Test full update check workflow"""
        # Mock update detection methods
        os_update = UpdateInfo(
            component_type="os_package",
            component_name="kernel",
            current_version="6.12.0",
            available_version="6.12.1",
            severity="security",
            description="Security update",
            release_date=datetime.now().isoformat(),
        )

        software_update = UpdateInfo(
            component_type="software",
            component_name="podman",
            current_version="4.9.0",
            available_version="5.0.0",
            severity="moderate",
            description="Feature update",
            release_date=datetime.now().isoformat(),
        )

        mock_os.return_value = [os_update]
        mock_software.return_value = [software_update]
        mock_collections.return_value = []
        mock_compat.return_value = "compatible"

        # Run full check
        summary = await self.detector.run_full_update_check()

        # Verify summary structure
        assert "check_timestamp" in summary
        assert "check_duration" in summary
        assert summary["total_updates"] == 2
        assert summary["updates_by_type"]["os_packages"] == 1
        assert summary["updates_by_type"]["software"] == 1
        assert summary["updates_by_type"]["collections"] == 0
        assert summary["updates_by_severity"]["security"] == 1
        assert summary["updates_by_severity"]["moderate"] == 1
        assert summary["compatibility_status"]["compatible"] == 2
        assert len(summary["updates"]) == 2
        assert len(summary["batches"]) > 0


class TestUpdateInfo:
    """Test cases for UpdateInfo dataclass"""

    def test_update_info_creation(self):
        """Test UpdateInfo creation and initialization"""
        update = UpdateInfo(
            component_type="os_package",
            component_name="kernel",
            current_version="6.12.0",
            available_version="6.12.1",
            severity="security",
            description="Security update",
            release_date="2025-11-08T10:00:00",
        )

        assert update.component_type == "os_package"
        assert update.component_name == "kernel"
        assert update.current_version == "6.12.0"
        assert update.available_version == "6.12.1"
        assert update.severity == "security"
        assert update.security_advisories == []  # Default initialization
        assert update.dependencies == []  # Default initialization
        assert update.compatibility_status == "unknown"


class TestUpdateBatch:
    """Test cases for UpdateBatch dataclass"""

    def test_update_batch_creation(self):
        """Test UpdateBatch creation and metrics calculation"""
        updates = [
            UpdateInfo(
                component_type="os_package",
                component_name="kernel",
                current_version="6.12.0",
                available_version="6.12.1",
                severity="security",
                description="Security update",
                release_date="2025-11-08T10:00:00",
                update_size=50000000,  # 50MB
            ),
            UpdateInfo(
                component_type="os_package",
                component_name="glibc",
                current_version="2.38",
                available_version="2.39",
                severity="security",
                description="Security update",
                release_date="2025-11-08T10:00:00",
                update_size=30000000,  # 30MB
            ),
        ]

        batch = UpdateBatch(
            batch_id="security_123",
            batch_type="security",
            updates=updates,
            total_size=0,  # Will be calculated
            estimated_duration="15-30 minutes",
            risk_level="medium",
            requires_reboot=True,
            rollback_plan="Snapshot rollback",
            created_at=datetime.now(),
        )

        assert batch.batch_id == "security_123"
        assert batch.batch_type == "security"
        assert len(batch.updates) == 2
        assert batch.total_size == 80000000  # 50MB + 30MB
        assert batch.requires_reboot is True


class TestCompatibilityMatrix:
    """Test cases for CompatibilityMatrix dataclass"""

    def test_compatibility_matrix_creation(self):
        """Test CompatibilityMatrix creation"""
        matrix = CompatibilityMatrix(
            component_name="podman",
            supported_versions={"10": ["4.9.0", "5.0.0"]},
            known_issues=[],
            test_results={"4.9.0": "passed"},
            last_updated=datetime.now(),
        )

        assert matrix.component_name == "podman"
        assert "10" in matrix.supported_versions
        assert "4.9.0" in matrix.supported_versions["10"]
        assert matrix.test_results["4.9.0"] == "passed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
