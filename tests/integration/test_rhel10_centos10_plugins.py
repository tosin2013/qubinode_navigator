#!/usr/bin/env python3
"""
Integration tests for RHEL 10 and CentOS Stream 10 plugins

Tests the functionality of both RHEL 10 and CentOS Stream 10 plugins
on the native CentOS Stream 10 development environment.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.base_plugin import ExecutionContext, PluginStatus, SystemState
from plugins.os.centos_stream10_plugin import CentOSStream10Plugin
from plugins.os.rhel10_plugin import RHEL10Plugin


class TestRHEL10Plugin(unittest.TestCase):
    """Test RHEL 10 plugin functionality"""

    def setUp(self):
        """Set up test environment"""
        self.config = {
            "packages": ["python3", "git", "vim"],
            "create_lab_user": True,
            "strict_hardware_validation": False,
            "strict_python_validation": False,
        }

        # Mock the OS detection to pass initialization
        with patch.object(
            RHEL10Plugin, "_is_rhel10_or_centos10", return_value=True
        ), patch.object(RHEL10Plugin, "_validate_microarchitecture", return_value=True):
            self.plugin = RHEL10Plugin(self.config)
            self.plugin.initialize()

    def tearDown(self):
        """Clean up test environment"""
        pass

    def test_plugin_initialization(self):
        """Test plugin initializes correctly"""
        self.assertEqual(self.plugin.name, "RHEL10Plugin")
        self.assertEqual(self.plugin.__version__, "1.0.0")
        self.assertIsInstance(self.plugin.packages, list)
        self.assertIn("python3", self.plugin.packages)

    def test_os_detection(self):
        """Test OS detection functionality"""
        # Test with mocked /etc/os-release content
        rhel10_content = 'ID="rhel"\nVERSION_ID="10.0"'
        centos10_content = 'ID="centos"\nVERSION_ID="10"\nNAME="CentOS Stream"'

        with patch("builtins.open", unittest.mock.mock_open(read_data=rhel10_content)):
            self.assertTrue(self.plugin._is_rhel10_or_centos10())

        with patch(
            "builtins.open", unittest.mock.mock_open(read_data=centos10_content)
        ):
            self.assertTrue(self.plugin._is_rhel10_or_centos10())

        # Test with non-RHEL/CentOS content
        other_content = 'ID="ubuntu"\nVERSION_ID="22.04"'
        with patch("builtins.open", unittest.mock.mock_open(read_data=other_content)):
            self.assertFalse(self.plugin._is_rhel10_or_centos10())

    def test_microarchitecture_validation(self):
        """Test x86_64-v3 microarchitecture validation"""
        # Test with all required flags present
        cpuinfo_good = """
processor	: 0
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx pdpe1gb rdtscp lm constant_tsc rep_good nopl xtopology nonstop_tsc cpuid tsc_known_freq pni pclmulqdq vmx ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm lzcnt 3dnowprefetch cpuid_fault epb invpcid_single pti ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid ept_ad fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt dtherm ida arat pln pts
"""

        with patch("builtins.open", unittest.mock.mock_open(read_data=cpuinfo_good)):
            self.assertTrue(self.plugin._validate_microarchitecture())

        # Test with missing required flags
        cpuinfo_bad = """
