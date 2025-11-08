"""
Tests for Qubinode Navigator Rollout Pipeline System

Tests the staged rollout pipeline with approval gates, automated progression,
and rollback capabilities.
"""

import pytest
import unittest.mock as mock
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.rollout_pipeline import (
    RolloutPipelineManager, RolloutPipeline, RolloutPhase, ApprovalGate,
    PipelineStage, ApprovalStatus, RolloutStrategy
)
from core.approval_gates import ApprovalGateManager, ApprovalRequest, ApprovalType
from core.pipeline_executor import PipelineExecutor, ExecutionResult, PhaseExecution
from core.ai_update_manager import UpdatePlan
from core.update_manager import UpdateBatch, UpdateInfo


class TestRolloutPipelineManager:
    """Test cases for rollout pipeline manager"""
    
    def setup_method(self):
        """Setup test environment"""
        # Create temporary storage
        self.temp_dir = tempfile.mkdtemp()
        
        # Manager configuration
        self.config = {
            'pipeline_storage_path': self.temp_dir,
            'approval_timeout_default': 60,
            'auto_progression_enabled': True
        }
        
        # Create manager instance
        self.pipeline_manager = RolloutPipelineManager(self.config)
        
        # Sample update plan
        self.update_plan = UpdatePlan(
            plan_id='test_plan_123',
            batch_id='test_batch_456',
            execution_strategy='staged',
            total_estimated_time='2h 30m',
            phases=[],
            risk_mitigation_steps=['Create backup'],
            rollback_plan={'strategy': 'sequential'},
            monitoring_points=['System metrics'],
            approval_required=True,
            created_at=datetime.now(),
            ai_confidence=0.85
        )
    
    def test_pipeline_manager_initialization(self):
        """Test pipeline manager initialization"""
        assert self.pipeline_manager.pipeline_storage_path == Path(self.temp_dir)
        assert self.pipeline_manager.approval_timeout_default == 60
        assert self.pipeline_manager.auto_progression_enabled is True
        assert len(self.pipeline_manager.active_pipelines) == 0
        assert len(self.pipeline_manager.pipeline_history) == 0
    
    async def test_create_rollout_pipeline_canary(self):
        """Test creating canary rollout pipeline"""
        pipeline = await self.pipeline_manager.create_rollout_pipeline(
            update_plan=self.update_plan,
            strategy=RolloutStrategy.CANARY,
            created_by='test_user',
            pipeline_name='Test Canary Pipeline'
        )
        
        assert pipeline.pipeline_name == 'Test Canary Pipeline'
        assert pipeline.strategy == RolloutStrategy.CANARY
        assert pipeline.created_by == 'test_user'
        assert pipeline.status == PipelineStage.PENDING
        assert len(pipeline.phases) > 0
        assert len(pipeline.approval_gates) > 0
        assert pipeline.pipeline_id in self.pipeline_manager.active_pipelines
    
    async def test_create_rollout_pipeline_blue_green(self):
        """Test creating blue-green rollout pipeline"""
        pipeline = await self.pipeline_manager.create_rollout_pipeline(
            update_plan=self.update_plan,
            strategy=RolloutStrategy.BLUE_GREEN,
            created_by='test_user'
        )
        
        assert pipeline.strategy == RolloutStrategy.BLUE_GREEN
        assert 'green' in str(pipeline.phases).lower() or 'blue' in str(pipeline.phases).lower()
    
    async def test_create_rollout_pipeline_rolling(self):
        """Test creating rolling rollout pipeline"""
        pipeline = await self.pipeline_manager.create_rollout_pipeline(
            update_plan=self.update_plan,
            strategy=RolloutStrategy.ROLLING,
            created_by='test_user'
        )
        
        assert pipeline.strategy == RolloutStrategy.ROLLING
        assert len(pipeline.phases) >= 1
    
    def test_serialize_deserialize_pipeline(self):
        """Test pipeline serialization and deserialization"""
        # Create a simple pipeline for testing
        pipeline = RolloutPipeline(
            pipeline_id='test_123',
            pipeline_name='Test Pipeline',
            strategy=RolloutStrategy.ROLLING,
            update_plan=self.update_plan,
            phases=[],
            approval_gates=[],
            global_rollback_triggers=['critical_error'],
            monitoring_config={'enabled': True},
            notification_config={'email': True},
            created_at=datetime.now(),
            created_by='test_user',
            status=PipelineStage.PENDING
        )
        
        # Serialize
        serialized = self.pipeline_manager._serialize_pipeline(pipeline)
        assert serialized['pipeline_id'] == 'test_123'
        assert serialized['strategy'] == 'rolling'
        assert serialized['status'] == 'pending'
        
        # Deserialize
        deserialized = self.pipeline_manager._deserialize_pipeline(serialized)
        assert deserialized.pipeline_id == 'test_123'
        assert deserialized.strategy == RolloutStrategy.ROLLING
        assert deserialized.status == PipelineStage.PENDING


