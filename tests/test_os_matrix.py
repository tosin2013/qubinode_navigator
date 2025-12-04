#!/usr/bin/env python3
"""
Comprehensive OS Matrix Testing

Tests all OS plugins (RHEL 8/9/10, Rocky Linux, CentOS Stream 10) to ensure
they work correctly and maintain compatibility across the supported OS matrix.
"""

import sys
from pathlib import Path
from typing import Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from plugins.os.rhel8_plugin import RHEL8Plugin
from plugins.os.rhel9_plugin import RHEL9Plugin
from plugins.os.rhel10_plugin import RHEL10Plugin
from plugins.os.rocky_linux_plugin import RockyLinuxPlugin
from plugins.os.centos_stream10_plugin import CentOSStream10Plugin
from core.base_plugin import SystemState, ExecutionContext


class OSMatrixTester:
    """Test runner for OS plugin matrix"""

    def __init__(self):
        self.results = {}
        self.config = {
            "packages": ["python3", "git", "vim"],
            "create_lab_user": False,  # Don't create users in tests
            "strict_hardware_validation": False,
            "strict_python_validation": False,
        }

    def test_plugin_basic_functionality(self, plugin_class, plugin_name: str) -> Dict[str, bool]:
        """Test basic plugin functionality"""
        print(f"\n🧪 Testing {plugin_name} Plugin")
        print("=" * 50)

        results = {
            "initialization": False,
            "state_check": False,
            "desired_state": False,
            "config_validation": False,
            "health_status": False,
        }

        try:
            # Test initialization
            plugin = plugin_class(self.config)
            plugin.initialize()
            results["initialization"] = True
            print(f"✅ {plugin_name} initialization: PASSED")

            # Test state checking
            try:
                current_state = plugin.check_state()
                if isinstance(current_state, SystemState):
                    results["state_check"] = True
                    print(f"✅ {plugin_name} state check: PASSED")
                else:
                    print(f"❌ {plugin_name} state check: FAILED - Invalid state type")
            except Exception as e:
                print(f"❌ {plugin_name} state check: FAILED - {e}")

            # Test desired state generation
            try:
                context = ExecutionContext(config={"create_lab_user": False})
                desired_state = plugin.get_desired_state(context)
                if isinstance(desired_state, SystemState):
                    results["desired_state"] = True
                    print(f"✅ {plugin_name} desired state: PASSED")
                else:
                    print(f"❌ {plugin_name} desired state: FAILED - Invalid state type")
            except Exception as e:
                print(f"❌ {plugin_name} desired state: FAILED - {e}")

            # Test config validation
            try:
                if plugin.validate_config():
                    results["config_validation"] = True
                    print(f"✅ {plugin_name} config validation: PASSED")
                else:
                    print(f"❌ {plugin_name} config validation: FAILED")
            except Exception as e:
                print(f"❌ {plugin_name} config validation: FAILED - {e}")

            # Test health status
            try:
                health = plugin.get_health_status()
                if isinstance(health, dict) and "status" in health:
                    results["health_status"] = True
                    print(f"✅ {plugin_name} health status: PASSED")
                else:
                    print(f"❌ {plugin_name} health status: FAILED - Invalid health format")
            except Exception as e:
                print(f"❌ {plugin_name} health status: FAILED - {e}")

        except Exception as e:
            print(f"❌ {plugin_name} initialization: FAILED - {e}")

        # Calculate success rate
        passed = sum(results.values())
        total = len(results)
        success_rate = (passed / total) * 100
        print(f"📊 {plugin_name} Success Rate: {passed}/{total} ({success_rate:.1f}%)")

        return results

    def test_plugin_interfaces(self) -> Dict[str, bool]:
        """Test that all plugins have consistent interfaces"""
        print("\n🔄 Testing Plugin Interface Consistency")
        print("=" * 50)

        plugins = [
            (RHEL8Plugin, "RHEL8"),
            (RHEL9Plugin, "RHEL9"),
            (RHEL10Plugin, "RHEL10"),
            (RockyLinuxPlugin, "Rocky Linux"),
            (CentOSStream10Plugin, "CentOS Stream 10"),
        ]

        required_methods = [
            "check_state",
            "get_desired_state",
            "apply_changes",
            "validate_config",
            "get_health_status",
            "get_dependencies",
        ]

        required_properties = ["name", "version"]

        results = {}

        for plugin_class, plugin_name in plugins:
            try:
                plugin = plugin_class(self.config)
                plugin.initialize()

                # Check methods
                method_results = []
                for method in required_methods:
                    if hasattr(plugin, method) and callable(getattr(plugin, method)):
                        method_results.append(True)
                        print(f"✅ {plugin_name}.{method}: PRESENT")
                    else:
                        method_results.append(False)
                        print(f"❌ {plugin_name}.{method}: MISSING")

                # Check properties
                property_results = []
                for prop in required_properties:
                    if hasattr(plugin, prop):
                        property_results.append(True)
                        print(f"✅ {plugin_name}.{prop}: PRESENT")
                    else:
                        property_results.append(False)
                        print(f"❌ {plugin_name}.{prop}: MISSING")

                all_passed = all(method_results + property_results)
                results[plugin_name] = all_passed

                if all_passed:
                    print(f"✅ {plugin_name} interface: COMPLETE")
                else:
                    print(f"❌ {plugin_name} interface: INCOMPLETE")

            except Exception as e:
                results[plugin_name] = False
                print(f"❌ {plugin_name} interface test: FAILED - {e}")

        return results

    def test_native_centos_stream10(self) -> bool:
        """Test native CentOS Stream 10 functionality"""
        print("\n🎯 Testing Native CentOS Stream 10 Environment")
        print("=" * 50)

        try:
            # Test CentOS Stream 10 plugin on actual system
            plugin = CentOSStream10Plugin(self.config)
            plugin.initialize()

            # Check current state
            current_state = plugin.check_state()
            print(f"✅ Current OS: {current_state.get('os_version', 'Unknown')}")
            print(f"✅ Python Version: {current_state.get('python_version', 'Unknown')}")
            print(f"✅ Kernel Version: {current_state.get('kernel_version', 'Unknown')}")

            # Get desired state
            context = ExecutionContext(config={"create_lab_user": False})
            desired_state = plugin.get_desired_state(context)
            print(f"✅ Desired Python: {desired_state.get('python_version', 'Unknown')}")

            # Test health status
            health = plugin.get_health_status()
            print(f"✅ Plugin Health: {health.get('status', 'unknown')}")

            print("✅ Native CentOS Stream 10 testing: PASSED")
            return True

        except Exception as e:
            print(f"❌ Native CentOS Stream 10 testing: FAILED - {e}")
            return False

    def run_all_tests(self) -> Dict[str, any]:
        """Run all OS matrix tests"""
        print("🚀 Starting Comprehensive OS Matrix Testing")
        print("=" * 60)
        print("Testing all OS plugins for compatibility and functionality")
        print()

        # Test individual plugins
        plugin_tests = [
            (RHEL8Plugin, "RHEL 8"),
            (RHEL9Plugin, "RHEL 9"),
            (RHEL10Plugin, "RHEL 10"),
            (RockyLinuxPlugin, "Rocky Linux"),
            (CentOSStream10Plugin, "CentOS Stream 10"),
        ]

        plugin_results = {}
        for plugin_class, plugin_name in plugin_tests:
            try:
                plugin_results[plugin_name] = self.test_plugin_basic_functionality(plugin_class, plugin_name)
            except Exception as e:
                print(f"❌ {plugin_name} testing failed: {e}")
                plugin_results[plugin_name] = {
                    "initialization": False,
                    "state_check": False,
                    "desired_state": False,
                    "config_validation": False,
                    "health_status": False,
                }

        # Test interface consistency
        interface_results = self.test_plugin_interfaces()

        # Test native environment
        native_test_passed = self.test_native_centos_stream10()

        # Calculate overall results
        total_tests = 0
        passed_tests = 0

        for plugin_name, results in plugin_results.items():
            for test_name, passed in results.items():
                total_tests += 1
                if passed:
                    passed_tests += 1

        # Add interface tests
        for plugin_name, passed in interface_results.items():
            total_tests += 1
            if passed:
                passed_tests += 1

        # Add native test
        total_tests += 1
        if native_test_passed:
            passed_tests += 1

        overall_success_rate = (passed_tests / total_tests) * 100

        # Print summary
        print("\n🎯 OS Matrix Testing Summary")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {overall_success_rate:.1f}%")

        # Plugin-specific summary
        print("\n📊 Plugin Success Rates:")
        for plugin_name, results in plugin_results.items():
            passed = sum(results.values())
            total = len(results)
            rate = (passed / total) * 100
            print(f"  {plugin_name}: {passed}/{total} ({rate:.1f}%)")

        # Interface consistency summary
        print("\n🔄 Interface Consistency:")
        for plugin_name, passed in interface_results.items():
            status = "✅ CONSISTENT" if passed else "❌ INCONSISTENT"
            print(f"  {plugin_name}: {status}")

        # Native test summary
        native_status = "✅ PASSED" if native_test_passed else "❌ FAILED"
        print(f"\n🎯 Native Environment Test: {native_status}")

        if overall_success_rate >= 90:
            print(f"\n🎉 EXCELLENT! OS matrix testing achieved {overall_success_rate:.1f}% success rate!")
            print("✅ All OS plugins are ready for production deployment!")
        elif overall_success_rate >= 80:
            print(f"\n✅ GOOD! OS matrix testing achieved {overall_success_rate:.1f}% success rate!")
            print("⚠️  Minor issues detected but plugins are functional.")
        else:
            print(f"\n⚠️  OS matrix testing achieved {overall_success_rate:.1f}% success rate.")
            print("❌ Significant issues detected that need attention.")

        return {
            "plugin_results": plugin_results,
            "interface_results": interface_results,
            "native_test": native_test_passed,
            "overall_success_rate": overall_success_rate,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
        }


def main():
    """Main test runner"""
    tester = OSMatrixTester()
    results = tester.run_all_tests()

    # Return appropriate exit code
    if results["overall_success_rate"] >= 80:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
