"""
Qubinode Navigator Compatibility Matrix Management System

This module provides dynamic management of compatibility matrices including
automated testing, validation, and updates based on real-world deployment results.

Based on ADR-0030: Software and OS Update Strategy
"""

import asyncio
import hashlib
import json
import logging
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
import yaml

from core.update_manager import CompatibilityMatrix, UpdateInfo


class TestStatus(Enum):
    """Test execution status"""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class CompatibilityLevel(Enum):
    """Compatibility assessment levels"""

    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    NEEDS_TESTING = "needs_testing"
    DEPRECATED = "deprecated"
    UNKNOWN = "unknown"


@dataclass
class TestResult:
    """Individual test result"""

    test_id: str
    component_name: str
    component_version: str
    os_version: str
    test_type: str  # unit, integration, smoke, compatibility
    status: TestStatus
    duration: float
    error_message: Optional[str] = None
    logs: Optional[str] = None
    environment: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class CompatibilityRule:
    """Compatibility rule definition"""

    rule_id: str
    component_name: str
    rule_type: str  # version_range, dependency, exclusion, requirement
    condition: str  # version expression or dependency spec
    os_versions: List[str]
    severity: str  # critical, high, medium, low
    description: str
    created_at: datetime
    last_validated: Optional[datetime] = None

    def __post_init__(self):
        if self.last_validated is None:
            self.last_validated = self.created_at


