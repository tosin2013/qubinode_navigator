"""
Tests for Qubinode Navigator Compatibility Manager

Tests the compatibility matrix management system including validation,
testing, and dynamic updates based on test results.
"""

import pytest
import unittest.mock as mock
import json
import tempfile
import os
import yaml
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.compatibility_manager import (
    CompatibilityManager, CompatibilityLevel, TestStatus, TestResult, CompatibilityRule
)


class TestCompatibilityManager:
    """Test cases for compatibility manager functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        # Create temporary directories
        self.temp_test_dir = tempfile.mkdtemp()
        
        # Create temporary matrix file
        self.temp_matrix_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
        matrix_data = {
            'podman': {
                'supported_versions': {
                    '10': ['4.9.0', '5.0.0'],
                    '9': ['4.6.0', '4.9.0']
                },
                'known_issues': [
                    {
                        'version': '4.8.0',
                        'issue': 'SELinux compatibility issue',
                        'severity': 'medium'
                    }
                ],
                'test_results': {
                    '4.9.0': 'passed',
                    '5.0.0': 'needs_testing',
                    '4.8.0': 'failed'
                },
                'last_updated': '2025-11-08T00:00:00'
            },
            'ansible': {
                'supported_versions': {
                    '10': ['2.16.0', '2.17.0'],
                    '9': ['2.15.0', '2.16.0']
                },
                'known_issues': [],
                'test_results': {
                    '2.16.0': 'passed',
                    '2.17.0': 'needs_testing'
                },
                'last_updated': '2025-11-08T00:00:00'
            }
        }
        
        yaml.dump(matrix_data, self.temp_matrix_file)
        self.temp_matrix_file.close()
        
        # Manager configuration
        self.config = {
            'matrix_file': self.temp_matrix_file.name,
            'test_results_dir': self.temp_test_dir,
            'ai_assistant_url': 'http://test:8080',
            'auto_update': True,
            'test_timeout': 30
        }
        
        # Create manager instance
        self.manager = CompatibilityManager(self.config)
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        try:
            shutil.rmtree(self.temp_test_dir)
            os.unlink(self.temp_matrix_file.name)
        except Exception:
            pass
    
    def test_manager_initialization(self):
        """Test compatibility manager initialization"""
        assert len(self.manager.compatibility_matrices) == 2
        assert 'podman' in self.manager.compatibility_matrices
        assert 'ansible' in self.manager.compatibility_matrices
        
        podman_matrix = self.manager.compatibility_matrices['podman']
        assert '10' in podman_matrix.supported_versions
        assert '4.9.0' in podman_matrix.supported_versions['10']
        assert podman_matrix.test_results['4.9.0'] == 'passed'
        assert len(podman_matrix.known_issues) == 1
    
    async def test_validate_compatibility_supported_version(self):
        """Test compatibility validation for supported version"""
        level, reason = await self.manager.validate_compatibility('podman', '4.9.0', '10')
        
        assert level == CompatibilityLevel.COMPATIBLE
        assert 'supported versions' in reason.lower()
    
    async def test_validate_compatibility_test_passed(self):
        """Test compatibility validation for version that passed tests"""
        level, reason = await self.manager.validate_compatibility('ansible', '2.16.0', '9')
        
        assert level == CompatibilityLevel.COMPATIBLE
        assert 'passed' in reason.lower()
    
    async def test_validate_compatibility_test_failed(self):
        """Test compatibility validation for version that failed tests"""
        level, reason = await self.manager.validate_compatibility('podman', '4.8.0', '10')
        
        assert level == CompatibilityLevel.INCOMPATIBLE
        assert 'failed' in reason.lower()
    
    async def test_validate_compatibility_needs_testing(self):
        """Test compatibility validation for untested version"""
        level, reason = await self.manager.validate_compatibility('podman', '5.1.0', '10')
        
        assert level == CompatibilityLevel.NEEDS_TESTING
        assert 'no compatibility information' in reason.lower()
    
    def test_evaluate_version_range_rule(self):
        """Test version range rule evaluation"""
        rule = CompatibilityRule(
            rule_id='test_rule',
            component_name='podman',
            rule_type='version_range',
            condition='>=4.9.0,<6.0.0',
            os_versions=['10'],
            severity='medium',
            description='Test rule',
            created_at=datetime.now()
        )
        
        # Version in range
        assert self.manager._evaluate_rule(rule, '5.0.0') is True
        
        # Version below range
        assert self.manager._evaluate_rule(rule, '4.8.0') is False
        
        # Version above range
        assert self.manager._evaluate_rule(rule, '6.0.0') is False
    
    def test_evaluate_exclusion_rule(self):
        """Test exclusion rule evaluation"""
        rule = CompatibilityRule(
            rule_id='test_exclusion',
            component_name='podman',
            rule_type='exclusion',
            condition='4.8.0',
            os_versions=['10'],
            severity='high',
            description='Exclude problematic version',
            created_at=datetime.now()
        )
        
        # Exact match should be excluded
        assert self.manager._evaluate_rule(rule, '4.8.0') is True
        
        # Different version should not be excluded
        assert self.manager._evaluate_rule(rule, '4.9.0') is False
    
    def test_get_recent_test_results(self):
        """Test getting recent test results"""
        # Add some test results
        old_result = TestResult(
            test_id='old_test',
            component_name='podman',
            component_version='4.9.0',
            os_version='10',
            test_type='smoke',
            status=TestStatus.PASSED,
            duration=10.0,
            timestamp=datetime.now() - timedelta(days=40)
        )
        
        recent_result = TestResult(
            test_id='recent_test',
            component_name='podman',
            component_version='4.9.0',
            os_version='10',
            test_type='smoke',
            status=TestStatus.PASSED,
            duration=15.0,
            timestamp=datetime.now() - timedelta(days=5)
        )
        
        self.manager.test_results['podman'] = [old_result, recent_result]
        
        # Get recent results (last 30 days)
        recent = self.manager._get_recent_test_results('podman', '4.9.0', '10', days=30)
        
        assert len(recent) == 1
        assert recent[0].test_id == 'recent_test'
    
    @mock.patch('subprocess.run')
    async def test_test_podman_compatibility_success(self, mock_run):
        """Test successful Podman compatibility test"""
        # Mock successful subprocess calls
        mock_run.side_effect = [
            mock.MagicMock(returncode=0, stdout='podman version 5.0.0'),  # version check
            mock.MagicMock(returncode=0, stdout='Hello from Docker!')     # container test
        ]
        
        success, logs = await self.manager._test_podman_compatibility('5.0.0')
        
        assert success is True
        assert 'passed' in logs.lower()
    
    @mock.patch('subprocess.run')
    async def test_test_podman_compatibility_failure(self, mock_run):
        """Test failed Podman compatibility test"""
        # Mock failed subprocess call
        mock_run.return_value = mock.MagicMock(returncode=1, stderr='Command failed')
        
        success, logs = await self.manager._test_podman_compatibility('5.0.0')
        
        assert success is False
        assert 'failed' in logs.lower()
    
    @mock.patch('subprocess.run')
    async def test_test_ansible_compatibility_success(self, mock_run):
        """Test successful Ansible compatibility test"""
        # Mock successful subprocess calls
        mock_run.side_effect = [
            mock.MagicMock(returncode=0, stdout='ansible [core 2.16.0]'),  # version check
            mock.MagicMock(returncode=0, stdout='PLAY RECAP')              # playbook test
        ]
        
        success, logs = await self.manager._test_ansible_compatibility('2.16.0')
        
        assert success is True
        assert 'passed' in logs.lower()
    
    @mock.patch('subprocess.run')
    async def test_test_git_compatibility_success(self, mock_run):
        """Test successful Git compatibility test"""
        # Mock successful subprocess calls
        mock_run.side_effect = [
            mock.MagicMock(returncode=0, stdout='git version 2.45.0'),  # version check
            mock.MagicMock(returncode=0, stdout='Initialized'),         # git init
            mock.MagicMock(returncode=0, stdout='')                     # git add
        ]
        
        success, logs = await self.manager._test_git_compatibility('2.45.0')
        
        assert success is True
        assert 'passed' in logs.lower()
    
    @mock.patch('subprocess.run')
    async def test_test_generic_compatibility_success(self, mock_run):
        """Test successful generic compatibility test"""
        # Mock successful version check
        mock_run.return_value = mock.MagicMock(returncode=0, stdout='test-app version 1.0.0')
        
        success, logs = await self.manager._test_generic_compatibility('test-app', '1.0.0')
        
        assert success is True
        assert 'passed' in logs.lower()
    
    @mock.patch('subprocess.run')
    async def test_run_compatibility_test_success(self, mock_run):
        """Test running a complete compatibility test"""
        # Mock successful Podman test
        mock_run.side_effect = [
            mock.MagicMock(returncode=0, stdout='podman version 5.0.0'),
            mock.MagicMock(returncode=0, stdout='Hello from Docker!')
        ]
        
        result = await self.manager.run_compatibility_test('podman', '5.0.0', '10', 'smoke')
        
        assert result.component_name == 'podman'
        assert result.component_version == '5.0.0'
        assert result.os_version == '10'
        assert result.test_type == 'smoke'
        assert result.status == TestStatus.PASSED
        assert result.duration > 0
        assert result.test_id.startswith('podman_5.0.0_10_smoke_')
        
        # Check that result was stored
        assert 'podman' in self.manager.test_results
        assert len(self.manager.test_results['podman']) > 0
    
    @mock.patch('subprocess.run')
    async def test_run_compatibility_test_failure(self, mock_run):
        """Test running a failed compatibility test"""
        # Mock failed test
        mock_run.return_value = mock.MagicMock(returncode=1, stderr='Test failed')
        
        result = await self.manager.run_compatibility_test('podman', '5.0.0', '10', 'smoke')
        
        assert result.status == TestStatus.FAILED
        assert result.error_message is not None
        assert 'failed' in result.error_message.lower()
    
    async def test_update_matrix_from_test_result_passed(self):
        """Test updating matrix from passed test result"""
        test_result = TestResult(
            test_id='test_123',
            component_name='new_component',
            component_version='1.0.0',
            os_version='10',
            test_type='smoke',
            status=TestStatus.PASSED,
            duration=10.0
        )
        
        await self.manager._update_matrix_from_test_result(test_result)
        
        # Check that matrix was created and updated
        assert 'new_component' in self.manager.compatibility_matrices
        matrix = self.manager.compatibility_matrices['new_component']
        
        assert matrix.test_results['1.0.0'] == 'passed'
        assert '10' in matrix.supported_versions
        assert '1.0.0' in matrix.supported_versions['10']
    
    async def test_update_matrix_from_test_result_failed(self):
        """Test updating matrix from failed test result"""
        test_result = TestResult(
            test_id='test_456',
            component_name='podman',
            component_version='5.1.0',
            os_version='10',
            test_type='smoke',
            status=TestStatus.FAILED,
            duration=5.0,
            error_message='Test failed due to incompatibility'
        )
        
        await self.manager._update_matrix_from_test_result(test_result)
        
        matrix = self.manager.compatibility_matrices['podman']
        
        assert matrix.test_results['5.1.0'] == 'failed'
        
        # Check that known issue was added
        new_issues = [issue for issue in matrix.known_issues if issue.get('version') == '5.1.0']
        assert len(new_issues) > 0
        assert 'incompatibility' in new_issues[0]['issue']
    
    async def test_save_and_load_compatibility_matrices(self):
        """Test saving and loading compatibility matrices"""
        # Modify a matrix
        matrix = self.manager.compatibility_matrices['podman']
        matrix.supported_versions['11'] = ['5.2.0']
        matrix.test_results['5.2.0'] = 'passed'
        
        # Save matrices
        await self.manager.save_compatibility_matrices()
        
        # Create new manager instance to test loading
        new_manager = CompatibilityManager(self.config)
        
        # Check that changes were persisted
        assert 'podman' in new_manager.compatibility_matrices
        new_matrix = new_manager.compatibility_matrices['podman']
        assert '11' in new_matrix.supported_versions
        assert '5.2.0' in new_matrix.supported_versions['11']
        assert new_matrix.test_results['5.2.0'] == 'passed'
    
    async def test_save_and_load_test_results(self):
        """Test saving and loading test results"""
        # Add test results
        test_result = TestResult(
            test_id='save_test',
            component_name='podman',
            component_version='5.0.0',
            os_version='10',
            test_type='integration',
            status=TestStatus.PASSED,
            duration=25.0
        )
        
        self.manager.test_results['podman'] = [test_result]
        
        # Save results
        await self.manager.save_test_results()
        
        # Create new manager instance to test loading
        new_manager = CompatibilityManager(self.config)
        
        # Check that results were persisted
        assert 'podman' in new_manager.test_results
        assert len(new_manager.test_results['podman']) > 0
        
        loaded_result = new_manager.test_results['podman'][0]
        assert loaded_result.test_id == 'save_test'
        assert loaded_result.component_name == 'podman'
        assert loaded_result.status == TestStatus.PASSED
    
    async def test_generate_compatibility_report(self):
        """Test generating compatibility report"""
        # Add some test results
        test_result = TestResult(
            test_id='report_test',
            component_name='podman',
            component_version='4.9.0',
            os_version='10',
            test_type='smoke',
            status=TestStatus.PASSED,
            duration=12.0,
            timestamp=datetime.now() - timedelta(days=2)
        )
        
        self.manager.test_results['podman'] = [test_result]
        
        # Generate report
        report = await self.manager.generate_compatibility_report()
        
        # Verify report structure
        assert 'report_timestamp' in report
        assert 'total_components' in report
        assert 'total_test_results' in report
        assert 'components' in report
        assert 'summary' in report
        
        # Check summary
        summary = report['summary']
        assert 'compatible_versions' in summary
        assert 'incompatible_versions' in summary
        assert 'needs_testing' in summary
        assert 'recent_tests' in summary
        assert 'test_success_rate' in summary
        
        # Check component details
        assert 'podman' in report['components']
        podman_report = report['components']['podman']
        assert 'supported_versions' in podman_report
        assert 'test_results' in podman_report
        assert 'recent_test_results' in podman_report
        
        # Check that recent test is included
        assert len(podman_report['recent_test_results']) > 0
        assert podman_report['recent_test_results'][0]['test_id'] == 'report_test'


class TestTestResult:
    """Test cases for TestResult dataclass"""
    
    def test_test_result_creation(self):
        """Test TestResult creation and initialization"""
        result = TestResult(
            test_id='test_123',
            component_name='podman',
            component_version='5.0.0',
            os_version='10',
            test_type='smoke',
            status=TestStatus.PASSED,
            duration=15.5
        )
        
        assert result.test_id == 'test_123'
        assert result.component_name == 'podman'
        assert result.component_version == '5.0.0'
        assert result.status == TestStatus.PASSED
        assert result.duration == 15.5
        assert result.timestamp is not None  # Auto-initialized
        assert result.error_message is None
        assert result.logs is None


class TestCompatibilityRule:
    """Test cases for CompatibilityRule dataclass"""
    
    def test_compatibility_rule_creation(self):
        """Test CompatibilityRule creation and initialization"""
        created_time = datetime.now()
        rule = CompatibilityRule(
            rule_id='rule_123',
            component_name='podman',
            rule_type='version_range',
            condition='>=4.9.0,<6.0.0',
            os_versions=['10', '9'],
            severity='medium',
            description='Version range rule for Podman',
            created_at=created_time
        )
        
        assert rule.rule_id == 'rule_123'
        assert rule.component_name == 'podman'
        assert rule.rule_type == 'version_range'
        assert rule.condition == '>=4.9.0,<6.0.0'
        assert rule.os_versions == ['10', '9']
        assert rule.severity == 'medium'
        assert rule.created_at == created_time
        assert rule.last_validated == created_time  # Auto-initialized


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
