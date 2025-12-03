#!/usr/bin/env python3
"""
Qubinode Navigator Monitoring Manager CLI

Command-line interface for managing monitoring and alerting system,
viewing metrics, managing alerts, and configuring monitoring rules.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.monitoring_manager import AlertSeverity, MetricType, MonitoringManager


async def main():
    """Main CLI entry point"""

    parser = argparse.ArgumentParser(
        description="Qubinode Navigator Monitoring Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View monitoring status
  python monitoring_manager.py status

  # List active alerts
  python monitoring_manager.py alerts --status active

  # View metrics summary
  python monitoring_manager.py metrics --metric-name cpu_usage --hours 6

  # Create test alert
  python monitoring_manager.py create-alert --title "Test Alert" --severity warning

  # Resolve alert
  python monitoring_manager.py resolve-alert --alert-id alert_123 --notes "Issue resolved"

  # View alert statistics
  python monitoring_manager.py stats --format json
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    status_parser = subparsers.add_parser(
        "status", help="Show monitoring system status"
    )
    status_parser.add_argument(
        "--format", choices=["summary", "json"], default="summary", help="Output format"
    )

    # Alerts command
    alerts_parser = subparsers.add_parser("alerts", help="List and manage alerts")
    alerts_parser.add_argument(
        "--status",
        choices=["active", "resolved", "all"],
        default="active",
        help="Filter alerts by status",
    )
    alerts_parser.add_argument(
        "--severity",
        choices=["info", "warning", "error", "critical"],
        help="Filter alerts by severity",
    )
    alerts_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # Metrics command
    metrics_parser = subparsers.add_parser("metrics", help="View metrics data")
    metrics_parser.add_argument("--metric-name", help="Specific metric name to view")
    metrics_parser.add_argument(
        "--hours", type=int, default=24, help="Hours of data to show"
    )
    metrics_parser.add_argument(
        "--format", choices=["summary", "json"], default="summary", help="Output format"
    )

    # Create alert command
    create_alert_parser = subparsers.add_parser(
        "create-alert", help="Create test alert"
    )
    create_alert_parser.add_argument("--title", required=True, help="Alert title")
    create_alert_parser.add_argument("--description", help="Alert description")
    create_alert_parser.add_argument(
        "--severity",
        choices=["info", "warning", "error", "critical"],
        default="warning",
        help="Alert severity",
    )
    create_alert_parser.add_argument("--source", default="cli", help="Alert source")

    # Resolve alert command
    resolve_parser = subparsers.add_parser("resolve-alert", help="Resolve active alert")
    resolve_parser.add_argument("--alert-id", required=True, help="Alert ID to resolve")
    resolve_parser.add_argument("--notes", help="Resolution notes")

    # Statistics command
    stats_parser = subparsers.add_parser("stats", help="Show monitoring statistics")
    stats_parser.add_argument(
        "--format", choices=["summary", "json"], default="summary", help="Output format"
    )

    # Test command
    test_parser = subparsers.add_parser("test", help="Test monitoring system")
    test_parser.add_argument(
        "--component",
        choices=["alerts", "metrics", "rules"],
        default="alerts",
        help="Component to test",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize monitoring manager
    config = {
        "monitoring_enabled": True,
        "alert_channels": ["log"],
        "metrics_storage_path": "data/metrics",
        "alerts_storage_path": "data/alerts",
    }

    monitoring_manager = MonitoringManager(config)

    # Execute command
    if args.command == "status":
        await handle_status_command(monitoring_manager, args)
    elif args.command == "alerts":
        await handle_alerts_command(monitoring_manager, args)
    elif args.command == "metrics":
        await handle_metrics_command(monitoring_manager, args)
    elif args.command == "create-alert":
        await handle_create_alert_command(monitoring_manager, args)
    elif args.command == "resolve-alert":
        await handle_resolve_alert_command(monitoring_manager, args)
    elif args.command == "stats":
        await handle_stats_command(monitoring_manager, args)
    elif args.command == "test":
        await handle_test_command(monitoring_manager, args)


async def handle_status_command(monitoring_manager: MonitoringManager, args):
    """Handle status command"""

    try:
        alert_stats = monitoring_manager.get_alert_statistics()
        metrics_summary = monitoring_manager.get_metrics_summary()

        status_data = {
            "monitoring_enabled": monitoring_manager.monitoring_enabled,
            "alert_channels": monitoring_manager.alert_channels,
            "active_alerts": alert_stats["active_alerts"],
            "total_alerts": alert_stats["total_alerts"],
            "total_metrics": metrics_summary["total_metrics"],
            "monitoring_rules": len(monitoring_manager.monitoring_rules),
            "storage_paths": {
                "metrics": str(monitoring_manager.metrics_storage_path),
                "alerts": str(monitoring_manager.alerts_storage_path),
            },
        }

        if args.format == "json":
            print(json.dumps(status_data, indent=2))
        else:
            print("=== Monitoring System Status ===")
            print(f"Monitoring Enabled: {status_data['monitoring_enabled']}")
            print(f"Alert Channels: {', '.join(status_data['alert_channels'])}")
            print(f"Active Alerts: {status_data['active_alerts']}")
            print(f"Total Alerts: {status_data['total_alerts']}")
            print(f"Total Metrics: {status_data['total_metrics']}")
            print(f"Monitoring Rules: {status_data['monitoring_rules']}")
            print(f"Metrics Storage: {status_data['storage_paths']['metrics']}")
            print(f"Alerts Storage: {status_data['storage_paths']['alerts']}")

    except Exception as e:
        print(f"Error getting monitoring status: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_alerts_command(monitoring_manager: MonitoringManager, args):
    """Handle alerts command"""

    try:
        alerts = []

        # Get alerts based on status filter
        if args.status in ["active", "all"]:
            for alert in monitoring_manager.active_alerts.values():
                if not args.severity or alert.severity.value == args.severity:
                    alerts.append(
                        {
                            "alert_id": alert.alert_id,
                            "title": alert.title,
                            "severity": alert.severity.value,
                            "source": alert.source,
                            "timestamp": alert.timestamp.isoformat(),
                            "status": "active",
                        }
                    )

        if args.status in ["resolved", "all"]:
            for alert in monitoring_manager.alert_history:
                if not args.severity or alert.severity.value == args.severity:
                    alerts.append(
                        {
                            "alert_id": alert.alert_id,
                            "title": alert.title,
                            "severity": alert.severity.value,
                            "source": alert.source,
                            "timestamp": alert.timestamp.isoformat(),
                            "resolved_at": (
                                alert.resolved_at.isoformat()
                                if alert.resolved_at
                                else None
                            ),
                            "status": "resolved",
                        }
                    )

        if args.format == "json":
            print(json.dumps(alerts, indent=2))
        else:
            if not alerts:
                print("No alerts found")
                return

            print("=== Alerts ===")
            print(
                f"{'Alert ID':<20} {'Title':<30} {'Severity':<10} {'Status':<10} {'Time':<20}"
            )
            print("-" * 95)

            for alert in sorted(alerts, key=lambda x: x["timestamp"], reverse=True):
                timestamp = datetime.fromisoformat(alert["timestamp"]).strftime(
                    "%Y-%m-%d %H:%M"
                )
                print(
                    f"{alert['alert_id']:<20} {alert['title'][:29]:<30} {alert['severity']:<10} {alert['status']:<10} {timestamp:<20}"
                )

    except Exception as e:
        print(f"Error listing alerts: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_metrics_command(monitoring_manager: MonitoringManager, args):
    """Handle metrics command"""

    try:
        metrics_summary = monitoring_manager.get_metrics_summary(
            metric_name=args.metric_name, hours=args.hours
        )

        if args.format == "json":
            print(json.dumps(metrics_summary, indent=2))
        else:
            print("=== Metrics Summary ===")
            print(f"Time Range: {args.hours} hours")
            print(f"Total Metrics: {metrics_summary['total_metrics']}")

            if args.metric_name:
                print(f"Metric Name: {args.metric_name}")
            else:
                print(
                    f"Metric Names: {', '.join(metrics_summary.get('metric_names', []))}"
                )

            if metrics_summary["total_metrics"] > 0:
                print(f"Oldest Metric: {metrics_summary['oldest_metric']}")
                print(f"Newest Metric: {metrics_summary['newest_metric']}")

    except Exception as e:
        print(f"Error getting metrics: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_create_alert_command(monitoring_manager: MonitoringManager, args):
    """Handle create alert command"""

    try:
        severity = AlertSeverity(args.severity)
        description = args.description or f"Test alert created via CLI"

        alert = await monitoring_manager.create_alert(
            title=args.title,
            description=description,
            severity=severity,
            source=args.source,
            metadata={"created_via": "cli", "test_alert": True},
        )

        print(f"✓ Created alert: {alert.alert_id}")
        print(f"  Title: {alert.title}")
        print(f"  Severity: {alert.severity.value}")
        print(f"  Source: {alert.source}")
        print(f"  Time: {alert.timestamp}")

    except Exception as e:
        print(f"Error creating alert: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_resolve_alert_command(monitoring_manager: MonitoringManager, args):
    """Handle resolve alert command"""

    try:
        if args.alert_id not in monitoring_manager.active_alerts:
            print(f"Alert {args.alert_id} not found in active alerts", file=sys.stderr)
            sys.exit(1)

        await monitoring_manager.resolve_alert(args.alert_id, args.notes)

        print(f"✓ Resolved alert: {args.alert_id}")
        if args.notes:
            print(f"  Resolution notes: {args.notes}")

    except Exception as e:
        print(f"Error resolving alert: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_stats_command(monitoring_manager: MonitoringManager, args):
    """Handle statistics command"""

    try:
        alert_stats = monitoring_manager.get_alert_statistics()
        metrics_summary = monitoring_manager.get_metrics_summary()

        stats_data = {
            "alerts": alert_stats,
            "metrics": metrics_summary,
            "monitoring_rules": {
                "total_rules": len(monitoring_manager.monitoring_rules),
                "enabled_rules": len(
                    [
                        r
                        for r in monitoring_manager.monitoring_rules.values()
                        if r.enabled
                    ]
                ),
            },
        }

        if args.format == "json":
            print(json.dumps(stats_data, indent=2))
        else:
            print("=== Monitoring Statistics ===")

            print("\nAlerts:")
            print(f"  Total: {alert_stats['total_alerts']}")
            print(f"  Active: {alert_stats['active_alerts']}")
            print(f"  Resolved: {alert_stats['resolved_alerts']}")
            print(f"  Resolution Rate: {alert_stats['resolution_rate']}%")

            if alert_stats["severity_breakdown"]:
                print("  Severity Breakdown:")
                for severity, count in alert_stats["severity_breakdown"].items():
                    print(f"    {severity}: {count}")

            print(f"\nMetrics:")
            print(f"  Total Metrics (24h): {metrics_summary['total_metrics']}")
            print(
                f"  Unique Metric Names: {len(metrics_summary.get('metric_names', []))}"
            )

            print(f"\nMonitoring Rules:")
            print(f"  Total Rules: {stats_data['monitoring_rules']['total_rules']}")
            print(f"  Enabled Rules: {stats_data['monitoring_rules']['enabled_rules']}")

    except Exception as e:
        print(f"Error getting statistics: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_test_command(monitoring_manager: MonitoringManager, args):
    """Handle test command"""

    try:
        print(f"Testing monitoring system component: {args.component}")

        if args.component == "alerts":
            # Test alert creation and resolution
            print("✓ Testing alert creation...")
            alert = await monitoring_manager.create_alert(
                title="Test Alert",
                description="This is a test alert",
                severity=AlertSeverity.INFO,
                source="test_cli",
                metadata={"test": True},
            )
            print(f"  Created alert: {alert.alert_id}")

            print("✓ Testing alert resolution...")
            await monitoring_manager.resolve_alert(alert.alert_id, "Test completed")
            print(f"  Resolved alert: {alert.alert_id}")

        elif args.component == "metrics":
            # Test metric recording
            print("✓ Testing metric recording...")
            await monitoring_manager.record_metric(
                "test_metric", 42.0, MetricType.GAUGE
            )
            await monitoring_manager.record_metric(
                "test_counter", 1.0, MetricType.COUNTER
            )
            print("  Recorded test metrics")

            # Test metrics summary
            summary = monitoring_manager.get_metrics_summary()
            print(f"  Total metrics: {summary['total_metrics']}")

        elif args.component == "rules":
            # Test monitoring rules
            print("✓ Testing monitoring rules...")
            print(f"  Total rules: {len(monitoring_manager.monitoring_rules)}")
            print(
                f"  Enabled rules: {len([r for r in monitoring_manager.monitoring_rules.values() if r.enabled])}"
            )

            # List rule names
            rule_names = [
                rule.name for rule in monitoring_manager.monitoring_rules.values()
            ]
            print(f"  Rule names: {', '.join(rule_names)}")

        print("✓ All tests passed")

    except Exception as e:
        print(f"Error running tests: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
