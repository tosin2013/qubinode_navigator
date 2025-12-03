#!/usr/bin/env python3
"""
Qubinode Navigator Update Validation CLI

Command-line interface for running automated update validation tests,
managing test environments, and generating validation reports.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.update_manager import UpdateDetector, UpdateInfo
from core.update_validator import UpdateValidator, ValidationResult, ValidationStage


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def print_validation_summary(results: Dict[str, Any]):
    """Print formatted validation results summary"""
    print("\n" + "=" * 80)
    print("🧪 UPDATE VALIDATION REPORT")
    print("=" * 80)

    # Basic info
    print(f"\n📊 VALIDATION SUMMARY")
    print(f"   Suite ID: {results['suite_id']}")
    print(f"   Container: {results['container_name']}")
    print(f"   Duration: {results['duration']:.2f}s")
    print(f"   Overall Result: {results['overall_result'].upper()}")

    # Test summary
    summary = results["summary"]
    print(f"\n📈 TEST STATISTICS")
    print(f"   Total Tests: {summary['total_tests']}")
    print(f"   ✅ Passed: {summary['passed']}")
    print(f"   ❌ Failed: {summary['failed']}")
    print(f"   ⚠️  Warnings: {summary['warnings']}")
    print(f"   🚫 Errors: {summary['errors']}")
    print(f"   ⏭️  Skipped: {summary['skipped']}")

    # Stage results
    print(f"\n🔄 STAGE RESULTS")
    for stage_name, stage_data in results["stages"].items():
        stage_icon = "✅" if stage_data["passed"] else "❌"
        print(
            f"   {stage_icon} {stage_name.replace('_', ' ').title()}: {stage_data['test_count']} tests"
        )

        # Show failed tests
        failed_tests = [
            t for t in stage_data["tests"] if t["status"] in ["failed", "error"]
        ]
        if failed_tests:
            for test in failed_tests:
                print(
                    f"      ❌ {test['test_id']}: {test.get('error', 'Unknown error')}"
                )


def print_test_details(results: Dict[str, Any]):
    """Print detailed test results"""
    print("\n" + "=" * 80)
    print("🔍 DETAILED TEST RESULTS")
    print("=" * 80)

    for stage_name, stage_data in results["stages"].items():
        print(f"\n📋 {stage_name.replace('_', ' ').title()}")
        print("-" * 60)

        for test in stage_data["tests"]:
            status_icon = {
                "passed": "✅",
                "failed": "❌",
                "warning": "⚠️",
                "error": "🚫",
                "skipped": "⏭️",
            }.get(test["status"], "❓")

            print(f"\n{status_icon} Test: {test['test_id']}")
            print(f"   Status: {test['status'].upper()}")
            print(f"   Duration: {test['duration']:.2f}s")

            if test.get("output"):
                print(f"   Output: {test['output'][:100]}...")

            if test.get("error"):
                print(f"   Error: {test['error']}")


async def validate_command(args):
    """Execute update validation command"""
    config = {
        "test_environment_dir": args.test_dir,
        "container_runtime": args.runtime,
        "base_image": args.base_image,
        "parallel_tests": args.parallel,
        "validation_timeout": args.timeout,
    }

    validator = UpdateValidator(config)

    # Create update info from command line arguments
    update_info = UpdateInfo(
        component_type=args.component_type,
        component_name=args.component,
        current_version=args.current_version,
        available_version=args.target_version,
        severity="medium",
        description=f"Manual validation of {args.component} update",
        release_date=datetime.now().strftime("%Y-%m-%d"),
    )

    print(
        f"🧪 Starting validation: {args.component} {args.current_version} → {args.target_version}"
    )

    try:
        # Create validation suite
        suite = await validator.create_validation_suite(update_info)
        print(f"📋 Created validation suite with {len(suite.tests)} tests")

        # Run validation
        results = await validator.run_validation_suite(suite.suite_id)

        # Display results
        if args.format == "json":
            print(json.dumps(results, indent=2, default=str))
        else:
            print_validation_summary(results)

            if args.detailed:
                print_test_details(results)

        # Save results if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {args.output}")

        # Return appropriate exit code
        if results["overall_result"] == "passed":
            return 0
        elif results["overall_result"] in ["warning", "skipped"]:
            return 1
        else:
            return 2

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return 3


async def batch_command(args):
    """Execute batch validation command"""
    config = {
        "test_environment_dir": args.test_dir,
        "container_runtime": args.runtime,
        "base_image": args.base_image,
        "parallel_tests": args.parallel,
        "validation_timeout": args.timeout,
    }

    validator = UpdateValidator(config)
    update_detector = UpdateDetector(config)

    print("🔍 Detecting available updates...")

    try:
        # Get available updates
        updates = await update_detector.check_all_updates()

        if not updates:
            print("✅ No updates available for validation")
            return 0

        print(f"📦 Found {len(updates)} updates to validate")

        # Create update batch
        from core.update_manager import UpdateBatch

        batch = UpdateBatch(
            batch_id=f"validation_batch_{int(datetime.now().timestamp())}",
            batch_type="validation",
            updates=updates[: args.max_updates],  # Limit number of updates
            created_at=datetime.now(),
        )

        # Run batch validation
        results = await validator.validate_update_batch(batch)

        # Display results
        if args.format == "json":
            print(json.dumps(results, indent=2, default=str))
        else:
            print("\n" + "=" * 80)
            print("📦 BATCH VALIDATION RESULTS")
            print("=" * 80)

            print(f"\n📊 BATCH SUMMARY")
            print(f"   Batch ID: {results['batch_id']}")
            print(f"   Batch Type: {results['batch_type']}")
            print(f"   Overall Status: {results['overall_status'].upper()}")
            print(f"   Updates Validated: {len(results['update_results'])}")

            print(f"\n🔍 UPDATE RESULTS")
            for component, result in results["update_results"].items():
                status_icon = "✅" if result["overall_result"] == "passed" else "❌"
                print(f"   {status_icon} {component}: {result['overall_result']}")
                print(
                    f"      Tests: {result['summary']['total_tests']} total, {result['summary']['passed']} passed"
                )

        # Save results if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {args.output}")

        # Return appropriate exit code
        if results["overall_status"] == "passed":
            return 0
        elif results["overall_status"] == "warning":
            return 1
        else:
            return 2

    except Exception as e:
        print(f"❌ Batch validation failed: {e}")
        return 3


async def list_command(args):
    """List available validation tests"""
    config = {}
    validator = UpdateValidator(config)

    print("📋 Available validation test templates:")

    for test_id, test_config in validator.test_templates.items():
        print(f"\n🧪 {test_id}")
        print(f"   Name: {test_config['name']}")
        print(f"   Type: {test_config['type']}")
        print(f"   Stage: {test_config['stage']}")
        print(f"   Critical: {test_config['critical']}")
        print(f"   Timeout: {test_config['timeout']}s")

        if "component_filter" in test_config:
            print(f"   Components: {', '.join(test_config['component_filter'])}")

    print(f"\n📊 Environment configurations:")
    for env_id, env_config in validator.environment_configs.items():
        print(f"\n🏗️  {env_id}")
        print(f"   Base Image: {env_config['base_image']}")
        print(f"   Packages: {len(env_config.get('packages', []))} packages")
        print(f"   Services: {len(env_config.get('services', []))} services")

    return 0


async def cleanup_command(args):
    """Cleanup test environments"""
    config = {"container_runtime": args.runtime}

    validator = UpdateValidator(config)

    print("🧹 Cleaning up test environments...")

    try:
        await validator.cleanup_all_containers()
        print("✅ Cleanup completed successfully")
        return 0

    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return 1


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Qubinode Navigator Update Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate single component update
  python3 update_validator.py validate podman --current-version 4.9.0 --target-version 5.0.0
  
  # Run batch validation for all available updates
  python3 update_validator.py batch --max-updates 5
  
  # List available test templates
  python3 update_validator.py list
  
  # Cleanup test environments
  python3 update_validator.py cleanup
        """,
    )

    parser.add_argument(
        "--test-dir",
        default="/tmp/update_validation",
        help="Test environment directory (default: /tmp/update_validation)",
    )

    parser.add_argument(
        "--runtime",
        default="podman",
        choices=["podman", "docker"],
        help="Container runtime (default: podman)",
    )

    parser.add_argument(
        "--base-image",
        default="quay.io/centos/centos:stream10",
        help="Base container image (default: quay.io/centos/centos:stream10)",
    )

    parser.add_argument(
        "--parallel", type=int, default=3, help="Maximum parallel tests (default: 3)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Validation timeout in seconds (default: 1800)",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate component update"
    )
    validate_parser.add_argument("component", help="Component name")
    validate_parser.add_argument(
        "--current-version", required=True, help="Current version"
    )
    validate_parser.add_argument(
        "--target-version", required=True, help="Target version"
    )
    validate_parser.add_argument(
        "--component-type",
        choices=["os_package", "software", "collection"],
        default="software",
        help="Component type (default: software)",
    )
    validate_parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )
    validate_parser.add_argument(
        "--detailed", action="store_true", help="Show detailed test results"
    )
    validate_parser.add_argument("--output", help="Save results to file")

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Validate batch of updates")
    batch_parser.add_argument(
        "--max-updates",
        type=int,
        default=10,
        help="Maximum updates to validate (default: 10)",
    )
    batch_parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )
    batch_parser.add_argument("--output", help="Save results to file")

    # List command
    list_parser = subparsers.add_parser(
        "list", help="List available tests and environments"
    )

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Cleanup test environments")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Setup logging
    setup_logging(args.log_level)

    try:
        if args.command == "validate":
            return await validate_command(args)
        elif args.command == "batch":
            return await batch_command(args)
        elif args.command == "list":
            return await list_command(args)
        elif args.command == "cleanup":
            return await cleanup_command(args)
        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\n❌ Operation interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
