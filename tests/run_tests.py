#!/usr/bin/env python3
"""
Test Runner for Qubinode Navigator Plugin Framework

Runs all unit and integration tests and provides a comprehensive report
as part of the testing and validation task in the implementation plan.
"""

import argparse
import os
import sys
import unittest
from io import StringIO
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def discover_and_run_tests(test_type="all", verbosity=2):
    """
    Discover and run tests

    Args:
        test_type: Type of tests to run ("unit", "integration", or "all")
        verbosity: Test output verbosity level

    Returns:
        tuple: (success, results)
    """

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    tests_dir = Path(__file__).parent

    if test_type in ["unit", "all"]:
        # Discover unit tests
        unit_tests = loader.discover(
            start_dir=str(tests_dir / "unit"),
            pattern="test_*.py",
            top_level_dir=str(tests_dir),
        )
        suite.addTests(unit_tests)

    if test_type in ["integration", "all"]:
        # Discover integration tests
        integration_tests = loader.discover(
            start_dir=str(tests_dir / "integration"),
            pattern="test_*.py",
            top_level_dir=str(tests_dir),
        )
        suite.addTests(integration_tests)

    # Run tests
    runner = unittest.TextTestRunner(
        verbosity=verbosity, stream=sys.stdout, buffer=True
    )

    result = runner.run(suite)

    return result.wasSuccessful(), result


def print_test_summary(result):
    """Print a summary of test results"""
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"  - {test}")

    if result.skipped:
        print(f"\nSKIPPED ({len(result.skipped)}):")
        for test, reason in result.skipped:
            print(f"  - {test}: {reason}")

    success_rate = (
        (
            (result.testsRun - len(result.failures) - len(result.errors))
            / result.testsRun
            * 100
        )
        if result.testsRun > 0
        else 0
    )
    print(f"\nSuccess Rate: {success_rate:.1f}%")

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED!")

    print("=" * 70)


def check_dependencies():
    """Check if all required dependencies are available"""
    print("Checking test dependencies...")

    required_modules = [
        "core.plugin_manager",
        "core.config_manager",
        "core.event_system",
        "core.base_plugin",
    ]

    missing_modules = []

    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            missing_modules.append(module)

    if missing_modules:
        print(f"\n❌ Missing required modules: {missing_modules}")
        return False

    print("\n✅ All dependencies available")
    return True


def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(
        description="Run Qubinode Navigator Plugin Framework Tests"
    )
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "all"],
        default="all",
        help="Type of tests to run (default: all)",
    )
    parser.add_argument(
        "--verbosity",
        type=int,
        choices=[0, 1, 2],
        default=2,
        help="Test output verbosity (default: 2)",
    )
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check dependencies before running tests",
    )

    args = parser.parse_args()

    print("Qubinode Navigator Plugin Framework Test Runner")
    print("=" * 70)

    if args.check_deps:
        if not check_dependencies():
            sys.exit(1)
        print()

    print(f"Running {args.type} tests...")
    print("-" * 70)

    success, result = discover_and_run_tests(args.type, args.verbosity)

    print_test_summary(result)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
