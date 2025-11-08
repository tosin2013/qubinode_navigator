"""
Qubinode Navigator Staged Rollout Pipeline

Core pipeline management for controlled update deployment with approval gates,
automated progression, and rollback capabilities.

Based on ADR-0030: Software and OS Update Strategy
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

from core.update_manager import UpdateInfo, UpdateBatch
from core.ai_update_manager import AIUpdateManager, UpdatePlan, AIAnalysis


class PipelineStage(Enum):
    """Pipeline deployment stages"""
    PENDING = "pending"
    APPROVED = "approved"
    DEPLOYING = "deploying"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class ApprovalStatus(Enum):
    """Approval gate status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"


class RolloutStrategy(Enum):
    """Rollout deployment strategies"""
    CANARY = "canary"          # Small subset first
    BLUE_GREEN = "blue_green"  # Parallel environment
    ROLLING = "rolling"        # Sequential batches
    ALL_AT_ONCE = "all_at_once"  # Single deployment


@dataclass
class ApprovalGate:
    """Approval gate configuration and status"""
    gate_id: str
    gate_name: str
    stage: str
    required_approvers: List[str]
    approval_timeout: int  # minutes
    auto_approve_conditions: Dict[str, Any]
    status: ApprovalStatus
    approvals: List[Dict[str, Any]]
    created_at: datetime
    expires_at: datetime
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(minutes=self.approval_timeout)


@dataclass
class RolloutPhase:
    """Individual phase in rollout pipeline"""
    phase_id: str
    phase_name: str
    stage: PipelineStage
    target_environments: List[str]
    update_batch: UpdateBatch
    validation_tests: List[str]
    success_criteria: Dict[str, Any]
    rollback_triggers: List[str]
    estimated_duration: str
    actual_duration: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    validation_results: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.validation_results is None:
            self.validation_results = {}


@dataclass
class RolloutPipeline:
    """Complete rollout pipeline configuration"""
    pipeline_id: str
    pipeline_name: str
    strategy: RolloutStrategy
    update_plan: UpdatePlan
    phases: List[RolloutPhase]
    approval_gates: List[ApprovalGate]
    global_rollback_triggers: List[str]
    monitoring_config: Dict[str, Any]
    notification_config: Dict[str, Any]
    created_at: datetime
    created_by: str
    status: PipelineStage = PipelineStage.PENDING
    current_phase: Optional[str] = None
    completed_at: Optional[datetime] = None
    total_duration: Optional[str] = None


