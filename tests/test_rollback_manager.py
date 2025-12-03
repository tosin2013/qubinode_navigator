"""
Tests for Qubinode Navigator Rollback Manager

Tests automated rollback mechanisms, trigger detection, rollback execution,
and validation of rollback success.
"""

import asyncio
import sys
import tempfile
import unittest.mock as mock
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.ai_update_manager import UpdatePlan
from core.pipeline_executor import ExecutionResult, PipelineExecutor
from core.rollback_manager import (
    RollbackAction,
    RollbackManager,
    RollbackPlan,
    RollbackStatus,
    RollbackTrigger,
)
from core.rollout_pipeline import (
    PipelineStage,
    RolloutPhase,
    RolloutPipeline,
    RolloutStrategy,
)
from core.update_manager import UpdateBatch, UpdateInfo


class TestRollbackManager:
    """Test cases for rollback manager"""

    def setup_method(self):
        """Setup test environment"""
        # Create temporary storage
        self.temp_dir = tempfile.mkdtemp()

        # Manager configuration
        self.config = {
            "rollback_storage_path": self.temp_dir,
            "auto_rollback_enabled": True,
            "rollback_timeout_minutes": 30,
            "error_rate_threshold": 0.05,
        }

        # Create manager instance
        self.rollback_manager = RollbackManager(self.config)

        # Sample update batch
        self.update_batch = UpdateBatch(
            batch_id="test_batch_123",
            batch_type="test",
            updates=[
                UpdateInfo(
                    component_type="software",
                    component_name="git",
                    current_version="2.44.0",
                    available_version="2.45.0",
                    severity="low",
                    description="Git update",
                    release_date="2025-11-08",
                )
            ],
            total_size=100,
            estimated_duration="30 minutes",
            risk_level="low",
            requires_reboot=False,
            rollback_plan="Standard rollback",
            created_at=datetime.now(),
        )

        # Sample pipeline
        self.test_pipeline = self._create_test_pipeline()

    def _create_test_pipeline(self) -> RolloutPipeline:
        """Create test pipeline"""
        update_plan = UpdatePlan(
            plan_id="test_plan_123",
            batch_id="test_batch_456",
            execution_strategy="rolling",
            total_estimated_time="1h",
            phases=[],
            risk_mitigation_steps=["Create backup"],
            rollback_plan={"strategy": "sequential"},
            monitoring_points=["System metrics"],
            approval_required=False,
            created_at=datetime.now(),
            ai_confidence=0.8,
        )

        test_phase = RolloutPhase(
            phase_id="test_phase_123",
            phase_name="Test Phase",
            stage=PipelineStage.COMPLETED,
            target_environments=["staging"],
            update_batch=self.update_batch,
            validation_tests=["health_check"],
            success_criteria={"min_test_pass_rate": 0.8},
            rollback_triggers=["critical_error"],
            estimated_duration="30 minutes",
        )

        return RolloutPipeline(
            pipeline_id="test_pipeline_123",
            pipeline_name="Test Pipeline",
            strategy=RolloutStrategy.ROLLING,
            update_plan=update_plan,
            phases=[test_phase],
            approval_gates=[],
            global_rollback_triggers=["critical_system_failure"],
            monitoring_config={"enabled": True},
            notification_config={"email": True},
            created_at=datetime.now(),
            created_by="test_user",
        )

    def test_rollback_manager_initialization(self):
        """Test rollback manager initialization"""
        assert self.rollback_manager.rollback_storage_path == Path(self.temp_dir)
        assert self.rollback_manager.auto_rollback_enabled is True
        assert self.rollback_manager.rollback_timeout_minutes == 30
        assert self.rollback_manager.error_rate_threshold == 0.05
        assert len(self.rollback_manager.active_rollbacks) == 0
        assert len(self.rollback_manager.rollback_history) == 0

    async def test_create_rollback_plan(self):
        """Test creating rollback plan"""
        trigger_details = {
            "error_message": "Deployment failed",
            "timestamp": datetime.now().isoformat(),
        }

        rollback_plan = await self.rollback_manager.create_rollback_plan(
            pipeline=self.test_pipeline,
            trigger=RollbackTrigger.DEPLOYMENT_FAILURE,
            trigger_details=trigger_details,
            created_by="test_user",
        )

        assert rollback_plan.pipeline_id == "test_pipeline_123"
        assert rollback_plan.trigger == RollbackTrigger.DEPLOYMENT_FAILURE
        assert rollback_plan.trigger_details == trigger_details
        assert rollback_plan.created_by == "test_user"
        assert rollback_plan.status == RollbackStatus.PENDING
        assert len(rollback_plan.rollback_actions) > 0
        assert rollback_plan.plan_id in self.rollback_manager.active_rollbacks

    async def test_generate_rollback_actions(self):
        """Test rollback action generation"""
        actions = await self.rollback_manager._generate_rollback_actions(
            pipeline=self.test_pipeline,
            trigger=RollbackTrigger.DEPLOYMENT_FAILURE,
            phase_id=None,
        )

        assert len(actions) > 0

        # Check for expected action types
        action_types = [action.action_type for action in actions]
        assert "service_stop" in action_types
        assert "package_rollback" in action_types
        assert "config_restore" in action_types
        assert "service_restart" in action_types

        # Check dependencies
        package_actions = [a for a in actions if a.action_type == "package_rollback"]
        config_actions = [a for a in actions if a.action_type == "config_restore"]

        if package_actions and config_actions:
            # Config restore should depend on package rollback
            config_action = config_actions[0]
            package_action_id = package_actions[0].action_id
            assert package_action_id in config_action.dependencies

    async def test_execute_rollback_success(self):
        """Test successful rollback execution"""
        # Create rollback plan
        rollback_plan = await self.rollback_manager.create_rollback_plan(
            pipeline=self.test_pipeline,
            trigger=RollbackTrigger.DEPLOYMENT_FAILURE,
            trigger_details={"test": "data"},
            created_by="test_user",
        )

        # Mock successful execution
        with mock.patch.object(
            self.rollback_manager, "_execute_rollback_action", return_value=True
        ):
            with mock.patch.object(
                self.rollback_manager, "_validate_rollback_success", return_value=True
            ):
                success = await self.rollback_manager.execute_rollback(rollback_plan)

        assert success is True
        assert rollback_plan.status == RollbackStatus.COMPLETED
        assert rollback_plan.started_at is not None
        assert rollback_plan.completed_at is not None
        assert rollback_plan.plan_id not in self.rollback_manager.active_rollbacks
        assert rollback_plan in self.rollback_manager.rollback_history

    async def test_execute_rollback_failure(self):
        """Test failed rollback execution"""
        # Create rollback plan
        rollback_plan = await self.rollback_manager.create_rollback_plan(
            pipeline=self.test_pipeline,
            trigger=RollbackTrigger.DEPLOYMENT_FAILURE,
            trigger_details={"test": "data"},
            created_by="test_user",
        )

        # Mock failed execution
        with mock.patch.object(
            self.rollback_manager, "_execute_rollback_action", return_value=False
        ):
            success = await self.rollback_manager.execute_rollback(rollback_plan)

        assert success is False
        assert rollback_plan.status == RollbackStatus.FAILED
        assert rollback_plan.error_message is not None
        assert rollback_plan.plan_id not in self.rollback_manager.active_rollbacks
        assert rollback_plan in self.rollback_manager.rollback_history

    async def test_execute_rollback_action_with_retries(self):
        """Test rollback action execution with retries"""
        action = RollbackAction(
            action_id="test_action_123",
            action_type="package_rollback",
            target_component="git",
            rollback_command="dnf downgrade git-2.44.0 -y",
            validation_command="rpm -q git | grep 2.44.0",
            timeout_seconds=300,
            retry_count=3,
        )

        # Mock successful execution on second attempt
        call_count = 0

        async def mock_sleep(duration):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt failed")

        with mock.patch("asyncio.sleep", side_effect=mock_sleep):
            # First call should fail, second should succeed
            success = await self.rollback_manager._execute_rollback_action(action)

        # Should succeed after retry
        assert success is True

    async def test_monitor_pipeline_health(self):
        """Test pipeline health monitoring"""
        # Test no triggers detected
        with mock.patch.object(
            self.rollback_manager, "_check_deployment_failure", return_value=False
        ):
            with mock.patch.object(
                self.rollback_manager,
                "_check_critical_system_failure",
                return_value=False,
            ):
                with mock.patch.object(
                    self.rollback_manager,
                    "_check_service_availability",
                    return_value=False,
                ):
                    with mock.patch.object(
                        self.rollback_manager, "_check_error_rates", return_value=False
                    ):
                        with mock.patch.object(
                            self.rollback_manager,
                            "_check_performance_degradation",
                            return_value=False,
                        ):
                            trigger = (
                                await self.rollback_manager.monitor_pipeline_health(
                                    self.test_pipeline
                                )
                            )

        assert trigger is None

        # Test deployment failure trigger
        with mock.patch.object(
            self.rollback_manager, "_check_deployment_failure", return_value=True
        ):
            trigger = await self.rollback_manager.monitor_pipeline_health(
                self.test_pipeline
            )

        assert trigger == RollbackTrigger.DEPLOYMENT_FAILURE

    async def test_check_deployment_failure(self):
        """Test deployment failure detection"""
        # Pipeline with failed phase
        failed_phase = RolloutPhase(
            phase_id="failed_phase_123",
            phase_name="Failed Phase",
            stage=PipelineStage.FAILED,
            target_environments=["staging"],
            update_batch=self.update_batch,
            validation_tests=["health_check"],
            success_criteria={"min_test_pass_rate": 0.8},
            rollback_triggers=["critical_error"],
            estimated_duration="30 minutes",
        )

        self.test_pipeline.phases.append(failed_phase)

        result = await self.rollback_manager._check_deployment_failure(
            self.test_pipeline
        )
        assert result is True

        # Remove failed phase
        self.test_pipeline.phases.remove(failed_phase)

        result = await self.rollback_manager._check_deployment_failure(
            self.test_pipeline
        )
        assert result is False

    async def test_trigger_manual_rollback(self):
        """Test manual rollback trigger"""
        rollback_plan = await self.rollback_manager.trigger_manual_rollback(
            pipeline_id="test_pipeline_456",
            reason="Critical bug detected",
            requested_by="admin_user",
        )

        assert rollback_plan is not None
        assert rollback_plan.trigger == RollbackTrigger.MANUAL_ROLLBACK_REQUESTED
        assert rollback_plan.trigger_details["reason"] == "Critical bug detected"
        assert rollback_plan.trigger_details["requested_by"] == "admin_user"
        assert rollback_plan.created_by == "admin_user"

    async def test_validate_rollback_success(self):
        """Test rollback validation"""
        rollback_plan = await self.rollback_manager.create_rollback_plan(
            pipeline=self.test_pipeline,
            trigger=RollbackTrigger.DEPLOYMENT_FAILURE,
            trigger_details={"test": "data"},
            created_by="test_user",
        )

        # Mock successful validation
        with mock.patch.object(
            self.rollback_manager,
            "_check_system_health",
            return_value={"status": "passed"},
        ):
            with mock.patch.object(
                self.rollback_manager,
                "_check_service_health",
                return_value={"status": "passed"},
            ):
                with mock.patch.object(
                    self.rollback_manager,
                    "_check_performance_metrics",
                    return_value={"status": "passed"},
                ):
                    success = await self.rollback_manager._validate_rollback_success(
                        rollback_plan
                    )

        assert success is True
        assert "system_health" in rollback_plan.validation_results
        assert "service_availability" in rollback_plan.validation_results
        assert "performance" in rollback_plan.validation_results

    def test_serialize_deserialize_rollback(self):
        """Test rollback serialization and deserialization"""
        # Create rollback plan
        actions = [
            RollbackAction(
                action_id="test_action_1",
                action_type="package_rollback",
                target_component="git",
                rollback_command="dnf downgrade git-2.44.0 -y",
                timeout_seconds=300,
                retry_count=3,
            )
        ]

        rollback_plan = RollbackPlan(
            plan_id="test_rollback_123",
            pipeline_id="test_pipeline_456",
            phase_id="test_phase_789",
            trigger=RollbackTrigger.DEPLOYMENT_FAILURE,
            trigger_details={"test": "data"},
            rollback_actions=actions,
            estimated_duration="30 minutes",
            created_at=datetime.now(),
            created_by="test_user",
            status=RollbackStatus.PENDING,
        )

        # Serialize
        serialized = self.rollback_manager._serialize_rollback(rollback_plan)
        assert serialized["plan_id"] == "test_rollback_123"
        assert serialized["trigger"] == "deployment_failure"
        assert serialized["status"] == "pending"
        assert len(serialized["rollback_actions"]) == 1

        # Deserialize
        deserialized = self.rollback_manager._deserialize_rollback(serialized)
        assert deserialized.plan_id == "test_rollback_123"
        assert deserialized.trigger == RollbackTrigger.DEPLOYMENT_FAILURE
        assert deserialized.status == RollbackStatus.PENDING
        assert len(deserialized.rollback_actions) == 1
        assert deserialized.rollback_actions[0].action_id == "test_action_1"

    def test_get_rollback_status(self):
        """Test rollback status retrieval"""
        # Create rollback plan
        actions = [
            RollbackAction(
                action_id="test_action_1",
                action_type="package_rollback",
                target_component="git",
                rollback_command="dnf downgrade git-2.44.0 -y",
                timeout_seconds=300,
                retry_count=3,
            )
        ]

        rollback_plan = RollbackPlan(
            plan_id="test_rollback_123",
            pipeline_id="test_pipeline_456",
            phase_id=None,
            trigger=RollbackTrigger.DEPLOYMENT_FAILURE,
            trigger_details={"test": "data"},
            rollback_actions=actions,
            estimated_duration="30 minutes",
            created_at=datetime.now(),
            created_by="test_user",
            status=RollbackStatus.COMPLETED,
        )

        # Add to history
        self.rollback_manager.rollback_history.append(rollback_plan)

        # Get status
        status = self.rollback_manager.get_rollback_status("test_rollback_123")

        assert status is not None
        assert status["plan_id"] == "test_rollback_123"
        assert status["pipeline_id"] == "test_pipeline_456"
        assert status["status"] == "completed"
        assert status["trigger"] == "deployment_failure"
        assert status["actions_count"] == 1

        # Test non-existent rollback
        status = self.rollback_manager.get_rollback_status("non_existent")
        assert status is None

    def test_get_rollback_statistics(self):
        """Test rollback statistics generation"""
        # Add test data
        completed_rollback = RollbackPlan(
            plan_id="completed_123",
            pipeline_id="pipeline_1",
            phase_id=None,
            trigger=RollbackTrigger.DEPLOYMENT_FAILURE,
            trigger_details={},
            rollback_actions=[],
            estimated_duration="30 minutes",
            created_at=datetime.now() - timedelta(hours=2),
            created_by="test_user",
            status=RollbackStatus.COMPLETED,
            started_at=datetime.now() - timedelta(hours=2),
            completed_at=datetime.now() - timedelta(hours=1, minutes=30),
        )

        failed_rollback = RollbackPlan(
            plan_id="failed_123",
            pipeline_id="pipeline_2",
            phase_id=None,
            trigger=RollbackTrigger.ERROR_RATE_HIGH,
            trigger_details={},
            rollback_actions=[],
            estimated_duration="45 minutes",
            created_at=datetime.now() - timedelta(hours=1),
            created_by="test_user",
            status=RollbackStatus.FAILED,
        )

        self.rollback_manager.rollback_history = [completed_rollback, failed_rollback]

        stats = self.rollback_manager.get_rollback_statistics()

        assert stats["total_rollbacks"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["success_rate"] == 50.0
        assert (
            stats["average_duration_minutes"] == 30.0
        )  # Only completed rollback counted
        assert stats["trigger_breakdown"]["deployment_failure"] == 1
        assert stats["trigger_breakdown"]["error_rate_high"] == 1
        assert stats["active_rollbacks"] == 0


class TestPipelineExecutorRollbackIntegration:
    """Test rollback integration with pipeline executor"""

    def setup_method(self):
        """Setup test environment"""
        self.config = {
            "max_concurrent_phases": 2,
            "phase_timeout_minutes": 60,
            "auto_rollback_enabled": True,
        }

        self.executor = PipelineExecutor(self.config)

        # Create test pipeline
        self.test_pipeline = self._create_test_pipeline()

    def _create_test_pipeline(self) -> RolloutPipeline:
        """Create test pipeline"""
        update_plan = UpdatePlan(
            plan_id="test_plan_123",
            batch_id="test_batch_456",
            execution_strategy="rolling",
            total_estimated_time="1h",
            phases=[],
            risk_mitigation_steps=[],
            rollback_plan={},
            monitoring_points=[],
            approval_required=False,
            created_at=datetime.now(),
            ai_confidence=0.8,
        )

        return RolloutPipeline(
            pipeline_id="test_pipeline_123",
            pipeline_name="Test Pipeline",
            strategy=RolloutStrategy.ROLLING,
            update_plan=update_plan,
            phases=[],
            approval_gates=[],
            global_rollback_triggers=[],
            monitoring_config={},
            notification_config={},
            created_at=datetime.now(),
            created_by="test_user",
        )

    def test_executor_rollback_manager_initialization(self):
        """Test executor has rollback manager"""
        assert self.executor.rollback_manager is not None
        assert isinstance(self.executor.rollback_manager, RollbackManager)

    async def test_trigger_manual_rollback(self):
        """Test manual rollback trigger through executor"""
        with mock.patch.object(
            self.executor.rollback_manager, "trigger_manual_rollback"
        ) as mock_trigger:
            with mock.patch.object(
                self.executor.rollback_manager, "execute_rollback", return_value=True
            ):
                mock_trigger.return_value = mock.MagicMock()

                success = await self.executor.trigger_manual_rollback(
                    pipeline_id="test_pipeline_123",
                    reason="Critical issue",
                    requested_by="admin",
                )

        assert success is True
        mock_trigger.assert_called_once_with(
            pipeline_id="test_pipeline_123",
            reason="Critical issue",
            requested_by="admin",
        )

    async def test_handle_pipeline_failure_with_rollback(self):
        """Test pipeline failure handling with rollback"""
        with mock.patch.object(
            self.executor.rollback_manager, "create_rollback_plan"
        ) as mock_create:
            with mock.patch.object(
                self.executor.rollback_manager, "execute_rollback", return_value=True
            ):
                mock_create.return_value = mock.MagicMock()

                success = await self.executor._handle_pipeline_failure(
                    self.test_pipeline, "Deployment failed"
                )

        assert success is True
        mock_create.assert_called_once()

        # Check that rollback plan was created with correct trigger
        call_args = mock_create.call_args
        assert call_args[1]["trigger"] == RollbackTrigger.DEPLOYMENT_FAILURE
        assert call_args[1]["trigger_details"]["error_message"] == "Deployment failed"


class TestRollbackTriggers:
    """Test rollback trigger enumeration"""

    def test_rollback_trigger_values(self):
        """Test rollback trigger enum values"""
        assert (
            RollbackTrigger.CRITICAL_SYSTEM_FAILURE.value == "critical_system_failure"
        )
        assert (
            RollbackTrigger.SECURITY_BREACH_DETECTED.value == "security_breach_detected"
        )
        assert RollbackTrigger.DATA_CORRUPTION.value == "data_corruption"
        assert RollbackTrigger.SERVICE_UNAVAILABLE.value == "service_unavailable"
        assert (
            RollbackTrigger.PERFORMANCE_DEGRADATION_SEVERE.value
            == "performance_degradation_severe"
        )
        assert RollbackTrigger.ERROR_RATE_HIGH.value == "error_rate_high"
        assert RollbackTrigger.DEPLOYMENT_FAILURE.value == "deployment_failure"
        assert RollbackTrigger.VALIDATION_FAILURE.value == "validation_failure"
        assert (
            RollbackTrigger.MANUAL_ROLLBACK_REQUESTED.value
            == "manual_rollback_requested"
        )
        assert RollbackTrigger.TIMEOUT_EXCEEDED.value == "timeout_exceeded"


class TestRollbackStatus:
    """Test rollback status enumeration"""

    def test_rollback_status_values(self):
        """Test rollback status enum values"""
        assert RollbackStatus.PENDING.value == "pending"
        assert RollbackStatus.IN_PROGRESS.value == "in_progress"
        assert RollbackStatus.COMPLETED.value == "completed"
        assert RollbackStatus.FAILED.value == "failed"
        assert RollbackStatus.CANCELLED.value == "cancelled"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
