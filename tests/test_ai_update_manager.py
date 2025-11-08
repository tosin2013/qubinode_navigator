"""
Tests for Qubinode Navigator AI-Powered Update Manager

Tests the AI integration with update management including analysis,
risk assessment, and automated planning capabilities.
"""

import pytest
import unittest.mock as mock
import json
import tempfile
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.ai_update_manager import (
    AIUpdateManager, RiskLevel, UpdateRecommendation, AIAnalysis, UpdatePlan
)
from core.update_manager import UpdateInfo, UpdateBatch


class TestAIUpdateManager:
    """Test cases for AI-powered update manager"""
    
    def setup_method(self):
        """Setup test environment"""
        # Manager configuration
        self.config = {
            'ai_assistant_url': 'http://test:8080',
            'ai_timeout': 10,
            'enable_ai_analysis': True,
            'auto_approval_threshold': 0.8
        }
        
        # Create manager instance
        self.ai_manager = AIUpdateManager(self.config)
        
        # Sample update info
        self.update_info = UpdateInfo(
            component_type='software',
            component_name='podman',
            current_version='4.9.0',
            available_version='5.0.0',
            severity='medium',
            description='Podman container runtime update',
            release_date='2025-11-08'
        )
    
    def test_ai_manager_initialization(self):
        """Test AI update manager initialization"""
        assert self.ai_manager.ai_assistant_url == 'http://test:8080'
        assert self.ai_manager.ai_timeout == 10
        assert self.ai_manager.enable_ai_analysis is True
        assert self.ai_manager.auto_approval_threshold == 0.8
        assert len(self.ai_manager.ai_analyses) == 0
        assert len(self.ai_manager.update_plans) == 0
    
    def test_create_analysis_prompt(self):
        """Test AI analysis prompt creation"""
        from core.compatibility_manager import CompatibilityLevel
        
        prompt = self.ai_manager._create_analysis_prompt(
            self.update_info, 
            CompatibilityLevel.COMPATIBLE, 
            "Listed in supported versions"
        )
        
        assert 'podman' in prompt
        assert '4.9.0' in prompt
        assert '5.0.0' in prompt
        assert 'compatible' in prompt
        assert 'JSON format' in prompt
        assert 'risk_level' in prompt
        assert 'recommendation' in prompt
    
    def test_parse_ai_analysis_json_response(self):
        """Test parsing AI response with JSON format"""
        ai_response = {
            'text': '''
            Based on the analysis, here is my assessment:
            
            {
                "risk_level": "low",
                "recommendation": "apply_with_testing",
                "confidence_score": 0.85,
                "reasoning": "Podman update is generally safe with proper testing",
                "security_impact": "No critical security issues identified",
                "compatibility_concerns": ["Minor API changes"],
                "testing_recommendations": ["Container functionality test", "Image operations test"],
                "rollback_strategy": "Use package manager rollback",
                "estimated_downtime": "5-10 minutes",
                "dependencies_impact": ["Docker compatibility"],
                "business_impact": "Minimal impact expected"
            }
            '''
        }
        
        analysis = self.ai_manager._parse_ai_analysis('test_123', self.update_info, ai_response)
        
        assert analysis.analysis_id == 'test_123'
        assert analysis.component_name == 'podman'
        assert analysis.risk_level == RiskLevel.LOW
        assert analysis.recommendation == UpdateRecommendation.APPLY_WITH_TESTING
        assert analysis.confidence_score == 0.85
        assert 'safe with proper testing' in analysis.reasoning
        assert len(analysis.compatibility_concerns) == 1
        assert len(analysis.testing_recommendations) == 2
    
    def test_parse_ai_analysis_text_response(self):
        """Test parsing AI response without JSON format"""
        ai_response = {
            'text': 'This is a critical security update that should be applied immediately. The risk is high due to security vulnerabilities.'
        }
        
        analysis = self.ai_manager._parse_ai_analysis('test_456', self.update_info, ai_response)
        
        assert analysis.analysis_id == 'test_456'
        assert analysis.component_name == 'podman'
        # Should extract high risk from text
        assert analysis.risk_level == RiskLevel.HIGH
        assert analysis.recommendation == UpdateRecommendation.APPLY_WITH_TESTING
        assert analysis.confidence_score == 0.6  # Default for text parsing
    
    def test_extract_analysis_from_text_critical(self):
        """Test extracting analysis from text with critical keywords"""
        text = "This is a critical update that needs immediate attention"
        
        analysis_data = self.ai_manager._extract_analysis_from_text(text)
        
        assert analysis_data['risk_level'] == 'high'
        assert analysis_data['recommendation'] == 'apply_with_testing'  # Default recommendation
    
    def test_extract_analysis_from_text_minor(self):
        """Test extracting analysis from text with minor keywords"""
        text = "This is a minor update with low risk and safe to apply"
        
        analysis_data = self.ai_manager._extract_analysis_from_text(text)
        
        assert analysis_data['risk_level'] == 'low'
    
    def test_create_fallback_analysis_security_update(self):
        """Test creating fallback analysis for security update"""
        security_update = UpdateInfo(
            component_type='software',
            component_name='ansible',
            current_version='2.15.0',
            available_version='2.16.0',
            severity='security',
            description='Security patch for Ansible',
            release_date='2025-11-08',
            security_advisories=['CVE-2025-1234']
        )
        
        analysis = self.ai_manager._create_fallback_analysis('fallback_123', security_update)
        
        assert analysis.analysis_id == 'fallback_123'
        assert analysis.component_name == 'ansible'
        assert analysis.risk_level == RiskLevel.MEDIUM
        assert analysis.recommendation == UpdateRecommendation.APPLY_WITH_TESTING
        assert analysis.confidence_score == 0.6
        assert 'advisories' in analysis.security_impact.lower()
    
    def test_create_fallback_analysis_low_severity(self):
        """Test creating fallback analysis for low severity update"""
        low_update = UpdateInfo(
            component_type='software',
            component_name='git',
            current_version='2.44.0',
            available_version='2.45.0',
            severity='low',
            description='Minor Git update',
            release_date='2025-11-08'
        )
        
        analysis = self.ai_manager._create_fallback_analysis('fallback_456', low_update)
        
        assert analysis.risk_level == RiskLevel.VERY_LOW
        assert analysis.recommendation == UpdateRecommendation.SCHEDULE_MAINTENANCE
    
    @mock.patch('requests.post')
    async def test_call_ai_assistant_success(self, mock_post):
        """Test successful AI Assistant call"""
        # Mock successful response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'text': 'AI analysis response',
            'metadata': {'model': 'granite-4.0-micro'}
        }
        mock_post.return_value = mock_response
        
        result = await self.ai_manager._call_ai_assistant('test prompt')
        
        assert result['text'] == 'AI analysis response'
        mock_post.assert_called_once()
        
        # Check request payload
        call_args = mock_post.call_args
        assert call_args[1]['json']['message'] == 'test prompt'
        assert call_args[1]['timeout'] == 10
    
    @mock.patch('requests.post')
    async def test_call_ai_assistant_timeout(self, mock_post):
        """Test AI Assistant call timeout"""
        # Mock timeout exception
        mock_post.side_effect = requests.exceptions.Timeout()
        
        with pytest.raises(Exception) as exc_info:
            await self.ai_manager._call_ai_assistant('test prompt')
        
        assert 'timed out' in str(exc_info.value)
    
    @mock.patch('requests.post')
    async def test_call_ai_assistant_connection_error(self, mock_post):
        """Test AI Assistant connection error"""
        # Mock connection error
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        with pytest.raises(Exception) as exc_info:
            await self.ai_manager._call_ai_assistant('test prompt')
        
        assert 'Could not connect' in str(exc_info.value)
    
    @mock.patch.object(AIUpdateManager, '_call_ai_assistant')
    @mock.patch.object(AIUpdateManager, 'compatibility_manager')
    async def test_analyze_update_with_ai_success(self, mock_compat_manager, mock_ai_call):
        """Test successful AI update analysis"""
        # Mock compatibility manager
        mock_compat_manager.validate_compatibility.return_value = (
            mock.MagicMock(value='compatible'), 
            'Listed in supported versions'
        )
        
        # Mock AI response
        mock_ai_call.return_value = {
            'text': '''
            {
                "risk_level": "medium",
                "recommendation": "apply_with_testing",
                "confidence_score": 0.9,
                "reasoning": "Standard update with good compatibility",
                "security_impact": "No security issues",
                "compatibility_concerns": [],
                "testing_recommendations": ["Basic functionality test"],
                "rollback_strategy": "Package manager rollback",
                "estimated_downtime": "10 minutes",
                "dependencies_impact": [],
                "business_impact": "Minimal impact"
            }
            '''
        }
        
        analysis = await self.ai_manager.analyze_update_with_ai(self.update_info)
        
        assert analysis.component_name == 'podman'
        assert analysis.risk_level == RiskLevel.MEDIUM
        assert analysis.recommendation == UpdateRecommendation.APPLY_WITH_TESTING
        assert analysis.confidence_score == 0.9
        assert 'Standard update' in analysis.reasoning
        
        # Check that analysis is cached
        cache_key = f"{self.update_info.component_name}_{self.update_info.available_version}"
        assert cache_key in self.ai_manager.analysis_cache
    
    async def test_analyze_update_with_ai_disabled(self):
        """Test AI analysis when AI is disabled"""
        self.ai_manager.enable_ai_analysis = False
        
        analysis = await self.ai_manager.analyze_update_with_ai(self.update_info)
        
        assert analysis.component_name == 'podman'
        assert analysis.confidence_score == 0.6  # Fallback confidence
        assert 'Fallback analysis' in analysis.reasoning
    
    def test_create_execution_phases_immediate(self):
        """Test creating execution phases for immediate strategy"""
        batch = UpdateBatch(
            batch_id='test_batch',
            batch_type='test',
            updates=[self.update_info],
            total_size=100,
            estimated_duration='30 minutes',
            risk_level='medium',
            requires_reboot=False,
            rollback_plan='Standard rollback',
            created_at=datetime.now()
        )
        
        analyses = {
            'podman': AIAnalysis(
                analysis_id='test_analysis',
                component_name='podman',
                component_version='5.0.0',
                risk_level=RiskLevel.LOW,
                recommendation=UpdateRecommendation.APPLY_IMMEDIATELY,
                confidence_score=0.9,
                reasoning='Low risk update',
                security_impact='No security impact',
                compatibility_concerns=[],
                testing_recommendations=[],
                rollback_strategy='Standard rollback'
            )
        }
        
        phases = self.ai_manager._create_execution_phases(batch, analyses, 'immediate')
        
        assert len(phases) == 1
        assert phases[0]['phase_id'] == 'immediate_execution'
        assert phases[0]['parallel_execution'] is True
        assert 'podman' in phases[0]['updates']
    
    def test_create_execution_phases_staged(self):
        """Test creating execution phases for staged strategy"""
        # Create multiple updates with different risk levels
        low_risk_update = UpdateInfo(
            component_type='software',
            component_name='git',
            current_version='2.44.0',
            available_version='2.45.0',
            severity='low',
            description='Git update',
            release_date='2025-11-08'
        )
        
        batch = UpdateBatch(
            batch_id='test_batch',
            batch_type='test',
            updates=[self.update_info, low_risk_update],
            total_size=200,
            estimated_duration='45 minutes',
            risk_level='medium',
            requires_reboot=False,
            rollback_plan='Standard rollback',
            created_at=datetime.now()
        )
        
        analyses = {
            'podman': AIAnalysis(
                analysis_id='test_analysis_1',
                component_name='podman',
                component_version='5.0.0',
                risk_level=RiskLevel.MEDIUM,
                recommendation=UpdateRecommendation.APPLY_WITH_TESTING,
                confidence_score=0.8,
                reasoning='Medium risk update',
                security_impact='No security impact',
                compatibility_concerns=[],
                testing_recommendations=[],
                rollback_strategy='Standard rollback'
            ),
            'git': AIAnalysis(
                analysis_id='test_analysis_2',
                component_name='git',
                component_version='2.45.0',
                risk_level=RiskLevel.LOW,
                recommendation=UpdateRecommendation.APPLY_IMMEDIATELY,
                confidence_score=0.9,
                reasoning='Low risk update',
                security_impact='No security impact',
                compatibility_concerns=[],
                testing_recommendations=[],
                rollback_strategy='Standard rollback'
            )
        }
        
        phases = self.ai_manager._create_execution_phases(batch, analyses, 'staged')
        
        assert len(phases) == 2
        
        # Check low risk phase
        low_risk_phase = phases[0]
        assert low_risk_phase['phase_id'] == 'stage_1_low_risk'
        assert 'git' in low_risk_phase['updates']
        assert low_risk_phase['parallel_execution'] is True
        
        # Check higher risk phase
        higher_risk_phase = phases[1]
        assert higher_risk_phase['phase_id'] == 'stage_2_higher_risk'
        assert 'podman' in higher_risk_phase['updates']
        assert higher_risk_phase['parallel_execution'] is False
    
    def test_create_execution_phases_maintenance_window(self):
        """Test creating execution phases for maintenance window strategy"""
        batch = UpdateBatch(
            batch_id='test_batch',
            batch_type='test',
            updates=[self.update_info],
            total_size=150,
            estimated_duration='60 minutes',
            risk_level='high',
            requires_reboot=True,
            rollback_plan='Full system rollback',
            created_at=datetime.now()
        )
        
        analyses = {
            'podman': AIAnalysis(
                analysis_id='test_analysis',
                component_name='podman',
                component_version='5.0.0',
                risk_level=RiskLevel.HIGH,
                recommendation=UpdateRecommendation.SCHEDULE_MAINTENANCE,
                confidence_score=0.8,
                reasoning='High risk update',
                security_impact='Potential security impact',
                compatibility_concerns=['API changes'],
                testing_recommendations=[],
                rollback_strategy='Standard rollback'
            )
        }
        
        phases = self.ai_manager._create_execution_phases(batch, analyses, 'maintenance_window')
        
        assert len(phases) == 3
        assert phases[0]['phase_id'] == 'maintenance_preparation'
        assert phases[1]['phase_id'] == 'maintenance_execution'
        assert phases[2]['phase_id'] == 'maintenance_verification'
        
        # Check that execution phase contains the update
        execution_phase = phases[1]
        assert 'podman' in execution_phase['updates']
        assert execution_phase['approval_required'] is True
    
    def test_generate_risk_mitigation_steps(self):
        """Test generating risk mitigation steps"""
        analyses = {
            'podman': AIAnalysis(
                analysis_id='test_analysis_1',
                component_name='podman',
                component_version='5.0.0',
                risk_level=RiskLevel.HIGH,
                recommendation=UpdateRecommendation.APPLY_WITH_TESTING,
                confidence_score=0.8,
                reasoning='High risk update',
                security_impact='Potential security impact',
                compatibility_concerns=['API compatibility'],
                testing_recommendations=[],
                rollback_strategy='Standard rollback',
                dependencies_impact=['Docker integration']
            ),
            'git': AIAnalysis(
                analysis_id='test_analysis_2',
                component_name='git',
                component_version='2.45.0',
                risk_level=RiskLevel.LOW,
                recommendation=UpdateRecommendation.APPLY_IMMEDIATELY,
                confidence_score=0.9,
                reasoning='Low risk update',
                security_impact='No security impact',
                compatibility_concerns=[],
                testing_recommendations=[],
                rollback_strategy='Standard rollback'
            )
        }
        
        mitigation_steps = self.ai_manager._generate_risk_mitigation_steps(analyses)
        
        # Check standard mitigation steps
        assert any('backup' in step.lower() for step in mitigation_steps)
        assert any('services' in step.lower() for step in mitigation_steps)
        assert any('rollback' in step.lower() for step in mitigation_steps)
        
        # Check component-specific mitigations
        assert any('podman' in step and 'high risk' in step for step in mitigation_steps)
        assert any('compatibility' in step.lower() for step in mitigation_steps)
        assert any('dependencies' in step.lower() for step in mitigation_steps)
    
    def test_calculate_overall_risk(self):
        """Test calculating overall risk level"""
        # Test critical risk
        critical_analyses = {
            'comp1': mock.MagicMock(risk_level=RiskLevel.CRITICAL),
            'comp2': mock.MagicMock(risk_level=RiskLevel.LOW)
        }
        assert self.ai_manager._calculate_overall_risk(critical_analyses) == 'critical'
        
        # Test high risk
        high_analyses = {
            'comp1': mock.MagicMock(risk_level=RiskLevel.HIGH),
            'comp2': mock.MagicMock(risk_level=RiskLevel.MEDIUM)
        }
        assert self.ai_manager._calculate_overall_risk(high_analyses) == 'high'
        
        # Test medium risk
        medium_analyses = {
            'comp1': mock.MagicMock(risk_level=RiskLevel.MEDIUM),
            'comp2': mock.MagicMock(risk_level=RiskLevel.LOW)
        }
        assert self.ai_manager._calculate_overall_risk(medium_analyses) == 'medium'
        
        # Test low risk
        low_analyses = {
            'comp1': mock.MagicMock(risk_level=RiskLevel.LOW),
            'comp2': mock.MagicMock(risk_level=RiskLevel.VERY_LOW)
        }
        assert self.ai_manager._calculate_overall_risk(low_analyses) == 'low'
        
        # Test empty analyses
        assert self.ai_manager._calculate_overall_risk({}) == 'unknown'