class CompatibilityManager:
    """
    Dynamic Compatibility Matrix Management System

    Provides automated testing, validation, and maintenance of
    component compatibility information across different OS versions.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.matrix_file = self.config.get(
            "matrix_file", "config/compatibility_matrix.yml"
        )
        self.test_results_dir = Path(
            self.config.get("test_results_dir", "/tmp/compatibility_tests")
        )
        self.ai_assistant_url = self.config.get(
            "ai_assistant_url", "http://localhost:8080"
        )
        self.auto_update = self.config.get("auto_update", True)
        self.test_timeout = self.config.get("test_timeout", 300)  # 5 minutes

        # State
        self.compatibility_matrices: Dict[str, CompatibilityMatrix] = {}
        self.test_results: Dict[str, List[TestResult]] = {}
        self.compatibility_rules: List[CompatibilityRule] = []
        self.pending_tests: List[Dict[str, Any]] = []

        # Ensure directories exist
        self.test_results_dir.mkdir(parents=True, exist_ok=True)

        # Load existing data
        self._load_compatibility_matrices()
        self._load_test_results()
        self._load_compatibility_rules()

    def _load_compatibility_matrices(self):
        """Load compatibility matrices from configuration"""
        try:
            matrix_file = Path(self.matrix_file)
            if matrix_file.exists():
                with open(matrix_file, "r") as f:
                    matrix_data = yaml.safe_load(f)

                for component, data in matrix_data.items():
                    self.compatibility_matrices[component] = CompatibilityMatrix(
                        component_name=component,
                        supported_versions=data.get("supported_versions", {}),
                        known_issues=data.get("known_issues", []),
                        test_results=data.get("test_results", {}),
                        last_updated=datetime.fromisoformat(
                            data.get("last_updated", datetime.now().isoformat())
                        ),
                    )

                self.logger.info(
                    f"Loaded {len(self.compatibility_matrices)} compatibility matrices"
                )
            else:
                self.logger.warning(
                    f"Compatibility matrix file not found: {matrix_file}"
                )

        except Exception as e:
            self.logger.error(f"Failed to load compatibility matrices: {e}")

    def _load_test_results(self):
        """Load historical test results"""
        try:
            results_file = self.test_results_dir / "test_results.json"
            if results_file.exists():
                with open(results_file, "r") as f:
                    results_data = json.load(f)

                for component, results in results_data.items():
                    self.test_results[component] = []
                    for result_data in results:
                        result = TestResult(
                            test_id=result_data["test_id"],
                            component_name=result_data["component_name"],
                            component_version=result_data["component_version"],
                            os_version=result_data["os_version"],
                            test_type=result_data["test_type"],
                            status=TestStatus(result_data["status"]),
                            duration=result_data["duration"],
                            error_message=result_data.get("error_message"),
                            logs=result_data.get("logs"),
                            environment=result_data.get("environment"),
                            timestamp=datetime.fromisoformat(result_data["timestamp"]),
                        )
                        self.test_results[component].append(result)

                self.logger.info(
                    f"Loaded test results for {len(self.test_results)} components"
                )

        except Exception as e:
            self.logger.error(f"Failed to load test results: {e}")

    def _load_compatibility_rules(self):
        """Load compatibility rules"""
        try:
            rules_file = self.test_results_dir / "compatibility_rules.json"
            if rules_file.exists():
                with open(rules_file, "r") as f:
                    rules_data = json.load(f)

                for rule_data in rules_data:
                    rule = CompatibilityRule(
                        rule_id=rule_data["rule_id"],
                        component_name=rule_data["component_name"],
                        rule_type=rule_data["rule_type"],
                        condition=rule_data["condition"],
                        os_versions=rule_data["os_versions"],
                        severity=rule_data["severity"],
                        description=rule_data["description"],
                        created_at=datetime.fromisoformat(rule_data["created_at"]),
                        last_validated=datetime.fromisoformat(
                            rule_data.get("last_validated", rule_data["created_at"])
                        ),
                    )
                    self.compatibility_rules.append(rule)

                self.logger.info(
                    f"Loaded {len(self.compatibility_rules)} compatibility rules"
                )

        except Exception as e:
            self.logger.error(f"Failed to load compatibility rules: {e}")

    async def validate_compatibility(
        self, component: str, version: str, os_version: str
    ) -> Tuple[CompatibilityLevel, str]:
        """Validate compatibility of a component version"""
        try:
            # Check existing matrix
            if component in self.compatibility_matrices:
                matrix = self.compatibility_matrices[component]

                # Check supported versions
                supported = matrix.supported_versions.get(os_version, [])
                if version in supported:
                    return CompatibilityLevel.COMPATIBLE, "Listed in supported versions"

                # Check test results
                test_status = matrix.test_results.get(version, "unknown")
                if test_status == "passed":
                    return CompatibilityLevel.COMPATIBLE, "Passed compatibility tests"
                elif test_status == "failed":
                    return CompatibilityLevel.INCOMPATIBLE, "Failed compatibility tests"

            # Check compatibility rules
            for rule in self.compatibility_rules:
                if rule.component_name == component and os_version in rule.os_versions:
                    if self._evaluate_rule(rule, version):
                        if rule.rule_type == "exclusion":
                            return (
                                CompatibilityLevel.INCOMPATIBLE,
                                f"Excluded by rule: {rule.description}",
                            )
                        elif rule.rule_type == "requirement":
                            return (
                                CompatibilityLevel.COMPATIBLE,
                                f"Meets requirement: {rule.description}",
                            )

            # Check recent test results
            recent_results = self._get_recent_test_results(
                component, version, os_version
            )
            if recent_results:
                passed = sum(1 for r in recent_results if r.status == TestStatus.PASSED)
                total = len(recent_results)
                if passed / total >= 0.8:  # 80% pass rate
                    return (
                        CompatibilityLevel.COMPATIBLE,
                        f"Recent tests: {passed}/{total} passed",
                    )
                elif passed / total < 0.5:  # Less than 50% pass rate
                    return (
                        CompatibilityLevel.INCOMPATIBLE,
                        f"Recent tests: {passed}/{total} passed",
                    )

            return (
                CompatibilityLevel.NEEDS_TESTING,
                "No compatibility information available",
            )

        except Exception as e:
            self.logger.error(
                f"Failed to validate compatibility for {component} {version}: {e}"
            )
            return CompatibilityLevel.UNKNOWN, f"Validation error: {str(e)}"

    def _evaluate_rule(self, rule: CompatibilityRule, version: str) -> bool:
        """Evaluate a compatibility rule against a version"""
        try:
            from packaging import version as pkg_version

            if rule.rule_type == "version_range":
                # Parse version range like ">=2.0.0,<3.0.0"
                conditions = rule.condition.split(",")
                for condition in conditions:
                    condition = condition.strip()
                    if condition.startswith(">="):
                        min_version = condition[2:].strip()
                        if pkg_version.parse(version) < pkg_version.parse(min_version):
                            return False
                    elif condition.startswith("<="):
                        max_version = condition[2:].strip()
                        if pkg_version.parse(version) > pkg_version.parse(max_version):
                            return False
                    elif condition.startswith(">"):
                        min_version = condition[1:].strip()
                        if pkg_version.parse(version) <= pkg_version.parse(min_version):
                            return False
                    elif condition.startswith("<"):
                        max_version = condition[1:].strip()
                        if pkg_version.parse(version) >= pkg_version.parse(max_version):
                            return False
                    elif condition.startswith("=="):
                        exact_version = condition[2:].strip()
                        if pkg_version.parse(version) != pkg_version.parse(
                            exact_version
                        ):
                            return False
                return True

            elif rule.rule_type == "exclusion":
                # Check if version matches exclusion pattern
                return version == rule.condition or version.startswith(rule.condition)

            elif rule.rule_type == "requirement":
                # Check if version meets requirement
                return pkg_version.parse(version) >= pkg_version.parse(rule.condition)

            return False

        except Exception as e:
            self.logger.error(f"Failed to evaluate rule {rule.rule_id}: {e}")
            return False

    def _get_recent_test_results(
        self, component: str, version: str, os_version: str, days: int = 30
    ) -> List[TestResult]:
        """Get recent test results for a component version"""
        if component not in self.test_results:
            return []

        cutoff_date = datetime.now() - timedelta(days=days)
        recent_results = []

        for result in self.test_results[component]:
            if (
                result.component_version == version
                and result.os_version == os_version
                and result.timestamp >= cutoff_date
            ):
                recent_results.append(result)

        return recent_results

    async def run_compatibility_test(
        self, component: str, version: str, os_version: str, test_type: str = "smoke"
    ) -> TestResult:
        """Run a compatibility test for a component version"""
        test_id = f"{component}_{version}_{os_version}_{test_type}_{int(time.time())}"

        self.logger.info(f"Running compatibility test: {test_id}")

        start_time = time.time()
        test_result = TestResult(
            test_id=test_id,
            component_name=component,
            component_version=version,
            os_version=os_version,
            test_type=test_type,
            status=TestStatus.RUNNING,
            duration=0.0,
        )

        try:
            # Run component-specific test
            if component == "podman":
                success, logs = await self._test_podman_compatibility(version)
            elif component == "ansible":
                success, logs = await self._test_ansible_compatibility(version)
            elif component == "git":
                success, logs = await self._test_git_compatibility(version)
            else:
                success, logs = await self._test_generic_compatibility(
                    component, version
                )

            test_result.duration = time.time() - start_time
            test_result.status = TestStatus.PASSED if success else TestStatus.FAILED
            test_result.logs = logs

            if not success:
                test_result.error_message = (
                    f"Compatibility test failed for {component} {version}"
                )

        except asyncio.TimeoutError:
            test_result.duration = time.time() - start_time
            test_result.status = TestStatus.TIMEOUT
            test_result.error_message = f"Test timed out after {self.test_timeout}s"

        except Exception as e:
            test_result.duration = time.time() - start_time
            test_result.status = TestStatus.FAILED
            test_result.error_message = str(e)
            test_result.logs = f"Exception during test: {e}"

        # Store test result
        if component not in self.test_results:
            self.test_results[component] = []
        self.test_results[component].append(test_result)

        # Update compatibility matrix if auto-update is enabled
        if self.auto_update:
            await self._update_matrix_from_test_result(test_result)

        self.logger.info(f"Test completed: {test_id} - {test_result.status.value}")
        return test_result

    async def _test_podman_compatibility(self, version: str) -> Tuple[bool, str]:
        """Test Podman compatibility"""
        try:
            # Basic functionality test
            result = subprocess.run(
                ["podman", "--version"], capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return False, f"Version check failed: {result.stderr}"

            # Container operations test
            result = subprocess.run(
                ["podman", "run", "--rm", "hello-world"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return False, f"Container test failed: {result.stderr}"

            return True, "Podman compatibility test passed"

        except subprocess.TimeoutExpired:
            return False, "Podman test timed out"
        except Exception as e:
            return False, f"Podman test error: {e}"

    async def _test_ansible_compatibility(self, version: str) -> Tuple[bool, str]:
        """Test Ansible compatibility"""
        try:
            # Version check
            result = subprocess.run(
                ["ansible", "--version"], capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return False, f"Version check failed: {result.stderr}"

            # Basic playbook test
            test_playbook = """
