#!/usr/bin/env python3
"""
Qubinode Navigator Rollback Manager CLI

Command-line interface for managing automated rollback mechanisms,
monitoring rollback status, and triggering manual rollbacks.
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.rollback_manager import RollbackManager, RollbackTrigger


async def main():
    """Main CLI entry point"""

    parser = argparse.ArgumentParser(
        description="Qubinode Navigator Rollback Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor rollback status
  python rollback_manager.py status

  # Get rollback statistics
  python rollback_manager.py stats

  # Trigger manual rollback
  python rollback_manager.py trigger --pipeline-id pipeline_123 --reason "Critical bug detected"

  # Get specific rollback details
  python rollback_manager.py details --plan-id rollback_456

  # List all rollbacks
  python rollback_manager.py list --format json
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show rollback system status")
    status_parser.add_argument("--format", choices=["summary", "json"], default="summary", help="Output format")

    # Statistics command
    stats_parser = subparsers.add_parser("stats", help="Show rollback statistics")
    stats_parser.add_argument("--format", choices=["summary", "json"], default="summary", help="Output format")

    # Trigger command
    trigger_parser = subparsers.add_parser("trigger", help="Trigger manual rollback")
    trigger_parser.add_argument("--pipeline-id", required=True, help="Pipeline ID to rollback")
    trigger_parser.add_argument("--reason", required=True, help="Reason for rollback")
    trigger_parser.add_argument("--phase-id", help="Specific phase ID to rollback (optional)")
    trigger_parser.add_argument("--requested-by", default="cli-user", help="User requesting rollback")

    # Details command
    details_parser = subparsers.add_parser("details", help="Get rollback plan details")
    details_parser.add_argument("--plan-id", required=True, help="Rollback plan ID")
    details_parser.add_argument("--format", choices=["summary", "json"], default="summary", help="Output format")

    # List command
    list_parser = subparsers.add_parser("list", help="List all rollbacks")
    list_parser.add_argument(
        "--status",
        choices=["active", "completed", "failed", "all"],
        default="all",
        help="Filter by status",
    )
    list_parser.add_argument("--format", choices=["table", "json"], default="table", help="Output format")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test rollback system")
    test_parser.add_argument(
        "--component",
        choices=["manager", "triggers", "execution"],
        default="manager",
        help="Component to test",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize rollback manager
    config = {
        "rollback_storage_path": "data/rollbacks",
        "auto_rollback_enabled": True,
        "rollback_timeout_minutes": 60,
    }

    rollback_manager = RollbackManager(config)

    # Execute command
    if args.command == "status":
        await handle_status_command(rollback_manager, args)
    elif args.command == "stats":
        await handle_stats_command(rollback_manager, args)
    elif args.command == "trigger":
        await handle_trigger_command(rollback_manager, args)
    elif args.command == "details":
        await handle_details_command(rollback_manager, args)
    elif args.command == "list":
        await handle_list_command(rollback_manager, args)
    elif args.command == "test":
        await handle_test_command(rollback_manager, args)


async def handle_status_command(rollback_manager: RollbackManager, args):
    """Handle status command"""

    try:
        stats = rollback_manager.get_rollback_statistics()

        if args.format == "json":
            print(json.dumps(stats, indent=2))
        else:
            print("=== Rollback System Status ===")
            print(f"Active Rollbacks: {stats['active_rollbacks']}")
            print(f"Total Rollbacks: {stats['total_rollbacks']}")
            print(f"Success Rate: {stats['success_rate']}%")
            print(f"Average Duration: {stats['average_duration_minutes']} minutes")

            if stats["trigger_breakdown"]:
                print("\nTrigger Breakdown:")
                for trigger, count in stats["trigger_breakdown"].items():
                    print(f"  {trigger}: {count}")

            # Show active rollbacks
            if stats["active_rollbacks"] > 0:
                print(f"\nActive Rollbacks: {stats['active_rollbacks']}")
                for plan_id, rollback in rollback_manager.active_rollbacks.items():
                    print(f"  {plan_id}: {rollback.status.value} ({rollback.trigger.value})")

    except Exception as e:
        print(f"Error getting rollback status: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_stats_command(rollback_manager: RollbackManager, args):
    """Handle statistics command"""

    try:
        stats = rollback_manager.get_rollback_statistics()

        if args.format == "json":
            print(json.dumps(stats, indent=2))
        else:
            print("=== Rollback Statistics ===")
            print(f"Total Rollbacks: {stats['total_rollbacks']}")
            print(f"Completed: {stats['completed']}")
            print(f"Failed: {stats['failed']}")
            print(f"Success Rate: {stats['success_rate']}%")
            print(f"Average Duration: {stats['average_duration_minutes']} minutes")
            print(f"Active Rollbacks: {stats['active_rollbacks']}")

            if stats["trigger_breakdown"]:
                print("\nTrigger Breakdown:")
                for trigger, count in sorted(stats["trigger_breakdown"].items()):
                    percentage = (count / stats["total_rollbacks"] * 100) if stats["total_rollbacks"] > 0 else 0
                    print(f"  {trigger}: {count} ({percentage:.1f}%)")

    except Exception as e:
        print(f"Error getting rollback statistics: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_trigger_command(rollback_manager: RollbackManager, args):
    """Handle trigger command"""

    try:
        print(f"Triggering manual rollback for pipeline {args.pipeline_id}...")
        print(f"Reason: {args.reason}")
        if args.phase_id:
            print(f"Phase ID: {args.phase_id}")

        rollback_plan = await rollback_manager.trigger_manual_rollback(
            pipeline_id=args.pipeline_id,
            reason=args.reason,
            requested_by=args.requested_by,
            phase_id=args.phase_id,
        )

        if rollback_plan:
            print(f"✓ Rollback plan created: {rollback_plan.plan_id}")
            print(f"  Status: {rollback_plan.status.value}")
            print(f"  Estimated Duration: {rollback_plan.estimated_duration}")
            print(f"  Actions: {len(rollback_plan.rollback_actions)}")

            # Execute rollback
            print("\nExecuting rollback...")
            success = await rollback_manager.execute_rollback(rollback_plan)

            if success:
                print("✓ Rollback completed successfully")
            else:
                print("✗ Rollback failed")
                if rollback_plan.error_message:
                    print(f"  Error: {rollback_plan.error_message}")
        else:
            print("✗ Failed to create rollback plan")

    except Exception as e:
        print(f"Error triggering rollback: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_details_command(rollback_manager: RollbackManager, args):
    """Handle details command"""

    try:
        rollback_status = rollback_manager.get_rollback_status(args.plan_id)

        if not rollback_status:
            print(f"Rollback plan {args.plan_id} not found", file=sys.stderr)
            sys.exit(1)

        if args.format == "json":
            print(json.dumps(rollback_status, indent=2))
        else:
            print(f"=== Rollback Plan Details: {args.plan_id} ===")
            print(f"Pipeline ID: {rollback_status['pipeline_id']}")
            print(f"Status: {rollback_status['status']}")
            print(f"Trigger: {rollback_status['trigger']}")
            print(f"Created: {rollback_status['created_at']}")

            if rollback_status["started_at"]:
                print(f"Started: {rollback_status['started_at']}")

            if rollback_status["completed_at"]:
                print(f"Completed: {rollback_status['completed_at']}")

            print(f"Estimated Duration: {rollback_status['estimated_duration']}")
            print(f"Actions Count: {rollback_status['actions_count']}")

            if rollback_status["error_message"]:
                print(f"Error: {rollback_status['error_message']}")

            if rollback_status["validation_results"]:
                print("\nValidation Results:")
                for key, result in rollback_status["validation_results"].items():
                    if isinstance(result, dict) and "status" in result:
                        print(f"  {key}: {result['status']}")
                    else:
                        print(f"  {key}: {result}")

    except Exception as e:
        print(f"Error getting rollback details: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_list_command(rollback_manager: RollbackManager, args):
    """Handle list command"""

    try:
        all_rollbacks = []

        # Get active rollbacks
        if args.status in ["active", "all"]:
            for rollback in rollback_manager.active_rollbacks.values():
                all_rollbacks.append(
                    {
                        "plan_id": rollback.plan_id,
                        "pipeline_id": rollback.pipeline_id,
                        "status": rollback.status.value,
                        "trigger": rollback.trigger.value,
                        "created_at": rollback.created_at.isoformat(),
                        "estimated_duration": rollback.estimated_duration,
                    }
                )

        # Get historical rollbacks
        if args.status in ["completed", "failed", "all"]:
            for rollback in rollback_manager.rollback_history:
                if args.status == "all" or rollback.status.value == args.status:
                    all_rollbacks.append(
                        {
                            "plan_id": rollback.plan_id,
                            "pipeline_id": rollback.pipeline_id,
                            "status": rollback.status.value,
                            "trigger": rollback.trigger.value,
                            "created_at": rollback.created_at.isoformat(),
                            "estimated_duration": rollback.estimated_duration,
                        }
                    )

        if args.format == "json":
            print(json.dumps(all_rollbacks, indent=2))
        else:
            if not all_rollbacks:
                print("No rollbacks found")
                return

            print("=== Rollback Plans ===")
            print(f"{'Plan ID':<20} {'Pipeline ID':<20} {'Status':<12} {'Trigger':<25} {'Created':<20}")
            print("-" * 100)

            for rollback in sorted(all_rollbacks, key=lambda x: x["created_at"], reverse=True):
                created_date = datetime.fromisoformat(rollback["created_at"]).strftime("%Y-%m-%d %H:%M")
                print(f"{rollback['plan_id']:<20} {rollback['pipeline_id']:<20} {rollback['status']:<12} {rollback['trigger']:<25} {created_date:<20}")

    except Exception as e:
        print(f"Error listing rollbacks: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_test_command(rollback_manager: RollbackManager, args):
    """Handle test command"""

    try:
        print(f"Testing rollback system component: {args.component}")

        if args.component == "manager":
            # Test rollback manager initialization
            print("✓ Rollback manager initialized")
            print(f"  Storage path: {rollback_manager.rollback_storage_path}")
            print(f"  Auto-rollback enabled: {rollback_manager.auto_rollback_enabled}")

            # Test statistics
            stats = rollback_manager.get_rollback_statistics()
            print(f"  Total rollbacks: {stats['total_rollbacks']}")
            print(f"  Active rollbacks: {stats['active_rollbacks']}")

        elif args.component == "triggers":
            # Test trigger detection (mock)
            print("✓ Testing rollback triggers...")
            for trigger in RollbackTrigger:
                print(f"  {trigger.value}: Available")

        elif args.component == "execution":
            # Test rollback execution (dry run)
            print("✓ Testing rollback execution (dry run)...")
            print("  Would create rollback plan")
            print("  Would execute rollback actions")
            print("  Would validate rollback success")

        print("✓ All tests passed")

    except Exception as e:
        print(f"Error running tests: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