class TestAIAnalysis:
    """Test AIAnalysis dataclass"""
    
    def test_ai_analysis_creation(self):
        """Test AIAnalysis creation and initialization"""
        analysis = AIAnalysis(
            analysis_id='test_123',
            component_name='podman',
            component_version='5.0.0',
            risk_level=RiskLevel.MEDIUM,
            recommendation=UpdateRecommendation.APPLY_WITH_TESTING,
            confidence_score=0.85,
            reasoning='Test analysis',
            security_impact='No security impact',
            compatibility_concerns=['Minor concerns'],
            testing_recommendations=['Test container functionality'],
            rollback_strategy='Use package manager'
        )
        
        assert analysis.analysis_id == 'test_123'
        assert analysis.component_name == 'podman'
        assert analysis.risk_level == RiskLevel.MEDIUM
        assert analysis.recommendation == UpdateRecommendation.APPLY_WITH_TESTING
        assert analysis.confidence_score == 0.85
        assert analysis.timestamp is not None  # Auto-initialized
        assert analysis.dependencies_impact == []  # Default empty list


class TestUpdatePlan:
    """Test UpdatePlan dataclass"""
    
    def test_update_plan_creation(self):
        """Test UpdatePlan creation and initialization"""
        created_time = datetime.now()
        plan = UpdatePlan(
            plan_id='plan_123',
            batch_id='batch_456',
            execution_strategy='staged',
            total_estimated_time='2h 30m',
            phases=[{'phase_id': 'test_phase'}],
            risk_mitigation_steps=['Create backup'],
            rollback_plan={'strategy': 'sequential'},
            monitoring_points=['System metrics'],
            approval_required=True,
            created_at=created_time,
            ai_confidence=0.9
        )
        
        assert plan.plan_id == 'plan_123'
        assert plan.batch_id == 'batch_456'
        assert plan.execution_strategy == 'staged'
        assert plan.approval_required is True
        assert plan.ai_confidence == 0.9
        assert plan.created_at == created_time


class TestRiskLevel:
    """Test RiskLevel enum"""
    
    def test_risk_level_values(self):
        """Test RiskLevel enum values"""
        assert RiskLevel.VERY_LOW.value == "very_low"
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"


class TestUpdateRecommendation:
    """Test UpdateRecommendation enum"""
    
    def test_update_recommendation_values(self):
        """Test UpdateRecommendation enum values"""
        assert UpdateRecommendation.APPLY_IMMEDIATELY.value == "apply_immediately"
        assert UpdateRecommendation.APPLY_WITH_TESTING.value == "apply_with_testing"
        assert UpdateRecommendation.SCHEDULE_MAINTENANCE.value == "schedule_maintenance"
        assert UpdateRecommendation.DEFER_UPDATE.value == "defer_update"
        assert UpdateRecommendation.BLOCK_UPDATE.value == "block_update"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
