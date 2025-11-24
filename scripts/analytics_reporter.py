#!/usr/bin/env python3
"""
Qubinode Navigator Analytics Reporter CLI

Command-line interface for generating analytics reports, dashboards,
and success rate tracking for update deployments.
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

from core.analytics_engine import AnalyticsEngine, TimeRange
from core.reporting_system import ReportingSystem


async def main():
    """Main CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description="Qubinode Navigator Analytics Reporter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate dashboard
  python analytics_reporter.py dashboard --time-range last_7d

  # Calculate success rates
  python analytics_reporter.py success-rates --time-range last_30d --format json

  # Generate executive summary report
  python analytics_reporter.py report --type executive_summary --time-range last_7d

  # Analyze trends
  python analytics_reporter.py trends --metric success_rate --time-range last_30d

  # List recent reports
  python analytics_reporter.py list-reports --limit 5

  # Export dashboard as HTML
  python analytics_reporter.py export-html --dashboard-id dashboard_123
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Generate analytics dashboard')
    dashboard_parser.add_argument('--time-range', choices=['last_24h', 'last_7d', 'last_30d', 'last_90d'],
                                 default='last_7d', help='Time range for dashboard')
    dashboard_parser.add_argument('--format', choices=['json', 'summary'], default='json',
                                 help='Output format')
    
    # Success rates command
    success_parser = subparsers.add_parser('success-rates', help='Calculate deployment success rates')
    success_parser.add_argument('--time-range', choices=['last_24h', 'last_7d', 'last_30d', 'last_90d'],
                                default='last_30d', help='Time range for analysis')
    success_parser.add_argument('--format', choices=['json', 'summary'], default='summary',
                               help='Output format')
    
    # Performance command
    performance_parser = subparsers.add_parser('performance', help='Analyze deployment performance')
    performance_parser.add_argument('--time-range', choices=['last_24h', 'last_7d', 'last_30d', 'last_90d'],
                                    default='last_30d', help='Time range for analysis')
    performance_parser.add_argument('--format', choices=['json', 'summary'], default='summary',
                                   help='Output format')
    
    # Trends command
    trends_parser = subparsers.add_parser('trends', help='Analyze metric trends')
    trends_parser.add_argument('--metric', required=True, 
                              choices=['success_rate', 'deployment_duration', 'failure_rate'],
                              help='Metric to analyze')
    trends_parser.add_argument('--time-range', choices=['last_24h', 'last_7d', 'last_30d', 'last_90d'],
                              default='last_30d', help='Time range for trend analysis')
    trends_parser.add_argument('--format', choices=['json', 'summary'], default='summary',
                              help='Output format')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate specific report type')
    report_parser.add_argument('--type', required=True,
                              choices=['executive_summary', 'operational_dashboard', 'technical_analysis', 'success_rate_tracking'],
                              help='Type of report to generate')
    report_parser.add_argument('--time-range', choices=['last_24h', 'last_7d', 'last_30d', 'last_90d'],
                              default='last_30d', help='Time range for report')
    report_parser.add_argument('--format', choices=['json', 'summary'], default='json',
                              help='Output format')
    
    # List reports command
    list_parser = subparsers.add_parser('list-reports', help='List recent reports')
    list_parser.add_argument('--limit', type=int, default=10, help='Number of reports to list')
    list_parser.add_argument('--format', choices=['table', 'json'], default='table',
                            help='Output format')
    
    # Get report command
    get_parser = subparsers.add_parser('get-report', help='Get specific report')
    get_parser.add_argument('--report-id', required=True, help='Report ID to retrieve')
    get_parser.add_argument('--format', choices=['json', 'summary'], default='json',
                           help='Output format')
    
    # Export HTML command
    export_parser = subparsers.add_parser('export-html', help='Export dashboard as HTML')
    export_parser.add_argument('--dashboard-id', help='Dashboard ID to export (latest if not specified)')
    export_parser.add_argument('--output-file', help='Output HTML file path')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test analytics system')
    test_parser.add_argument('--component', choices=['analytics', 'reporting', 'dashboard'], 
                            default='analytics', help='Component to test')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize systems
    config = {
        'pipeline_storage_path': 'data/pipelines',
        'metrics_storage_path': 'data/metrics',
        'alerts_storage_path': 'data/alerts',
        'rollback_storage_path': 'data/rollbacks',
        'reports_storage_path': 'data/reports'
    }
    
    analytics_engine = AnalyticsEngine(config)
    reporting_system = ReportingSystem(config)
    
    # Execute command
    if args.command == 'dashboard':
        await handle_dashboard_command(reporting_system, args)
    elif args.command == 'success-rates':
        await handle_success_rates_command(analytics_engine, args)
    elif args.command == 'performance':
        await handle_performance_command(analytics_engine, args)
    elif args.command == 'trends':
        await handle_trends_command(analytics_engine, args)
    elif args.command == 'report':
        await handle_report_command(reporting_system, args)
    elif args.command == 'list-reports':
        await handle_list_reports_command(reporting_system, args)
    elif args.command == 'get-report':
        await handle_get_report_command(reporting_system, args)
    elif args.command == 'export-html':
        await handle_export_html_command(reporting_system, args)
    elif args.command == 'test':
        await handle_test_command(analytics_engine, reporting_system, args)