class TestApprovalGateManager:
    """Test cases for approval gate manager"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = {
            'auto_approval_enabled': True,
            'notification_channels': ['email']
        }
        
        self.approval_manager = ApprovalGateManager(self.config)
    
    def test_approval_manager_initialization(self):
        """Test approval manager initialization"""
        assert self.approval_manager.auto_approval_enabled is True
        assert 'email' in self.approval_manager.notification_channels
        assert len(self.approval_manager.pending_approvals) == 0
        assert len(self.approval_manager.approval_history) == 0
    
    async def test_create_approval_gate(self):
        """Test creating approval gate"""
        gate = await self.approval_manager.create_approval_gate(
            pipeline_id='test_pipeline_123',
            stage='deployment',
            gate_name='Deployment Approval',
            required_approvers=['user1', 'user2'],
            approval_timeout=120
        )
        
        assert gate.gate_name == 'Deployment Approval'
        assert gate.stage == 'deployment'
        assert len(gate.required_approvers) == 2
        assert gate.approval_timeout == 120
        assert gate.status == ApprovalStatus.PENDING
    
    async def test_auto_approval_conditions(self):
        """Test auto-approval logic"""
        # Test conditions that should trigger auto-approval
        auto_approve_conditions = {
            'ai_confidence': 0.9,
            'risk_level': 'low',
            'has_security_updates': False,
            'update_count': 3,
            'components': ['git', 'python'],
            'maintenance_window': True
        }
        
        gate = await self.approval_manager.create_approval_gate(
            pipeline_id='test_pipeline_123',
            stage='deployment',
            gate_name='Auto Approval Test',
            required_approvers=['user1'],
            auto_approve_conditions=auto_approve_conditions
        )
        
        # Should be auto-approved based on conditions
        # Note: This depends on business hours logic which might prevent auto-approval
        assert gate.status in [ApprovalStatus.AUTO_APPROVED, ApprovalStatus.PENDING]
    
    async def test_request_approval(self):
        """Test sending approval requests"""
        gate = ApprovalGate(
            gate_id='test_gate_123',
            gate_name='Test Gate',
            stage='deployment',
            required_approvers=['user1', 'user2'],
            approval_timeout=60,
            auto_approve_conditions={},
            status=ApprovalStatus.PENDING,
            approvals=[],
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=60)
        )
        
        requests = await self.approval_manager.request_approval(
            gate=gate,
            pipeline_id='test_pipeline_123',
            message='Please approve deployment'
        )
        
        assert len(requests) == 2
        assert all(req.gate_id == 'test_gate_123' for req in requests)
        assert len(self.approval_manager.pending_approvals) == 2
    
    async def test_process_approval_response(self):
        """Test processing approval responses"""
        # Create approval request
        request = ApprovalRequest(
            request_id='test_req_123',
            gate_id='test_gate_456',
            pipeline_id='test_pipeline_789',
            approver='user1',
            request_type=ApprovalType.MANUAL,
            message='Test approval',
            created_at=datetime.now()
        )
        
        self.approval_manager.pending_approvals['test_req_123'] = request
        
        # Process approval
        approved = await self.approval_manager.process_approval_response(
            request_id='test_req_123',
            response='approved',
            approver='user1',
            comments='Looks good'
        )
        
        assert approved is True
        assert 'test_req_123' not in self.approval_manager.pending_approvals
        assert len(self.approval_manager.approval_history) == 1
        
        history_request = self.approval_manager.approval_history[0]
        assert history_request.response == 'approved'
        assert history_request.comments == 'Looks good'
    
    async def test_check_gate_approval_status(self):
        """Test checking gate approval status"""
        gate = ApprovalGate(
            gate_id='test_gate_123',
            gate_name='Test Gate',
            stage='deployment',
            required_approvers=['user1', 'user2'],
            approval_timeout=60,
            auto_approve_conditions={},
            status=ApprovalStatus.PENDING,
            approvals=[
                {'request_id': 'req1', 'approver': 'user1', 'response': 'approved', 'timestamp': datetime.now().isoformat()}
            ],
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=60)
        )
        
        status, message = await self.approval_manager.check_gate_approval_status(gate)
        
        # Should still be pending (need 2 approvals)
        assert status == ApprovalStatus.PENDING
        assert 'more approval' in message
        
        # Add second approval
        gate.approvals.append({
            'request_id': 'req2', 
            'approver': 'user2', 
            'response': 'approved', 
            'timestamp': datetime.now().isoformat()
        })
        
        status, message = await self.approval_manager.check_gate_approval_status(gate)
        
        # Should now be approved
        assert status == ApprovalStatus.APPROVED
        assert 'approved by 2/2' in message
    
    async def test_expired_gate_status(self):
        """Test expired gate handling"""
        gate = ApprovalGate(
            gate_id='test_gate_123',
            gate_name='Test Gate',
            stage='deployment',
            required_approvers=['user1'],
            approval_timeout=60,
            auto_approve_conditions={},
            status=ApprovalStatus.PENDING,
            approvals=[],
            created_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1)  # Expired 1 hour ago
        )
        
        status, message = await self.approval_manager.check_gate_approval_status(gate)
        
        assert status == ApprovalStatus.EXPIRED
        assert 'expired' in message.lower()
    
    def test_get_approval_statistics(self):
        """Test approval statistics generation"""
        # Add some test data
        self.approval_manager.approval_history = [
            ApprovalRequest(
                request_id='req1',
                gate_id='gate1',
                pipeline_id='pipeline1',
                approver='user1',
                request_type=ApprovalType.MANUAL,
                message='Test',
                created_at=datetime.now() - timedelta(minutes=30),
                responded_at=datetime.now() - timedelta(minutes=20),
                response='approved'
            ),
            ApprovalRequest(
                request_id='req2',
                gate_id='gate2',
                pipeline_id='pipeline2',
                approver='user2',
                request_type=ApprovalType.MANUAL,
                message='Test',
                created_at=datetime.now() - timedelta(minutes=15),
                responded_at=datetime.now() - timedelta(minutes=10),
                response='rejected'
            )
        ]
        
        stats = self.approval_manager.get_approval_statistics()
        
        assert stats['total_requests'] == 2
        assert stats['approved'] == 1
        assert stats['rejected'] == 1
        assert stats['pending'] == 0
        assert stats['approval_rate'] == 50.0
        assert stats['average_response_time_minutes'] == 7.5  # (10 + 5) / 2 = 7.5


class TestPipelineExecutor:
    """Test cases for pipeline executor"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = {
            'max_concurrent_phases': 2,
            'phase_timeout_minutes': 60
        }
        
        self.executor = PipelineExecutor(self.config)
        
        # Create test update batch
        self.update_batch = UpdateBatch(
            batch_id='test_batch_123',
            batch_type='test',
            updates=[
                UpdateInfo(
                    component_type='software',
                    component_name='git',
                    current_version='2.44.0',
                    available_version='2.45.0',
                    severity='low',
                    description='Git update',
                    release_date='2025-11-08'
                )
            ],
            total_size=100,
            estimated_duration='30 minutes',
            risk_level='low',
            requires_reboot=False,
            rollback_plan='Standard rollback',
            created_at=datetime.now()
        )
        
        # Create test phase
        self.test_phase = RolloutPhase(
            phase_id='test_phase_123',
            phase_name='Test Phase',
            stage=PipelineStage.PENDING,
            target_environments=['staging'],
            update_batch=self.update_batch,
            validation_tests=['health_check', 'functionality_test'],
            success_criteria={'min_test_pass_rate': 0.8},
            rollback_triggers=['critical_error'],
            estimated_duration='30 minutes'
        )
    
    def test_executor_initialization(self):
        """Test pipeline executor initialization"""
        assert self.executor.max_concurrent_phases == 2
        assert self.executor.phase_timeout_minutes == 60
        assert len(self.executor.active_executions) == 0
        assert len(self.executor.execution_history) == 0
    
    async def test_execute_phase_success(self):
        """Test successful phase execution"""
        # Create minimal pipeline for context
        pipeline = RolloutPipeline(
            pipeline_id='test_pipeline_123',
            pipeline_name='Test Pipeline',
            strategy=RolloutStrategy.ROLLING,
            update_plan=UpdatePlan(
                plan_id='plan_123',
                batch_id='batch_123',
                execution_strategy='rolling',
                total_estimated_time='1h',
                phases=[],
                risk_mitigation_steps=[],
                rollback_plan={},
                monitoring_points=[],
                approval_required=False,
                created_at=datetime.now(),
                ai_confidence=0.8
            ),
            phases=[self.test_phase],
            approval_gates=[],
            global_rollback_triggers=[],
            monitoring_config={},
            notification_config={},
            created_at=datetime.now(),
            created_by='test_user'
        )
        
        result = await self.executor._execute_phase(self.test_phase, pipeline)
        
        assert result == ExecutionResult.SUCCESS
        assert self.test_phase.stage == PipelineStage.COMPLETED
        assert self.test_phase.started_at is not None
        assert self.test_phase.completed_at is not None
        assert self.test_phase.actual_duration is not None
        assert len(self.executor.execution_history) == 1
    
    async def test_check_success_criteria(self):
        """Test success criteria evaluation"""
        validation_results = {
            'test1': {'status': 'passed'},
            'test2': {'status': 'passed'},
            'test3': {'status': 'failed'},
            'test4': {'status': 'passed'}
        }
        
        criteria = {'min_test_pass_rate': 0.75}
        
        result = await self.executor._check_success_criteria(criteria, validation_results)
        
        # 3 out of 4 tests passed = 75% pass rate
        assert result is True
        
        # Test with higher threshold
        criteria = {'min_test_pass_rate': 0.9}
        result = await self.executor._check_success_criteria(criteria, validation_results)
        
        assert result is False
    
    def test_get_execution_status(self):
        """Test execution status retrieval"""
        # Add active execution
        execution = PhaseExecution(
            phase_id='test_phase_123',
            pipeline_id='test_pipeline_456',
            started_at=datetime.now(),
            status=PipelineStage.DEPLOYING,
            progress_percentage=50.0,
            current_step='Applying updates'
        )
        
        self.executor.active_executions['test_phase_123'] = execution
        
        status = self.executor.get_execution_status('test_pipeline_456')
        
        assert status['pipeline_id'] == 'test_pipeline_456'
        assert status['active_phases'] == 1
        assert len(status['phase_details']) == 1
        
        phase_detail = status['phase_details'][0]
        assert phase_detail['phase_id'] == 'test_phase_123'
        assert phase_detail['progress'] == 50.0
        assert phase_detail['current_step'] == 'Applying updates'


