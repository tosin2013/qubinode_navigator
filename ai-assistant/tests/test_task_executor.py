"""
Tests for services/task_executor.py - Task Executor Service.

Tests cover:
- TaskExecutionLog and ExecutionSessionLog models
- ExecutionResult model
- TaskExecutor class methods
- Helper functions
"""

import pytest
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Set test mode
os.environ["TEST_MODE"] = "true"

from services.task_executor import (
    TaskExecutionLog,
    ExecutionSessionLog,
    ExecutionResult,
    TaskExecutor,
    execute_session_plan,
    EXECUTION_LOGS_DIR,
)


class TestTaskExecutionLog:
    """Tests for TaskExecutionLog model."""

    def test_log_minimal(self):
        """Test creating a minimal task execution log."""
        log = TaskExecutionLog(
            task_index=0,
            task_description="Create a VM",
            started_at="2024-01-01T10:00:00",
        )
        assert log.task_index == 0
        assert log.task_description == "Create a VM"
        assert log.status == "pending"
        assert log.completed_at is None
        assert log.error is None

    def test_log_full(self):
        """Test creating a full task execution log."""
        log = TaskExecutionLog(
            task_index=1,
            task_description="Deploy FreeIPA",
            started_at="2024-01-01T10:00:00",
            completed_at="2024-01-01T10:05:00",
            duration_ms=300000,
            developer_result={"success": True, "confidence": 0.85},
            status="completed",
        )
        assert log.status == "completed"
        assert log.duration_ms == 300000
        assert log.developer_result["confidence"] == 0.85

    def test_log_failed(self):
        """Test task log with failure."""
        log = TaskExecutionLog(
            task_index=2,
            task_description="Failed task",
            started_at="2024-01-01T10:00:00",
            completed_at="2024-01-01T10:01:00",
            status="failed",
            error="Connection timeout",
        )
        assert log.status == "failed"
        assert log.error == "Connection timeout"


class TestExecutionSessionLog:
    """Tests for ExecutionSessionLog model."""

    def test_session_log_minimal(self):
        """Test creating a minimal session log."""
        log = ExecutionSessionLog(
            session_id="sess-123",
            started_at="2024-01-01T10:00:00",
            plan={"user_intent": "Deploy VM"},
        )
        assert log.session_id == "sess-123"
        assert log.overall_status == "pending"
        assert log.task_logs == []
        assert log.escalations == []

    def test_session_log_full(self):
        """Test creating a full session log."""
        task_log = TaskExecutionLog(
            task_index=0,
            task_description="Task 1",
            started_at="2024-01-01T10:00:00",
            status="completed",
        )
        log = ExecutionSessionLog(
            session_id="sess-456",
            started_at="2024-01-01T10:00:00",
            completed_at="2024-01-01T10:30:00",
            plan={"user_intent": "Deploy infrastructure"},
            task_logs=[task_log],
            overall_status="completed",
            overall_confidence=0.9,
            summary="All tasks completed successfully",
            log_file_path="/tmp/log.json",
        )
        assert log.overall_status == "completed"
        assert len(log.task_logs) == 1
        assert log.overall_confidence == 0.9