async def handle_dashboard_command(reporting_system: ReportingSystem, args):
    """Handle dashboard command"""
    
    try:
        time_range = TimeRange(args.time_range)
        dashboard = reporting_system.generate_dashboard(time_range)
        
        if args.format == 'json':
            print(json.dumps(dashboard, indent=2, default=str))
        else:
            print("=== Analytics Dashboard ===")
            print(f"Generated: {dashboard['generated_at']}")
            print(f"Time Range: {dashboard['time_range'].replace('_', ' ').title()}")
            print(f"Dashboard ID: {dashboard['dashboard_id']}")
            
            print("\n=== Key Performance Indicators ===")
            for kpi_name, kpi_data in dashboard['kpis'].items():
                status_symbol = {'success': '✓', 'warning': '⚠', 'danger': '✗', 'info': 'ℹ'}.get(kpi_data['status'], '•')
                trend_symbol = {'up': '↑', 'down': '↓', 'stable': '→', 'neutral': '•'}.get(kpi_data['trend'], '•')
                print(f"  {status_symbol} {kpi_name.replace('_', ' ').title()}: {kpi_data['value']}{kpi_data['unit']} {trend_symbol}")
            
            print("\n=== Overview ===")
            overview = dashboard['sections']['overview']
            print(f"  {overview['summary']}")
            
            print("\n=== Key Insights ===")
            for insight in dashboard['sections']['recommendations']['insights']:
                print(f"  • {insight}")
    
    except Exception as e:
        print(f"Error generating dashboard: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_success_rates_command(analytics_engine: AnalyticsEngine, args):
    """Handle success rates command"""
    
    try:
        time_range = TimeRange(args.time_range)
        success_metrics = analytics_engine.calculate_success_rates(time_range)
        
        if args.format == 'json':
            print(json.dumps(success_metrics.__dict__, indent=2))
        else:
            print("=== Deployment Success Rates ===")
            print(f"Time Period: {success_metrics.time_period.replace('_', ' ').title()}")
            print(f"Total Deployments: {success_metrics.total_deployments}")
            print(f"Successful: {success_metrics.successful_deployments}")
            print(f"Failed: {success_metrics.failed_deployments}")
            print(f"Rolled Back: {success_metrics.rolled_back_deployments}")
            print(f"Success Rate: {success_metrics.success_rate}%")
            print(f"Failure Rate: {success_metrics.failure_rate}%")
            print(f"Rollback Rate: {success_metrics.rollback_rate}%")
            print(f"Average Duration: {success_metrics.average_duration} minutes")
            print(f"Median Duration: {success_metrics.median_duration} minutes")
    
    except Exception as e:
        print(f"Error calculating success rates: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_performance_command(analytics_engine: AnalyticsEngine, args):
    """Handle performance command"""
    
    try:
        time_range = TimeRange(args.time_range)
        performance_metrics = analytics_engine.calculate_performance_metrics(time_range)
        
        if args.format == 'json':
            print(json.dumps(performance_metrics.__dict__, indent=2))
        else:
            print("=== Deployment Performance Metrics ===")
            print(f"Time Period: {time_range.value.replace('_', ' ').title()}")
            print(f"Average Deployment Time: {performance_metrics.average_deployment_time} minutes")
            print(f"Median Deployment Time: {performance_metrics.median_deployment_time} minutes")
            print(f"Fastest Deployment: {performance_metrics.fastest_deployment} minutes")
            print(f"Slowest Deployment: {performance_metrics.slowest_deployment} minutes")
            print(f"95th Percentile: {performance_metrics.p95_deployment_time} minutes")
            print(f"99th Percentile: {performance_metrics.p99_deployment_time} minutes")
            print(f"Throughput: {performance_metrics.throughput_per_day} deployments/day")
            
            if performance_metrics.resource_utilization:
                print("\n=== Resource Utilization ===")
                for resource, value in performance_metrics.resource_utilization.items():
                    print(f"  {resource.replace('_', ' ').title()}: {value}%")
    
    except Exception as e:
        print(f"Error calculating performance metrics: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_trends_command(analytics_engine: AnalyticsEngine, args):
    """Handle trends command"""
    
    try:
        time_range = TimeRange(args.time_range)
        trend_analysis = analytics_engine.analyze_trends(args.metric, time_range)
        
        if args.format == 'json':
            print(json.dumps(trend_analysis.__dict__, indent=2, default=str))
        else:
            print(f"=== Trend Analysis: {args.metric.replace('_', ' ').title()} ===")
            print(f"Time Period: {time_range.value.replace('_', ' ').title()}")
            print(f"Trend Direction: {trend_analysis.trend_direction.title()}")
            print(f"Trend Strength: {trend_analysis.trend_strength}")
            print(f"Correlation Coefficient: {trend_analysis.correlation_coefficient}")
            
            if trend_analysis.forecast_next_period:
                print(f"Forecast Next Period: {trend_analysis.forecast_next_period}")
            
            print(f"\nData Points: {len(trend_analysis.time_series)}")
            
            if trend_analysis.time_series:
                print("Recent Values:")
                for timestamp, value in trend_analysis.time_series[-5:]:  # Last 5 points
                    time_str = timestamp.strftime('%Y-%m-%d %H:%M') if hasattr(timestamp, 'strftime') else str(timestamp)
                    print(f"  {time_str}: {value}")
    
    except Exception as e:
        print(f"Error analyzing trends: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_report_command(reporting_system: ReportingSystem, args):
    """Handle report command"""
    
    try:
        time_range = TimeRange(args.time_range)
        report = reporting_system.generate_report(args.type, time_range, args.format)
        
        if args.format == 'json':
            print(json.dumps(report, indent=2, default=str))
        else:
            print(f"=== {report['report_name']} ===")
            print(f"Generated: {report['generated_at']}")
            print(f"Time Range: {report['time_range'].replace('_', ' ').title()}")
            print(f"Report ID: {report['report_id']}")
            print(f"\nDescription: {report['description']}")
            
            # Show executive summary if available
            if 'executive_summary' in report:
                exec_summary = report['executive_summary']
                print(f"\n=== Executive Summary ===")
                print(f"Headline: {exec_summary['headline']}")
                print(f"Status: {exec_summary['status'].replace('_', ' ').title()}")
                
                print("\nKey Metrics:")
                for metric, value in exec_summary['key_metrics'].items():
                    print(f"  {metric}: {value}")
                
                if exec_summary['top_insights']:
                    print("\nTop Insights:")
                    for insight in exec_summary['top_insights']:
                        print(f"  • {insight}")
    
    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_list_reports_command(reporting_system: ReportingSystem, args):
    """Handle list reports command"""
    
    try:
        reports = reporting_system.list_reports(args.limit)
        
        if args.format == 'json':
            print(json.dumps(reports, indent=2))
        else:
            if not reports:
                print("No reports found")
                return
            
            print("=== Recent Reports ===")
            print(f"{'Report ID':<20} {'Name':<30} {'Type':<20} {'Time Range':<15} {'Generated':<20}")
            print("-" * 110)
            
            for report in reports:
                generated_date = datetime.fromisoformat(report['generated_at']).strftime('%Y-%m-%d %H:%M')
                print(f"{report['report_id']:<20} {report['report_name'][:29]:<30} {report['report_type']:<20} {report['time_range']:<15} {generated_date:<20}")
    
    except Exception as e:
        print(f"Error listing reports: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_get_report_command(reporting_system: ReportingSystem, args):
    """Handle get report command"""
    
    try:
        report = reporting_system.get_report(args.report_id)
        
        if not report:
            print(f"Report {args.report_id} not found", file=sys.stderr)
            sys.exit(1)
        
        if args.format == 'json':
            print(json.dumps(report, indent=2, default=str))
        else:
            print(f"=== {report['report_name']} ===")
            print(f"Report ID: {report['report_id']}")
            print(f"Type: {report['report_type']}")
            print(f"Generated: {report['generated_at']}")
            print(f"Time Range: {report['time_range']}")
            print(f"Description: {report['description']}")
    
    except Exception as e:
        print(f"Error getting report: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_export_html_command(reporting_system: ReportingSystem, args):
    """Handle export HTML command"""
    
    try:
        # Generate or get dashboard
        if args.dashboard_id:
            # This would typically load an existing dashboard
            dashboard = reporting_system.generate_dashboard(TimeRange.LAST_7D)
            dashboard['dashboard_id'] = args.dashboard_id
        else:
            dashboard = reporting_system.generate_dashboard(TimeRange.LAST_7D)
        
        # Generate HTML
        html_content = reporting_system.export_dashboard_html(dashboard)
        
        # Save to file
        if args.output_file:
            output_path = Path(args.output_file)
        else:
            output_path = Path(f"dashboard_{dashboard['dashboard_id']}.html")
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        print(f"✓ Dashboard exported to {output_path}")
        print(f"  Dashboard ID: {dashboard['dashboard_id']}")
        print(f"  File size: {output_path.stat().st_size} bytes")
    
    except Exception as e:
        print(f"Error exporting dashboard: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_test_command(analytics_engine: AnalyticsEngine, reporting_system: ReportingSystem, args):
    """Handle test command"""
    
    try:
        print(f"Testing analytics system component: {args.component}")
        
        if args.component == 'analytics':
            print("✓ Testing analytics engine...")
            
            # Test success rate calculation
            success_metrics = analytics_engine.calculate_success_rates(TimeRange.LAST_7D)
            print(f"  Success rate calculation: {success_metrics.success_rate}%")
            
            # Test performance metrics
            performance_metrics = analytics_engine.calculate_performance_metrics(TimeRange.LAST_7D)
            print(f"  Performance metrics: {performance_metrics.average_deployment_time} min avg")
            
            # Test trend analysis
            trend_analysis = analytics_engine.analyze_trends("success_rate", TimeRange.LAST_7D)
            print(f"  Trend analysis: {trend_analysis.trend_direction}")
            
        elif args.component == 'reporting':
            print("✓ Testing reporting system...")
            
            # Test report generation
            report = reporting_system.generate_report('executive_summary', TimeRange.LAST_7D)
            print(f"  Report generation: {report['report_id']}")
            
            # Test report listing
            reports = reporting_system.list_reports(5)
            print(f"  Report listing: {len(reports)} reports found")
            
        elif args.component == 'dashboard':
            print("✓ Testing dashboard generation...")
            
            # Test dashboard generation
            dashboard = reporting_system.generate_dashboard(TimeRange.LAST_7D)
            print(f"  Dashboard generation: {dashboard['dashboard_id']}")
            print(f"  KPIs: {len(dashboard['kpis'])}")
            print(f"  Charts: {len(dashboard['charts'])}")
            print(f"  Sections: {len(dashboard['sections'])}")
        
        print("✓ All tests passed")
    
    except Exception as e:
        print(f"Error running tests: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
