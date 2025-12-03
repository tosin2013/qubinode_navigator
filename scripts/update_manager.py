#!/usr/bin/env python3
"""
Qubinode Navigator Update Manager CLI

Command-line interface for automated update detection and management.
Provides comprehensive update checking, compatibility analysis, and batch management.
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

from core.update_manager import UpdateBatch, UpdateDetector, UpdateInfo


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def print_update_summary(summary: Dict[str, Any]):
    """Print formatted update summary"""
    print("\n" + "=" * 80)
    print("🔄 QUBINODE NAVIGATOR UPDATE SUMMARY")
    print("=" * 80)

    # Basic statistics
    print(f"\n📊 UPDATE STATISTICS")
    print(f"   Check Time: {summary['check_timestamp']}")
    print(f"   Duration: {summary['check_duration']:.2f}s")
    print(f"   Total Updates: {summary['total_updates']}")

    # Updates by type
    by_type = summary["updates_by_type"]
    print(f"\n📦 UPDATES BY TYPE")
    print(f"   OS Packages: {by_type['os_packages']}")
    print(f"   Software: {by_type['software']}")
    print(f"   Collections: {by_type['collections']}")

    # Updates by severity
    by_severity = summary["updates_by_severity"]
    print(f"\n🚨 UPDATES BY SEVERITY")
    if by_severity["security"] > 0:
        print(f"   🔴 Security: {by_severity['security']}")
    if by_severity["critical"] > 0:
        print(f"   🟠 Critical: {by_severity['critical']}")
    if by_severity["important"] > 0:
        print(f"   🟡 Important: {by_severity['important']}")
    if by_severity["moderate"] > 0:
        print(f"   🔵 Moderate: {by_severity['moderate']}")
    if by_severity["low"] > 0:
        print(f"   ⚪ Low: {by_severity['low']}")

    # Compatibility status
    compat = summary["compatibility_status"]
    print(f"\n🔍 COMPATIBILITY STATUS")
    print(f"   ✅ Compatible: {compat['compatible']}")
    print(f"   ❌ Incompatible: {compat['incompatible']}")
    print(f"   🧪 Needs Testing: {compat['needs_testing']}")
    print(f"   ❓ Unknown: {compat['unknown']}")

    # Update batches
    print(f"\n📋 UPDATE BATCHES")
    print(f"   Total Batches: {summary['update_batches']}")

    for batch in summary["batches"]:
        batch_icon = {"security": "🔒", "critical": "🚨", "maintenance": "🔧"}.get(
            batch["batch_type"], "📦"
        )

        print(f"\n   {batch_icon} {batch['batch_type'].upper()} BATCH")
        print(f"      ID: {batch['batch_id']}")
        print(f"      Updates: {len(batch['updates'])}")
        print(
            f"      Size: {batch['total_size'] / 1024 / 1024:.1f} MB"
            if batch["total_size"] > 0
            else "      Size: Unknown"
        )
        print(f"      Duration: {batch['estimated_duration']}")
        print(f"      Risk: {batch['risk_level'].upper()}")
        print(f"      Reboot Required: {'Yes' if batch['requires_reboot'] else 'No'}")


def print_detailed_updates(updates: list):
    """Print detailed update information"""
    if not updates:
        print("\n✅ No updates available")
        return

    print(f"\n📋 DETAILED UPDATE LIST ({len(updates)} updates)")
    print("-" * 80)

    # Group by type
    by_type = {}
    for update in updates:
        if update["component_type"] not in by_type:
            by_type[update["component_type"]] = []
        by_type[update["component_type"]].append(update)

    for component_type, type_updates in by_type.items():
        type_icon = {
            "os_package": "📦",
            "software": "💻",
            "collection": "📚",
            "container": "🐳",
        }.get(component_type, "📄")

        print(f"\n{type_icon} {component_type.upper().replace('_', ' ')}")

        for update in type_updates:
            severity_icon = {
                "security": "🔴",
                "critical": "🟠",
                "important": "🟡",
                "moderate": "🔵",
                "low": "⚪",
            }.get(update["severity"], "❓")

            compat_icon = {
                "compatible": "✅",
                "incompatible": "❌",
                "needs_testing": "🧪",
                "unknown": "❓",
            }.get(update["compatibility_status"], "❓")

            print(f"   {severity_icon} {update['component_name']}")
            print(f"      Current: {update['current_version']}")
            print(f"      Available: {update['available_version']}")
            print(f"      Severity: {update['severity'].upper()}")
            print(
                f"      Compatibility: {compat_icon} {update['compatibility_status']}"
            )
            if update.get("description"):
                print(f"      Description: {update['description']}")
            if update.get("changelog_url"):
                print(f"      Changelog: {update['changelog_url']}")


def print_json_output(data: Dict[str, Any]):
    """Print data in JSON format"""
    print(json.dumps(data, indent=2, default=str))


async def check_updates_command(args):
    """Execute update check command"""
    # Initialize update detector
    config = {
        "ai_assistant_url": args.ai_url,
        "cache_directory": args.cache_dir,
        "compatibility_file": args.compatibility_file,
        "enable_ai_compatibility": args.enable_ai,
    }

    detector = UpdateDetector(config)

    print("🔍 Checking for updates...")

    try:
        # Run update detection
        summary = await detector.run_full_update_check()

        # Output results
        if args.format == "json":
            print_json_output(summary)
        else:
            print_update_summary(summary)

            if args.detailed:
                print_detailed_updates(summary["updates"])

        # Save results if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(summary, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {args.output}")

        # Return appropriate exit code
        if summary["total_updates"] > 0:
            if any(
                u["severity"] in ["security", "critical"] for u in summary["updates"]
            ):
                return 2  # Critical updates available
            else:
                return 1  # Updates available
        else:
            return 0  # No updates

    except Exception as e:
        print(f"❌ Update check failed: {e}")
        return 3


async def check_os_command(args):
    """Execute OS-only update check"""
    config = {"ai_assistant_url": args.ai_url}
    detector = UpdateDetector(config)

    print("🔍 Checking for OS package updates...")

    try:
        updates = await detector.detect_os_updates()

        if args.format == "json":
            print_json_output([update.__dict__ for update in updates])
        else:
            print(f"Found {len(updates)} OS package updates")
            if updates:
                for update in updates[:10]:  # Show first 10
                    print(
                        f"  • {update.component_name}: {update.current_version} → {update.available_version}"
                    )
                if len(updates) > 10:
                    print(f"  ... and {len(updates) - 10} more")

        return 0 if len(updates) == 0 else 1

    except Exception as e:
        print(f"❌ OS update check failed: {e}")
        return 3


async def check_software_command(args):
    """Execute software-only update check"""
    config = {"ai_assistant_url": args.ai_url}
    detector = UpdateDetector(config)

    print("🔍 Checking for software updates...")

    try:
        updates = await detector.detect_software_updates()

        if args.format == "json":
            print_json_output([update.__dict__ for update in updates])
        else:
            print(f"Found {len(updates)} software updates")
            if updates:
                for update in updates:
                    print(
                        f"  • {update.component_name}: {update.current_version} → {update.available_version}"
                    )

        return 0 if len(updates) == 0 else 1

    except Exception as e:
        print(f"❌ Software update check failed: {e}")
        return 3


async def check_collections_command(args):
    """Execute collections-only update check"""
    config = {"ai_assistant_url": args.ai_url}
    detector = UpdateDetector(config)

    print("🔍 Checking for Ansible collection updates...")

    try:
        updates = await detector.detect_collection_updates()

        if args.format == "json":
            print_json_output([update.__dict__ for update in updates])
        else:
            print(f"Found {len(updates)} collection updates")
            if updates:
                for update in updates:
                    print(
                        f"  • {update.component_name}: {update.current_version} → {update.available_version}"
                    )

        return 0 if len(updates) == 0 else 1

    except Exception as e:
        print(f"❌ Collection update check failed: {e}")
        return 3


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Qubinode Navigator Update Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check all updates
  python3 update_manager.py check
  
  # Check with detailed output
  python3 update_manager.py check --detailed
  
  # Check only OS packages
  python3 update_manager.py check-os
  
  # Check only software
  python3 update_manager.py check-software
  
  # Check only collections
  python3 update_manager.py check-collections
  
  # Output as JSON
  python3 update_manager.py check --format json
  
  # Save results to file
  python3 update_manager.py check --output updates.json
        """,
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

    parser.add_argument(
        "--cache-dir",
        default="/tmp/update_cache",
        help="Cache directory for update data (default: /tmp/update_cache)",
    )

    parser.add_argument(
        "--compatibility-file",
        default="config/compatibility_matrix.yml",
        help="Compatibility matrix file (default: config/compatibility_matrix.yml)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check for all updates")
    check_parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )
    check_parser.add_argument(
        "--detailed", action="store_true", help="Show detailed update information"
    )
    check_parser.add_argument("--output", help="Save results to file")
    check_parser.add_argument(
        "--no-ai",
        dest="enable_ai",
        action="store_false",
        default=True,
        help="Disable AI-powered compatibility checks (faster but less intelligent)",
    )

    # Check OS command
    os_parser = subparsers.add_parser(
        "check-os", help="Check for OS package updates only"
    )
    os_parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )

    # Check software command
    software_parser = subparsers.add_parser(
        "check-software", help="Check for software updates only"
    )
    software_parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )

    # Check collections command
    collections_parser = subparsers.add_parser(
        "check-collections", help="Check for Ansible collection updates only"
    )
    collections_parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Setup logging
    setup_logging(args.log_level)

    try:
        if args.command == "check":
            return await check_updates_command(args)
        elif args.command == "check-os":
            return await check_os_command(args)
        elif args.command == "check-software":
            return await check_software_command(args)
        elif args.command == "check-collections":
            return await check_collections_command(args)
        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\n❌ Update check interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
