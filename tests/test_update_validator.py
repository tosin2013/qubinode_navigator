"""
Tests for Qubinode Navigator Update Validator

Tests the automated update validation infrastructure including
containerized testing, test execution, and result evaluation.
"""

import pytest
import unittest.mock as mock
import tempfile
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.update_validator import (
    UpdateValidator,
    ValidationStage,
    ValidationResult,
    ValidationTest,
    ValidationExecution,
    ValidationSuite,
)
from core.update_manager import UpdateInfo


class TestUpdateValidator:
    """Test cases for update validator functionality"""

    def setup_method(self):
        """Setup test environment"""
        # Create temporary directory
        self.temp_test_dir = tempfile.mkdtemp()

        # Validator configuration
        self.config = {
            "test_environment_dir": self.temp_test_dir,
            "container_runtime": "podman",
            "base_image": "quay.io/centos/centos:stream10",
            "parallel_tests": 2,
            "validation_timeout": 300,
        }

        # Create validator instance
        self.validator = UpdateValidator(self.config)

        # Sample update info
        self.update_info = UpdateInfo(
            component_type="software",
            component_name="podman",
            current_version="4.9.0",
            available_version="5.0.0",
            severity="medium",
            description="Podman container runtime update",
            release_date="2025-11-08",
        )

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil

        try:
            shutil.rmtree(self.temp_test_dir)
        except Exception:
            pass

    def test_validator_initialization(self):
        """Test update validator initialization"""
        assert self.validator.container_runtime == "podman"
        assert self.validator.base_image == "quay.io/centos/centos:stream10"
        assert self.validator.parallel_tests == 2
        assert len(self.validator.test_templates) > 0
        assert len(self.validator.environment_configs) > 0

    async def test_create_validation_suite(self):
        """Test creating validation suite"""
        suite = await self.validator.create_validation_suite(self.update_info)

        assert suite.suite_id.startswith("validation_podman_5.0.0_")
        assert suite.update_info.component_name == "podman"
        assert len(suite.tests) > 0
        assert suite.suite_id in self.validator.validation_suites

        # Check that tests are generated for different stages
        pre_tests = suite.get_tests_by_stage(ValidationStage.PRE_UPDATE_TESTS)
        post_tests = suite.get_tests_by_stage(ValidationStage.POST_UPDATE_TESTS)

        assert len(pre_tests) > 0
        assert len(post_tests) > 0

    async def test_generate_podman_tests(self):
        """Test generating Podman-specific tests"""
        tests = self._create_podman_tests(self.update_info)

        assert len(tests) >= 2  # Version check and container test

        # Check for version verification test
        version_tests = [t for t in tests if "version" in t.test_name.lower()]
        assert len(version_tests) > 0

        # Check for container functionality test
        container_tests = [t for t in tests if "container" in t.test_name.lower()]
        assert len(container_tests) > 0

    def _create_podman_tests(self, update_info):
        """Helper method to create Podman tests"""
        return self.validator._create_podman_tests(update_info)

    async def test_generate_ansible_tests(self):
        """Test generating Ansible-specific tests"""
        ansible_update = UpdateInfo(
            component_type="software",
            component_name="ansible",
            current_version="2.15.0",
            available_version="2.16.0",
            severity="medium",
            description="Ansible automation update",
            release_date="2025-11-08",
        )

        tests = self.validator._create_ansible_tests(ansible_update)

        assert len(tests) >= 2  # Version check and functionality test

        # Check for version verification test
        version_tests = [t for t in tests if "version" in t.test_name.lower()]
        assert len(version_tests) > 0

        # Check for functionality test
        func_tests = [t for t in tests if "functionality" in t.test_name.lower()]
        assert len(func_tests) > 0

    def test_validation_test_creation(self):
        """Test ValidationTest dataclass creation"""
        test = ValidationTest(
            test_id="test_123",
            test_name="Test Name",
            test_type="functional",
            component="podman",
            stage=ValidationStage.POST_UPDATE_TESTS,
            command='echo "test"',
            expected_result="exit_code_0",
            timeout=60,
            critical=True,
        )

        assert test.test_id == "test_123"
        assert test.stage == ValidationStage.POST_UPDATE_TESTS
        assert test.critical is True
        assert test.environment == {}  # Default empty dict

    def test_validation_execution_creation(self):
        """Test ValidationExecution dataclass creation"""
        start_time = datetime.now()
        execution = ValidationExecution(
            test_id="test_123",
            execution_id="exec_123",
            status=ValidationResult.PASSED,
            start_time=start_time,
        )

        assert execution.test_id == "test_123"
        assert execution.status == ValidationResult.PASSED
        assert execution.start_time == start_time
        assert execution.end_time is None
        assert execution.duration == 0.0

    def test_validation_execution_duration_calculation(self):
        """Test duration calculation in ValidationExecution"""
        start_time = datetime.now()
        end_time = datetime.now()

        execution = ValidationExecution(
            test_id="test_123",
            execution_id="exec_123",
            status=ValidationResult.PASSED,
            start_time=start_time,
            end_time=end_time,
        )

        assert execution.duration >= 0.0

    def test_evaluate_test_result_exit_code_0(self):
        """Test evaluating exit_code_0 test result"""
        test = ValidationTest(
            test_id="test_123",
            test_name="Test",
            test_type="functional",
            component="test",
            stage=ValidationStage.POST_UPDATE_TESTS,
            command='echo "test"',
            expected_result="exit_code_0",
        )

        result = self.validator._evaluate_test_result(test, "output", "")
        assert result is True

    def test_evaluate_test_result_version_match(self):
        """Test evaluating version_match test result"""
        test = ValidationTest(
            test_id="test_123",
            test_name="Version Test",
            test_type="functional",
            component="test",
            stage=ValidationStage.POST_UPDATE_TESTS,
            command='echo "version"',
            expected_result="version_match",
        )

        # Should pass with version in output
        result = self.validator._evaluate_test_result(test, "podman version 5.0.0", "")
        assert result is True

        # Should fail without version in output
        result = self.validator._evaluate_test_result(
            test, "command output without key words", ""
        )
        assert result is False

    def test_evaluate_test_result_hello_world(self):
        """Test evaluating hello_world_output test result"""
        test = ValidationTest(
            test_id="test_123",
            test_name="Hello Test",
            test_type="functional",
            component="test",
            stage=ValidationStage.POST_UPDATE_TESTS,
            command='echo "hello"',
            expected_result="hello_world_output",
        )

        # Should pass with hello in output
        result = self.validator._evaluate_test_result(test, "Hello from Docker!", "")
        assert result is True

        # Should fail without hello in output
        result = self.validator._evaluate_test_result(test, "no greeting", "")
        assert result is False

    def test_evaluate_test_result_ansible_facts(self):
        """Test evaluating ansible_facts test result"""
        test = ValidationTest(
            test_id="test_123",
            test_name="Ansible Test",
            test_type="functional",
            component="test",
            stage=ValidationStage.POST_UPDATE_TESTS,
            command="ansible localhost -m setup",
            expected_result="ansible_facts",
        )

        # Should pass with ansible_facts in output
        result = self.validator._evaluate_test_result(test, "ansible_facts: {...}", "")
        assert result is True

        # Should pass with SUCCESS in output
        result = self.validator._evaluate_test_result(test, "localhost | SUCCESS", "")
        assert result is True

        # Should fail without expected output
        result = self.validator._evaluate_test_result(test, "failed to connect", "")
        assert result is False

    @mock.patch("subprocess.run")
    async def test_execute_validation_test_success(self, mock_run):
        """Test successful validation test execution"""
        # Mock successful subprocess call
        mock_run.return_value = mock.MagicMock(
            returncode=0, stdout="test output", stderr=""
        )

        test = ValidationTest(
            test_id="test_success",
            test_name="Success Test",
            test_type="functional",
            component="test",
            stage=ValidationStage.POST_UPDATE_TESTS,
            command='echo "success"',
            expected_result="exit_code_0",
            timeout=30,
        )

        execution = await self.validator.execute_validation_test(test, "test_container")

        assert execution.status == ValidationResult.PASSED
        assert execution.output == "test output"
        assert execution.exit_code == 0
        assert execution.duration > 0
        assert execution.error_message is None

    @mock.patch("subprocess.run")
    async def test_execute_validation_test_failure(self, mock_run):
        """Test failed validation test execution"""
        # Mock failed subprocess call
        mock_run.return_value = mock.MagicMock(
            returncode=1, stdout="", stderr="command failed"
        )

        test = ValidationTest(
            test_id="test_failure",
            test_name="Failure Test",
            test_type="functional",
            component="test",
            stage=ValidationStage.POST_UPDATE_TESTS,
            command="false",
            expected_result="exit_code_0",
            timeout=30,
        )

        execution = await self.validator.execute_validation_test(test, "test_container")

        assert execution.status == ValidationResult.FAILED
        assert execution.exit_code == 1
        assert execution.error_message == "command failed"

    @mock.patch("subprocess.run")
    async def test_execute_validation_test_timeout(self, mock_run):
        """Test validation test timeout"""
        # Mock timeout exception
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

        test = ValidationTest(
            test_id="test_timeout",
            test_name="Timeout Test",
            test_type="functional",
            component="test",
            stage=ValidationStage.POST_UPDATE_TESTS,
            command="sleep 60",
            expected_result="exit_code_0",
            timeout=30,
        )

        execution = await self.validator.execute_validation_test(test, "test_container")

        assert execution.status == ValidationResult.FAILED
        assert execution.duration == 30  # Should equal timeout
        assert "timed out" in execution.error_message.lower()

    def test_determine_overall_result_passed(self):
        """Test determining overall result - passed"""
        results = {
            "summary": {
                "passed": 5,
                "failed": 0,
                "warnings": 0,
                "errors": 0,
                "skipped": 0,
            }
        }

        overall = self.validator._determine_overall_result(results)
        assert overall == "passed"

    def test_determine_overall_result_failed(self):
        """Test determining overall result - failed"""
        results = {
            "summary": {
                "passed": 3,
                "failed": 2,
                "warnings": 0,
                "errors": 0,
                "skipped": 0,
            }
        }

        overall = self.validator._determine_overall_result(results)
        assert overall == "failed"

    def test_determine_overall_result_warning(self):
        """Test determining overall result - warning"""
        results = {
            "summary": {
                "passed": 3,
                "failed": 0,
                "warnings": 2,
                "errors": 0,
                "skipped": 0,
            }
        }

        overall = self.validator._determine_overall_result(results)
        assert overall == "warning"

    def test_determine_overall_result_error(self):
        """Test determining overall result - error"""
        results = {
            "summary": {
                "passed": 3,
                "failed": 0,
                "warnings": 0,
                "errors": 1,
                "skipped": 0,
            }
        }

        overall = self.validator._determine_overall_result(results)
        assert overall == "error"

    def test_determine_overall_result_skipped(self):
        """Test determining overall result - skipped"""
        results = {
            "summary": {
                "passed": 0,
                "failed": 0,
                "warnings": 0,
                "errors": 0,
                "skipped": 5,
            }
        }

        overall = self.validator._determine_overall_result(results)
        assert overall == "skipped"

    @mock.patch("subprocess.run")
    async def test_create_test_environment_success(self, mock_run):
        """Test successful test environment creation"""
        # Mock successful container creation
        mock_run.return_value = mock.MagicMock(returncode=0, stderr="")

        suite = ValidationSuite(
            suite_id="test_suite",
            update_info=self.update_info,
            tests=[],
            environment_config=self.validator.environment_configs["default"],
            created_at=datetime.now(),
        )

        container_name = await self.validator.create_test_environment(suite)

        assert container_name == "validation_test_suite"
        assert container_name in self.validator.active_containers

    @mock.patch("subprocess.run")
    async def test_create_test_environment_failure(self, mock_run):
        """Test failed test environment creation"""
        # Mock failed container creation
        mock_run.return_value = mock.MagicMock(
            returncode=1, stderr="container creation failed"
        )

        suite = ValidationSuite(
            suite_id="test_suite",
            update_info=self.update_info,
            tests=[],
            environment_config=self.validator.environment_configs["default"],
            created_at=datetime.now(),
        )

        with pytest.raises(Exception) as exc_info:
            await self.validator.create_test_environment(suite)

        assert "Failed to create container" in str(exc_info.value)

    @mock.patch("subprocess.run")
    async def test_cleanup_container(self, mock_run):
        """Test container cleanup"""
        # Mock successful cleanup
        mock_run.return_value = mock.MagicMock(returncode=0)

        container_name = "test_container"
        self.validator.active_containers.add(container_name)

        await self.validator._cleanup_container(container_name)

        assert container_name not in self.validator.active_containers

        # Verify stop and rm commands were called
        assert mock_run.call_count == 2
        stop_call = mock_run.call_args_list[0][0][0]
        rm_call = mock_run.call_args_list[1][0][0]

        assert "stop" in stop_call
        assert "rm" in rm_call
        assert container_name in stop_call
        assert container_name in rm_call


class TestValidationStage:
    """Test ValidationStage enum"""

    def test_validation_stage_values(self):
        """Test ValidationStage enum values"""
        assert ValidationStage.PREPARATION.value == "preparation"
        assert ValidationStage.PRE_UPDATE_TESTS.value == "pre_update_tests"
        assert ValidationStage.UPDATE_APPLICATION.value == "update_application"
        assert ValidationStage.POST_UPDATE_TESTS.value == "post_update_tests"
        assert ValidationStage.ROLLBACK_VALIDATION.value == "rollback_validation"
        assert ValidationStage.CLEANUP.value == "cleanup"


class TestValidationResult:
    """Test ValidationResult enum"""

    def test_validation_result_values(self):
        """Test ValidationResult enum values"""
        assert ValidationResult.PASSED.value == "passed"
        assert ValidationResult.FAILED.value == "failed"
        assert ValidationResult.WARNING.value == "warning"
        assert ValidationResult.SKIPPED.value == "skipped"
        assert ValidationResult.ERROR.value == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
