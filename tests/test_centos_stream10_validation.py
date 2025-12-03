#!/usr/bin/env python3
"""
CentOS Stream 10 Native Validation Test

Tests the native capabilities of our CentOS Stream 10 environment
to validate RHEL 10/CentOS 10 plugin development advantages.
"""

import sys
import platform
import subprocess


def test_python312_native():
    """Test native Python 3.12 capabilities"""
    print("🐍 Testing Native Python 3.12 Capabilities")
    print("=" * 50)

    version = sys.version_info
    print(f"✅ Python Version: {version.major}.{version.minor}.{version.micro}")
    print(f"✅ Platform: {platform.platform()}")
    print(f"✅ Architecture: {platform.machine()}")

    # Test Python 3.12 features
    try:
        # Test f-string improvements
        name = "CentOS Stream 10"
        version_str = f"{version.major}.{version.minor}"
        result = f"Running on {name} with Python {version_str}"
        print(f"✅ F-string test: {result}")

        # Test pathlib (should work well in 3.12)
        from pathlib import Path

        current_dir = Path.cwd()
        print(f"✅ Pathlib test: {current_dir}")

        return True
    except Exception as e:
        print(f"❌ Python test failed: {e}")
        return False


def test_x86_64_v3_microarchitecture():
    """Test x86_64-v3 microarchitecture requirements"""
    print("\n🔍 Testing x86_64-v3 Microarchitecture")
    print("=" * 50)

    try:
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read()

        # Required flags for x86_64-v3
        required_flags = ["avx", "avx2", "bmi1", "bmi2", "f16c", "fma", "abm", "movbe"]

        found_flags = []
        missing_flags = []

        for flag in required_flags:
            if flag in cpuinfo:
                found_flags.append(flag)
                print(f"✅ {flag}")
            else:
                missing_flags.append(flag)
                print(f"❌ {flag}")

        if not missing_flags:
            print("✅ All x86_64-v3 requirements satisfied!")
            return True
        else:
            print(f"❌ Missing flags: {', '.join(missing_flags)}")
            return False

    except Exception as e:
        print(f"❌ Architecture test failed: {e}")
        return False


def test_dnf_capabilities():
    """Test DNF package management capabilities"""
    print("\n📦 Testing DNF Package Management")
    print("=" * 50)

    try:
        # Test DNF version
        result = subprocess.run(["dnf", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version_line = result.stdout.strip().split("\n")[0]
            print(f"✅ DNF Version: {version_line}")
        else:
            print("❌ DNF version check failed")
            return False

        # Test DNF modularity (should be removed in Stream 10)
        result = subprocess.run(
            ["dnf", "module", "list"], capture_output=True, text=True
        )
        if "No such command: module" in result.stderr or result.returncode != 0:
            print("✅ DNF modularity removed (as expected in Stream 10)")
        else:
            print("⚠️  DNF modularity still present")

        # Test package search (non-destructive)
        result = subprocess.run(
            ["dnf", "search", "python3", "--quiet"], capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✅ Package search functionality working")
        else:
            print("❌ Package search failed")
            return False

        return True

    except Exception as e:
        print(f"❌ DNF test failed: {e}")
        return False


def test_container_capabilities():
    """Test container platform capabilities"""
    print("\n🐳 Testing Container Platform")
    print("=" * 50)

    try:
        # Test Podman
        result = subprocess.run(["podman", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ {version}")
        else:
            print("❌ Podman not available")
            return False

        # Test Buildah
        result = subprocess.run(
            ["buildah", "--version"], capture_output=True, text=True
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ {version}")
        else:
            print("⚠️  Buildah not available")

        return True

    except Exception as e:
        print(f"❌ Container test failed: {e}")
        return False


def main():
    """Run all validation tests"""
    print("🚀 CentOS Stream 10 Native Validation Test")
    print("=" * 60)
    print("Testing native development environment advantages")
    print("for RHEL 10/CentOS 10 plugin development")
    print()

    tests = [
        test_python312_native,
        test_x86_64_v3_microarchitecture,
        test_dnf_capabilities,
        test_container_capabilities,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)

    print("\n🎯 Validation Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)

    print(f"Tests Passed: {passed}/{total}")

    if passed == total:
        print("✅ ALL TESTS PASSED - Native CentOS Stream 10 environment ready!")
        print("🚀 RHEL 10/CentOS 10 plugin development can proceed with confidence!")
    else:
        print("⚠️  Some tests failed - review requirements")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
