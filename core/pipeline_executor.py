"""
Qubinode Navigator Pipeline Execution Engine

Handles the execution of rollout pipelines, phase progression,
validation, and rollback operations.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from core.rollout_pipeline import (
    RolloutPipeline,
    RolloutPhase,
    PipelineStage,
    RolloutStrategy,
)
from core.approval_gates import ApprovalGateManager, ApprovalStatus
from core.update_validator import UpdateValidator
from core.update_manager import UpdateBatch
from core.rollback_manager import RollbackManager, RollbackTrigger


class ExecutionResult(Enum):
    """Pipeline execution results"""

    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class PhaseExecution:
    """Phase execution tracking"""

    phase_id: str
    pipeline_id: str
    started_at: datetime
    status: PipelineStage
    progress_percentage: float = 0.0
    current_step: str = ""
    validation_results: Dict[str, Any] = None
    error_details: Optional[str] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.validation_results is None:
            self.validation_results = {}


class PipelineExecutor:
    """
    Pipeline Execution Engine

    Orchestrates the execution of rollout pipelines including
    phase progression, validation, monitoring, and rollback.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.max_concurrent_phases = self.config.get("max_concurrent_phases", 2)
        self.phase_timeout_minutes = self.config.get("phase_timeout_minutes", 120)
        self.validation_timeout_minutes = self.config.get(
            "validation_timeout_minutes", 30
        )
        self.rollback_timeout_minutes = self.config.get("rollback_timeout_minutes", 60)

        # Components
        self.approval_manager = ApprovalGateManager(config)
        self.update_validator = UpdateValidator(config)
        self.rollback_manager = RollbackManager(config)

        # State
        self.active_executions: Dict[str, PhaseExecution] = {}
        self.execution_history: List[PhaseExecution] = []

        # Monitoring
        self.health_checks = {}
        self.performance_metrics = {}

    async def execute_pipeline(self, pipeline: RolloutPipeline) -> ExecutionResult:
        """Execute complete rollout pipeline"""

        self.logger.info(f"Starting execution of pipeline {pipeline.pipeline_id}")

        try:
            # Update pipeline status
            pipeline.status = PipelineStage.DEPLOYING

            # Start health monitoring for rollback detection
            monitoring_task = asyncio.create_task(
                self._monitor_pipeline_for_rollback(pipeline)
            )

            # Execute phases based on strategy
            if pipeline.strategy == RolloutStrategy.CANARY:
                result = await self._execute_canary_strategy(pipeline)
            elif pipeline.strategy == RolloutStrategy.BLUE_GREEN:
                result = await self._execute_blue_green_strategy(pipeline)
            elif pipeline.strategy == RolloutStrategy.ROLLING:
                result = await self._execute_rolling_strategy(pipeline)
            elif pipeline.strategy == RolloutStrategy.ALL_AT_ONCE:
                result = await self._execute_all_at_once_strategy(pipeline)
            else:
                raise ValueError(f"Unknown rollout strategy: {pipeline.strategy}")

            # Stop monitoring
            monitoring_task.cancel()

            # Update final status
            if result == ExecutionResult.SUCCESS:
                pipeline.status = PipelineStage.COMPLETED
                pipeline.completed_at = datetime.now()
            elif result == ExecutionResult.FAILED:
                pipeline.status = PipelineStage.FAILED
            elif result == ExecutionResult.ROLLED_BACK:
                pipeline.status = PipelineStage.ROLLED_BACK
            elif result == ExecutionResult.CANCELLED:
                pipeline.status = PipelineStage.CANCELLED

            self.logger.info(
                f"Pipeline {pipeline.pipeline_id} execution completed with result: {result.value}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            pipeline.status = PipelineStage.FAILED

            # Check if rollback is needed
            if self.rollback_manager.auto_rollback_enabled:
                rollback_result = await self._handle_pipeline_failure(pipeline, str(e))
                if rollback_result:
                    return ExecutionResult.ROLLED_BACK

            return ExecutionResult.FAILED

    async def _execute_canary_strategy(
        self, pipeline: RolloutPipeline
    ) -> ExecutionResult:
        """Execute canary deployment strategy"""

        self.logger.info(
            f"Executing canary strategy for pipeline {pipeline.pipeline_id}"
        )

        # Phase 1: Deploy to canary environment (small subset)
        canary_phases = [p for p in pipeline.phases if "canary" in p.phase_name.lower()]
        if canary_phases:
            canary_result = await self._execute_phase(canary_phases[0], pipeline)
            if canary_result != ExecutionResult.SUCCESS:
                return canary_result

            # Monitor canary for specified duration
            await self._monitor_canary_deployment(canary_phases[0], pipeline)

        # Phase 2: Check approval gates for full rollout
        full_rollout_approved = await self._check_phase_approvals(
            pipeline, "full_rollout"
        )
        if not full_rollout_approved:
            return ExecutionResult.CANCELLED

        # Phase 3: Execute remaining phases
        remaining_phases = [
            p for p in pipeline.phases if "canary" not in p.phase_name.lower()
        ]
        for phase in remaining_phases:
            result = await self._execute_phase(phase, pipeline)
            if result != ExecutionResult.SUCCESS:
                return result

        return ExecutionResult.SUCCESS

    async def _execute_blue_green_strategy(
        self, pipeline: RolloutPipeline
    ) -> ExecutionResult:
        """Execute blue-green deployment strategy"""

        self.logger.info(
            f"Executing blue-green strategy for pipeline {pipeline.pipeline_id}"
        )

        # Phase 1: Deploy to green environment
        green_phases = [p for p in pipeline.phases if "green" in p.phase_name.lower()]
        for phase in green_phases:
            result = await self._execute_phase(phase, pipeline)
            if result != ExecutionResult.SUCCESS:
                return result

        # Phase 2: Validate green environment
        validation_result = await self._validate_environment(pipeline, "green")
        if not validation_result:
            return ExecutionResult.FAILED

        # Phase 3: Check approval for traffic switch
        switch_approved = await self._check_phase_approvals(pipeline, "traffic_switch")
        if not switch_approved:
            return ExecutionResult.CANCELLED

        # Phase 4: Switch traffic to green
        switch_result = await self._switch_traffic(pipeline, "blue", "green")
        if switch_result != ExecutionResult.SUCCESS:
            return switch_result

        # Phase 5: Decommission blue environment
        blue_phases = [p for p in pipeline.phases if "blue" in p.phase_name.lower()]
        for phase in blue_phases:
            await self._decommission_environment(phase, pipeline)

        return ExecutionResult.SUCCESS

    async def _execute_rolling_strategy(
        self, pipeline: RolloutPipeline
    ) -> ExecutionResult:
        """Execute rolling deployment strategy"""

        self.logger.info(
            f"Executing rolling strategy for pipeline {pipeline.pipeline_id}"
        )

        # Execute phases sequentially with validation between each
        for i, phase in enumerate(pipeline.phases):
            # Check approval gates before each phase
            if i > 0:  # Skip approval for first phase
                approved = await self._check_phase_approvals(pipeline, f"phase_{i}")
                if not approved:
                    return ExecutionResult.CANCELLED

            # Execute phase
            result = await self._execute_phase(phase, pipeline)
            if result != ExecutionResult.SUCCESS:
                return result

            # Validate phase completion
            validation_result = await self._validate_phase_completion(phase, pipeline)
            if not validation_result:
                return ExecutionResult.FAILED

            # Wait between phases (except last one)
            if i < len(pipeline.phases) - 1:
                await asyncio.sleep(30)  # 30-second pause between phases

        return ExecutionResult.SUCCESS

    async def _execute_all_at_once_strategy(
        self, pipeline: RolloutPipeline
    ) -> ExecutionResult:
        """Execute all-at-once deployment strategy"""

        self.logger.info(
            f"Executing all-at-once strategy for pipeline {pipeline.pipeline_id}"
        )

        # Check final approval gate
        approved = await self._check_phase_approvals(pipeline, "deployment")
        if not approved:
            return ExecutionResult.CANCELLED

        # Execute all phases in parallel
        phase_tasks = []
        for phase in pipeline.phases:
            task = asyncio.create_task(self._execute_phase(phase, pipeline))
            phase_tasks.append(task)

        # Wait for all phases to complete
        results = await asyncio.gather(*phase_tasks, return_exceptions=True)

        # Check results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(
                    f"Phase {pipeline.phases[i].phase_id} failed: {result}"
                )
                return ExecutionResult.FAILED
            elif result != ExecutionResult.SUCCESS:
                return result

        return ExecutionResult.SUCCESS

    async def _execute_phase(
        self, phase: RolloutPhase, pipeline: RolloutPipeline
    ) -> ExecutionResult:
        """Execute individual pipeline phase"""

        phase_execution = PhaseExecution(
            phase_id=phase.phase_id,
            pipeline_id=pipeline.pipeline_id,
            started_at=datetime.now(),
            status=PipelineStage.DEPLOYING,
        )

        self.active_executions[phase.phase_id] = phase_execution

        try:
            self.logger.info(f"Executing phase {phase.phase_id}: {phase.phase_name}")

            # Update phase status
            phase.stage = PipelineStage.DEPLOYING
            phase.started_at = datetime.now()
            pipeline.current_phase = phase.phase_id

            # Execute deployment steps
            phase_execution.current_step = "Preparing deployment"
            phase_execution.progress_percentage = 10.0

            # Apply updates
            phase_execution.current_step = "Applying updates"
            phase_execution.progress_percentage = 30.0

            deployment_result = await self._deploy_updates(
                phase.update_batch, phase.target_environments
            )
            if not deployment_result:
                raise Exception("Update deployment failed")

            # Run validation tests
            phase_execution.current_step = "Running validation tests"
            phase_execution.progress_percentage = 60.0

            validation_result = await self._run_phase_validation(phase, pipeline)
            if not validation_result:
                raise Exception("Phase validation failed")

            phase_execution.validation_results = validation_result

            # Complete phase
            phase_execution.current_step = "Completing phase"
            phase_execution.progress_percentage = 100.0
            phase_execution.status = PipelineStage.COMPLETED
            phase_execution.completed_at = datetime.now()

            phase.stage = PipelineStage.COMPLETED
            phase.completed_at = datetime.now()

            # Calculate duration
            duration = phase.completed_at - phase.started_at
            phase.actual_duration = f"{duration.total_seconds() / 60:.1f} minutes"

            self.logger.info(
                f"Phase {phase.phase_id} completed successfully in {phase.actual_duration}"
            )

            # Move to history
            self.execution_history.append(phase_execution)
            del self.active_executions[phase.phase_id]

            return ExecutionResult.SUCCESS

        except Exception as e:
            self.logger.error(f"Phase {phase.phase_id} execution failed: {e}")

            phase_execution.status = PipelineStage.FAILED
            phase_execution.error_details = str(e)
            phase_execution.completed_at = datetime.now()

            phase.stage = PipelineStage.FAILED
            phase.error_message = str(e)

            # Move to history
            self.execution_history.append(phase_execution)
            del self.active_executions[phase.phase_id]

            return ExecutionResult.FAILED

    async def _deploy_updates(
        self, update_batch: UpdateBatch, target_environments: List[str]
    ) -> bool:
        """Deploy updates to target environments"""

        try:
            self.logger.info(
                f"Deploying {len(update_batch.updates)} updates to {len(target_environments)} environments"
            )

            # Simulate deployment process
            for env in target_environments:
                self.logger.debug(f"Deploying to environment: {env}")

                # Apply each update in the batch
                for update in update_batch.updates:
                    self.logger.debug(
                        f"Applying update: {update.component_name} {update.available_version}"
                    )

                    # Simulate update application
                    await asyncio.sleep(1)  # Simulate deployment time

            return True

        except Exception as e:
            self.logger.error(f"Update deployment failed: {e}")
            return False

    async def _run_phase_validation(
        self, phase: RolloutPhase, pipeline: RolloutPipeline
    ) -> Dict[str, Any]:
        """Run validation tests for phase"""

        try:
            validation_results = {}

            # Run each validation test
            for test_name in phase.validation_tests:
                self.logger.debug(f"Running validation test: {test_name}")

                # Simulate test execution
                test_result = {
                    "test_name": test_name,
                    "status": "passed",
                    "duration": "30s",
                    "details": f"Validation test {test_name} completed successfully",
                }

                validation_results[test_name] = test_result
                await asyncio.sleep(0.5)  # Simulate test time

            # Check success criteria
            success_criteria_met = await self._check_success_criteria(
                phase.success_criteria, validation_results
            )

            validation_results["overall_status"] = (
                "passed" if success_criteria_met else "failed"
            )
            validation_results["criteria_met"] = success_criteria_met

            return validation_results

        except Exception as e:
            self.logger.error(f"Phase validation failed: {e}")
            return {"overall_status": "failed", "error": str(e)}

    async def _check_success_criteria(
        self, criteria: Dict[str, Any], validation_results: Dict[str, Any]
    ) -> bool:
        """Check if success criteria are met"""

        try:
            # Check minimum test pass rate
            if "min_test_pass_rate" in criteria:
                passed_tests = len(
                    [
                        r
                        for r in validation_results.values()
                        if isinstance(r, dict) and r.get("status") == "passed"
                    ]
                )
                total_tests = len(
                    [r for r in validation_results.values() if isinstance(r, dict)]
                )

                if total_tests > 0:
                    pass_rate = passed_tests / total_tests
                    if pass_rate < criteria["min_test_pass_rate"]:
                        return False

            # Check performance thresholds
            if "max_response_time" in criteria:
                # Simulate performance check
                pass

            # Check error rates
            if "max_error_rate" in criteria:
                # Simulate error rate check
                pass

            return True

        except Exception as e:
            self.logger.error(f"Success criteria check failed: {e}")
            return False

    async def _check_phase_approvals(
        self, pipeline: RolloutPipeline, phase_name: str
    ) -> bool:
        """Check if phase has required approvals"""

        # Find approval gates for this phase
        phase_gates = [
            gate for gate in pipeline.approval_gates if phase_name in gate.stage
        ]

        if not phase_gates:
            return True  # No approval required

        # Check each gate
        for gate in phase_gates:
            status, message = await self.approval_manager.check_gate_approval_status(
                gate
            )

            if (
                status == ApprovalStatus.APPROVED
                or status == ApprovalStatus.AUTO_APPROVED
            ):
                continue
            elif status == ApprovalStatus.REJECTED:
                self.logger.warning(f"Phase {phase_name} rejected: {message}")
                return False
            elif status == ApprovalStatus.EXPIRED:
                self.logger.warning(f"Phase {phase_name} approval expired: {message}")
                return False
            else:
                # Still pending - wait for approval
                self.logger.info(f"Waiting for approval: {message}")
                return False

        return True

    async def _monitor_canary_deployment(
        self, canary_phase: RolloutPhase, pipeline: RolloutPipeline
    ):
        """Monitor canary deployment for issues"""

        monitor_duration = 300  # 5 minutes
        self.logger.info(f"Monitoring canary deployment for {monitor_duration} seconds")

        start_time = time.time()
        while time.time() - start_time < monitor_duration:
            # Check health metrics
            health_status = await self._check_deployment_health(canary_phase)

            if not health_status["healthy"]:
                self.logger.warning(
                    f"Canary deployment health issue detected: {health_status['issues']}"
                )
                # Could trigger automatic rollback here

            await asyncio.sleep(30)  # Check every 30 seconds

        self.logger.info("Canary monitoring completed")

    async def _check_deployment_health(self, phase: RolloutPhase) -> Dict[str, Any]:
        """Check deployment health metrics"""

        # Simulate health checks
        return {
            "healthy": True,
            "response_time": 150,  # ms
            "error_rate": 0.01,  # 1%
            "cpu_usage": 45,  # %
            "memory_usage": 60,  # %
            "issues": [],
        }

    async def _validate_environment(
        self, pipeline: RolloutPipeline, environment: str
    ) -> bool:
        """Validate deployment environment"""

        self.logger.info(
            f"Validating {environment} environment for pipeline {pipeline.pipeline_id}"
        )

        # Run environment-specific validation
        # This would integrate with the UpdateValidator

        return True  # Simplified for now

    async def _switch_traffic(
        self, pipeline: RolloutPipeline, from_env: str, to_env: str
    ) -> ExecutionResult:
        """Switch traffic between environments"""

        self.logger.info(
            f"Switching traffic from {from_env} to {to_env} for pipeline {pipeline.pipeline_id}"
        )

        # Simulate traffic switch
        await asyncio.sleep(5)

        return ExecutionResult.SUCCESS

    async def _decommission_environment(
        self, phase: RolloutPhase, pipeline: RolloutPipeline
    ):
        """Decommission old environment"""

        self.logger.info(f"Decommissioning environment for phase {phase.phase_id}")

        # Simulate environment cleanup
        await asyncio.sleep(2)

    async def _validate_phase_completion(
        self, phase: RolloutPhase, pipeline: RolloutPipeline
    ) -> bool:
        """Validate that phase completed successfully"""

        # Check phase status and validation results
        if phase.stage != PipelineStage.COMPLETED:
            return False

        # Additional validation checks could go here

        return True

    def get_execution_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get current execution status for pipeline"""

        active_phases = [
            exec
            for exec in self.active_executions.values()
            if exec.pipeline_id == pipeline_id
        ]

        return {
            "pipeline_id": pipeline_id,
            "active_phases": len(active_phases),
            "phase_details": [
                {
                    "phase_id": exec.phase_id,
                    "status": exec.status.value,
                    "progress": exec.progress_percentage,
                    "current_step": exec.current_step,
                    "started_at": exec.started_at.isoformat(),
                }
                for exec in active_phases
            ],
        }

    async def _monitor_pipeline_for_rollback(self, pipeline: RolloutPipeline):
        """Monitor pipeline for rollback triggers"""

        try:
            while pipeline.status in [
                PipelineStage.DEPLOYING,
                PipelineStage.VALIDATING,
            ]:
                # Check for rollback triggers
                trigger = await self.rollback_manager.monitor_pipeline_health(pipeline)

                if trigger:
                    self.logger.warning(
                        f"Rollback trigger detected for pipeline {pipeline.pipeline_id}: {trigger.value}"
                    )

                    # Create and execute rollback plan
                    rollback_plan = await self.rollback_manager.create_rollback_plan(
                        pipeline=pipeline,
                        trigger=trigger,
                        trigger_details={"detected_at": datetime.now().isoformat()},
                        created_by="system",
                    )

                    # Execute rollback
                    rollback_success = await self.rollback_manager.execute_rollback(
                        rollback_plan
                    )

                    if rollback_success:
                        pipeline.status = PipelineStage.ROLLED_BACK
                        self.logger.info(
                            f"Pipeline {pipeline.pipeline_id} successfully rolled back"
                        )
                    else:
                        pipeline.status = PipelineStage.FAILED
                        self.logger.error(
                            f"Pipeline {pipeline.pipeline_id} rollback failed"
                        )

                    break

                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds

        except asyncio.CancelledError:
            self.logger.debug(
                f"Rollback monitoring cancelled for pipeline {pipeline.pipeline_id}"
            )
        except Exception as e:
            self.logger.error(
                f"Rollback monitoring error for pipeline {pipeline.pipeline_id}: {e}"
            )

    async def _handle_pipeline_failure(
        self, pipeline: RolloutPipeline, error_message: str
    ) -> bool:
        """Handle pipeline failure with automatic rollback"""

        try:
            self.logger.info(f"Handling pipeline failure for {pipeline.pipeline_id}")

            # Create rollback plan for deployment failure
            rollback_plan = await self.rollback_manager.create_rollback_plan(
                pipeline=pipeline,
                trigger=RollbackTrigger.DEPLOYMENT_FAILURE,
                trigger_details={
                    "error_message": error_message,
                    "failed_at": datetime.now().isoformat(),
                },
                created_by="system",
            )

            # Execute rollback
            rollback_success = await self.rollback_manager.execute_rollback(
                rollback_plan
            )

            if rollback_success:
                self.logger.info(
                    f"Pipeline {pipeline.pipeline_id} failure handled with successful rollback"
                )
                return True
            else:
                self.logger.error(f"Pipeline {pipeline.pipeline_id} rollback failed")
                return False

        except Exception as e:
            self.logger.error(f"Failed to handle pipeline failure: {e}")
            return False

    async def trigger_manual_rollback(
        self, pipeline_id: str, reason: str, requested_by: str
    ) -> bool:
        """Trigger manual rollback for pipeline"""

        try:
            rollback_plan = await self.rollback_manager.trigger_manual_rollback(
                pipeline_id=pipeline_id, reason=reason, requested_by=requested_by
            )

            if rollback_plan:
                rollback_success = await self.rollback_manager.execute_rollback(
                    rollback_plan
                )
                return rollback_success

            return False

        except Exception as e:
            self.logger.error(f"Manual rollback trigger failed: {e}")
            return False