---
- hosts: localhost
  connection: local
  tasks:
    - name: Test task
      debug:
        msg: "Ansible compatibility test"
            """

            playbook_file = (
                self.test_results_dir / f"test_playbook_{int(time.time())}.yml"
            )
            with open(playbook_file, "w") as f:
                f.write(test_playbook)

            result = subprocess.run(
                ["ansible-playbook", str(playbook_file)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            playbook_file.unlink()  # Cleanup

            if result.returncode != 0:
                return False, f"Playbook test failed: {result.stderr}"

            return True, "Ansible compatibility test passed"

        except subprocess.TimeoutExpired:
            return False, "Ansible test timed out"
        except Exception as e:
            return False, f"Ansible test error: {e}"

    async def _test_git_compatibility(self, version: str) -> Tuple[bool, str]:
        """Test Git compatibility"""
        try:
            # Version check
            result = subprocess.run(
                ["git", "--version"], capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return False, f"Version check failed: {result.stderr}"

            # Basic operations test
            test_dir = self.test_results_dir / f"git_test_{int(time.time())}"
            test_dir.mkdir()

            # Initialize repo
            result = subprocess.run(
                ["git", "init"],
                cwd=test_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return False, f"Git init failed: {result.stderr}"

            # Create and add file
            test_file = test_dir / "test.txt"
            test_file.write_text("test content")

            result = subprocess.run(
                ["git", "add", "test.txt"],
                cwd=test_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return False, f"Git add failed: {result.stderr}"

            # Cleanup
            import shutil

            shutil.rmtree(test_dir)

            return True, "Git compatibility test passed"

        except subprocess.TimeoutExpired:
            return False, "Git test timed out"
        except Exception as e:
            return False, f"Git test error: {e}"

    async def _test_generic_compatibility(
        self, component: str, version: str
    ) -> Tuple[bool, str]:
        """Generic compatibility test"""
        try:
            # Try basic version check
            result = subprocess.run(
                [component, "--version"], capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return True, f"Generic compatibility test passed for {component}"
            else:
                return False, f"Version check failed: {result.stderr}"

        except FileNotFoundError:
            return False, f"Component {component} not found"
        except subprocess.TimeoutExpired:
            return False, f"{component} test timed out"
        except Exception as e:
            return False, f"{component} test error: {e}"

    async def _update_matrix_from_test_result(self, test_result: TestResult):
        """Update compatibility matrix based on test result"""
        try:
            component = test_result.component_name

            # Ensure matrix exists
            if component not in self.compatibility_matrices:
                self.compatibility_matrices[component] = CompatibilityMatrix(
                    component_name=component,
                    supported_versions={},
                    known_issues=[],
                    test_results={},
                    last_updated=datetime.now(),
                )

            matrix = self.compatibility_matrices[component]

            # Update test results
            if test_result.status == TestStatus.PASSED:
                matrix.test_results[test_result.component_version] = "passed"

                # Add to supported versions if not already there
                if test_result.os_version not in matrix.supported_versions:
                    matrix.supported_versions[test_result.os_version] = []

                if (
                    test_result.component_version
                    not in matrix.supported_versions[test_result.os_version]
                ):
                    matrix.supported_versions[test_result.os_version].append(
                        test_result.component_version
                    )

            elif test_result.status == TestStatus.FAILED:
                matrix.test_results[test_result.component_version] = "failed"

                # Add to known issues if error message is available
                if test_result.error_message:
                    issue = {
                        "version": test_result.component_version,
                        "issue": test_result.error_message,
                        "severity": "medium",
                        "discovered_at": test_result.timestamp.isoformat(),
                    }
                    matrix.known_issues.append(issue)

            matrix.last_updated = datetime.now()

            # Save updated matrix
            await self.save_compatibility_matrices()

        except Exception as e:
            self.logger.error(f"Failed to update matrix from test result: {e}")

    async def save_compatibility_matrices(self):
        """Save compatibility matrices to file"""
        try:
            matrix_data = {}

            for component, matrix in self.compatibility_matrices.items():
                matrix_data[component] = {
                    "supported_versions": matrix.supported_versions,
                    "known_issues": matrix.known_issues,
                    "test_results": matrix.test_results,
                    "last_updated": matrix.last_updated.isoformat(),
                }

            with open(self.matrix_file, "w") as f:
                yaml.dump(matrix_data, f, default_flow_style=False, sort_keys=True)

            self.logger.info(
                f"Saved {len(self.compatibility_matrices)} compatibility matrices"
            )

        except Exception as e:
            self.logger.error(f"Failed to save compatibility matrices: {e}")

    async def save_test_results(self):
        """Save test results to file"""
        try:
            results_data = {}

            for component, results in self.test_results.items():
                results_data[component] = []
                for result in results:
                    result_dict = asdict(result)
                    result_dict["status"] = result.status.value
                    result_dict["timestamp"] = result.timestamp.isoformat()
                    results_data[component].append(result_dict)

            results_file = self.test_results_dir / "test_results.json"
            with open(results_file, "w") as f:
                json.dump(results_data, f, indent=2, default=str)

            self.logger.info(
                f"Saved test results for {len(self.test_results)} components"
            )

        except Exception as e:
            self.logger.error(f"Failed to save test results: {e}")

    async def generate_compatibility_report(self) -> Dict[str, Any]:
        """Generate comprehensive compatibility report"""
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "total_components": len(self.compatibility_matrices),
            "total_test_results": sum(
                len(results) for results in self.test_results.values()
            ),
            "total_rules": len(self.compatibility_rules),
            "components": {},
            "summary": {
                "compatible_versions": 0,
                "incompatible_versions": 0,
                "needs_testing": 0,
                "recent_tests": 0,
                "test_success_rate": 0.0,
            },
        }

        total_tests = 0
        passed_tests = 0
        recent_cutoff = datetime.now() - timedelta(days=7)

        for component, matrix in self.compatibility_matrices.items():
            component_report = {
                "supported_versions": matrix.supported_versions,
                "test_results": matrix.test_results,
                "known_issues": len(matrix.known_issues),
                "last_updated": matrix.last_updated.isoformat(),
                "recent_test_results": [],
            }

            # Count compatible/incompatible versions
            for version, status in matrix.test_results.items():
                if status == "passed":
                    report["summary"]["compatible_versions"] += 1
                elif status == "failed":
                    report["summary"]["incompatible_versions"] += 1
                else:
                    report["summary"]["needs_testing"] += 1

            # Add recent test results
            if component in self.test_results:
                for result in self.test_results[component]:
                    total_tests += 1
                    if result.status == TestStatus.PASSED:
                        passed_tests += 1

                    if result.timestamp >= recent_cutoff:
                        report["summary"]["recent_tests"] += 1
                        component_report["recent_test_results"].append(
                            {
                                "test_id": result.test_id,
                                "version": result.component_version,
                                "os_version": result.os_version,
                                "status": result.status.value,
                                "duration": result.duration,
                                "timestamp": result.timestamp.isoformat(),
                            }
                        )

            report["components"][component] = component_report

        # Calculate success rate
        if total_tests > 0:
            report["summary"]["test_success_rate"] = (passed_tests / total_tests) * 100

        return report
