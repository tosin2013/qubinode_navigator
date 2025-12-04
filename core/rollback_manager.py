"""
Qubinode Navigator Automated Rollback Manager

Handles automated rollback mechanisms for failed updates, including
trigger detection, rollback execution, and recovery validation.

Based on ADR-0030: Software and OS Update Strategy
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import json

from core.rollout_pipeline import RolloutPipeline, RolloutPhase, PipelineStage


class RollbackTrigger(Enum):
    """Types of rollback triggers"""

    CRITICAL_SYSTEM_FAILURE = "critical_system_failure"
    SECURITY_BREACH_DETECTED = "security_breach_detected"
    DATA_CORRUPTION = "data_corruption"
    SERVICE_UNAVAILABLE = "service_unavailable"
    PERFORMANCE_DEGRADATION_SEVERE = "performance_degradation_severe"
    ERROR_RATE_HIGH = "error_rate_high"
    DEPLOYMENT_FAILURE = "deployment_failure"
    VALIDATION_FAILURE = "validation_failure"
    MANUAL_ROLLBACK_REQUESTED = "manual_rollback_requested"
    TIMEOUT_EXCEEDED = "timeout_exceeded"


class RollbackStatus(Enum):
    """Rollback execution status"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RollbackAction:
    """Individual rollback action"""

    action_id: str
    action_type: str  # "package_rollback", "config_restore", "service_restart", etc.
    target_component: str
    rollback_command: str
    validation_command: Optional[str] = None
    timeout_seconds: int = 300
    retry_count: int = 3
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class RollbackPlan:
    """Complete rollback execution plan"""

    plan_id: str
    pipeline_id: str
    phase_id: Optional[str]
    trigger: RollbackTrigger
    trigger_details: Dict[str, Any]
    rollback_actions: List[RollbackAction]
    estimated_duration: str
    created_at: datetime
    created_by: str
    status: RollbackStatus = RollbackStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    validation_results: Dict[str, Any] = None

    def __post_init__(self):
        if self.validation_results is None:
            self.validation_results = {}


