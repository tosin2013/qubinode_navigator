#!/usr/bin/env python3
"""
Qubinode Navigator Rollout Pipeline CLI

Command-line interface for managing staged rollout pipelines with
approval gates, automated progression, and rollback capabilities.
"""

import sys
import argparse
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.rollout_pipeline import RolloutPipelineManager, RolloutStrategy
from core.pipeline_executor import PipelineExecutor, ExecutionResult
from core.approval_gates import ApprovalGateManager
from core.ai_update_manager import AIUpdateManager
from core.update_manager import UpdateBatch, UpdateInfo


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def print_pipeline_status(pipeline):
    """Print formatted pipeline status"""
    status_icons = {
        "pending": "⏳",
        "approved": "✅",
        "deploying": "🚀",
        "validating": "🧪",
        "completed": "✅",
        "failed": "❌",
        "rolled_back": "🔄",
        "cancelled": "🚫",
    }

    strategy_icons = {
        "canary": "🐤",
        "blue_green": "🔵🟢",
        "rolling": "🔄",
        "all_at_once": "⚡",
    }

    status_icon = status_icons.get(pipeline.status.value, "❓")
    strategy_icon = strategy_icons.get(pipeline.strategy.value, "❓")

    print(f"\n{status_icon} Pipeline: {pipeline.pipeline_name}")
    print(f"   ID: {pipeline.pipeline_id}")
    print(
        f"   {strategy_icon} Strategy: {pipeline.strategy.value.replace('_', ' ').title()}"
    )
    print(f"   Status: {pipeline.status.value.replace('_', ' ').title()}")
    print(f"   Created: {pipeline.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Created by: {pipeline.created_by}")

    if pipeline.current_phase:
        print(f"   Current Phase: {pipeline.current_phase}")

    if pipeline.completed_at:
        print(f"   Completed: {pipeline.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Duration: {pipeline.total_duration}")

    print(f"   Phases: {len(pipeline.phases)}")
    print(f"   Approval Gates: {len(pipeline.approval_gates)}")


def print_phase_details(phases):
    """Print detailed phase information"""
    print("\n📋 PIPELINE PHASES")
    print("=" * 60)

    for i, phase in enumerate(phases, 1):
        stage_icon = {
            "pending": "⏳",
            "approved": "✅",
            "deploying": "🚀",
            "validating": "🧪",
            "completed": "✅",
            "failed": "❌",
        }.get(phase.stage.value, "❓")

        print(f"\n{stage_icon} Phase {i}: {phase.phase_name}")
        print(f"   ID: {phase.phase_id}")
        print(f"   Status: {phase.stage.value.replace('_', ' ').title()}")
        print(f"   Environments: {', '.join(phase.target_environments)}")
        print(f"   Updates: {len(phase.update_batch.updates)}")
        print(f"   Estimated Duration: {phase.estimated_duration}")

        if phase.actual_duration:
            print(f"   Actual Duration: {phase.actual_duration}")

        if phase.validation_tests:
            print(f"   Validation Tests: {len(phase.validation_tests)}")

        if phase.error_message:
            print(f"   ❌ Error: {phase.error_message}")