processor	: 0
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx pdpe1gb rdtscp lm constant_tsc
"""

        with patch("builtins.open", unittest.mock.mock_open(read_data=cpuinfo_bad)):
            self.assertFalse(self.plugin._validate_microarchitecture())

    def test_check_state(self):
        """Test system state checking"""
        with patch.object(
            self.plugin, "_get_os_version", return_value="CentOS Stream release 10"
        ), patch.object(
            self.plugin, "_get_python_version", return_value=(3, 12)
        ), patch.object(
            self.plugin, "_get_kernel_version", return_value=(6, 12)
        ), patch.object(
            self.plugin, "_get_installed_packages", return_value=["python3", "git"]
        ), patch.object(
            self.plugin, "_is_service_enabled", return_value=True
        ), patch.object(
            self.plugin, "_is_service_active", return_value=True
        ), patch.object(
            self.plugin, "_user_exists", return_value=False
        ), patch.object(
            self.plugin, "_validate_microarchitecture", return_value=True
        ):

            state = self.plugin.check_state()
            self.assertIsInstance(state, SystemState)
            self.assertEqual(state.get("python_version"), (3, 12))
            self.assertEqual(state.get("kernel_version"), (6, 12))
            self.assertTrue(state.get("firewalld_enabled"))
            self.assertTrue(state.get("microarch_valid"))

    def test_get_desired_state(self):
        """Test desired state generation"""
        context = ExecutionContext(config={"create_lab_user": True})

        desired_state = self.plugin.get_desired_state(context)
        self.assertIsInstance(desired_state, SystemState)
        self.assertEqual(desired_state.get("python_version"), (3, 12))
        self.assertEqual(desired_state.get("kernel_version"), (6, 0))
        self.assertTrue(desired_state.get("firewalld_enabled"))
        self.assertTrue(desired_state.get("lab_user_exists"))
        self.assertTrue(desired_state.get("microarch_valid"))

    def test_validate_config(self):
        """Test configuration validation"""
        self.assertTrue(self.plugin.validate_config())

        # Test with invalid config
        self.plugin.config["packages"] = "not-a-list"
        self.assertFalse(self.plugin.validate_config())

    def test_get_health_status(self):
        """Test health status reporting"""
        with patch.object(
            self.plugin, "_is_rhel10_or_centos10", return_value=True
        ), patch.object(
            self.plugin, "_validate_microarchitecture", return_value=True
        ), patch.object(
            self.plugin, "_get_python_version", return_value=(3, 12)
        ), patch.object(
            self.plugin, "_get_kernel_version", return_value=(6, 12)
        ):

            health = self.plugin.get_health_status()
            self.assertIsInstance(health, dict)
            self.assertTrue(health["os_compatible"])
            self.assertTrue(health["microarch_valid"])
            self.assertEqual(health["python_version"], (3, 12))


class TestCentOSStream10Plugin(unittest.TestCase):
    """Test CentOS Stream 10 plugin functionality"""

    def setUp(self):
        """Set up test environment"""
        self.config = {
            "packages": ["python3", "git", "vim", "podman"],
            "create_lab_user": True,
            "strict_hardware_validation": False,
            "strict_python_validation": False,
        }

        # Mock the OS detection to pass initialization
        with patch.object(
            CentOSStream10Plugin, "_is_centos_stream10", return_value=True
        ), patch.object(
            CentOSStream10Plugin, "_validate_x86_64_v3_microarchitecture"
        ), patch.object(
            CentOSStream10Plugin, "_validate_python312_compatibility"
        ):
            self.plugin = CentOSStream10Plugin(self.config)
            self.plugin.initialize()

    def tearDown(self):
        """Clean up test environment"""
        pass

    def test_plugin_initialization(self):
        """Test plugin initializes correctly"""
        self.assertEqual(self.plugin.name, "CentOSStream10Plugin")
        self.assertEqual(self.plugin.__version__, "1.0.0")
        self.assertIsInstance(self.plugin.packages, list)
        # Check that the plugin uses config packages when provided
        self.assertIn("python3", self.plugin.packages)
        self.assertIn("podman", self.plugin.packages)
        # Note: container-tools is in default packages, not config packages

    def test_os_detection(self):
        """Test CentOS Stream 10 detection"""
        # Test with CentOS Stream 10 content
        centos10_content = 'ID="centos"\nVERSION_ID="10"\nNAME="CentOS Stream"'

        with patch(
            "builtins.open", unittest.mock.mock_open(read_data=centos10_content)
        ):
            self.assertTrue(self.plugin._is_centos_stream10())

        # Test with alternative format
        centos10_alt = "CentOS Stream release 10"
        with patch("builtins.open", unittest.mock.mock_open(read_data=centos10_alt)):
            self.assertTrue(self.plugin._is_centos_stream10())

        # Test with non-CentOS content
        other_content = 'ID="rhel"\nVERSION_ID="9.0"'
        with patch("builtins.open", unittest.mock.mock_open(read_data=other_content)):
            self.assertFalse(self.plugin._is_centos_stream10())

    def test_check_state(self):
        """Test system state checking"""
        with patch.object(
            self.plugin, "_get_os_version", return_value="CentOS Stream release 10"
        ), patch.object(
            self.plugin, "_get_python_version", return_value=(3, 12)
        ), patch.object(
            self.plugin, "_get_kernel_version", return_value=(6, 12)
        ), patch.object(
            self.plugin,
            "_get_installed_packages",
            return_value=["python3", "git", "podman"],
        ), patch.object(
            self.plugin, "_is_service_enabled", return_value=True
        ), patch.object(
            self.plugin, "_is_service_active", return_value=True
        ), patch.object(
            self.plugin, "_user_exists", return_value=False
        ):

            state = self.plugin.check_state()
            self.assertIsInstance(state, SystemState)
            self.assertEqual(state.get("python_version"), (3, 12))
            self.assertEqual(state.get("kernel_version"), (6, 12))
            self.assertTrue(state.get("firewalld_enabled"))

    def test_get_desired_state(self):
        """Test desired state generation"""
        context = ExecutionContext(config={"create_lab_user": True})

        desired_state = self.plugin.get_desired_state(context)
        self.assertIsInstance(desired_state, SystemState)
        self.assertEqual(desired_state.get("python_version"), (3, 12))
        self.assertEqual(desired_state.get("kernel_version"), (6, 0))
        self.assertTrue(desired_state.get("firewalld_enabled"))
        self.assertTrue(desired_state.get("lab_user_exists"))

    def test_validate_config(self):
        """Test configuration validation"""
        self.assertTrue(self.plugin.validate_config())

        # Test with invalid config
        self.plugin.config["packages"] = "not-a-list"
        self.assertFalse(self.plugin.validate_config())


class TestPluginIntegration(unittest.TestCase):
    """Integration tests for both plugins"""

    def test_plugin_compatibility(self):
        """Test that both plugins can coexist and have compatible interfaces"""
        config = {
            "packages": ["python3", "git"],
            "create_lab_user": True,
            "strict_hardware_validation": False,
            "strict_python_validation": False,
        }

        # No need for temporary config file

        try:
            # Mock initialization for both plugins
            with patch.object(
                RHEL10Plugin, "_is_rhel10_or_centos10", return_value=True
            ), patch.object(
                RHEL10Plugin, "_validate_microarchitecture", return_value=True
            ), patch.object(
                CentOSStream10Plugin, "_is_centos_stream10", return_value=True
            ), patch.object(
                CentOSStream10Plugin, "_validate_x86_64_v3_microarchitecture"
            ), patch.object(
                CentOSStream10Plugin, "_validate_python312_compatibility"
            ):

                rhel10_plugin = RHEL10Plugin(config)
                rhel10_plugin.initialize()
                centos10_plugin = CentOSStream10Plugin(config)
                centos10_plugin.initialize()

                # Both plugins should have the same interface
                self.assertTrue(hasattr(rhel10_plugin, "check_state"))
                self.assertTrue(hasattr(centos10_plugin, "check_state"))

                self.assertTrue(hasattr(rhel10_plugin, "get_desired_state"))
                self.assertTrue(hasattr(centos10_plugin, "get_desired_state"))

                self.assertTrue(hasattr(rhel10_plugin, "apply_changes"))
                self.assertTrue(hasattr(centos10_plugin, "apply_changes"))

                # Both should have no dependencies
                self.assertEqual(rhel10_plugin.get_dependencies(), [])
                self.assertEqual(centos10_plugin.get_dependencies(), [])

        finally:
            pass


def run_native_tests():
    """Run tests that can execute on the native CentOS Stream 10 environment"""
    print("🧪 Running Native CentOS Stream 10 Plugin Tests")
    print("=" * 60)

    # Test actual plugin functionality on native system
    config = {
        "packages": ["python3", "git"],
        "create_lab_user": False,  # Don't actually create users in tests
        "strict_hardware_validation": False,
        "strict_python_validation": False,
    }

    try:
        # Test CentOS Stream 10 plugin on native system
        print("\n🎯 Testing CentOS Stream 10 Plugin on Native System")
        centos10_plugin = CentOSStream10Plugin(config)
        centos10_plugin.initialize()

        # Check current state
        current_state = centos10_plugin.check_state()
        print(f"✅ Current OS: {current_state.get('os_version')}")
        print(f"✅ Python Version: {current_state.get('python_version')}")
        print(f"✅ Kernel Version: {current_state.get('kernel_version')}")

        # Get desired state
        context = ExecutionContext(config={"create_lab_user": False})
        desired_state = centos10_plugin.get_desired_state(context)
        print(f"✅ Desired Python: {desired_state.get('python_version')}")

        # Test health status
        health = centos10_plugin.get_health_status()
        print(f"✅ Plugin Health: {health.get('status', 'unknown')}")

        print("✅ Native CentOS Stream 10 plugin tests completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Native test failed: {e}")
        return False
    finally:
        pass


if __name__ == "__main__":
    # Run unit tests
    print("🧪 Running RHEL 10/CentOS Stream 10 Plugin Tests")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestRHEL10Plugin))
    suite.addTests(loader.loadTestsFromTestCase(TestCentOSStream10Plugin))
    suite.addTests(loader.loadTestsFromTestCase(TestPluginIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Run native tests if unit tests pass
    if result.wasSuccessful():
        print("\n" + "=" * 60)
        native_success = run_native_tests()

        if native_success:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ RHEL 10/CentOS Stream 10 plugins are ready for production!")
        else:
            print("\n⚠️  Native tests failed")
            sys.exit(1)
    else:
        print(
            f"\n❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)"
        )
        sys.exit(1)