class RolloutPipelineManager:
    """
    Staged Rollout Pipeline Manager
    
    Manages controlled deployment pipelines with approval gates,
    automated progression, and rollback capabilities.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.pipeline_storage_path = Path(self.config.get('pipeline_storage_path', 'data/pipelines'))
        self.approval_timeout_default = self.config.get('approval_timeout_default', 240)  # 4 hours
        self.auto_progression_enabled = self.config.get('auto_progression_enabled', True)
        self.notification_enabled = self.config.get('notification_enabled', True)
        
        # State
        self.active_pipelines: Dict[str, RolloutPipeline] = {}
        self.pipeline_history: List[RolloutPipeline] = []
        
        # Initialize storage
        self.pipeline_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing pipelines
        self._load_pipelines()
    
    def _load_pipelines(self):
        """Load existing pipelines from storage"""
        try:
            for pipeline_file in self.pipeline_storage_path.glob("pipeline_*.json"):
                with open(pipeline_file, 'r') as f:
                    pipeline_data = json.load(f)
                    pipeline = self._deserialize_pipeline(pipeline_data)
                    
                    if pipeline.status in [PipelineStage.PENDING, PipelineStage.APPROVED, PipelineStage.DEPLOYING, PipelineStage.VALIDATING]:
                        self.active_pipelines[pipeline.pipeline_id] = pipeline
                    else:
                        self.pipeline_history.append(pipeline)
            
            self.logger.info(f"Loaded {len(self.active_pipelines)} active pipelines and {len(self.pipeline_history)} completed pipelines")
            
        except Exception as e:
            self.logger.error(f"Failed to load pipelines: {e}")
    
    def _save_pipeline(self, pipeline: RolloutPipeline):
        """Save pipeline to storage"""
        try:
            pipeline_file = self.pipeline_storage_path / f"pipeline_{pipeline.pipeline_id}.json"
            pipeline_data = self._serialize_pipeline(pipeline)
            
            def json_serializer(obj):
                if hasattr(obj, 'value'):  # Enum objects
                    return obj.value
                return str(obj)
            
            with open(pipeline_file, 'w') as f:
                json.dump(pipeline_data, f, indent=2, default=json_serializer)
            
            self.logger.debug(f"Saved pipeline {pipeline.pipeline_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to save pipeline {pipeline.pipeline_id}: {e}")
    
    def _serialize_pipeline(self, pipeline: RolloutPipeline) -> Dict[str, Any]:
        """Serialize pipeline to JSON-compatible format"""
        return {
            'pipeline_id': pipeline.pipeline_id,
            'pipeline_name': pipeline.pipeline_name,
            'strategy': pipeline.strategy.value,
            'update_plan': asdict(pipeline.update_plan),
            'phases': [asdict(phase) for phase in pipeline.phases],
            'approval_gates': [asdict(gate) for gate in pipeline.approval_gates],
            'global_rollback_triggers': pipeline.global_rollback_triggers,
            'monitoring_config': pipeline.monitoring_config,
            'notification_config': pipeline.notification_config,
            'created_at': pipeline.created_at.isoformat(),
            'created_by': pipeline.created_by,
            'status': pipeline.status.value,
            'current_phase': pipeline.current_phase,
            'completed_at': pipeline.completed_at.isoformat() if pipeline.completed_at else None,
            'total_duration': pipeline.total_duration
        }
    
    def _deserialize_pipeline(self, data: Dict[str, Any]) -> RolloutPipeline:
        """Deserialize pipeline from JSON format"""
        # Convert string enums back to enum objects
        strategy = RolloutStrategy(data['strategy'])
        status = PipelineStage(data['status'])
        
        # Deserialize phases
        phases = []
        for phase_data in data['phases']:
            # Create a copy to avoid modifying original data
            phase_copy = phase_data.copy()
            phase_copy['stage'] = PipelineStage(phase_copy['stage'])
            if phase_copy.get('started_at'):
                phase_copy['started_at'] = datetime.fromisoformat(phase_copy['started_at'])
            if phase_copy.get('completed_at'):
                phase_copy['completed_at'] = datetime.fromisoformat(phase_copy['completed_at'])
            phases.append(RolloutPhase(**phase_copy))
        
        # Deserialize approval gates
        approval_gates = []
        for gate_data in data['approval_gates']:
            # Create a copy to avoid modifying original data
            gate_copy = gate_data.copy()
            gate_copy['status'] = ApprovalStatus(gate_copy['status'])
            gate_copy['created_at'] = datetime.fromisoformat(gate_copy['created_at'])
            gate_copy['expires_at'] = datetime.fromisoformat(gate_copy['expires_at'])
            if gate_copy.get('approved_at'):
                gate_copy['approved_at'] = datetime.fromisoformat(gate_copy['approved_at'])
            approval_gates.append(ApprovalGate(**gate_copy))
        
        # Deserialize update plan (simplified)
        update_plan_data = data['update_plan'].copy()
        if isinstance(update_plan_data['created_at'], str):
            update_plan_data['created_at'] = datetime.fromisoformat(update_plan_data['created_at'])
        update_plan = UpdatePlan(**update_plan_data)
        
        return RolloutPipeline(
            pipeline_id=data['pipeline_id'],
            pipeline_name=data['pipeline_name'],
            strategy=strategy,
            update_plan=update_plan,
            phases=phases,
            approval_gates=approval_gates,
            global_rollback_triggers=data['global_rollback_triggers'],
            monitoring_config=data['monitoring_config'],
            notification_config=data['notification_config'],
            created_at=datetime.fromisoformat(data['created_at']),
            created_by=data['created_by'],
            status=status,
            current_phase=data.get('current_phase'),
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            total_duration=data.get('total_duration')
        )
    
    async def create_rollout_pipeline(
        self, 
        update_plan: UpdatePlan, 
        strategy: RolloutStrategy,
        created_by: str,
        pipeline_name: Optional[str] = None
    ) -> RolloutPipeline:
        """Create new rollout pipeline from update plan"""
        
        pipeline_id = f"rollout_{int(time.time())}"
        if not pipeline_name:
            pipeline_name = f"Rollout for {update_plan.batch_id}"
        
        self.logger.info(f"Creating rollout pipeline {pipeline_id} with strategy {strategy.value}")
        
        # Generate phases based on strategy and update plan
        phases = await self._generate_rollout_phases(update_plan, strategy)
        
        # Generate approval gates
        approval_gates = self._generate_approval_gates(phases, update_plan)
        
        # Configure monitoring and notifications
        monitoring_config = self._generate_monitoring_config(update_plan)
        notification_config = self._generate_notification_config()
        
        # Create pipeline
        pipeline = RolloutPipeline(
            pipeline_id=pipeline_id,
            pipeline_name=pipeline_name,
            strategy=strategy,
            update_plan=update_plan,
            phases=phases,
            approval_gates=approval_gates,
            global_rollback_triggers=self._get_global_rollback_triggers(),
            monitoring_config=monitoring_config,
            notification_config=notification_config,
            created_at=datetime.now(),
            created_by=created_by,
            status=PipelineStage.PENDING
        )
        
        # Save and register pipeline
        self.active_pipelines[pipeline_id] = pipeline
        self._save_pipeline(pipeline)
        
        self.logger.info(f"Created rollout pipeline {pipeline_id} with {len(phases)} phases and {len(approval_gates)} approval gates")
        
        return pipeline
    
    async def _generate_rollout_phases(self, update_plan: UpdatePlan, strategy: RolloutStrategy) -> List[RolloutPhase]:
        """Generate rollout phases based on strategy"""
        phases = []
        
        if strategy == RolloutStrategy.CANARY:
            # Canary phase
            phases.append(RolloutPhase(
                phase_id=f"canary_{int(time.time())}",
                phase_name="Canary Deployment",
                stage=PipelineStage.PENDING,
                target_environments=["canary"],
                update_batch=self._create_sample_batch(),
                validation_tests=["health_check", "smoke_test"],
                success_criteria={"min_test_pass_rate": 0.9},
                rollback_triggers=["error_rate_high"],
                estimated_duration="30 minutes"
            ))
            
            # Production phase
            phases.append(RolloutPhase(
                phase_id=f"production_{int(time.time())}",
                phase_name="Production Deployment",
                stage=PipelineStage.PENDING,
                target_environments=["production"],
                update_batch=self._create_sample_batch(),
                validation_tests=["health_check", "integration_test"],
                success_criteria={"min_test_pass_rate": 0.95},
                rollback_triggers=["error_rate_high", "performance_degradation"],
                estimated_duration="60 minutes"
            ))
        
        elif strategy == RolloutStrategy.BLUE_GREEN:
            # Green deployment
            phases.append(RolloutPhase(
                phase_id=f"green_{int(time.time())}",
                phase_name="Green Environment Deployment",
                stage=PipelineStage.PENDING,
                target_environments=["green"],
                update_batch=self._create_sample_batch(),
                validation_tests=["health_check", "functionality_test"],
                success_criteria={"min_test_pass_rate": 0.95},
                rollback_triggers=["deployment_failure"],
                estimated_duration="45 minutes"
            ))
            
            # Traffic switch
            phases.append(RolloutPhase(
                phase_id=f"switch_{int(time.time())}",
                phase_name="Traffic Switch",
                stage=PipelineStage.PENDING,
                target_environments=["production"],
                update_batch=self._create_sample_batch(),
                validation_tests=["traffic_validation"],
                success_criteria={"min_test_pass_rate": 1.0},
                rollback_triggers=["traffic_errors"],
                estimated_duration="15 minutes"
            ))
        
        elif strategy == RolloutStrategy.ROLLING:
            # Multiple rolling phases
            environments = ["staging", "production-1", "production-2", "production-3"]
            for i, env in enumerate(environments):
                phases.append(RolloutPhase(
                    phase_id=f"rolling_{i}_{int(time.time())}",
                    phase_name=f"Rolling Phase {i+1} ({env})",
                    stage=PipelineStage.PENDING,
                    target_environments=[env],
                    update_batch=self._create_sample_batch(),
                    validation_tests=["health_check", "functionality_test"],
                    success_criteria={"min_test_pass_rate": 0.9},
                    rollback_triggers=["error_rate_high"],
                    estimated_duration="30 minutes"
                ))
        
        else:  # ALL_AT_ONCE
            phases.append(RolloutPhase(
                phase_id=f"all_at_once_{int(time.time())}",
                phase_name="All-at-Once Deployment",
                stage=PipelineStage.PENDING,
                target_environments=["staging", "production"],
                update_batch=self._create_sample_batch(),
                validation_tests=["health_check", "integration_test", "performance_test"],
                success_criteria={"min_test_pass_rate": 0.95},
                rollback_triggers=["critical_error", "performance_degradation"],
                estimated_duration="90 minutes"
            ))
        
        return phases
    
    def _create_sample_batch(self) -> UpdateBatch:
        """Create sample update batch for phases"""
        from core.update_manager import UpdateInfo
        
        sample_update = UpdateInfo(
            component_type='software',
            component_name='sample',
            current_version='1.0.0',
            available_version='1.1.0',
            severity='medium',
            description='Sample update for rollout',
            release_date='2025-11-08'
        )
        
        return UpdateBatch(
            batch_id=f"sample_batch_{int(time.time())}",
            batch_type='rollout',
            updates=[sample_update],
            total_size=100,
            estimated_duration='30 minutes',
            risk_level='medium',
            requires_reboot=False,
            rollback_plan='Standard rollback',
            created_at=datetime.now()
        )
    
    def _generate_approval_gates(self, phases: List[RolloutPhase], update_plan: UpdatePlan) -> List[ApprovalGate]:
        """Generate approval gates for phases"""
        gates = []
        
        # Pre-deployment gate
        gates.append(ApprovalGate(
            gate_id=f"pre_deploy_{int(time.time())}",
            gate_name="Pre-Deployment Approval",
            stage="pre_deployment",
            required_approvers=["ops_lead", "security_lead"],
            approval_timeout=self.approval_timeout_default,
            auto_approve_conditions={
                'ai_confidence': update_plan.ai_confidence,
                'risk_level': 'low' if update_plan.ai_confidence > 0.8 else 'medium'
            },
            status=ApprovalStatus.PENDING,
            approvals=[],
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=self.approval_timeout_default)
        ))
        
        # Production deployment gate (if applicable)
        production_phases = [p for p in phases if 'production' in p.phase_name.lower()]
        if production_phases:
            gates.append(ApprovalGate(
                gate_id=f"prod_deploy_{int(time.time())}",
                gate_name="Production Deployment Approval",
                stage="production_deployment",
                required_approvers=["ops_manager", "release_manager"],
                approval_timeout=self.approval_timeout_default,
                auto_approve_conditions={},  # Never auto-approve production
                status=ApprovalStatus.PENDING,
                approvals=[],
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=self.approval_timeout_default)
            ))
        
        return gates
    
    def _generate_monitoring_config(self, update_plan: UpdatePlan) -> Dict[str, Any]:
        """Generate monitoring configuration"""
        return {
            'enabled': True,
            'metrics': [
                'response_time',
                'error_rate',
                'cpu_usage',
                'memory_usage',
                'disk_usage'
            ],
            'thresholds': {
                'error_rate_max': 0.05,
                'response_time_max': 2000,
                'cpu_usage_max': 80,
                'memory_usage_max': 85
            },
            'check_interval': 30,
            'alert_channels': ['email', 'slack']
        }
    
    def _generate_notification_config(self) -> Dict[str, Any]:
        """Generate notification configuration"""
        return {
            'enabled': self.notification_enabled,
            'channels': {
                'email': {
                    'enabled': True,
                    'recipients': ['ops-team@company.com', 'release-team@company.com']
                },
                'slack': {
                    'enabled': True,
                    'channel': '#deployments',
                    'webhook_url': 'https://hooks.slack.com/services/...'
                }
            },
            'events': [
                'pipeline_started',
                'phase_completed',
                'approval_required',
                'deployment_failed',
                'rollback_triggered'
            ]
        }
    
    def _get_global_rollback_triggers(self) -> List[str]:
        """Get global rollback triggers"""
        return [
            'critical_system_failure',
            'security_breach_detected',
            'data_corruption',
            'service_unavailable',
            'performance_degradation_severe',
            'manual_rollback_requested'
        ]