class TestExecutionResult:
    """Tests for ExecutionResult model."""

    def test_result_success(self):
        """Test successful execution result."""
        session_log = ExecutionSessionLog(
            session_id="sess-789",
            started_at="2024-01-01T10:00:00",
            plan={"user_intent": "Test"},
        )
        result = ExecutionResult(
            success=True,
            session_id="sess-789",
            tasks_executed=3,
            tasks_succeeded=3,
            tasks_failed=0,
            tasks_escalated=0,
            overall_confidence=0.95,
            execution_log=session_log,
            log_file_path="/tmp/log.json",
            summary="All 3 tasks completed successfully",
        )
        assert result.success is True
        assert result.tasks_succeeded == 3
        assert result.escalation_needed is False

    def test_result_with_failures(self):
        """Test execution result with failures."""
        session_log = ExecutionSessionLog(
            session_id="sess-fail",
            started_at="2024-01-01T10:00:00",
            plan={"user_intent": "Test"},
        )
        result = ExecutionResult(
            success=False,
            session_id="sess-fail",
            tasks_executed=3,
            tasks_succeeded=1,
            tasks_failed=2,
            tasks_escalated=0,
            overall_confidence=0.5,
            execution_log=session_log,
            log_file_path="/tmp/log.json",
            summary="2 of 3 tasks failed",
        )
        assert result.success is False
        assert result.tasks_failed == 2

    def test_result_with_escalations(self):
        """Test execution result with escalations."""
        session_log = ExecutionSessionLog(
            session_id="sess-esc",
            started_at="2024-01-01T10:00:00",
            plan={"user_intent": "Test"},
        )
        result = ExecutionResult(
            success=False,
            session_id="sess-esc",
            tasks_executed=2,
            tasks_succeeded=1,
            tasks_failed=0,
            tasks_escalated=1,
            overall_confidence=0.7,
            execution_log=session_log,
            log_file_path="/tmp/log.json",
            escalation_needed=True,
            escalation_requests=[],
            summary="1 task escalated",
        )
        assert result.escalation_needed is True
        assert result.tasks_escalated == 1


