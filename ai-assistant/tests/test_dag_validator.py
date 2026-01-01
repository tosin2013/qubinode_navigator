"""
Tests for dag_validator.py - DAG Validation and Discovery

Tests cover:
- DAGStatus and ValidationStatus enums
- ValidationCheck, DAGInfo, DAGValidationResult dataclasses
- DAGValidator initialization and methods
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from datetime import datetime

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Set test mode
os.environ["TEST_MODE"] = "true"

from dag_validator import (
    DAGStatus,
    ValidationStatus,
    ValidationCheck,
    DAGInfo,
    DAGValidationResult,
    DAGSearchResult,
    DAGCreationRequest,
    DAGValidator,
)


class TestDAGStatus:
    """Tests for DAGStatus enum."""

    def test_all_statuses_exist(self):
        """Test that all DAG statuses are defined."""
        assert DAGStatus.ACTIVE
        assert DAGStatus.PAUSED
        assert DAGStatus.UNKNOWN
        assert DAGStatus.NOT_FOUND

    def test_status_values(self):
        """Test status enum values."""
        assert DAGStatus.ACTIVE.value == "active"
        assert DAGStatus.PAUSED.value == "paused"
        assert DAGStatus.UNKNOWN.value == "unknown"
        assert DAGStatus.NOT_FOUND.value == "not_found"


class TestValidationStatus:
    """Tests for ValidationStatus enum."""

    def test_all_statuses_exist(self):
        """Test that all validation statuses are defined."""
        assert ValidationStatus.PASSED
        assert ValidationStatus.FAILED
        assert ValidationStatus.WARNING
        assert ValidationStatus.SKIPPED

    def test_status_values(self):
        """Test validation status enum values."""
        assert ValidationStatus.PASSED.value == "passed"
        assert ValidationStatus.FAILED.value == "failed"
        assert ValidationStatus.WARNING.value == "warning"
        assert ValidationStatus.SKIPPED.value == "skipped"


class TestValidationCheck:
    """Tests for ValidationCheck dataclass."""

    def test_check_creation_minimal(self):
        """Test validation check with minimal fields."""
        check = ValidationCheck(
            name="syntax_check",
            status=ValidationStatus.PASSED,
            message="Syntax is valid",
        )
        assert check.name == "syntax_check"
        assert check.status == ValidationStatus.PASSED
        assert check.message == "Syntax is valid"
        assert check.details is None
        assert check.fix_suggestion is None

    def test_check_creation_full(self):
        """Test validation check with all fields."""
        check = ValidationCheck(
            name="param_check",
            status=ValidationStatus.FAILED,
            message="Missing required parameter",
            details={"param_name": "vm_name", "expected_type": "str"},
            fix_suggestion="Add vm_name parameter to the DAG config",
        )
        assert check.name == "param_check"
        assert check.status == ValidationStatus.FAILED
        assert check.details["param_name"] == "vm_name"
        assert check.fix_suggestion is not None


class TestDAGInfo:
    """Tests for DAGInfo dataclass."""

    def test_dag_info_minimal(self):
        """Test DAGInfo with minimal fields."""
        info = DAGInfo(
            dag_id="test_dag",
            file_path="/opt/airflow/dags/test_dag.py",
        )
        assert info.dag_id == "test_dag"
        assert info.file_path == "/opt/airflow/dags/test_dag.py"
        assert info.description == ""
        assert info.schedule is None
        assert info.tags == []
        assert info.params == {}
        assert info.status == DAGStatus.UNKNOWN
        assert info.is_suitable is False
        assert info.match_score == 0.0

    def test_dag_info_full(self):
        """Test DAGInfo with all fields."""
        checks = [
            ValidationCheck(
                name="test", status=ValidationStatus.PASSED, message="OK"
            )
        ]
        info = DAGInfo(
            dag_id="freeipa_deployment",
            file_path="/opt/airflow/dags/freeipa_deployment.py",
            description="Deploy FreeIPA server",
            schedule="@daily",
            tags=["infrastructure", "freeipa"],
            params={"vm_name": "freeipa", "memory": 4096},
            status=DAGStatus.ACTIVE,
            is_suitable=True,
            match_score=0.95,
            validation_checks=checks,
        )
        assert info.dag_id == "freeipa_deployment"
        assert info.description == "Deploy FreeIPA server"
        assert info.schedule == "@daily"
        assert "infrastructure" in info.tags
        assert info.params["memory"] == 4096
        assert info.status == DAGStatus.ACTIVE
        assert info.is_suitable is True
        assert info.match_score == 0.95
        assert len(info.validation_checks) == 1


class TestDAGValidationResult:
    """Tests for DAGValidationResult dataclass."""

    def test_validation_result_passed(self):
        """Test validation result when passed."""
        checks = [
            ValidationCheck(
                name="syntax",
                status=ValidationStatus.PASSED,
                message="Syntax OK",
            ),
            ValidationCheck(
                name="params",
                status=ValidationStatus.PASSED,
                message="Params OK",
            ),
        ]
        result = DAGValidationResult(
            dag_id="test_dag",
            is_valid=True,
            checks=checks,
            overall_status=ValidationStatus.PASSED,
            can_proceed=True,
        )
        assert result.is_valid is True
        assert result.can_proceed is True
        assert len(result.checks) == 2
        assert result.error_summary is None

    def test_validation_result_failed(self):
        """Test validation result when failed."""
        checks = [
            ValidationCheck(
                name="syntax",
                status=ValidationStatus.FAILED,
                message="Syntax error on line 42",
                fix_suggestion="Check indentation",
            )
        ]
        result = DAGValidationResult(
            dag_id="broken_dag",
            is_valid=False,
            checks=checks,
            overall_status=ValidationStatus.FAILED,
            can_proceed=False,
            error_summary="DAG has syntax errors",
            user_actions=[{"type": "fix", "description": "Fix syntax"}],
        )
        assert result.is_valid is False
        assert result.can_proceed is False
        assert result.error_summary == "DAG has syntax errors"
        assert len(result.user_actions) == 1


class TestDAGSearchResult:
    """Tests for DAGSearchResult dataclass."""

    def test_search_result_found(self):
        """Test search result when DAG is found."""
        dag = DAGInfo(dag_id="test_dag", file_path="/path/to/dag.py")
        result = DAGSearchResult(
            found=True,
            matching_dags=[dag],
            best_match=dag,
            create_new_recommended=False,
            recommendation="Use existing test_dag",
        )
        assert result.found is True
        assert len(result.matching_dags) == 1
        assert result.best_match is not None
        assert result.create_new_recommended is False

    def test_search_result_not_found(self):
        """Test search result when no DAG is found."""
        result = DAGSearchResult(
            found=False,
            matching_dags=[],
            create_new_recommended=True,
            recommendation="Create new DAG for this use case",
        )
        assert result.found is False
        assert len(result.matching_dags) == 0
        assert result.best_match is None
        assert result.create_new_recommended is True


class TestDAGCreationRequest:
    """Tests for DAGCreationRequest dataclass."""

    def test_creation_request_minimal(self):
        """Test DAG creation request with minimal fields."""
        request = DAGCreationRequest(
            dag_id="new_dag",
            description="A new DAG",
            task_description="Deploy something",
        )
        assert request.dag_id == "new_dag"
        assert request.description == "A new DAG"
        assert request.task_description == "Deploy something"


class TestDAGValidator:
    """Tests for DAGValidator class."""

    def test_validator_initialization_defaults(self):
        """Test validator with default values."""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "exists", return_value=False):
                validator = DAGValidator()
                # Should add /api/v1 to default URL
                assert validator.airflow_api_url == "http://localhost:8888/api/v1"
                assert validator._dag_cache == {}
                assert validator._cache_timestamp is None

    def test_validator_initialization_with_env(self):
        """Test validator reads from environment."""
        env_vars = {
            "AIRFLOW_API_URL": "http://airflow:8080",
            "AIRFLOW_DAGS_PATH": "/custom/dags",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            validator = DAGValidator()
            # Should add /api/v1 since env doesn't include it
            assert validator.airflow_api_url == "http://airflow:8080/api/v1"
            assert str(validator.dags_path) == "/custom/dags"

    def test_validator_initialization_api_v1_not_duplicated(self):
        """Test that /api/v1 is not duplicated if already present."""
        env_vars = {
            "AIRFLOW_API_URL": "http://airflow:8080/api/v1",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            validator = DAGValidator()
            # Should NOT duplicate /api/v1
            assert validator.airflow_api_url == "http://airflow:8080/api/v1"
            assert "/api/v1/api/v1" not in validator.airflow_api_url

    def test_validator_initialization_explicit_params(self):
        """Test validator with explicit parameters."""
        validator = DAGValidator(
            dags_path="/explicit/dags",
            airflow_api_url="http://explicit:9000",
        )
        assert str(validator.dags_path) == "/explicit/dags"
        assert validator.airflow_api_url == "http://explicit:9000/api/v1"

    @pytest.mark.asyncio
    async def test_discover_dags_empty_path(self):
        """Test discover_dags when path doesn't exist."""
        validator = DAGValidator(dags_path="/nonexistent/path")
        dags = await validator.discover_dags()
        assert dags == []

    @pytest.mark.asyncio
    async def test_discover_dags_with_cache(self):
        """Test discover_dags uses cache when valid."""
        validator = DAGValidator(dags_path="/test/dags")

        # Pre-populate cache
        cached_dag = DAGInfo(dag_id="cached_dag", file_path="/test/dags/cached.py")
        validator._dag_cache = {"cached_dag": cached_dag}
        validator._cache_timestamp = datetime.now()

        dags = await validator.discover_dags(force_refresh=False)

        assert len(dags) == 1
        assert dags[0].dag_id == "cached_dag"

    @pytest.mark.asyncio
    async def test_discover_dags_force_refresh(self):
        """Test discover_dags ignores cache when force_refresh=True."""
        with patch.object(Path, "exists", return_value=False):
            validator = DAGValidator(dags_path="/test/dags")

            # Pre-populate cache
            cached_dag = DAGInfo(dag_id="cached_dag", file_path="/test/dags/cached.py")
            validator._dag_cache = {"cached_dag": cached_dag}
            validator._cache_timestamp = datetime.now()

            # Force refresh should check filesystem (which doesn't exist)
            dags = await validator.discover_dags(force_refresh=True)

            assert dags == []

    @pytest.mark.asyncio
    async def test_find_dag_for_task_no_match(self):
        """Test finding DAG when no match exists."""
        validator = DAGValidator(dags_path="/test/dags")

        with patch.object(validator, "discover_dags", new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = []

            result = await validator.find_dag_for_task("deploy freeipa")

            assert result.found is False
            assert result.matching_dags == []

    @pytest.mark.asyncio
    async def test_find_dag_for_task_with_match(self):
        """Test finding DAG when a match exists."""
        validator = DAGValidator(dags_path="/test/dags")

        freeipa_dag = DAGInfo(
            dag_id="freeipa_deployment",
            file_path="/test/dags/freeipa.py",
            description="Deploy FreeIPA server",
            tags=["freeipa", "infrastructure"],
        )

        with patch.object(validator, "discover_dags", new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = [freeipa_dag]

            result = await validator.find_dag_for_task("deploy freeipa server")

            # Should find a match based on tags/description
            assert result is not None

    @pytest.mark.asyncio
    async def test_validate_dag_for_params(self):
        """Test DAG parameter validation."""
        validator = DAGValidator(dags_path="/test/dags")

        # Mock httpx for Airflow API call
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"is_paused": False}
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await validator.validate_dag(
                dag_id="test_dag",
                task_params={"vm_name": "test-vm"},
            )

            assert result.dag_id == "test_dag"


class TestDAGValidatorHelpers:
    """Tests for DAGValidator helper methods."""

    def test_cache_ttl(self):
        """Test that cache TTL is set correctly."""
        validator = DAGValidator(dags_path="/test")
        assert validator._cache_ttl_seconds == 300  # 5 minutes

    def test_empty_cache_on_init(self):
        """Test that cache is empty on initialization."""
        validator = DAGValidator(dags_path="/test")
        assert validator._dag_cache == {}
        assert validator._cache_timestamp is None