class RollbackManager:
    """
    Automated Rollback Manager

    Handles detection of rollback triggers, execution of rollback plans,
    and validation of rollback success.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.rollback_storage_path = Path(self.config.get("rollback_storage_path", "data/rollbacks"))
        self.auto_rollback_enabled = self.config.get("auto_rollback_enabled", True)
        self.rollback_timeout_minutes = self.config.get("rollback_timeout_minutes", 60)
        self.validation_timeout_minutes = self.config.get("validation_timeout_minutes", 15)

        # Trigger thresholds
        self.error_rate_threshold = self.config.get("error_rate_threshold", 0.05)  # 5%
        self.performance_degradation_threshold = self.config.get("performance_degradation_threshold", 0.3)  # 30%
        self.service_unavailable_threshold = self.config.get("service_unavailable_threshold", 300)  # 5 minutes

        # State
        self.active_rollbacks: Dict[str, RollbackPlan] = {}
        self.rollback_history: List[RollbackPlan] = []
        self.trigger_monitors: Dict[str, Any] = {}

        # Initialize storage
        self.rollback_storage_path.mkdir(parents=True, exist_ok=True)

        # Load existing rollbacks
        self._load_rollbacks()

    def _load_rollbacks(self):
        """Load existing rollbacks from storage"""
        try:
            for rollback_file in self.rollback_storage_path.glob("rollback_*.json"):
                with open(rollback_file, "r") as f:
                    rollback_data = json.load(f)
                    rollback = self._deserialize_rollback(rollback_data)

                    if rollback.status in [
                        RollbackStatus.PENDING,
                        RollbackStatus.IN_PROGRESS,
                    ]:
                        self.active_rollbacks[rollback.plan_id] = rollback
                    else:
                        self.rollback_history.append(rollback)

            self.logger.info(f"Loaded {len(self.active_rollbacks)} active rollbacks and {len(self.rollback_history)} completed rollbacks")

        except Exception as e:
            self.logger.error(f"Failed to load rollbacks: {e}")

    def _save_rollback(self, rollback: RollbackPlan):
        """Save rollback to storage"""
        try:
            rollback_file = self.rollback_storage_path / f"rollback_{rollback.plan_id}.json"
            rollback_data = self._serialize_rollback(rollback)

            def json_serializer(obj):
                if hasattr(obj, "value"):  # Enum objects
                    return obj.value
                return str(obj)

            with open(rollback_file, "w") as f:
                json.dump(rollback_data, f, indent=2, default=json_serializer)

            self.logger.debug(f"Saved rollback {rollback.plan_id}")

        except Exception as e:
            self.logger.error(f"Failed to save rollback {rollback.plan_id}: {e}")

    def _serialize_rollback(self, rollback: RollbackPlan) -> Dict[str, Any]:
        """Serialize rollback to JSON-compatible format"""
        return {
            "plan_id": rollback.plan_id,
            "pipeline_id": rollback.pipeline_id,
            "phase_id": rollback.phase_id,
            "trigger": rollback.trigger.value,
            "trigger_details": rollback.trigger_details,
            "rollback_actions": [asdict(action) for action in rollback.rollback_actions],
            "estimated_duration": rollback.estimated_duration,
            "created_at": rollback.created_at.isoformat(),
            "created_by": rollback.created_by,
            "status": rollback.status.value,
            "started_at": rollback.started_at.isoformat() if rollback.started_at else None,
            "completed_at": rollback.completed_at.isoformat() if rollback.completed_at else None,
            "error_message": rollback.error_message,
            "validation_results": rollback.validation_results,
        }

    def _deserialize_rollback(self, data: Dict[str, Any]) -> RollbackPlan:
        """Deserialize rollback from JSON format"""
        # Convert string enums back to enum objects
        trigger = RollbackTrigger(data["trigger"])
        status = RollbackStatus(data["status"])

        # Deserialize rollback actions
        actions = []
        for action_data in data["rollback_actions"]:
            actions.append(RollbackAction(**action_data))

        return RollbackPlan(
            plan_id=data["plan_id"],
            pipeline_id=data["pipeline_id"],
            phase_id=data.get("phase_id"),
            trigger=trigger,
            trigger_details=data["trigger_details"],
            rollback_actions=actions,
            estimated_duration=data["estimated_duration"],
            created_at=datetime.fromisoformat(data["created_at"]),
            created_by=data["created_by"],
            status=status,
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error_message=data.get("error_message"),
            validation_results=data.get("validation_results", {}),
        )

    async def monitor_pipeline_health(self, pipeline: RolloutPipeline) -> Optional[RollbackTrigger]:
        """Monitor pipeline health and detect rollback triggers"""

        try:
            # Check for critical system failures
            if await self._check_critical_system_failure(pipeline):
                return RollbackTrigger.CRITICAL_SYSTEM_FAILURE

            # Check for service availability
            if await self._check_service_availability(pipeline):
                return RollbackTrigger.SERVICE_UNAVAILABLE

            # Check error rates
            if await self._check_error_rates(pipeline):
                return RollbackTrigger.ERROR_RATE_HIGH

            # Check performance degradation
            if await self._check_performance_degradation(pipeline):
                return RollbackTrigger.PERFORMANCE_DEGRADATION_SEVERE

            # Check deployment status
            if await self._check_deployment_failure(pipeline):
                return RollbackTrigger.DEPLOYMENT_FAILURE

            return None

        except Exception as e:
            self.logger.error(f"Health monitoring failed for pipeline {pipeline.pipeline_id}: {e}")
            return None

    async def _check_critical_system_failure(self, pipeline: RolloutPipeline) -> bool:
        """Check for critical system failures"""
        # This would integrate with system monitoring tools
        # For now, simulate check
        return False

    async def _check_service_availability(self, pipeline: RolloutPipeline) -> bool:
        """Check if services are available"""
        # This would check service health endpoints
        # For now, simulate check
        return False

    async def _check_error_rates(self, pipeline: RolloutPipeline) -> bool:
        """Check if error rates exceed threshold"""
        # This would integrate with monitoring systems
        # For now, simulate check
        return False

    async def _check_performance_degradation(self, pipeline: RolloutPipeline) -> bool:
        """Check for performance degradation"""
        # This would check performance metrics
        # For now, simulate check
        return False

    async def _check_deployment_failure(self, pipeline: RolloutPipeline) -> bool:
        """Check for deployment failures"""
        # Check if any phases have failed
        failed_phases = [p for p in pipeline.phases if p.stage == PipelineStage.FAILED]
        return len(failed_phases) > 0

    async def create_rollback_plan(
        self,
        pipeline: RolloutPipeline,
        trigger: RollbackTrigger,
        trigger_details: Dict[str, Any],
        phase_id: Optional[str] = None,
        created_by: str = "system",
    ) -> RollbackPlan:
        """Create rollback plan for pipeline"""

        plan_id = f"rollback_{int(time.time())}"

        self.logger.info(f"Creating rollback plan {plan_id} for pipeline {pipeline.pipeline_id} due to {trigger.value}")

        # Generate rollback actions based on pipeline and trigger
        rollback_actions = await self._generate_rollback_actions(pipeline, trigger, phase_id)

        # Estimate duration
        estimated_duration = self._estimate_rollback_duration(rollback_actions)

        # Create rollback plan
        rollback_plan = RollbackPlan(
            plan_id=plan_id,
            pipeline_id=pipeline.pipeline_id,
            phase_id=phase_id,
            trigger=trigger,
            trigger_details=trigger_details,
            rollback_actions=rollback_actions,
            estimated_duration=estimated_duration,
            created_at=datetime.now(),
            created_by=created_by,
            status=RollbackStatus.PENDING,
        )

        # Save and register rollback
        self.active_rollbacks[plan_id] = rollback_plan
        self._save_rollback(rollback_plan)

        self.logger.info(f"Created rollback plan {plan_id} with {len(rollback_actions)} actions")

        return rollback_plan

    async def _generate_rollback_actions(
        self,
        pipeline: RolloutPipeline,
        trigger: RollbackTrigger,
        phase_id: Optional[str] = None,
    ) -> List[RollbackAction]:
        """Generate rollback actions based on pipeline and trigger"""

        actions = []

        # Get phases to rollback (reverse order)
        phases_to_rollback = []
        if phase_id:
            # Rollback specific phase and all subsequent phases
            phase_found = False
            for phase in pipeline.phases:
                if phase.phase_id == phase_id:
                    phase_found = True
                if phase_found and phase.stage in [
                    PipelineStage.COMPLETED,
                    PipelineStage.DEPLOYING,
                    PipelineStage.FAILED,
                ]:
                    phases_to_rollback.append(phase)
        else:
            # Rollback all completed/failed phases
            phases_to_rollback = [p for p in pipeline.phases if p.stage in [PipelineStage.COMPLETED, PipelineStage.FAILED]]

        # Reverse order for rollback
        phases_to_rollback.reverse()

        # Generate actions for each phase
        for i, phase in enumerate(phases_to_rollback):
            phase_actions = await self._generate_phase_rollback_actions(phase, i)
            actions.extend(phase_actions)

        # Add global rollback actions
        global_actions = await self._generate_global_rollback_actions(pipeline, trigger)
        actions.extend(global_actions)

        return actions

    async def _generate_phase_rollback_actions(self, phase: RolloutPhase, sequence: int) -> List[RollbackAction]:
        """Generate rollback actions for a specific phase"""

        actions = []

        # Stop services action
        actions.append(
            RollbackAction(
                action_id=f"stop_services_{phase.phase_id}_{sequence}",
                action_type="service_stop",
                target_component=f"phase_{phase.phase_id}",
                rollback_command="systemctl stop qubinode-services",
                validation_command="systemctl is-active qubinode-services",
                timeout_seconds=120,
                retry_count=2,
            )
        )

        # Package rollback action
        for update in phase.update_batch.updates:
            actions.append(
                RollbackAction(
                    action_id=f"rollback_package_{update.component_name}_{sequence}",
                    action_type="package_rollback",
                    target_component=update.component_name,
                    rollback_command=f"dnf downgrade {update.component_name}-{update.current_version} -y",
                    validation_command=f"rpm -q {update.component_name} | grep {update.current_version}",
                    timeout_seconds=300,
                    retry_count=3,
                    dependencies=[f"stop_services_{phase.phase_id}_{sequence}"],
                )
            )

        # Configuration restore action
        actions.append(
            RollbackAction(
                action_id=f"restore_config_{phase.phase_id}_{sequence}",
                action_type="config_restore",
                target_component=f"phase_{phase.phase_id}",
                rollback_command=f"cp /backup/config_{phase.phase_id}/* /etc/ -R",
                validation_command="test -f /etc/qubinode.conf",
                timeout_seconds=60,
                retry_count=2,
                dependencies=[f"rollback_package_{update.component_name}_{sequence}" for update in phase.update_batch.updates],
            )
        )

        # Restart services action
        actions.append(
            RollbackAction(
                action_id=f"restart_services_{phase.phase_id}_{sequence}",
                action_type="service_restart",
                target_component=f"phase_{phase.phase_id}",
                rollback_command="systemctl start qubinode-services",
                validation_command="systemctl is-active qubinode-services",
                timeout_seconds=180,
                retry_count=3,
                dependencies=[f"restore_config_{phase.phase_id}_{sequence}"],
            )
        )

        return actions

    async def _generate_global_rollback_actions(self, pipeline: RolloutPipeline, trigger: RollbackTrigger) -> List[RollbackAction]:
        """Generate global rollback actions"""

        actions = []

        # System validation action
        actions.append(
            RollbackAction(
                action_id=f"system_validation_{int(time.time())}",
                action_type="system_validation",
                target_component="system",
                rollback_command="qubinode-cli validate-system",
                validation_command="qubinode-cli health-check",
                timeout_seconds=300,
                retry_count=1,
            )
        )

        # Cleanup action
        actions.append(
            RollbackAction(
                action_id=f"cleanup_{int(time.time())}",
                action_type="cleanup",
                target_component="system",
                rollback_command="qubinode-cli cleanup-rollback",
                timeout_seconds=120,
                retry_count=1,
                dependencies=[f"system_validation_{int(time.time())}"],
            )
        )

        return actions

    def _estimate_rollback_duration(self, actions: List[RollbackAction]) -> str:
        """Estimate total rollback duration"""

        total_seconds = sum(action.timeout_seconds for action in actions)
        total_minutes = total_seconds / 60

        if total_minutes < 60:
            return f"{total_minutes:.0f} minutes"
        else:
            hours = total_minutes / 60
            return f"{hours:.1f} hours"

    async def execute_rollback(self, rollback_plan: RollbackPlan) -> bool:
        """Execute rollback plan"""

        if not self.auto_rollback_enabled:
            self.logger.warning(f"Auto-rollback disabled, skipping execution of {rollback_plan.plan_id}")
            return False

        self.logger.info(f"Starting rollback execution for plan {rollback_plan.plan_id}")

        try:
            # Update status
            rollback_plan.status = RollbackStatus.IN_PROGRESS
            rollback_plan.started_at = datetime.now()
            self._save_rollback(rollback_plan)

            # Execute actions in dependency order
            executed_actions = set()

            while len(executed_actions) < len(rollback_plan.rollback_actions):
                progress_made = False

                for action in rollback_plan.rollback_actions:
                    if action.action_id in executed_actions:
                        continue

                    # Check if dependencies are satisfied
                    dependencies_met = all(dep in executed_actions for dep in action.dependencies)

                    if dependencies_met:
                        success = await self._execute_rollback_action(action)
                        if success:
                            executed_actions.add(action.action_id)
                            progress_made = True
                        else:
                            raise Exception(f"Rollback action {action.action_id} failed")

                if not progress_made:
                    raise Exception("Rollback execution stuck - circular dependencies or all remaining actions failed")

            # Validate rollback success
            validation_success = await self._validate_rollback_success(rollback_plan)

            if validation_success:
                rollback_plan.status = RollbackStatus.COMPLETED
                rollback_plan.completed_at = datetime.now()
                self.logger.info(f"Rollback {rollback_plan.plan_id} completed successfully")
                result = True
            else:
                rollback_plan.status = RollbackStatus.FAILED
                rollback_plan.error_message = "Rollback validation failed"
                self.logger.error(f"Rollback {rollback_plan.plan_id} validation failed")
                result = False

            # Move to history
            self.rollback_history.append(rollback_plan)
            del self.active_rollbacks[rollback_plan.plan_id]
            self._save_rollback(rollback_plan)

            return result

        except Exception as e:
            self.logger.error(f"Rollback execution failed: {e}")
            rollback_plan.status = RollbackStatus.FAILED
            rollback_plan.error_message = str(e)
            rollback_plan.completed_at = datetime.now()

            # Move to history
            self.rollback_history.append(rollback_plan)
            del self.active_rollbacks[rollback_plan.plan_id]
            self._save_rollback(rollback_plan)

            return False

    async def _execute_rollback_action(self, action: RollbackAction) -> bool:
        """Execute individual rollback action"""

        self.logger.info(f"Executing rollback action {action.action_id}: {action.action_type}")

        for attempt in range(action.retry_count):
            try:
                # Execute rollback command
                self.logger.debug(f"Running command: {action.rollback_command}")

                # Simulate command execution
                await asyncio.sleep(1)  # Simulate execution time

                # Validate if validation command is provided
                if action.validation_command:
                    self.logger.debug(f"Validating with: {action.validation_command}")
                    # Simulate validation
                    await asyncio.sleep(0.5)

                self.logger.info(f"Rollback action {action.action_id} completed successfully")
                return True

            except Exception as e:
                self.logger.warning(f"Rollback action {action.action_id} attempt {attempt + 1} failed: {e}")
                if attempt < action.retry_count - 1:
                    await asyncio.sleep(5)  # Wait before retry
                else:
                    self.logger.error(f"Rollback action {action.action_id} failed after {action.retry_count} attempts")
                    return False

        return False

    async def _validate_rollback_success(self, rollback_plan: RollbackPlan) -> bool:
        """Validate that rollback was successful"""

        try:
            self.logger.info(f"Validating rollback success for plan {rollback_plan.plan_id}")

            validation_results = {}

            # System health check
            validation_results["system_health"] = await self._check_system_health()

            # Service availability check
            validation_results["service_availability"] = await self._check_service_health()

            # Performance check
            validation_results["performance"] = await self._check_performance_metrics()

            # Overall validation
            all_checks_passed = all(result.get("status") == "passed" for result in validation_results.values())

            rollback_plan.validation_results = validation_results

            return all_checks_passed

        except Exception as e:
            self.logger.error(f"Rollback validation failed: {e}")
            return False

    async def _check_system_health(self) -> Dict[str, Any]:
        """Check system health after rollback"""
        # Simulate system health check
        return {
            "status": "passed",
            "cpu_usage": 25,
            "memory_usage": 45,
            "disk_usage": 60,
        }

    async def _check_service_health(self) -> Dict[str, Any]:
        """Check service health after rollback"""
        # Simulate service health check
        return {"status": "passed", "services_running": 12, "services_failed": 0}

    async def _check_performance_metrics(self) -> Dict[str, Any]:
        """Check performance metrics after rollback"""
        # Simulate performance check
        return {"status": "passed", "response_time": 150, "throughput": 1000}

    async def trigger_manual_rollback(
        self,
        pipeline_id: str,
        reason: str,
        requested_by: str,
        phase_id: Optional[str] = None,
    ) -> Optional[RollbackPlan]:
        """Trigger manual rollback"""

        # Find pipeline (this would integrate with pipeline manager)
        # For now, create a mock pipeline
        from core.rollout_pipeline import RolloutPipeline, RolloutStrategy
        from core.ai_update_manager import UpdatePlan

        mock_pipeline = RolloutPipeline(
            pipeline_id=pipeline_id,
            pipeline_name=f"Pipeline {pipeline_id}",
            strategy=RolloutStrategy.ROLLING,
            update_plan=UpdatePlan(
                plan_id="mock_plan",
                batch_id="mock_batch",
                execution_strategy="rolling",
                total_estimated_time="1h",
                phases=[],
                risk_mitigation_steps=[],
                rollback_plan={},
                monitoring_points=[],
                approval_required=False,
                created_at=datetime.now(),
                ai_confidence=0.8,
            ),
            phases=[],
            approval_gates=[],
            global_rollback_triggers=[],
            monitoring_config={},
            notification_config={},
            created_at=datetime.now(),
            created_by="system",
        )

        trigger_details = {
            "reason": reason,
            "requested_by": requested_by,
            "timestamp": datetime.now().isoformat(),
        }

        rollback_plan = await self.create_rollback_plan(
            pipeline=mock_pipeline,
            trigger=RollbackTrigger.MANUAL_ROLLBACK_REQUESTED,
            trigger_details=trigger_details,
            phase_id=phase_id,
            created_by=requested_by,
        )

        return rollback_plan

    def get_rollback_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get rollback status"""

        # Check active rollbacks
        if plan_id in self.active_rollbacks:
            rollback = self.active_rollbacks[plan_id]
        else:
            # Check history
            rollback = next((r for r in self.rollback_history if r.plan_id == plan_id), None)

        if not rollback:
            return None

        return {
            "plan_id": rollback.plan_id,
            "pipeline_id": rollback.pipeline_id,
            "status": rollback.status.value,
            "trigger": rollback.trigger.value,
            "created_at": rollback.created_at.isoformat(),
            "started_at": rollback.started_at.isoformat() if rollback.started_at else None,
            "completed_at": rollback.completed_at.isoformat() if rollback.completed_at else None,
            "estimated_duration": rollback.estimated_duration,
            "actions_count": len(rollback.rollback_actions),
            "error_message": rollback.error_message,
            "validation_results": rollback.validation_results,
        }

    def get_rollback_statistics(self) -> Dict[str, Any]:
        """Get rollback statistics"""

        all_rollbacks = list(self.active_rollbacks.values()) + self.rollback_history

        if not all_rollbacks:
            return {
                "total_rollbacks": 0,
                "success_rate": 0.0,
                "average_duration_minutes": 0.0,
                "trigger_breakdown": {},
                "active_rollbacks": 0,
            }

        # Calculate statistics
        completed_rollbacks = [r for r in all_rollbacks if r.status == RollbackStatus.COMPLETED]
        failed_rollbacks = [r for r in all_rollbacks if r.status == RollbackStatus.FAILED]

        success_rate = len(completed_rollbacks) / len(all_rollbacks) * 100 if all_rollbacks else 0

        # Calculate average duration for completed rollbacks
        durations = []
        for rollback in completed_rollbacks:
            if rollback.started_at and rollback.completed_at:
                duration = (rollback.completed_at - rollback.started_at).total_seconds() / 60
                durations.append(duration)

        average_duration = sum(durations) / len(durations) if durations else 0

        # Trigger breakdown
        trigger_counts = {}
        for rollback in all_rollbacks:
            trigger = rollback.trigger.value
            trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1

        return {
            "total_rollbacks": len(all_rollbacks),
            "completed": len(completed_rollbacks),
            "failed": len(failed_rollbacks),
            "success_rate": round(success_rate, 1),
            "average_duration_minutes": round(average_duration, 1),
            "trigger_breakdown": trigger_counts,
            "active_rollbacks": len(self.active_rollbacks),
        }