class TestTaskExecutor:
    """Tests for TaskExecutor class."""

    @pytest.fixture
    def executor(self):
        """Create a TaskExecutor for testing."""
        return TaskExecutor(
            session_id="test-session",
            rag_service=None,
            lineage_service=None,
            working_directory="/tmp/test",
        )

    def test_executor_initialization(self, executor):
        """Test executor initialization."""
        assert executor.session_id == "test-session"
        assert executor.rag_service is None
        assert executor.lineage_service is None
        assert executor.working_directory == "/tmp/test"
        assert executor.execution_log is None

    def test_calculate_duration(self, executor):
        """Test _calculate_duration method."""
        start = "2024-01-01T10:00:00"
        end = "2024-01-01T10:05:00"

        duration = executor._calculate_duration(start, end)

        # 5 minutes = 300 seconds = 300000 ms
        assert duration == 300000

    def test_calculate_duration_invalid(self, executor):
        """Test _calculate_duration with invalid input."""
        duration = executor._calculate_duration("invalid", "also-invalid")
        assert duration == 0

    def test_infer_target_files_dag(self, executor):
        """Test _infer_target_files for DAG tasks."""
        files = executor._infer_target_files("Create a new DAG for deployment")
        assert "airflow/dags/" in files

    def test_infer_target_files_plugin(self, executor):
        """Test _infer_target_files for plugin tasks."""
        files = executor._infer_target_files("Develop a new plugin for VM management")
        assert "plugins/" in files

    def test_infer_target_files_test(self, executor):
        """Test _infer_target_files for test tasks."""
        files = executor._infer_target_files("Add unit tests for the service")
        assert "tests/" in files

    def test_infer_target_files_config(self, executor):
        """Test _infer_target_files for config tasks."""
        files = executor._infer_target_files("Update configuration settings")
        assert "config/" in files

    def test_infer_target_files_default(self, executor):
        """Test _infer_target_files with no specific keywords."""
        files = executor._infer_target_files("Do something generic")
        assert files == ["./"]

    def test_infer_target_files_multiple(self, executor):
        """Test _infer_target_files with multiple keywords."""
        files = executor._infer_target_files("Create a DAG and add tests")
        assert "airflow/dags/" in files
        assert "tests/" in files

    def test_generate_summary(self, executor):
        """Test _generate_summary method."""
        # Create a mock plan
        mock_plan = MagicMock()
        mock_plan.user_intent = "Deploy FreeIPA"
        mock_plan.planned_tasks = ["Task 1", "Task 2", "Task 3"]

        executor.log_file_path = "/tmp/test.json"

        summary = executor._generate_summary(
            plan=mock_plan,
            tasks_succeeded=2,
            tasks_failed=1,
            tasks_escalated=0,
            overall_confidence=0.75,
            code_changes=[],
        )

        assert "Deploy FreeIPA" in summary
        assert "Succeeded: 2" in summary
        assert "Failed: 1" in summary
        assert "75.00%" in summary

    def test_generate_summary_with_code_changes(self, executor):
        """Test _generate_summary with code changes."""
        mock_plan = MagicMock()
        mock_plan.user_intent = "Update DAG"
        mock_plan.planned_tasks = ["Task 1"]

        executor.log_file_path = "/tmp/test.json"

        code_changes = [
            {"task": "Modify DAG file", "mode": "aider"},
        ]

        summary = executor._generate_summary(
            plan=mock_plan,
            tasks_succeeded=1,
            tasks_failed=0,
            tasks_escalated=0,
            overall_confidence=0.9,
            code_changes=code_changes,
        )

        assert "Code Changes:" in summary
        assert "aider" in summary

    def test_generate_summary_with_escalations(self, executor):
        """Test _generate_summary with escalations."""
        mock_plan = MagicMock()
        mock_plan.user_intent = "Complex task"
        mock_plan.planned_tasks = ["Task 1", "Task 2"]

        executor.log_file_path = "/tmp/test.json"

        summary = executor._generate_summary(
            plan=mock_plan,
            tasks_succeeded=1,
            tasks_failed=0,
            tasks_escalated=1,
            overall_confidence=0.6,
            code_changes=[],
        )

        assert "Escalations Required:" in summary

    def test_write_log(self, executor, capsys):
        """Test _write_log method prints to stdout."""
        executor._write_log("Test message")

        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_save_log(self, executor):
        """Test _save_log method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            executor.log_file_path = f"{tmpdir}/test_log.json"
            executor.execution_log = ExecutionSessionLog(
                session_id="test",
                started_at="2024-01-01T10:00:00",
                plan={"test": "data"},
            )

            executor._save_log()

            assert Path(executor.log_file_path).exists()

    def test_save_log_no_log(self, executor):
        """Test _save_log when no log exists."""
        # Should not raise
        executor._save_log()


class TestExecuteSessionPlan:
    """Tests for execute_session_plan convenience function."""

    @pytest.mark.asyncio
    async def test_execute_session_plan_creates_executor(self):
        """Test that execute_session_plan creates TaskExecutor."""
        mock_plan = MagicMock()
        mock_plan.user_intent = "Test intent"
        mock_plan.planned_tasks = []
        mock_plan.required_providers = []
        mock_plan.estimated_confidence = 0.8
        mock_plan.model_dump = MagicMock(return_value={"user_intent": "Test intent"})

        with patch.object(TaskExecutor, "execute_plan", new_callable=AsyncMock) as mock_execute:
            # Create a mock result
            mock_session_log = ExecutionSessionLog(
                session_id="test",
                started_at="2024-01-01T10:00:00",
                plan={"test": True},
            )
            mock_result = ExecutionResult(
                success=True,
                session_id="test",
                tasks_executed=0,
                tasks_succeeded=0,
                tasks_failed=0,
                tasks_escalated=0,
                overall_confidence=1.0,
                execution_log=mock_session_log,
                log_file_path="/tmp/test.json",
                summary="No tasks",
            )
            mock_execute.return_value = mock_result

            result = await execute_session_plan(
                session_id="test-session",
                plan=mock_plan,
            )

            mock_execute.assert_called_once()


class TestLogsDirectory:
    """Tests for execution logs directory."""

    def test_logs_directory_exists(self):
        """Test that execution logs directory is created."""
        assert EXECUTION_LOGS_DIR.exists()

    def test_logs_directory_is_dir(self):
        """Test that execution logs directory is a directory."""
        assert EXECUTION_LOGS_DIR.is_dir()