def print_approval_gates(gates):
    """Print approval gate information"""
    print("\n🚪 APPROVAL GATES")
    print("=" * 60)

    for gate in gates:
        status_icon = {
            "pending": "⏳",
            "approved": "✅",
            "rejected": "❌",
            "expired": "⏰",
            "auto_approved": "🤖",
        }.get(gate.status.value, "❓")

        print(f"\n{status_icon} Gate: {gate.gate_name}")
        print(f"   ID: {gate.gate_id}")
        print(f"   Stage: {gate.stage}")
        print(f"   Status: {gate.status.value.replace('_', ' ').title()}")
        print(f"   Required Approvers: {', '.join(gate.required_approvers)}")
        print(f"   Expires: {gate.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if gate.approved_by:
            print(f"   Approved by: {gate.approved_by}")
            print(f"   Approved at: {gate.approved_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if gate.approvals:
            print(f"   Approvals: {len(gate.approvals)}/{len(gate.required_approvers)}")


async def create_command(args):
    """Execute pipeline creation command"""
    config = {
        "pipeline_storage_path": args.storage_path,
        "auto_progression_enabled": not args.no_auto_progression,
    }

    pipeline_manager = RolloutPipelineManager(config)
    ai_manager = AIUpdateManager()

    print("🔍 Creating rollout pipeline...")

    try:
        # Get update plan (simplified - would normally come from AI analysis)
        if args.plan_file:
            with open(args.plan_file, "r") as f:
                plan_data = json.load(f)
            # Would deserialize UpdatePlan here
            print(f"📋 Loaded update plan from {args.plan_file}")
        else:
            # Create a sample plan for demonstration
            print("📋 Creating sample update plan...")
            update_result = await ai_manager.update_detector.run_full_update_check()
            updates = [
                UpdateInfo(**update_dict)
                for update_dict in update_result.get("updates", [])[: args.max_updates]
            ]

            if not updates:
                print("✅ No updates available for pipeline creation")
                return 0

            # Create update batch
            batch = UpdateBatch(
                batch_id=f"batch_{int(datetime.now().timestamp())}",
                batch_type="rollout",
                updates=updates,
                total_size=sum(getattr(u, "update_size", None) or 100 for u in updates),
                estimated_duration=f"{len(updates) * 5} minutes",
                risk_level="medium",
                requires_reboot=any(
                    getattr(u, "requires_reboot", False) for u in updates
                ),
                rollback_plan="Standard package rollback",
                created_at=datetime.now(),
            )

            # Get AI analysis and create plan
            analyses = await ai_manager.analyze_update_batch(batch)
            plan = await ai_manager.create_update_plan(batch, analyses)

        # Create rollout pipeline
        strategy = RolloutStrategy(args.strategy)
        pipeline = await pipeline_manager.create_rollout_pipeline(
            update_plan=plan,
            strategy=strategy,
            created_by=args.created_by,
            pipeline_name=args.name,
        )

        # Display created pipeline
        if args.format == "summary":
            print_pipeline_status(pipeline)
            print_phase_details(pipeline.phases)
            print_approval_gates(pipeline.approval_gates)
        elif args.format == "json":
            pipeline_data = pipeline_manager._serialize_pipeline(pipeline)
            print(json.dumps(pipeline_data, indent=2))

        print(f"\n✅ Created rollout pipeline: {pipeline.pipeline_id}")
        return 0

    except Exception as e:
        print(f"❌ Pipeline creation failed: {e}")
        return 1


async def list_command(args):
    """Execute pipeline listing command"""
    config = {"pipeline_storage_path": args.storage_path}
    pipeline_manager = RolloutPipelineManager(config)

    print("📋 Rollout Pipelines")
    print("=" * 60)

    # List active pipelines
    if pipeline_manager.active_pipelines:
        print(f"\n🚀 ACTIVE PIPELINES ({len(pipeline_manager.active_pipelines)})")
        for pipeline in pipeline_manager.active_pipelines.values():
            if not args.status or pipeline.status.value == args.status:
                print_pipeline_status(pipeline)

    # List completed pipelines
    if args.include_completed and pipeline_manager.pipeline_history:
        print(f"\n📚 COMPLETED PIPELINES ({len(pipeline_manager.pipeline_history)})")
        for pipeline in pipeline_manager.pipeline_history[-args.limit :]:
            if not args.status or pipeline.status.value == args.status:
                print_pipeline_status(pipeline)

    return 0


async def status_command(args):
    """Execute pipeline status command"""
    config = {"pipeline_storage_path": args.storage_path}
    pipeline_manager = RolloutPipelineManager(config)
    executor = PipelineExecutor()

    if args.pipeline_id not in pipeline_manager.active_pipelines:
        print(f"❌ Pipeline {args.pipeline_id} not found")
        return 1

    pipeline = pipeline_manager.active_pipelines[args.pipeline_id]

    if args.format == "summary":
        print_pipeline_status(pipeline)
        print_phase_details(pipeline.phases)
        print_approval_gates(pipeline.approval_gates)

        # Get execution status
        exec_status = executor.get_execution_status(args.pipeline_id)
        if exec_status["active_phases"] > 0:
            print("\n⚡ ACTIVE EXECUTION")
            print("=" * 60)
            for phase_detail in exec_status["phase_details"]:
                print(f"   Phase: {phase_detail['phase_id']}")
                print(f"   Progress: {phase_detail['progress']:.1f}%")
                print(f"   Current Step: {phase_detail['current_step']}")

    elif args.format == "json":
        pipeline_data = pipeline_manager._serialize_pipeline(pipeline)
        exec_status = executor.get_execution_status(args.pipeline_id)
        pipeline_data["execution_status"] = exec_status
        print(json.dumps(pipeline_data, indent=2))

    return 0


async def execute_command(args):
    """Execute pipeline execution command"""
    config = {"pipeline_storage_path": args.storage_path}
    pipeline_manager = RolloutPipelineManager(config)
    executor = PipelineExecutor()

    if args.pipeline_id not in pipeline_manager.active_pipelines:
        print(f"❌ Pipeline {args.pipeline_id} not found")
        return 1

    pipeline = pipeline_manager.active_pipelines[args.pipeline_id]

    print(f"🚀 Executing pipeline: {pipeline.pipeline_name}")
    print(f"   Strategy: {pipeline.strategy.value}")
    print(f"   Phases: {len(pipeline.phases)}")

    if not args.force:
        confirm = input("\nProceed with execution? (y/N): ")
        if confirm.lower() != "y":
            print("❌ Execution cancelled")
            return 0

    try:
        result = await executor.execute_pipeline(pipeline)

        result_icons = {
            "success": "✅",
            "failed": "❌",
            "rolled_back": "🔄",
            "cancelled": "🚫",
            "timeout": "⏰",
        }

        icon = result_icons.get(result.value, "❓")
        print(f"\n{icon} Pipeline execution completed: {result.value}")

        # Save updated pipeline
        pipeline_manager._save_pipeline(pipeline)

        return 0 if result == ExecutionResult.SUCCESS else 1

    except Exception as e:
        print(f"❌ Pipeline execution failed: {e}")
        return 1


async def approve_command(args):
    """Execute approval command"""
    approval_manager = ApprovalGateManager()

    try:
        success = await approval_manager.process_approval_response(
            request_id=args.request_id,
            response=args.response,
            approver=args.approver,
            comments=args.comments,
        )

        if success:
            print(f"✅ Approval {args.response} recorded for request {args.request_id}")
        else:
            print("❌ Failed to process approval response")

        return 0 if success else 1

    except Exception as e:
        print(f"❌ Approval processing failed: {e}")
        return 1


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Qubinode Navigator Rollout Pipeline Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create canary rollout pipeline
  python3 rollout_pipeline.py create --strategy canary --name "Q4 Updates"

  # List active pipelines
  python3 rollout_pipeline.py list --status deploying

  # Execute pipeline
  python3 rollout_pipeline.py execute --pipeline-id rollout_123456789

  # Approve deployment gate
  python3 rollout_pipeline.py approve --request-id req_123 --response approved
        """,
    )

    parser.add_argument(
        "--storage-path",
        default="data/pipelines",
        help="Pipeline storage directory (default: data/pipelines)",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create new rollout pipeline")
    create_parser.add_argument(
        "--strategy",
        choices=["canary", "blue_green", "rolling", "all_at_once"],
        default="rolling",
        help="Rollout strategy (default: rolling)",
    )
    create_parser.add_argument("--name", help="Pipeline name")
    create_parser.add_argument(
        "--created-by", default="cli-user", help="Pipeline creator (default: cli-user)"
    )
    create_parser.add_argument("--plan-file", help="JSON file containing update plan")
    create_parser.add_argument(
        "--max-updates",
        type=int,
        default=10,
        help="Maximum updates to include (default: 10)",
    )
    create_parser.add_argument(
        "--no-auto-progression",
        action="store_true",
        help="Disable automatic phase progression",
    )
    create_parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List rollout pipelines")
    list_parser.add_argument(
        "--status",
        choices=[
            "pending",
            "approved",
            "deploying",
            "validating",
            "completed",
            "failed",
            "rolled_back",
            "cancelled",
        ],
        help="Filter by pipeline status",
    )
    list_parser.add_argument(
        "--include-completed", action="store_true", help="Include completed pipelines"
    )
    list_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum pipelines to show (default: 10)"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show pipeline status")
    status_parser.add_argument("pipeline_id", help="Pipeline ID to check")
    status_parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )

    # Execute command
    execute_parser = subparsers.add_parser("execute", help="Execute rollout pipeline")
    execute_parser.add_argument("pipeline_id", help="Pipeline ID to execute")
    execute_parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompt"
    )

    # Approve command
    approve_parser = subparsers.add_parser("approve", help="Process approval request")
    approve_parser.add_argument("request_id", help="Approval request ID")
    approve_parser.add_argument(
        "--response",
        choices=["approved", "rejected"],
        required=True,
        help="Approval response",
    )
    approve_parser.add_argument("--approver", required=True, help="Approver name/ID")
    approve_parser.add_argument("--comments", help="Approval comments")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Setup logging
    setup_logging(args.log_level)

    try:
        if args.command == "create":
            return await create_command(args)
        elif args.command == "list":
            return await list_command(args)
        elif args.command == "status":
            return await status_command(args)
        elif args.command == "execute":
            return await execute_command(args)
        elif args.command == "approve":
            return await approve_command(args)
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
