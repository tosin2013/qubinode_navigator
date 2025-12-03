#!/usr/bin/env python3
"""
Qubinode Navigator AI-Powered Update Management CLI

Command-line interface for AI-enhanced update management including
intelligent analysis, risk assessment, and automated planning.
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

from core.ai_update_manager import AIUpdateManager, RiskLevel, UpdateRecommendation
from core.update_manager import UpdateBatch, UpdateDetector, UpdateInfo


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def print_ai_analysis(component_name: str, analysis):
    """Print formatted AI analysis"""
    risk_icons = {
        "very_low": "🟢",
        "low": "🟡",
        "medium": "🟠",
        "high": "🔴",
        "critical": "🚨",
    }

    recommendation_icons = {
        "apply_immediately": "⚡",
        "apply_with_testing": "🧪",
        "schedule_maintenance": "📅",
        "defer_update": "⏸️",
        "block_update": "🚫",
    }

    risk_icon = risk_icons.get(analysis.risk_level.value, "❓")
    rec_icon = recommendation_icons.get(analysis.recommendation.value, "❓")

    print(f"\n🤖 AI Analysis: {component_name}")
    print(f"   {risk_icon} Risk Level: {analysis.risk_level.value.upper()}")
    print(
        f"   {rec_icon} Recommendation: {analysis.recommendation.value.replace('_', ' ').title()}"
    )
    print(f"   🎯 Confidence: {analysis.confidence_score:.1%}")
    print(f"   💭 Reasoning: {analysis.reasoning}")

    if analysis.security_impact:
        print(f"   🔒 Security Impact: {analysis.security_impact}")

    if analysis.compatibility_concerns:
        print(f"   ⚠️  Compatibility Concerns:")
        for concern in analysis.compatibility_concerns:
            print(f"      • {concern}")

    if analysis.testing_recommendations:
        print(f"   🧪 Testing Recommendations:")
        for rec in analysis.testing_recommendations:
            print(f"      • {rec}")

    if analysis.estimated_downtime:
        print(f"   ⏱️  Estimated Downtime: {analysis.estimated_downtime}")


def print_update_plan(plan):
    """Print formatted update execution plan"""
    print(f"\n📋 AI-Generated Update Plan: {plan.plan_id}")
    print(f"   🎯 Strategy: {plan.execution_strategy.replace('_', ' ').title()}")
    print(f"   ⏱️  Total Time: {plan.total_estimated_time}")
    print(f"   🤖 AI Confidence: {plan.ai_confidence:.1%}")
    print(f"   ✅ Approval Required: {'Yes' if plan.approval_required else 'No'}")

    print(f"\n📊 Execution Phases:")
    for i, phase in enumerate(plan.phases, 1):
        print(f"   Phase {i}: {phase['name']}")
        print(f"      Duration: {phase['estimated_duration']}")
        print(
            f"      Updates: {', '.join(phase['updates']) if phase['updates'] else 'N/A'}"
        )
        if phase.get("parallel_execution"):
            print(f"      Execution: Parallel")
        if phase.get("approval_required"):
            print(f"      Approval: Required")

    print(f"\n🛡️  Risk Mitigation Steps:")
    for step in plan.risk_mitigation_steps:
        print(f"   • {step}")

    print(f"\n📊 Monitoring Points:")
    for point in plan.monitoring_points:
        print(f"   • {point}")


async def analyze_command(args):
    """Execute AI analysis command"""
    config = {
        "ai_assistant_url": args.ai_url,
        "ai_timeout": args.timeout,
        "enable_ai_analysis": not args.no_ai,
    }

    ai_manager = AIUpdateManager(config)

    print("🔍 Detecting available updates...")

    try:
        # Get available updates
        update_result = await ai_manager.update_detector.run_full_update_check()
        updates = [
            UpdateInfo(**update_dict)
            for update_dict in update_result.get("updates", [])
        ]

        if not updates:
            print("✅ No updates available for analysis")
            return 0

        print(f"📦 Found {len(updates)} updates for AI analysis")

        # Limit updates if requested
        if args.max_updates:
            updates = updates[: args.max_updates]
            print(f"🔢 Analyzing first {len(updates)} updates")

        # Analyze each update
        analyses = {}
        for update in updates:
            print(f"\n🤖 Analyzing {update.component_name}...")
            analysis = await ai_manager.analyze_update_with_ai(update)
            analyses[update.component_name] = analysis

            if args.format == "summary":
                print_ai_analysis(update.component_name, analysis)

        # Generate summary
        if args.format == "summary":
            print(f"\n📊 ANALYSIS SUMMARY")
            risk_counts = {}
            rec_counts = {}

            for analysis in analyses.values():
                risk_level = analysis.risk_level.value
                recommendation = analysis.recommendation.value

                risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
                rec_counts[recommendation] = rec_counts.get(recommendation, 0) + 1

            print(f"   Risk Distribution:")
            for risk, count in risk_counts.items():
                print(f"      {risk.replace('_', ' ').title()}: {count}")

            print(f"   Recommendations:")
            for rec, count in rec_counts.items():
                print(f"      {rec.replace('_', ' ').title()}: {count}")

        elif args.format == "json":
            # JSON output
            json_output = {
                "analysis_timestamp": datetime.now().isoformat(),
                "total_updates": len(updates),
                "analyses": {
                    name: {
                        "risk_level": analysis.risk_level.value,
                        "recommendation": analysis.recommendation.value,
                        "confidence_score": analysis.confidence_score,
                        "reasoning": analysis.reasoning,
                        "security_impact": analysis.security_impact,
                        "compatibility_concerns": analysis.compatibility_concerns,
                        "testing_recommendations": analysis.testing_recommendations,
                        "estimated_downtime": analysis.estimated_downtime,
                    }
                    for name, analysis in analyses.items()
                },
            }
            print(json.dumps(json_output, indent=2))

        # Save results if requested
        if args.output:
            output_data = {
                "analysis_timestamp": datetime.now().isoformat(),
                "analyses": {
                    name: {
                        "analysis_id": analysis.analysis_id,
                        "component_name": analysis.component_name,
                        "component_version": analysis.component_version,
                        "risk_level": analysis.risk_level.value,
                        "recommendation": analysis.recommendation.value,
                        "confidence_score": analysis.confidence_score,
                        "reasoning": analysis.reasoning,
                        "security_impact": analysis.security_impact,
                        "compatibility_concerns": analysis.compatibility_concerns,
                        "testing_recommendations": analysis.testing_recommendations,
                        "rollback_strategy": analysis.rollback_strategy,
                        "estimated_downtime": analysis.estimated_downtime,
                        "dependencies_impact": analysis.dependencies_impact,
                        "business_impact": analysis.business_impact,
                        "timestamp": analysis.timestamp.isoformat(),
                    }
                    for name, analysis in analyses.items()
                },
            }

            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            print(f"\n💾 Analysis results saved to: {args.output}")

        return 0

    except Exception as e:
        print(f"❌ AI analysis failed: {e}")
        return 1


async def plan_command(args):
    """Execute AI planning command"""
    config = {
        "ai_assistant_url": args.ai_url,
        "ai_timeout": args.timeout,
        "enable_ai_analysis": not args.no_ai,
        "auto_approval_threshold": args.approval_threshold,
    }

    ai_manager = AIUpdateManager(config)

    print("🔍 Creating AI-powered update plan...")

    try:
        # Get available updates
        update_result = await ai_manager.update_detector.run_full_update_check()
        updates = [
            UpdateInfo(**update_dict)
            for update_dict in update_result.get("updates", [])
        ]

        if not updates:
            print("✅ No updates available for planning")
            return 0

        # Limit updates if requested
        if args.max_updates:
            updates = updates[: args.max_updates]

        print(f"📦 Planning for {len(updates)} updates")

        # Create update batch
        batch = UpdateBatch(
            batch_id=f"ai_batch_{int(datetime.now().timestamp())}",
            batch_type="ai_planned",
            updates=updates,
            created_at=datetime.now(),
        )

        # Analyze batch with AI
        print("🤖 Performing AI analysis...")
        analyses = await ai_manager.analyze_update_batch(batch)

        # Create update plan
        print("📋 Generating execution plan...")
        plan = await ai_manager.create_update_plan(batch, analyses)

        # Display plan
        if args.format == "summary":
            print_update_plan(plan)
        elif args.format == "json":
            plan_data = {
                "plan_id": plan.plan_id,
                "batch_id": plan.batch_id,
                "execution_strategy": plan.execution_strategy,
                "total_estimated_time": plan.total_estimated_time,
                "phases": plan.phases,
                "risk_mitigation_steps": plan.risk_mitigation_steps,
                "rollback_plan": plan.rollback_plan,
                "monitoring_points": plan.monitoring_points,
                "approval_required": plan.approval_required,
                "ai_confidence": plan.ai_confidence,
                "created_at": plan.created_at.isoformat(),
            }
            print(json.dumps(plan_data, indent=2))

        # Save plan if requested
        if args.output:
            plan_data = {
                "plan_id": plan.plan_id,
                "batch_id": plan.batch_id,
                "execution_strategy": plan.execution_strategy,
                "total_estimated_time": plan.total_estimated_time,
                "phases": plan.phases,
                "risk_mitigation_steps": plan.risk_mitigation_steps,
                "rollback_plan": plan.rollback_plan,
                "monitoring_points": plan.monitoring_points,
                "approval_required": plan.approval_required,
                "ai_confidence": plan.ai_confidence,
                "created_at": plan.created_at.isoformat(),
                "analyses": {
                    name: {
                        "risk_level": analysis.risk_level.value,
                        "recommendation": analysis.recommendation.value,
                        "confidence_score": analysis.confidence_score,
                        "reasoning": analysis.reasoning,
                    }
                    for name, analysis in analyses.items()
                },
            }

            with open(args.output, "w") as f:
                json.dump(plan_data, f, indent=2)
            print(f"\n💾 Update plan saved to: {args.output}")

        return 0

    except Exception as e:
        print(f"❌ Planning failed: {e}")
        return 1


async def recommend_command(args):
    """Execute AI recommendations command"""
    config = {
        "ai_assistant_url": args.ai_url,
        "ai_timeout": args.timeout,
        "enable_ai_analysis": not args.no_ai,
        "auto_approval_threshold": args.approval_threshold,
    }

    ai_manager = AIUpdateManager(config)

    print("🤖 Getting AI update recommendations...")

    try:
        # Get available updates
        update_result = await ai_manager.update_detector.run_full_update_check()
        updates = [
            UpdateInfo(**update_dict)
            for update_dict in update_result.get("updates", [])
        ]

        if not updates:
            print("✅ No updates available for recommendations")
            return 0

        # Get AI recommendations
        recommendations = await ai_manager.get_update_recommendations(updates)

        # Display recommendations
        if args.format == "summary":
            print(f"\n🎯 AI UPDATE RECOMMENDATIONS")
            print("=" * 60)

            auto_approve_count = 0
            for component, rec in recommendations.items():
                rec_icon = {
                    "apply_immediately": "⚡",
                    "apply_with_testing": "🧪",
                    "schedule_maintenance": "📅",
                    "defer_update": "⏸️",
                    "block_update": "🚫",
                }.get(rec["recommendation"], "❓")

                risk_icon = {
                    "very_low": "🟢",
                    "low": "🟡",
                    "medium": "🟠",
                    "high": "🔴",
                    "critical": "🚨",
                }.get(rec["risk_level"], "❓")

                auto_approve = "✅" if rec["should_auto_approve"] else "👤"
                if rec["should_auto_approve"]:
                    auto_approve_count += 1

                print(f"\n{rec_icon} {component}")
                print(
                    f"   {risk_icon} Risk: {rec['risk_level'].replace('_', ' ').title()}"
                )
                print(f"   🎯 Confidence: {rec['confidence']:.1%}")
                print(
                    f"   {auto_approve} Auto-approve: {'Yes' if rec['should_auto_approve'] else 'No'}"
                )
                print(f"   💭 {rec['reasoning']}")

            print(f"\n📊 SUMMARY")
            print(f"   Total Updates: {len(recommendations)}")
            print(f"   Auto-approvable: {auto_approve_count}")
            print(f"   Require Review: {len(recommendations) - auto_approve_count}")

        elif args.format == "json":
            output = {
                "recommendations_timestamp": datetime.now().isoformat(),
                "total_updates": len(recommendations),
                "auto_approvable": sum(
                    1 for r in recommendations.values() if r["should_auto_approve"]
                ),
                "recommendations": recommendations,
            }
            print(json.dumps(output, indent=2))

        # Save recommendations if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(recommendations, f, indent=2)
            print(f"\n💾 Recommendations saved to: {args.output}")

        return 0

    except Exception as e:
        print(f"❌ Recommendations failed: {e}")
        return 1


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Qubinode Navigator AI-Powered Update Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze updates with AI
  python3 ai_update_manager.py analyze --max-updates 10
  
  # Create AI-powered update plan
  python3 ai_update_manager.py plan --max-updates 5
  
  # Get AI recommendations
  python3 ai_update_manager.py recommend --approval-threshold 0.8
        """,
    )

    parser.add_argument(
        "--ai-url",
        default="http://localhost:8080",
        help="AI Assistant service URL (default: http://localhost:8080)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="AI request timeout in seconds (default: 30)",
    )

    parser.add_argument(
        "--no-ai", action="store_true", help="Disable AI analysis (use fallback logic)"
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze updates with AI")
    analyze_parser.add_argument(
        "--max-updates", type=int, help="Maximum updates to analyze"
    )
    analyze_parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )
    analyze_parser.add_argument("--output", help="Save analysis results to file")

    # Plan command
    plan_parser = subparsers.add_parser("plan", help="Create AI-powered update plan")
    plan_parser.add_argument(
        "--max-updates", type=int, help="Maximum updates to include in plan"
    )
    plan_parser.add_argument(
        "--approval-threshold",
        type=float,
        default=0.8,
        help="Auto-approval confidence threshold (default: 0.8)",
    )
    plan_parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )
    plan_parser.add_argument("--output", help="Save plan to file")

    # Recommend command
    recommend_parser = subparsers.add_parser(
        "recommend", help="Get AI update recommendations"
    )
    recommend_parser.add_argument(
        "--approval-threshold",
        type=float,
        default=0.8,
        help="Auto-approval confidence threshold (default: 0.8)",
    )
    recommend_parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )
    recommend_parser.add_argument("--output", help="Save recommendations to file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Setup logging
    setup_logging(args.log_level)

    try:
        if args.command == "analyze":
            return await analyze_command(args)
        elif args.command == "plan":
            return await plan_command(args)
        elif args.command == "recommend":
            return await recommend_command(args)
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
