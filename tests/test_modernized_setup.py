#!/usr/bin/env python3

"""
Comprehensive Test Suite for Modernized Setup Script
====================================================

This test suite validates the modernized setup script (setup_modernized.sh)
across all supported environments and configurations.
"""

import subprocess
import sys
import os
from pathlib import Path


class ModernizedSetupTester:
    def __init__(self):
        self.test_results = []
        # Use QUBINODE_HOME environment variable or default to /opt
        qubinode_home = os.environ.get('QUBINODE_HOME', '/opt/qubinode_navigator')
        self.setup_script = Path(f"{qubinode_home}/setup_modernized.sh")

    def run_bash_function(self, function_name, setup_env=True):
        """Run a specific bash function from the setup script"""
        qubinode_home = os.environ.get('QUBINODE_HOME', '/opt/qubinode_navigator')
        
        cmd = f"source {self.setup_script}"
        if setup_env:
            cmd += " && get_os_version && detect_cloud_provider"
        cmd += f" && {function_name}"

        result = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True,
            text=True,
            cwd=qubinode_home,
        )
        return result

    def test_os_detection(self):
        """Test OS detection functionality"""
        print("🔍 Testing OS Detection...")

        result = self.run_bash_function("get_os_version", setup_env=False)

        success = result.returncode == 0 and "CENTOS10" in result.stdout and "CentOSStream10Plugin" in result.stdout

        self.test_results.append(
            {
                "test": "OS Detection",
                "success": success,
                "output": result.stdout,
                "error": result.stderr,
            }
        )

        print(f"   {'✅' if success else '❌'} OS Detection: {'PASSED' if success else 'FAILED'}")
        return success

    def test_cloud_detection(self):
        """Test cloud provider detection"""
        print("🌐 Testing Cloud Provider Detection...")

        result = self.run_bash_function("detect_cloud_provider", setup_env=False)

        success = result.returncode == 0 and ("Red Hat Demo Environment" in result.stdout or "REDHAT_DEMO" in result.stdout or "BARE_METAL" in result.stdout or "Bare Metal" in result.stdout)

        self.test_results.append(
            {
                "test": "Cloud Detection",
                "success": success,
                "output": result.stdout,
                "error": result.stderr,
            }
        )

        print(f"   {'✅' if success else '❌'} Cloud Detection: {'PASSED' if success else 'FAILED'}")
        return success

    def test_plugin_selection(self):
        """Test plugin selection logic"""
        print("🧠 Testing Plugin Selection...")

        result = self.run_bash_function("select_plugins")

        success = result.returncode == 0 and "CentOSStream10Plugin" in result.stdout

        self.test_results.append(
            {
                "test": "Plugin Selection",
                "success": success,
                "output": result.stdout,
                "error": result.stderr,
            }
        )

        print(f"   {'✅' if success else '❌'} Plugin Selection: {'PASSED' if success else 'FAILED'}")
        return success

    def test_plugin_framework_setup(self):
        """Test plugin framework setup"""
        print("🔧 Testing Plugin Framework Setup...")

        result = self.run_bash_function("setup_plugin_framework", setup_env=False)

        success = result.returncode == 0 and "Plugin framework ready" in result.stdout

        self.test_results.append(
            {
                "test": "Plugin Framework Setup",
                "success": success,
                "output": result.stdout,
                "error": result.stderr,
            }
        )

        print(f"   {'✅' if success else '❌'} Plugin Framework Setup: {'PASSED' if success else 'FAILED'}")
        return success

    def test_cli_integration(self):
        """Test CLI tool integration"""
        print("🔌 Testing CLI Integration...")
        
        qubinode_home = os.environ.get('QUBINODE_HOME', '/opt/qubinode_navigator')

        # Test CLI list command
        result = subprocess.run(
            ["python3", "qubinode_cli.py", "list"],
            capture_output=True,
            text=True,
            cwd=qubinode_home,
        )

        success = result.returncode == 0 and "CentOSStream10Plugin" in result.stdout and "Available Plugins" in result.stdout

        self.test_results.append(
            {
                "test": "CLI Integration",
                "success": success,
                "output": result.stdout,
                "error": result.stderr,
            }
        )

        print(f"   {'✅' if success else '❌'} CLI Integration: {'PASSED' if success else 'FAILED'}")
        return success

    def test_configuration_validation(self):
        """Test configuration file validation"""
        print("📋 Testing Configuration Validation...")
        
        qubinode_home = os.environ.get('QUBINODE_HOME', '/opt/qubinode_navigator')

        # Check if configuration files exist
        config_file = Path(f"{qubinode_home}/config/plugins.yml")
        tmp_config = Path("/tmp/config.yml")
        notouch_env = Path(f"{qubinode_home}/notouch.env")

        success = config_file.exists() and tmp_config.exists()

        self.test_results.append(
            {
                "test": "Configuration Validation",
                "success": success,
                "output": f"Config files: {config_file.exists()}, {tmp_config.exists()}, {notouch_env.exists()}",
                "error": "",
            }
        )

        print(f"   {'✅' if success else '❌'} Configuration Validation: {'PASSED' if success else 'FAILED'}")
        return success

    def test_environment_compatibility(self):
        """Test environment compatibility"""
        print("🖥️ Testing Environment Compatibility...")

        # Check Python version
        python_result = subprocess.run(["python3", "--version"], capture_output=True, text=True)

        # Check required packages
        packages_result = subprocess.run(
            [
                "python3",
                "-c",
                "import yaml, requests, hvac; print('All packages available')",
            ],
            capture_output=True,
            text=True,
        )

        success = python_result.returncode == 0 and "Python 3.12" in python_result.stdout and packages_result.returncode == 0

        self.test_results.append(
            {
                "test": "Environment Compatibility",
                "success": success,
                "output": f"Python: {python_result.stdout.strip()}, Packages: {packages_result.stdout.strip()}",
                "error": packages_result.stderr,
            }
        )

        print(f"   {'✅' if success else '❌'} Environment Compatibility: {'PASSED' if success else 'FAILED'}")
        return success

    def run_all_tests(self):
        """Run all tests and generate report"""
        print("🧪 Starting Comprehensive Test Suite for Modernized Setup")
        print("=" * 60)

        tests = [
            self.test_os_detection,
            self.test_cloud_detection,
            self.test_plugin_selection,
            self.test_plugin_framework_setup,
            self.test_cli_integration,
            self.test_configuration_validation,
            self.test_environment_compatibility,
        ]

        passed = 0
        total = len(tests)

        for test in tests:
            if test():
                passed += 1

        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

        if passed == total:
            print("🎉 All tests PASSED! Modernized setup is ready for deployment.")
            return True
        else:
            print("⚠️ Some tests FAILED. Review the results above.")
            return False

    def generate_detailed_report(self):
        """Generate detailed test report"""
        print("\n📋 Detailed Test Report")
        print("=" * 60)

        for result in self.test_results:
            print(f"\n🔍 {result['test']}")
            print(f"Status: {'✅ PASSED' if result['success'] else '❌ FAILED'}")
            if result["output"]:
                print(f"Output: {result['output'][:200]}...")
            if result["error"]:
                print(f"Error: {result['error'][:200]}...")


if __name__ == "__main__":
    tester = ModernizedSetupTester()

    success = tester.run_all_tests()
    tester.generate_detailed_report()

    sys.exit(0 if success else 1)
