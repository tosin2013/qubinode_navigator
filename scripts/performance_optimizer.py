#!/usr/bin/env python3
"""
Qubinode Navigator Performance Optimizer CLI

Command-line interface for performance monitoring, optimization,
and resource tuning for deployment operations.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.performance_optimizer import OptimizationLevel, PerformanceOptimizer


async def main():
    """Main CLI entry point"""

    parser = argparse.ArgumentParser(
        description="Qubinode Navigator Performance Optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show performance status
  python performance_optimizer.py status

  # Start performance monitoring
  python performance_optimizer.py monitor --duration 300

  # Get optimization recommendations
  python performance_optimizer.py recommendations --impact high

  # Apply optimization
  python performance_optimizer.py optimize --recommendation-id opt_123

  # Clear performance cache
  python performance_optimizer.py clear-cache

  # Test performance optimization
  python performance_optimizer.py test --component monitoring
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show performance status")
    status_parser.add_argument(
        "--format", choices=["summary", "json"], default="summary", help="Output format"
    )

    # Monitor command
    monitor_parser = subparsers.add_parser(
        "monitor", help="Start performance monitoring"
    )
    monitor_parser.add_argument(
        "--duration", type=int, default=60, help="Monitoring duration in seconds"
    )
    monitor_parser.add_argument(
        "--optimization-level",
        choices=["conservative", "balanced", "aggressive"],
        default="balanced",
        help="Optimization level",
    )
    monitor_parser.add_argument(
        "--interval", type=int, default=30, help="Monitoring interval in seconds"
    )

    # Recommendations command
    rec_parser = subparsers.add_parser(
        "recommendations", help="Get optimization recommendations"
    )
    rec_parser.add_argument(
        "--impact", choices=["low", "medium", "high"], help="Filter by impact level"
    )
    rec_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # Optimize command
    opt_parser = subparsers.add_parser("optimize", help="Apply optimization")
    opt_parser.add_argument(
        "--recommendation-id", required=True, help="Recommendation ID to apply"
    )

    # Clear cache command
    cache_parser = subparsers.add_parser("clear-cache", help="Clear performance cache")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test performance optimization")
    test_parser.add_argument(
        "--component",
        choices=["monitoring", "optimization", "caching"],
        default="monitoring",
        help="Component to test",
    )

    # Metrics command
    metrics_parser = subparsers.add_parser("metrics", help="Show performance metrics")
    metrics_parser.add_argument(
        "--hours", type=int, default=1, help="Hours of metrics to show"
    )
    metrics_parser.add_argument(
        "--format", choices=["summary", "json"], default="summary", help="Output format"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize performance optimizer
    config = {
        "optimization_level": getattr(args, "optimization_level", "balanced"),
        "monitoring_interval": getattr(args, "interval", 30),
        "auto_optimization_enabled": True,
        "cache_enabled": True,
        "thread_pool_size": 4,
        "process_pool_size": 2,
        "connection_pool_size": 10,
    }

    optimizer = PerformanceOptimizer(config)

    # Execute command
    try:
        if args.command == "status":
            await handle_status_command(optimizer, args)
        elif args.command == "monitor":
            await handle_monitor_command(optimizer, args)
        elif args.command == "recommendations":
            await handle_recommendations_command(optimizer, args)
        elif args.command == "optimize":
            await handle_optimize_command(optimizer, args)
        elif args.command == "clear-cache":
            await handle_clear_cache_command(optimizer, args)
        elif args.command == "test":
            await handle_test_command(optimizer, args)
        elif args.command == "metrics":
            await handle_metrics_command(optimizer, args)
    finally:
        await optimizer.cleanup()


async def handle_status_command(optimizer: PerformanceOptimizer, args):
    """Handle status command"""

    try:
        # Start monitoring briefly to get current metrics
        await optimizer.start_monitoring()
        await asyncio.sleep(2)  # Wait for initial metrics

        summary = optimizer.get_performance_summary()

        if args.format == "json":
            print(json.dumps(summary, indent=2))
        else:
            print("=== Performance Optimizer Status ===")
            print(f"Status: {summary['status'].replace('_', ' ').title()}")
            print(f"Optimization Level: {summary['optimization_level'].title()}")

            if summary["status"] == "active":
                print("\n=== Current Metrics ===")
                metrics = summary["current_metrics"]
                print(f"CPU Usage: {metrics['cpu_usage']}%")
                print(f"Memory Usage: {metrics['memory_usage']}%")
                print(f"Disk Usage: {metrics['disk_usage']}%")
                print(f"Process Count: {metrics['process_count']}")
                print(f"Load Average: {', '.join(map(str, metrics['load_average']))}")

                print("\n=== Resource Limits ===")
                for resource, limits in summary["resource_limits"].items():
                    status_symbol = {
                        "normal": "✓",
                        "warning": "⚠",
                        "critical": "✗",
                    }.get(limits["status"], "•")
                    print(
                        f"  {status_symbol} {resource.upper()}: {limits['current']}% (limit: {limits['soft_limit']}%/{limits['hard_limit']}%)"
                    )

                print(f"\n=== Optimization Recommendations ===")
                print(f"Active High-Impact: {summary['active_recommendations']}")
                print(f"Total Recommendations: {summary['total_recommendations']}")

                print(f"\n=== Cache Statistics ===")
                cache_stats = summary["cache_stats"]
                print(f"Cache Enabled: {cache_stats['enabled']}")
                print(f"Cache Entries: {cache_stats['entries']}")

    except Exception as e:
        print(f"Error getting performance status: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_monitor_command(optimizer: PerformanceOptimizer, args):
    """Handle monitor command"""

    try:
        print(f"Starting performance monitoring for {args.duration} seconds...")
        print(f"Optimization Level: {args.optimization_level}")
        print(f"Monitoring Interval: {args.interval} seconds")

        # Start monitoring
        await optimizer.start_monitoring()

        # Monitor for specified duration
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < args.duration:
            await asyncio.sleep(5)  # Update every 5 seconds

            # Get current summary
            summary = optimizer.get_performance_summary()

            if summary["status"] == "active":
                metrics = summary["current_metrics"]
                print(
                    f"\r[{datetime.now().strftime('%H:%M:%S')}] "
                    f"CPU: {metrics['cpu_usage']}% | "
                    f"MEM: {metrics['memory_usage']}% | "
                    f"DISK: {metrics['disk_usage']}% | "
                    f"PROC: {metrics['process_count']}",
                    end="",
                    flush=True,
                )

        print(f"\n\nMonitoring completed after {args.duration} seconds")

        # Show final recommendations
        recommendations = optimizer.get_optimization_recommendations("high")
        if recommendations:
            print(f"\n=== High-Impact Optimization Opportunities ===")
            for rec in recommendations[:3]:  # Show top 3
                print(f"• {rec.description}")
                print(
                    f"  Current: {rec.current_value}, Recommended: {rec.recommended_value}"
                )
                print(f"  Estimated Improvement: {rec.estimated_improvement}%")

    except Exception as e:
        print(f"Error during monitoring: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_recommendations_command(optimizer: PerformanceOptimizer, args):
    """Handle recommendations command"""

    try:
        # Start monitoring briefly to generate recommendations
        await optimizer.start_monitoring()
        await asyncio.sleep(5)  # Wait for recommendations to be generated

        recommendations = optimizer.get_optimization_recommendations(args.impact)

        if args.format == "json":
            rec_data = [
                {
                    "recommendation_id": rec.recommendation_id,
                    "resource_type": rec.resource_type.value,
                    "current_value": rec.current_value,
                    "recommended_value": rec.recommended_value,
                    "impact_level": rec.impact_level,
                    "description": rec.description,
                    "implementation_steps": rec.implementation_steps,
                    "estimated_improvement": rec.estimated_improvement,
                }
                for rec in recommendations
            ]
            print(json.dumps(rec_data, indent=2))
        else:
            if not recommendations:
                print("No optimization recommendations found")
                return

            print("=== Optimization Recommendations ===")
            print(
                f"{'ID':<20} {'Resource':<10} {'Impact':<8} {'Current':<10} {'Recommended':<12} {'Improvement':<12}"
            )
            print("-" * 85)

            for rec in recommendations:
                print(
                    f"{rec.recommendation_id:<20} {rec.resource_type.value:<10} {rec.impact_level:<8} "
                    f"{rec.current_value:<10.1f} {rec.recommended_value:<12.1f} {rec.estimated_improvement:<12.1f}%"
                )

            print(f"\nTotal recommendations: {len(recommendations)}")

            # Show details for high-impact recommendations
            high_impact = [r for r in recommendations if r.impact_level == "high"]
            if high_impact:
                print(f"\n=== High-Impact Recommendation Details ===")
                for rec in high_impact[:2]:  # Show first 2
                    print(f"\n{rec.description}")
                    print("Implementation Steps:")
                    for i, step in enumerate(rec.implementation_steps, 1):
                        print(f"  {i}. {step}")

    except Exception as e:
        print(f"Error getting recommendations: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_optimize_command(optimizer: PerformanceOptimizer, args):
    """Handle optimize command"""

    try:
        print(f"Applying optimization: {args.recommendation_id}")

        success = await optimizer.apply_optimization(args.recommendation_id)

        if success:
            print("✓ Optimization applied successfully")
        else:
            print("✗ Failed to apply optimization")
            sys.exit(1)

    except Exception as e:
        print(f"Error applying optimization: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_clear_cache_command(optimizer: PerformanceOptimizer, args):
    """Handle clear cache command"""

    try:
        optimizer.clear_cache()
        print("✓ Performance cache cleared")

    except Exception as e:
        print(f"Error clearing cache: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_test_command(optimizer: PerformanceOptimizer, args):
    """Handle test command"""

    try:
        print(f"Testing performance optimization component: {args.component}")

        if args.component == "monitoring":
            print("✓ Testing performance monitoring...")

            # Test monitoring start/stop
            await optimizer.start_monitoring()
            print("  Monitoring started")

            await asyncio.sleep(2)
            summary = optimizer.get_performance_summary()
            print(f"  Collected metrics: {summary['status']}")

            await optimizer.stop_monitoring()
            print("  Monitoring stopped")

        elif args.component == "optimization":
            print("✓ Testing optimization engine...")

            # Test recommendation generation
            await optimizer.start_monitoring()
            await asyncio.sleep(3)

            recommendations = optimizer.get_optimization_recommendations()
            print(f"  Generated recommendations: {len(recommendations)}")

        elif args.component == "caching":
            print("✓ Testing caching system...")

            # Test cache operations
            optimizer._cache["test_key"] = "test_value"
            print(f"  Cache entries: {len(optimizer._cache)}")

            optimizer.clear_cache()
            print(f"  Cache cleared: {len(optimizer._cache)} entries")

        print("✓ All tests passed")

    except Exception as e:
        print(f"Error running tests: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_metrics_command(optimizer: PerformanceOptimizer, args):
    """Handle metrics command"""

    try:
        # Start monitoring to collect metrics
        await optimizer.start_monitoring()
        await asyncio.sleep(5)  # Collect some metrics

        if args.format == "json":
            metrics_data = []
            for metric in optimizer.performance_history[
                -args.hours * 2 :
            ]:  # Approximate
                metrics_data.append(
                    {
                        "timestamp": metric.timestamp.isoformat(),
                        "cpu_usage": metric.cpu_usage,
                        "memory_usage": metric.memory_usage,
                        "disk_usage": metric.disk_usage,
                        "process_count": metric.process_count,
                        "load_average": metric.load_average,
                    }
                )
            print(json.dumps(metrics_data, indent=2))
        else:
            print("=== Performance Metrics ===")
            print(f"Time Range: Last {args.hours} hour(s)")
            print(f"Total Data Points: {len(optimizer.performance_history)}")

            if optimizer.performance_history:
                recent = optimizer.performance_history[-5:]  # Last 5 measurements

                print(f"\nRecent Measurements:")
                print(
                    f"{'Time':<20} {'CPU%':<8} {'Memory%':<10} {'Disk%':<8} {'Processes':<10}"
                )
                print("-" * 60)

                for metric in recent:
                    time_str = metric.timestamp.strftime("%H:%M:%S")
                    print(
                        f"{time_str:<20} {metric.cpu_usage:<8.1f} {metric.memory_usage:<10.1f} "
                        f"{metric.disk_usage:<8.1f} {metric.process_count:<10}"
                    )

                # Calculate averages
                avg_cpu = sum(m.cpu_usage for m in recent) / len(recent)
                avg_mem = sum(m.memory_usage for m in recent) / len(recent)
                avg_disk = sum(m.disk_usage for m in recent) / len(recent)

                print(f"\nAverages:")
                print(
                    f"CPU: {avg_cpu:.1f}%, Memory: {avg_mem:.1f}%, Disk: {avg_disk:.1f}%"
                )
            else:
                print("No metrics data available")

    except Exception as e:
        print(f"Error getting metrics: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
