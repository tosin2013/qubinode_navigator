"""
Tests for agents/observer.py - Lineage Observer Agent

Tests cover:
- ExecutionStatus and ConcernLevel enums
- TaskObservation and Concern dataclasses
- ObserverReport model
- LineageObserverAgent initialization and methods
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Set test mode
os.environ["TEST_MODE"] = "true"

from agents.observer import (
    ExecutionStatus,
    ConcernLevel,
    TaskObservation,
    Concern,
    ObserverReport,
    LineageObserverAgent,
    ObserverDependencies,
)


class TestExecutionStatus:
    """Tests for ExecutionStatus enum."""

    def test_all_statuses_exist(self):
        """Test that all execution statuses are defined."""
        assert ExecutionStatus.QUEUED
        assert ExecutionStatus.RUNNING
        assert ExecutionStatus.SUCCESS
        assert ExecutionStatus.FAILED
        assert ExecutionStatus.SKIPPED
        assert ExecutionStatus.UP_FOR_RETRY
        assert ExecutionStatus.UP_FOR_RESCHEDULE
        assert ExecutionStatus.UPSTREAM_FAILED
        assert ExecutionStatus.UNKNOWN

    def test_status_values(self):
        """Test execution status enum values."""
        assert ExecutionStatus.QUEUED.value == "queued"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.SUCCESS.value == "success"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.UNKNOWN.value == "unknown"


class TestConcernLevel:
    """Tests for ConcernLevel enum."""

    def test_all_levels_exist(self):
        """Test that all concern levels are defined."""
        assert ConcernLevel.INFO
        assert ConcernLevel.WARNING
        assert ConcernLevel.ERROR
        assert ConcernLevel.CRITICAL

    def test_level_values(self):
        """Test concern level enum values."""
        assert ConcernLevel.INFO.value == "info"
        assert ConcernLevel.WARNING.value == "warning"
        assert ConcernLevel.ERROR.value == "error"
        assert ConcernLevel.CRITICAL.value == "critical"


class TestTaskObservation:
    """Tests for TaskObservation dataclass."""

    def test_observation_minimal(self):
        """Test task observation with minimal fields."""
        obs = TaskObservation(
            task_id="create_vm",
            status=ExecutionStatus.SUCCESS,
        )
        assert obs.task_id == "create_vm"
        assert obs.status == ExecutionStatus.SUCCESS
        assert obs.duration_seconds is None
        assert obs.start_time is None
        assert obs.end_time is None
        assert obs.log_snippet is None
        assert obs.error_message is None
        assert obs.concerns == []

    def test_observation_full(self):
        """Test task observation with all fields."""
        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 1, 10, 5, 0)
        obs = TaskObservation(
            task_id="deploy_service",
            status=ExecutionStatus.FAILED,
            duration_seconds=300.0,
            start_time=start,
            end_time=end,
            log_snippet="Error: Connection refused",
            error_message="SSH connection failed",
            concerns=["Network timeout", "Retry recommended"],
        )
        assert obs.task_id == "deploy_service"
        assert obs.status == ExecutionStatus.FAILED
        assert obs.duration_seconds == 300.0
        assert obs.start_time == start
        assert obs.end_time == end
        assert "Connection refused" in obs.log_snippet
        assert obs.error_message == "SSH connection failed"
        assert len(obs.concerns) == 2


class TestConcern:
    """Tests for Concern dataclass."""

    def test_concern_minimal(self):
        """Test concern with minimal fields."""
        concern = Concern(
            level=ConcernLevel.WARNING,
            category="performance",
            message="Task took longer than expected",
        )
        assert concern.level == ConcernLevel.WARNING
        assert concern.category == "performance"
        assert concern.message == "Task took longer than expected"
        assert concern.task_id is None
        assert concern.recommendation is None

    def test_concern_full(self):
        """Test concern with all fields."""
        concern = Concern(
            level=ConcernLevel.ERROR,
            category="connectivity",
            message="SSH connection failed",
            task_id="create_vm",
            recommendation="Check network connectivity and SSH keys",
        )
        assert concern.level == ConcernLevel.ERROR
        assert concern.category == "connectivity"
        assert concern.task_id == "create_vm"
        assert concern.recommendation is not None


class TestObserverReport:
    """Tests for ObserverReport Pydantic model."""

    def test_report_success(self):
        """Test observer report for successful execution."""
        report = ObserverReport(
            dag_id="test_dag",
            run_id="run-123",
            overall_status=ExecutionStatus.SUCCESS,
            is_complete=True,
            success=True,
            progress_percent=100.0,
            total_tasks=3,
            completed_tasks=3,
            failed_tasks=0,
            running_tasks=0,
        )
        assert report.dag_id == "test_dag"
        assert report.run_id == "run-123"
        assert report.overall_status == ExecutionStatus.SUCCESS
        assert report.is_complete is True
        assert report.success is True
        assert report.progress_percent == 100.0
        assert report.total_tasks == 3
        assert report.completed_tasks == 3

    def test_report_running(self):
        """Test observer report for running execution."""
        report = ObserverReport(
            dag_id="test_dag",
            run_id="run-456",
            overall_status=ExecutionStatus.RUNNING,
            is_complete=False,
            success=False,
            progress_percent=50.0,
            total_tasks=4,
            completed_tasks=2,
            failed_tasks=0,
            running_tasks=1,
        )
        assert report.overall_status == ExecutionStatus.RUNNING
        assert report.is_complete is False
        assert report.progress_percent == 50.0

    def test_report_failed(self):
        """Test observer report for failed execution."""
        report = ObserverReport(
            dag_id="test_dag",
            run_id="run-789",
            overall_status=ExecutionStatus.FAILED,
            is_complete=True,
            success=False,
            progress_percent=66.0,
            total_tasks=3,
            completed_tasks=2,
            failed_tasks=1,
            running_tasks=0,
            detailed_message="Task create_vm failed due to SSH error",
        )
        assert report.overall_status == ExecutionStatus.FAILED
        assert report.is_complete is True
        assert report.success is False
        assert report.failed_tasks == 1
        assert "SSH error" in report.detailed_message


class TestObserverDependencies:
    """Tests for ObserverDependencies dataclass."""

    def test_dependencies_creation(self):
        """Test observer dependencies creation."""
        deps = ObserverDependencies(
            airflow_api_url="http://localhost:8888",
            airflow_user="admin",
            airflow_pass="password",
            marquez_api_url="http://localhost:5001",
        )
        assert deps.airflow_api_url == "http://localhost:8888"
        assert deps.airflow_user == "admin"
        assert deps.airflow_pass == "password"
        assert deps.marquez_api_url == "http://localhost:5001"


class TestLineageObserverAgent:
    """Tests for LineageObserverAgent class."""

    def test_agent_initialization_defaults(self):
        """Test agent with default values."""
        with patch.dict(os.environ, {}, clear=True):
            agent = LineageObserverAgent()
            assert agent.airflow_api_url == "http://localhost:8888"
            assert agent.airflow_user == "admin"
            assert agent.airflow_pass == "admin"
            assert agent.marquez_api_url == "http://localhost:5001"
            assert agent._observation_history == []

    def test_agent_initialization_with_env(self):
        """Test agent reads from environment."""
        env_vars = {
            "AIRFLOW_API_URL": "http://airflow:8080",
            "AIRFLOW_API_USER": "custom_user",
            "AIRFLOW_API_PASSWORD": "custom_pass",
            "MARQUEZ_API_URL": "http://marquez:5000",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            agent = LineageObserverAgent()
            assert agent.airflow_api_url == "http://airflow:8080"
            assert agent.airflow_user == "custom_user"
            assert agent.airflow_pass == "custom_pass"
            assert agent.marquez_api_url == "http://marquez:5000"

    def test_agent_initialization_explicit_params(self):
        """Test agent with explicit parameters."""
        agent = LineageObserverAgent(
            airflow_api_url="http://explicit:9000",
            airflow_user="explicit_user",
            airflow_pass="explicit_pass",
            marquez_api_url="http://explicit-marquez:6000",
        )
        assert agent.airflow_api_url == "http://explicit:9000"
        assert agent.airflow_user == "explicit_user"
        assert agent.marquez_api_url == "http://explicit-marquez:6000"

    def test_agent_creates_dependencies(self):
        """Test that agent creates ObserverDependencies."""
        agent = LineageObserverAgent()
        assert agent.deps is not None
        assert isinstance(agent.deps, ObserverDependencies)

    @pytest.mark.asyncio
    async def test_observe_success(self):
        """Test observing a successful DAG run."""
        agent = LineageObserverAgent()

        with patch("httpx.AsyncClient") as mock_client:
            # Mock DAG run response
            mock_dag_run_response = MagicMock()
            mock_dag_run_response.status_code = 200
            mock_dag_run_response.json.return_value = {
                "state": "success",
                "start_date": "2024-01-01T10:00:00Z",
                "end_date": "2024-01-01T10:05:00Z",
            }

            # Mock task instances response
            mock_tasks_response = MagicMock()
            mock_tasks_response.status_code = 200
            mock_tasks_response.json.return_value = {
                "task_instances": [
                    {"task_id": "task1", "state": "success", "duration": 60.0},
                    {"task_id": "task2", "state": "success", "duration": 120.0},
                ]
            }

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=[mock_dag_run_response, mock_tasks_response]
            )

            report = await agent.observe(
                dag_id="test_dag",
                run_id="run-123",
                check_logs=False,
            )

            assert report.dag_id == "test_dag"
            assert report.run_id == "run-123"

    @pytest.mark.asyncio
    async def test_observe_failure(self):
        """Test observing a failed DAG run."""
        agent = LineageObserverAgent()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "state": "failed",
                "start_date": "2024-01-01T10:00:00Z",
                "end_date": "2024-01-01T10:03:00Z",
            }

            # Mock task instances response
            mock_tasks_response = MagicMock()
            mock_tasks_response.status_code = 200
            mock_tasks_response.json.return_value = {
                "task_instances": [
                    {"task_id": "task1", "state": "success", "duration": 60.0},
                    {"task_id": "task2", "state": "failed", "duration": 30.0},
                ]
            }

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=[mock_response, mock_tasks_response]
            )

            report = await agent.observe(
                dag_id="test_dag",
                run_id="run-456",
                check_logs=False,
            )

            assert report.dag_id == "test_dag"

    @pytest.mark.asyncio
    async def test_observe_api_error(self):
        """Test observing when API returns error."""
        agent = LineageObserverAgent()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            report = await agent.observe(
                dag_id="nonexistent_dag",
                run_id="run-999",
            )

            # Should still return a report with error info
            assert report.dag_id == "nonexistent_dag"
