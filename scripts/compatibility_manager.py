#!/usr/bin/env python3
"""
Qubinode Navigator Compatibility Matrix Management CLI

Command-line interface for managing compatibility matrices, running tests,
and validating component compatibility across different OS versions.
"""

import sys
import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.compatibility_manager import (
    CompatibilityManager,
    CompatibilityLevel,
    TestStatus,
)


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def print_compatibility_report(report: Dict[str, Any]):
    """Print formatted compatibility report"""
    print("\n" + "=" * 80)
    print("🔍 COMPATIBILITY MATRIX REPORT")
    print("=" * 80)

    # Summary statistics
    summary = report["summary"]
    print("\n📊 SUMMARY STATISTICS")
    print(f"   Report Time: {report['report_timestamp']}")
    print(f"   Total Components: {report['total_components']}")
    print(f"   Total Test Results: {report['total_test_results']}")
    print(f"   Total Rules: {report['total_rules']}")
    print(f"   Recent Tests (7 days): {summary['recent_tests']}")
    print(f"   Test Success Rate: {summary['test_success_rate']:.1f}%")

    # Compatibility status
    print("\n🎯 COMPATIBILITY STATUS")
    print(f"   ✅ Compatible Versions: {summary['compatible_versions']}")
    print(f"   ❌ Incompatible Versions: {summary['incompatible_versions']}")
    print(f"   🧪 Needs Testing: {summary['needs_testing']}")

    # Component details
    print("\n📦 COMPONENT DETAILS")
    for component, details in report["components"].items():
        print(f"\n   🔧 {component.upper()}")
        print(f"      Last Updated: {details['last_updated']}")
        print(f"      Known Issues: {details['known_issues']}")
        print(f"      Recent Tests: {len(details['recent_test_results'])}")

        # Show supported versions
        if details["supported_versions"]:
            print("      Supported Versions:")
            for os_ver, versions in details["supported_versions"].items():
                print(f"        OS {os_ver}: {', '.join(versions[:3])}" + (f" (+{len(versions)-3} more)" if len(versions) > 3 else ""))

        # Show recent test results
        if details["recent_test_results"]:
            print("      Recent Test Results:")
            for test in details["recent_test_results"][:3]:  # Show last 3
                status_icon = "✅" if test["status"] == "passed" else "❌" if test["status"] == "failed" else "⏳"
                print(f"        {status_icon} {test['version']} on OS {test['os_version']} - {test['status']}")


def print_test_result(result):
    """Print formatted test result"""
    status_icon = {
        "passed": "✅",
        "failed": "❌",
        "running": "⏳",
        "timeout": "⏰",
        "skipped": "⏭️",
    }.get(result.status.value, "❓")

    print(f"\n{status_icon} Test Result: {result.test_id}")
    print(f"   Component: {result.component_name} {result.component_version}")
    print(f"   OS Version: {result.os_version}")
    print(f"   Test Type: {result.test_type}")
    print(f"   Status: {result.status.value.upper()}")
    print(f"   Duration: {result.duration:.2f}s")

    if result.error_message:
        print(f"   Error: {result.error_message}")

    if result.logs and len(result.logs) < 200:  # Show short logs
        print(f"   Logs: {result.logs}")


async def validate_command(args):
    """Execute compatibility validation command"""
    config = {
        "matrix_file": args.matrix_file,
        "test_results_dir": args.test_dir,
        "ai_assistant_url": args.ai_url,
    }

    manager = CompatibilityManager(config)

    print(f"🔍 Validating compatibility: {args.component} {args.version} on OS {args.os_version}")

    try:
        level, reason = await manager.validate_compatibility(args.component, args.version, args.os_version)

        level_icon = {
            "compatible": "✅",
            "incompatible": "❌",
            "needs_testing": "🧪",
            "deprecated": "⚠️",
            "unknown": "❓",
        }.get(level.value, "❓")

        print(f"\n{level_icon} Compatibility: {level.value.upper()}")
        print(f"   Reason: {reason}")

        if args.format == "json":
            result = {
                "component": args.component,
                "version": args.version,
                "os_version": args.os_version,
                "compatibility_level": level.value,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            }
            print(json.dumps(result, indent=2))

        # Return appropriate exit code
        if level == CompatibilityLevel.COMPATIBLE:
            return 0
        elif level == CompatibilityLevel.INCOMPATIBLE:
            return 2
        else:
            return 1

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return 3


