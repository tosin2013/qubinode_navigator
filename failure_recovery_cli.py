#!/usr/bin/env python3
"""
Failure Recovery CLI - Test failure diagnosis and recovery locally

Usage:
    python3 failure_recovery_cli.py diagnose --plugin <name> --error <message>
    python3 failure_recovery_cli.py plan <plugin> --analysis-file <json>
    python3 failure_recovery_cli.py execute <plugin> --recovery-file <json>
    python3 failure_recovery_cli.py detect-shadows --scan-hours 1
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

# Must be before project imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402

# Try to import ShadowErrorDetector, but make it optional
try:
    from ai_assistant.src.shadow_error_detector import ShadowErrorDetector
except ImportError:
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai-assistant"))
        from src.shadow_error_detector import ShadowErrorDetector
    except ImportError:
        ShadowErrorDetector = None

from core.base_plugin import DiagnosticContext
from core.failure_analyzer import (
    FailureAnalyzer,
    RootCauseCategory,
)
from core.recovery_planner import RecoveryPlanner


def diagnose_failure(args):
    """Diagnose a failure using FailureAnalyzer"""

    print(f"\n{'='*60}")
    print(f"Failure Diagnosis: {args.plugin}")
    print(f"{'='*60}\n")

    # Initialize analyzer
    analyzer = FailureAnalyzer()

    # Create diagnostic context
    ctx = DiagnosticContext(
        plugin_name=args.plugin,
        failure_timestamp=datetime.now(),
        error_message=args.error,
    )

    print("[INFO] Collecting system diagnostics...")
    ctx.service_health = {
        "libvirtd": DiagnosticContext.get_service_status("libvirtd"),
        "podman": DiagnosticContext.get_service_status("podman"),
        "airflow": DiagnosticContext.get_service_status("airflow"),
    }
    ctx.system_resources = DiagnosticContext.get_system_resources()
    ctx.recent_logs = DiagnosticContext.get_plugin_logs(args.plugin)

    print("[INFO] Analyzing failure...")
    analysis = analyzer.analyze(ctx)

    # Output results
    print(f"\nRoot Cause: {analysis.root_cause.value}")
    print(f"Confidence: {analysis.confidence:.0%}")
    print(f"Severity: {analysis.severity.value}")
    print(f"Description: {analysis.root_cause_description}\n")

    if analysis.pattern_matches:
        print(f"Pattern Matches: {', '.join(analysis.pattern_matches)}")

    if analysis.affected_services:
        print(f"Affected Services: {', '.join(analysis.affected_services)}")

    if analysis.correlated_failures:
        print(f"Correlated Failures: {', '.join(analysis.correlated_failures)}")

    print("\nRecommended Actions:")
    for i, action in enumerate(analysis.recommended_actions, 1):
        print(f"  {i}. {action}")

    # Save analysis to file if requested
    if args.output:
        analysis_dict = {
            "timestamp": analysis.timestamp.isoformat(),
            "plugin": analysis.failed_plugin,
            "root_cause": analysis.root_cause.value,
            "confidence": analysis.confidence,
            "severity": analysis.severity.value,
            "affected_services": analysis.affected_services,
            "pattern_matches": analysis.pattern_matches,
            "recommended_actions": analysis.recommended_actions,
        }

        with open(args.output, "w") as f:
            json.dump(analysis_dict, f, indent=2)

        print(f"\n[OK] Analysis saved to {args.output}")


def plan_recovery(args):
    """Create recovery plan from failure analysis"""

    print(f"\n{'='*60}")
    print("Recovery Planning")
    print(f"{'='*60}\n")

    # Load analysis
    with open(args.analysis_file, "r") as f:
        analysis_dict = json.load(f)

    # Recreate FailureAnalysis object
    from core.failure_analyzer import FailureAnalysis, FailureSeverity

    analysis = FailureAnalysis(
        timestamp=datetime.fromisoformat(analysis_dict["timestamp"]),
        failed_plugin=analysis_dict["plugin"],
        error_message="(from saved analysis)",
        root_cause=RootCauseCategory[analysis_dict["root_cause"].upper()],
        root_cause_description="",
        confidence=analysis_dict["confidence"],
        severity=FailureSeverity[analysis_dict["severity"].upper()],
        affected_services=analysis_dict.get("affected_services", []),
    )

    # Create recovery plan
    planner = RecoveryPlanner(
        github_token=os.getenv("GITHUB_TOKEN"),
        github_repo=os.getenv("GITHUB_REPOSITORY"),
    )
    plan = planner.plan_recovery(analysis)

    # Output plan
    print(f"Recovery Options for: {plan.failed_plugin}\n")

    for i, option in enumerate(plan.recovery_options, 1):
        print(f"{i}. {option.action_type.value.upper()}")
        print(f"   Priority: {option.priority}/3")
        print(f"   Confidence: {option.confidence:.0%}")
        print(f"   Risk: {option.risk_level}")
        print(f"   Duration: {option.estimated_duration_seconds}s")
        print(f"   Description: {option.description}\n")
        print("   Steps:")
        for step in option.steps:
            print(f"     - {step}")
        print()

    # Save plan as markdown
    if args.output:
        markdown = plan.to_markdown()
        with open(args.output, "w") as f:
            f.write(markdown)
        print(f"[OK] Recovery plan saved to {args.output}")


def execute_recovery(args):
    """Execute a recovery option"""

    print(f"\n{'='*60}")
    print("Recovery Execution")
    print(f"{'='*60}\n")

    # This would require full integration with plugin system
    # For now, just show what would be executed
    print("[INFO] Recovery execution requires active plugin system")
    print("[INFO] Use: python3 qubinode_cli.py execute --plugins <plugin_name>")


def detect_shadows(args):
    """Scan for shadow errors"""

    if ShadowErrorDetector is None:
        print(f"\n{'='*60}")
        print("Shadow Error Detection")
        print(f"{'='*60}\n")
        print("[ERROR] ShadowErrorDetector module not available")
        print("[INFO] Install ai-assistant dependencies to enable shadow error detection")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("Shadow Error Detection")
    print(f"{'='*60}\n")

    async def run_scan():
        detector = ShadowErrorDetector()

        print(f"[INFO] Scanning for shadow errors (last {args.scan_hours} hour(s))...")
        errors = await detector.scan_for_shadow_errors()

        if errors:
            print(f"\n[WARN] Found {len(errors)} shadow errors:\n")
            for error in errors:
                print(f"- {error.error_type}: {error.description}")
                print(f"  DAG: {error.dag_id}")
                print(f"  Confidence: {error.correlation_confidence:.0%}\n")
        else:
            print("[OK] No shadow errors detected")

    asyncio.run(run_scan())


def main():
    parser = argparse.ArgumentParser(description="Failure Recovery CLI - Test failure diagnosis and recovery")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # diagnose command
    diagnose_parser = subparsers.add_parser("diagnose", help="Diagnose a failure")
    diagnose_parser.add_argument("--plugin", required=True, help="Plugin name")
    diagnose_parser.add_argument("--error", required=True, help="Error message")
    diagnose_parser.add_argument("--output", help="Save analysis to file (JSON)")
    diagnose_parser.set_defaults(func=diagnose_failure)

    # plan command
    plan_parser = subparsers.add_parser("plan", help="Create recovery plan")
    plan_parser.add_argument("--analysis-file", required=True, help="Path to analysis JSON")
    plan_parser.add_argument("--output", help="Save plan to file (Markdown)")
    plan_parser.set_defaults(func=plan_recovery)

    # execute command
    exec_parser = subparsers.add_parser("execute", help="Execute recovery")
    exec_parser.add_argument("plugin", help="Plugin to recover")
    exec_parser.add_argument("--recovery-file", help="Path to recovery plan")
    exec_parser.set_defaults(func=execute_recovery)

    # detect-shadows command
    shadow_parser = subparsers.add_parser("detect-shadows", help="Detect shadow errors")
    shadow_parser.add_argument("--scan-hours", type=int, default=1, help="Hours to scan")
    shadow_parser.set_defaults(func=detect_shadows)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        args.func(args)
    except Exception as e:
        print(f"\n[ERROR] {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
