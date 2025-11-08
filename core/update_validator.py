"""
Qubinode Navigator Automated Update Validation Infrastructure

This module provides comprehensive automated testing infrastructure for validating
updates before deployment, including containerized testing, rollback validation,
and integration with the compatibility matrix system.
"""

import asyncio
import json
import logging
import subprocess
import tempfile
import time
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import requests
from enum import Enum

from core.update_manager import UpdateDetector, UpdateInfo, UpdateBatch
from core.compatibility_manager import CompatibilityManager, TestResult, TestStatus


class ValidationStage(Enum):
    """Update validation stages"""
    PREPARATION = "preparation"
    PRE_UPDATE_TESTS = "pre_update_tests"
    UPDATE_APPLICATION = "update_application"
    POST_UPDATE_TESTS = "post_update_tests"
    ROLLBACK_VALIDATION = "rollback_validation"
    CLEANUP = "cleanup"


class ValidationResult(Enum):
    """Validation result status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ValidationTest:
    """Individual validation test definition"""
    test_id: str
    test_name: str
    test_type: str  # functional, performance, security, integration
    component: str
    stage: ValidationStage
    command: str
    expected_result: str
    timeout: int = 300
    critical: bool = True
    retry_count: int = 0
    environment: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.environment is None:
            self.environment = {}


@dataclass
class ValidationExecution:
    """Validation test execution result"""
    test_id: str
    execution_id: str
    status: ValidationResult
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0
    output: str = ""
    error_message: Optional[str] = None
    exit_code: Optional[int] = None
    retry_attempt: int = 0
    
    def __post_init__(self):
        if self.end_time and self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()


@dataclass
class ValidationSuite:
    """Collection of validation tests for an update"""
    suite_id: str
    update_info: UpdateInfo
    tests: List[ValidationTest]
    environment_config: Dict[str, Any]
    created_at: datetime
    
    def get_tests_by_stage(self, stage: ValidationStage) -> List[ValidationTest]:
        """Get tests for a specific validation stage"""
        return [test for test in self.tests if test.stage == stage]


class UpdateValidator:
    """
    Automated Update Validation Infrastructure
    
    Provides comprehensive testing infrastructure for validating updates
    including containerized testing, rollback validation, and integration
    with compatibility and update management systems.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.test_environment_dir = Path(self.config.get('test_environment_dir', '/tmp/update_validation'))
        self.container_runtime = self.config.get('container_runtime', 'podman')
        self.base_image = self.config.get('base_image', 'quay.io/centos/centos:stream10')
        self.ai_assistant_url = self.config.get('ai_assistant_url', 'http://localhost:8080')
        self.parallel_tests = self.config.get('parallel_tests', 3)
        self.validation_timeout = self.config.get('validation_timeout', 1800)  # 30 minutes
        
        # State
        self.validation_suites: Dict[str, ValidationSuite] = {}
        self.test_executions: Dict[str, List[ValidationExecution]] = {}
        self.active_containers: Set[str] = set()
        
        # Initialize components
        self.update_detector = UpdateDetector(config)
        self.compatibility_manager = CompatibilityManager(config)
        
        # Ensure directories exist
        self.test_environment_dir.mkdir(parents=True, exist_ok=True)
        
        # Load test definitions
        self._load_test_definitions()
    
    def _load_test_definitions(self):
        """Load predefined test definitions"""
        self.test_templates = {
            'system_health': {
                'name': 'System Health Check',
                'type': 'functional',
                'stage': 'pre_update_tests',
                'command': 'systemctl status && df -h && free -m',
                'expected_result': 'exit_code_0',
                'timeout': 60,
                'critical': True
            },
            'service_status': {
                'name': 'Critical Services Status',
                'type': 'functional',
                'stage': 'post_update_tests',
                'command': 'systemctl is-active sshd NetworkManager',
                'expected_result': 'all_active',
                'timeout': 30,
                'critical': True
            }
        }
        
        self.environment_configs = {
            'default': {
                'base_image': self.base_image,
                'packages': ['systemd', 'openssh-server', 'NetworkManager'],
                'services': ['sshd', 'NetworkManager'],
                'environment_vars': {
                    'LANG': 'en_US.UTF-8',
                    'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
                }
            }
        }
    
    async def create_validation_suite(self, update_info: UpdateInfo) -> ValidationSuite:
        """Create a validation suite for an update"""
        suite_id = f"validation_{update_info.component_name}_{update_info.available_version}_{int(time.time())}"
        
        # Generate tests based on component type and update
        tests = await self._generate_tests_for_update(update_info)
        
        # Get environment configuration
        env_config = self.environment_configs.get('default', {})
        
        suite = ValidationSuite(
            suite_id=suite_id,
            update_info=update_info,
            tests=tests,
            environment_config=env_config,
            created_at=datetime.now()
        )
        
        self.validation_suites[suite_id] = suite
        self.logger.info(f"Created validation suite {suite_id} with {len(tests)} tests")
        
        return suite
    
    async def _generate_tests_for_update(self, update_info: UpdateInfo) -> List[ValidationTest]:
        """Generate validation tests for a specific update"""
        tests = []
        
        # Add standard pre-update tests
        tests.extend(self._create_standard_tests(update_info, ValidationStage.PRE_UPDATE_TESTS))
        
        # Add component-specific tests
        if update_info.component_name == 'podman':
            tests.extend(self._create_podman_tests(update_info))
        elif update_info.component_name == 'ansible':
            tests.extend(self._create_ansible_tests(update_info))
        
        # Add standard post-update tests
        tests.extend(self._create_standard_tests(update_info, ValidationStage.POST_UPDATE_TESTS))
        
        return tests
    
    def _create_standard_tests(self, update_info: UpdateInfo, stage: ValidationStage) -> List[ValidationTest]:
        """Create standard validation tests"""
        tests = []
        
        if stage == ValidationStage.PRE_UPDATE_TESTS:
            tests.append(ValidationTest(
                test_id=f"pre_health_{int(time.time())}",
                test_name="Pre-Update System Health",
                test_type="functional",
                component=update_info.component_name,
                stage=stage,
                command="systemctl status && df -h && free -m",
                expected_result="exit_code_0",
                timeout=60,
                critical=True
            ))
        
        elif stage == ValidationStage.POST_UPDATE_TESTS:
            tests.append(ValidationTest(
                test_id=f"post_health_{int(time.time())}",
                test_name="Post-Update System Health",
                test_type="functional",
                component=update_info.component_name,
                stage=stage,
                command="systemctl status && df -h && free -m",
                expected_result="exit_code_0",
                timeout=60,
                critical=True
            ))
        
        return tests
    
    def _create_podman_tests(self, update_info: UpdateInfo) -> List[ValidationTest]:
        """Create Podman-specific validation tests"""
        tests = []
        
        tests.append(ValidationTest(
            test_id=f"podman_version_{int(time.time())}",
            test_name="Podman Version Verification",
            test_type="functional",
            component="podman",
            stage=ValidationStage.POST_UPDATE_TESTS,
            command="podman --version",
            expected_result="version_match",
            timeout=30,
            critical=True
        ))
        
        tests.append(ValidationTest(
            test_id=f"podman_container_{int(time.time())}",
            test_name="Podman Container Functionality",
            test_type="functional",
            component="podman",
            stage=ValidationStage.POST_UPDATE_TESTS,
            command="podman run --rm hello-world",
            expected_result="hello_world_output",
            timeout=120,
            critical=True
        ))
        
        return tests
    
    def _create_ansible_tests(self, update_info: UpdateInfo) -> List[ValidationTest]:
        """Create Ansible-specific validation tests"""
        tests = []
        
        tests.append(ValidationTest(
            test_id=f"ansible_version_{int(time.time())}",
            test_name="Ansible Version Verification",
            test_type="functional",
            component="ansible",
            stage=ValidationStage.POST_UPDATE_TESTS,
            command="ansible --version",
            expected_result="version_match",
            timeout=30,
            critical=True
        ))
        
        tests.append(ValidationTest(
            test_id=f"ansible_functionality_{int(time.time())}",
            test_name="Ansible Basic Functionality",
            test_type="functional",
            component="ansible",
            stage=ValidationStage.POST_UPDATE_TESTS,
            command="ansible localhost -m setup",
            expected_result="ansible_facts",
            timeout=60,
            critical=True
        ))
        
        return tests
    
    async def create_test_environment(self, suite: ValidationSuite) -> str:
        """Create isolated test environment for validation"""
        container_name = f"validation_{suite.suite_id}"
        
        try:
            # Create container from base image
            create_cmd = [
                self.container_runtime, 'run', '-d',
                '--name', container_name,
                '--privileged',  # Needed for systemd
                '-v', '/sys/fs/cgroup:/sys/fs/cgroup:ro',
                suite.environment_config.get('base_image', self.base_image),
                '/usr/sbin/init'
            ]
            
            result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                raise Exception(f"Failed to create container: {result.stderr}")
            
            self.active_containers.add(container_name)
            
            # Wait for container to be ready
            await asyncio.sleep(5)
            
            self.logger.info(f"Created test environment: {container_name}")
            return container_name
            
        except Exception as e:
            self.logger.error(f"Failed to create test environment: {e}")
            if container_name in self.active_containers:
                await self._cleanup_container(container_name)
            raise
    
    async def execute_validation_test(self, test: ValidationTest, container_name: str) -> ValidationExecution:
        """Execute a single validation test"""
        execution_id = f"exec_{test.test_id}_{int(time.time())}"
        
        execution = ValidationExecution(
            test_id=test.test_id,
            execution_id=execution_id,
            status=ValidationResult.FAILED,
            start_time=datetime.now()
        )
        
        try:
            # Prepare command for container execution
            exec_cmd = [
                self.container_runtime, 'exec', container_name,
                'bash', '-c', test.command
            ]
            
            # Execute test with timeout
            result = subprocess.run(
                exec_cmd,
                capture_output=True,
                text=True,
                timeout=test.timeout
            )
            
            execution.end_time = datetime.now()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            execution.output = result.stdout
            execution.exit_code = result.returncode
            
            # Evaluate test result
            if result.returncode == 0:
                if self._evaluate_test_result(test, result.stdout, result.stderr):
                    execution.status = ValidationResult.PASSED
                else:
                    execution.status = ValidationResult.WARNING
                    execution.error_message = "Test passed but output validation failed"
            else:
                execution.status = ValidationResult.FAILED
                execution.error_message = result.stderr
            
        except subprocess.TimeoutExpired:
            execution.end_time = datetime.now()
            execution.duration = test.timeout
            execution.status = ValidationResult.FAILED
            execution.error_message = f"Test timed out after {test.timeout}s"
            
        except Exception as e:
            execution.end_time = datetime.now()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            execution.status = ValidationResult.ERROR
            execution.error_message = str(e)
        
        # Store execution result
        if test.test_id not in self.test_executions:
            self.test_executions[test.test_id] = []
        self.test_executions[test.test_id].append(execution)
        
        self.logger.info(f"Test {test.test_id} completed: {execution.status.value}")
        return execution
    
    def _evaluate_test_result(self, test: ValidationTest, stdout: str, stderr: str) -> bool:
        """Evaluate if test result matches expected outcome"""
        expected = test.expected_result
        
        if expected == "exit_code_0":
            return True  # Already checked exit code
        elif expected == "version_match":
            return any(word in stdout.lower() for word in ['version', 'v.']) and not any(word in stdout.lower() for word in ['without', 'command', 'output'])
        elif expected == "hello_world_output":
            return "hello" in stdout.lower()
        elif expected == "ansible_facts":
            return "ansible_facts" in stdout or "SUCCESS" in stdout
        elif expected == "all_active":
            return "active" in stdout or "running" in stdout
        elif expected == "services_status":
            return "active" in stdout or "running" in stdout
        elif expected == "network_accessible":
            return "64 bytes" in stdout or "ip" in stdout.lower()
        elif expected == "version_info":
            return any(word in stdout.lower() for word in ['version', 'v.', 'ver'])
        elif expected == "hello_output":
            return "hello" in stdout.lower()
        elif expected == "image_info":
            return len(stdout.strip()) > 0
        elif expected == "collections_listed":
            return "collection" in stdout.lower() or "namespace" in stdout.lower()
        elif expected == "git_operations":
            return "initialized" in stdout.lower() or len(stdout.strip()) > 0
        elif expected == "kernel_info":
            return len(stdout.strip()) > 0
        elif expected == "modules_info":
            return len(stdout.strip()) > 0
        elif expected == "systemd_status":
            return "systemd" in stdout.lower() or "active" in stdout.lower()
        elif expected == "performance_metrics":
            return len(stdout.strip()) > 0
        elif expected == "memory_info":
            return "mem" in stdout.lower()
        elif expected == "selinux_info":
            return len(stdout.strip()) > 0
        elif expected == "firewall_info":
            return len(stdout.strip()) > 0
        elif expected == "package_count":
            return stdout.strip().isdigit()
        else:
            # For unknown expectations, be more conservative
            return len(stdout.strip()) > 0
    
    async def run_validation_suite(self, suite_id: str) -> Dict[str, Any]:
        """Run complete validation suite"""
        if suite_id not in self.validation_suites:
            raise ValueError(f"Validation suite {suite_id} not found")
        
        suite = self.validation_suites[suite_id]
        self.logger.info(f"Starting validation suite: {suite_id}")
        
        # Create test environment
        container_name = await self.create_test_environment(suite)
        
        results = {
            'suite_id': suite_id,
            'start_time': datetime.now().isoformat(),
            'container_name': container_name,
            'stages': {},
            'summary': {
                'total_tests': len(suite.tests),
                'passed': 0,
                'failed': 0,
                'warnings': 0,
                'errors': 0,
                'skipped': 0
            }
        }
        
        try:
            # Run tests by stage
            for stage in ValidationStage:
                stage_tests = suite.get_tests_by_stage(stage)
                if not stage_tests:
                    continue
                
                self.logger.info(f"Running {stage.value} stage with {len(stage_tests)} tests")
                
                stage_results = []
                stage_passed = True
                
                # Execute tests sequentially for simplicity
                for test in stage_tests:
                    execution = await self.execute_validation_test(test, container_name)
                    
                    stage_results.append({
                        'test_id': execution.test_id,
                        'status': execution.status.value,
                        'duration': execution.duration,
                        'output': execution.output[:200] if execution.output else None,
                        'error': execution.error_message
                    })
                    
                    # Update summary
                    results['summary'][execution.status.value] += 1
                    
                    # Check if critical test failed
                    if execution.status == ValidationResult.FAILED and test.critical:
                        stage_passed = False
                
                results['stages'][stage.value] = {
                    'tests': stage_results,
                    'passed': stage_passed,
                    'test_count': len(stage_tests)
                }
                
                # Stop if critical stage failed
                if not stage_passed and stage == ValidationStage.PRE_UPDATE_TESTS:
                    self.logger.warning(f"Critical stage {stage.value} failed, stopping validation")
                    break
        
        finally:
            # Cleanup test environment
            await self._cleanup_container(container_name)
        
        results['end_time'] = datetime.now().isoformat()
        results['duration'] = (datetime.fromisoformat(results['end_time']) - 
                             datetime.fromisoformat(results['start_time'])).total_seconds()
        
        # Determine overall result
        results['overall_result'] = self._determine_overall_result(results)
        
        self.logger.info(f"Validation suite {suite_id} completed: {results['overall_result']}")
        return results
    
    def _determine_overall_result(self, results: Dict[str, Any]) -> str:
        """Determine overall validation result"""
        summary = results['summary']
        
        if summary['errors'] > 0:
            return 'error'
        elif summary['failed'] > 0:
            return 'failed'
        elif summary['warnings'] > 0:
            return 'warning'
        elif summary['passed'] > 0:
            return 'passed'
        else:
            return 'skipped'
    
    async def _cleanup_container(self, container_name: str):
        """Cleanup test container"""
        try:
            # Stop and remove container
            subprocess.run([self.container_runtime, 'stop', container_name], 
                          capture_output=True, timeout=30)
            subprocess.run([self.container_runtime, 'rm', container_name], 
                          capture_output=True, timeout=30)
            
            self.active_containers.discard(container_name)
            self.logger.info(f"Cleaned up container: {container_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup container {container_name}: {e}")
    
    async def validate_update_batch(self, batch: UpdateBatch) -> Dict[str, Any]:
        """Validate an entire update batch"""
        batch_results = {
            'batch_id': batch.batch_id,
            'batch_type': batch.batch_type,
            'start_time': datetime.now().isoformat(),
            'update_results': {},
            'overall_status': 'pending'
        }
        
        try:
            # Validate each update in the batch
            for update in batch.updates:
                self.logger.info(f"Validating update: {update.component_name} {update.available_version}")
                
                # Create validation suite
                suite = await self.create_validation_suite(update)
                
                # Run validation
                result = await self.run_validation_suite(suite.suite_id)
                
                batch_results['update_results'][update.component_name] = result
            
            # Determine batch result
            all_passed = all(
                result['overall_result'] == 'passed' 
                for result in batch_results['update_results'].values()
            )
            
            batch_results['overall_status'] = 'passed' if all_passed else 'failed'
            
        except Exception as e:
            batch_results['overall_status'] = 'error'
            batch_results['error'] = str(e)
            self.logger.error(f"Batch validation failed: {e}")
        
        batch_results['end_time'] = datetime.now().isoformat()
        return batch_results
    
    async def cleanup_all_containers(self):
        """Cleanup all active test containers"""
        for container_name in list(self.active_containers):
            await self._cleanup_container(container_name)