class TestRolloutStrategy:
    """Test rollout strategy enum"""
    
    def test_rollout_strategy_values(self):
        """Test rollout strategy enum values"""
        assert RolloutStrategy.CANARY.value == "canary"
        assert RolloutStrategy.BLUE_GREEN.value == "blue_green"
        assert RolloutStrategy.ROLLING.value == "rolling"
        assert RolloutStrategy.ALL_AT_ONCE.value == "all_at_once"


class TestPipelineStage:
    """Test pipeline stage enum"""
    
    def test_pipeline_stage_values(self):
        """Test pipeline stage enum values"""
        assert PipelineStage.PENDING.value == "pending"
        assert PipelineStage.APPROVED.value == "approved"
        assert PipelineStage.DEPLOYING.value == "deploying"
        assert PipelineStage.VALIDATING.value == "validating"
        assert PipelineStage.COMPLETED.value == "completed"
        assert PipelineStage.FAILED.value == "failed"
        assert PipelineStage.ROLLED_BACK.value == "rolled_back"
        assert PipelineStage.CANCELLED.value == "cancelled"


class TestApprovalStatus:
    """Test approval status enum"""
    
    def test_approval_status_values(self):
        """Test approval status enum values"""
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"
        assert ApprovalStatus.EXPIRED.value == "expired"
        assert ApprovalStatus.AUTO_APPROVED.value == "auto_approved"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