async def test_command(args):
    """Execute compatibility test command"""
    config = {
        "matrix_file": args.matrix_file,
        "test_results_dir": args.test_dir,
        "ai_assistant_url": args.ai_url,
        "auto_update": args.auto_update,
        "test_timeout": args.timeout,
    }

    manager = CompatibilityManager(config)

    print(f"🧪 Running compatibility test: {args.component} {args.version} on OS {args.os_version}")

    try:
        result = await manager.run_compatibility_test(args.component, args.version, args.os_version, args.test_type)

        if args.format == "json":
            result_dict = {
                "test_id": result.test_id,
                "component_name": result.component_name,
                "component_version": result.component_version,
                "os_version": result.os_version,
                "test_type": result.test_type,
                "status": result.status.value,
                "duration": result.duration,
                "error_message": result.error_message,
                "timestamp": result.timestamp.isoformat(),
            }
            print(json.dumps(result_dict, indent=2))
        else:
            print_test_result(result)

        # Save results
        await manager.save_test_results()
        if args.auto_update:
            await manager.save_compatibility_matrices()

        # Return appropriate exit code
        if result.status == TestStatus.PASSED:
            return 0
        elif result.status == TestStatus.FAILED:
            return 2
        else:
            return 1

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 3


async def report_command(args):
    """Execute compatibility report command"""
    config = {"matrix_file": args.matrix_file, "test_results_dir": args.test_dir}

    manager = CompatibilityManager(config)

    print("📊 Generating compatibility report...")

    try:
        report = await manager.generate_compatibility_report()

        if args.format == "json":
            print(json.dumps(report, indent=2, default=str))
        else:
            print_compatibility_report(report)

        # Save report if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\n💾 Report saved to: {args.output}")

        return 0

    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        return 3


async def update_command(args):
    """Execute matrix update command"""
    config = {
        "matrix_file": args.matrix_file,
        "test_results_dir": args.test_dir,
        "auto_update": True,
    }

    manager = CompatibilityManager(config)

    print("🔄 Updating compatibility matrices...")

    try:
        # Save current matrices
        await manager.save_compatibility_matrices()
        await manager.save_test_results()

        print("✅ Compatibility matrices updated successfully")
        return 0

    except Exception as e:
        print(f"❌ Matrix update failed: {e}")
        return 3


async def list_command(args):
    """Execute list components command"""
    config = {"matrix_file": args.matrix_file, "test_results_dir": args.test_dir}

    manager = CompatibilityManager(config)

    print("📋 Available components:")

    try:
        if not manager.compatibility_matrices:
            print("   No components found in compatibility matrix")
            return 0

        for component, matrix in manager.compatibility_matrices.items():
            print(f"\n🔧 {component}")
            print(f"   Last Updated: {matrix.last_updated}")
            print(f"   Supported OS Versions: {list(matrix.supported_versions.keys())}")
            print(f"   Test Results: {len(matrix.test_results)} versions tested")
            print(f"   Known Issues: {len(matrix.known_issues)}")

        return 0

    except Exception as e:
        print(f"❌ Failed to list components: {e}")
        return 3


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Qubinode Navigator Compatibility Matrix Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate compatibility
  python3 compatibility_manager.py validate podman 5.0.0 --os-version 10

  # Run compatibility test
  python3 compatibility_manager.py test ansible 2.16.0 --os-version 9

  # Generate compatibility report
  python3 compatibility_manager.py report

  # List available components
  python3 compatibility_manager.py list

  # Update matrices
  python3 compatibility_manager.py update
        """,
    )

    parser.add_argument(
        "--matrix-file",
        default="config/compatibility_matrix.yml",
        help="Compatibility matrix file (default: config/compatibility_matrix.yml)",
    )

    parser.add_argument(
        "--test-dir",
        default="/tmp/compatibility_tests",
        help="Test results directory (default: /tmp/compatibility_tests)",
    )

    parser.add_argument(
        "--ai-url",
        default="http://localhost:8080",
        help="AI Assistant service URL (default: http://localhost:8080)",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate component compatibility")
    validate_parser.add_argument("component", help="Component name")
    validate_parser.add_argument("version", help="Component version")
    validate_parser.add_argument("--os-version", required=True, help="OS version")
    validate_parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )

    # Test command
    test_parser = subparsers.add_parser("test", help="Run compatibility test")
    test_parser.add_argument("component", help="Component name")
    test_parser.add_argument("version", help="Component version")
    test_parser.add_argument("--os-version", required=True, help="OS version")
    test_parser.add_argument(
        "--test-type",
        choices=["smoke", "unit", "integration", "compatibility"],
        default="smoke",
        help="Test type (default: smoke)",
    )
    test_parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Test timeout in seconds (default: 300)",
    )
    test_parser.add_argument(
        "--auto-update",
        action="store_true",
        default=True,
        help="Auto-update matrix with test results (default: true)",
    )
    test_parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate compatibility report")
    report_parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )
    report_parser.add_argument("--output", help="Save report to file")

    # Update command
    subparsers.add_parser("update", help="Update compatibility matrices")

    # List command
    subparsers.add_parser("list", help="List available components")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Setup logging
    setup_logging(args.log_level)

    try:
        if args.command == "validate":
            return await validate_command(args)
        elif args.command == "test":
            return await test_command(args)
        elif args.command == "report":
            return await report_command(args)
        elif args.command == "update":
            return await update_command(args)
        elif args.command == "list":
            return await list_command(args)
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
