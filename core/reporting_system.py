"""
Qubinode Navigator Reporting System

Dashboard and visualization system for analytics reports,
success rate tracking, and performance monitoring.

Based on ADR-0030: Software and OS Update Strategy
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.analytics_engine import AnalyticsEngine, ReportType, TimeRange


class ReportingSystem:
    """
    Comprehensive Reporting System

    Provides dashboard generation, report scheduling, and
    visualization capabilities for analytics data.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.reports_storage_path = Path(
            self.config.get("reports_storage_path", "data/reports")
        )
        self.dashboard_enabled = self.config.get("dashboard_enabled", True)
        self.auto_generate_reports = self.config.get("auto_generate_reports", True)

        # Initialize storage
        self.reports_storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize analytics engine
        self.analytics_engine = AnalyticsEngine(config)

        # Report templates
        self.report_templates = self._load_report_templates()

    def _load_report_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load report templates configuration"""
        return {
            "executive_summary": {
                "name": "Executive Summary",
                "description": "High-level overview for management",
                "sections": ["success_metrics", "key_insights", "trends"],
                "format": "summary",
                "frequency": "weekly",
            },
            "operational_dashboard": {
                "name": "Operational Dashboard",
                "description": "Detailed operational metrics",
                "sections": [
                    "success_metrics",
                    "performance_metrics",
                    "alert_statistics",
                    "trends",
                ],
                "format": "detailed",
                "frequency": "daily",
            },
            "technical_analysis": {
                "name": "Technical Analysis Report",
                "description": "Deep technical analysis and recommendations",
                "sections": [
                    "performance_metrics",
                    "failure_analysis",
                    "component_analysis",
                    "recommendations",
                ],
                "format": "detailed",
                "frequency": "monthly",
            },
            "success_rate_tracking": {
                "name": "Success Rate Tracking",
                "description": "Focus on deployment success rates and trends",
                "sections": ["success_metrics", "trends", "strategy_breakdown"],
                "format": "summary",
                "frequency": "weekly",
            },
        }

    def generate_dashboard(
        self, time_range: TimeRange = TimeRange.LAST_7D
    ) -> Dict[str, Any]:
        """Generate comprehensive dashboard data"""

        self.logger.info(f"Generating dashboard for {time_range.value}")

        # Get summary report
        summary_report = self.analytics_engine.generate_summary_report(time_range)

        # Get detailed metrics
        detailed_report = self.analytics_engine.generate_detailed_report(time_range)

        # Create dashboard structure
        dashboard = {
            "dashboard_id": f"dashboard_{int(datetime.now().timestamp())}",
            "generated_at": datetime.now().isoformat(),
            "time_range": time_range.value,
            "title": f"Qubinode Navigator Analytics Dashboard - {time_range.value.replace('_', ' ').title()}",
            # Key Performance Indicators
            "kpis": self._extract_kpis(summary_report),
            # Charts and visualizations
            "charts": self._generate_chart_data(summary_report, detailed_report),
            # Summary sections
            "sections": {
                "overview": self._create_overview_section(summary_report),
                "performance": self._create_performance_section(summary_report),
                "trends": self._create_trends_section(summary_report),
                "alerts": self._create_alerts_section(summary_report),
                "recommendations": self._create_recommendations_section(summary_report),
            },
            # Raw data for detailed views
            "raw_data": {
                "summary_report": summary_report,
                "detailed_report": detailed_report,
            },
        }

        # Save dashboard
        self._save_dashboard(dashboard)

        return dashboard

    def _extract_kpis(self, summary_report: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key performance indicators"""
        success_metrics = summary_report["success_metrics"]
        performance_metrics = summary_report["performance_metrics"]

        return {
            "success_rate": {
                "value": success_metrics["success_rate"],
                "unit": "%",
                "trend": self._get_trend_indicator(summary_report, "success_rate"),
                "status": self._get_status_color(
                    success_metrics["success_rate"], 95, 85
                ),
            },
            "average_deployment_time": {
                "value": performance_metrics["average_deployment_time"],
                "unit": "minutes",
                "trend": self._get_trend_indicator(
                    summary_report, "deployment_duration"
                ),
                "status": self._get_status_color(
                    performance_metrics["average_deployment_time"], 30, 60, reverse=True
                ),
            },
            "total_deployments": {
                "value": success_metrics["total_deployments"],
                "unit": "deployments",
                "trend": "neutral",
                "status": "info",
            },
            "rollback_rate": {
                "value": success_metrics["rollback_rate"],
                "unit": "%",
                "trend": self._get_trend_indicator(summary_report, "rollback_rate"),
                "status": self._get_status_color(
                    success_metrics["rollback_rate"], 2, 5, reverse=True
                ),
            },
            "active_alerts": {
                "value": summary_report["alert_statistics"]["active_alerts"],
                "unit": "alerts",
                "trend": "neutral",
                "status": self._get_status_color(
                    summary_report["alert_statistics"]["active_alerts"],
                    2,
                    5,
                    reverse=True,
                ),
            },
            "throughput": {
                "value": performance_metrics["throughput_per_day"],
                "unit": "deployments/day",
                "trend": "neutral",
                "status": "info",
            },
        }

    def _get_trend_indicator(
        self, summary_report: Dict[str, Any], metric_name: str
    ) -> str:
        """Get trend indicator for a metric"""
        trends = summary_report.get("trends", {})

        if metric_name in trends:
            trend_data = trends[metric_name]
            direction = trend_data.get("trend_direction", "stable")

            if direction == "increasing":
                return "up"
            elif direction == "decreasing":
                return "down"
            else:
                return "stable"

        return "neutral"

    def _get_status_color(
        self,
        value: float,
        good_threshold: float,
        warning_threshold: float,
        reverse: bool = False,
    ) -> str:
        """Get status color based on value and thresholds"""
        if reverse:
            # For metrics where lower is better (e.g., failure rate, duration)
            if value <= good_threshold:
                return "success"
            elif value <= warning_threshold:
                return "warning"
            else:
                return "danger"
        else:
            # For metrics where higher is better (e.g., success rate)
            if value >= good_threshold:
                return "success"
            elif value >= warning_threshold:
                return "warning"
            else:
                return "danger"

    def _generate_chart_data(
        self, summary_report: Dict[str, Any], detailed_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate data for charts and visualizations"""

        charts = {
            "success_rate_trend": {
                "type": "line",
                "title": "Success Rate Trend",
                "data": self._format_trend_data(
                    summary_report["trends"]["success_rate"]
                ),
                "options": {
                    "yAxis": {"min": 0, "max": 100, "unit": "%"},
                    "colors": ["#28a745"],
                },
            },
            "deployment_duration_trend": {
                "type": "line",
                "title": "Deployment Duration Trend",
                "data": self._format_trend_data(
                    summary_report["trends"]["deployment_duration"]
                ),
                "options": {
                    "yAxis": {"min": 0, "unit": "minutes"},
                    "colors": ["#007bff"],
                },
            },
            "status_distribution": {
                "type": "pie",
                "title": "Deployment Status Distribution",
                "data": [
                    {
                        "label": "Successful",
                        "value": summary_report["success_metrics"][
                            "successful_deployments"
                        ],
                        "color": "#28a745",
                    },
                    {
                        "label": "Failed",
                        "value": summary_report["success_metrics"][
                            "failed_deployments"
                        ],
                        "color": "#dc3545",
                    },
                    {
                        "label": "Rolled Back",
                        "value": summary_report["success_metrics"][
                            "rolled_back_deployments"
                        ],
                        "color": "#ffc107",
                    },
                ],
            },
            "strategy_performance": {
                "type": "bar",
                "title": "Performance by Strategy",
                "data": self._format_strategy_data(
                    detailed_report.get("strategy_breakdown", {})
                ),
                "options": {
                    "yAxis": {"min": 0, "max": 100, "unit": "%"},
                    "colors": ["#007bff", "#28a745", "#ffc107", "#dc3545"],
                },
            },
            "daily_deployments": {
                "type": "bar",
                "title": "Daily Deployment Volume",
                "data": self._format_daily_data(
                    detailed_report.get("daily_statistics", {})
                ),
                "options": {
                    "yAxis": {"min": 0, "unit": "deployments"},
                    "colors": ["#6c757d"],
                },
            },
        }

        return charts

    def _format_trend_data(self, trend_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format trend data for chart display"""
        time_series = trend_data.get("time_series", [])

        return [
            {
                "x": (
                    point[0].strftime("%Y-%m-%d %H:%M")
                    if isinstance(point[0], datetime)
                    else str(point[0])
                ),
                "y": point[1],
            }
            for point in time_series
        ]

    def _format_strategy_data(
        self, strategy_breakdown: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Format strategy performance data"""
        return [
            {"label": strategy.replace("_", " ").title(), "value": data["success_rate"]}
            for strategy, data in strategy_breakdown.items()
        ]

    def _format_daily_data(self, daily_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format daily statistics data"""
        return [
            {"x": date, "y": stats["total"]}
            for date, stats in sorted(daily_stats.items())
        ]

    def _create_overview_section(
        self, summary_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create overview section"""
        success_metrics = summary_report["success_metrics"]

        return {
            "title": "Deployment Overview",
            "summary": f"In the {success_metrics['time_period'].replace('_', ' ')}, there were {success_metrics['total_deployments']} total deployments with a {success_metrics['success_rate']}% success rate.",
            "metrics": {
                "Total Deployments": success_metrics["total_deployments"],
                "Successful": success_metrics["successful_deployments"],
                "Failed": success_metrics["failed_deployments"],
                "Rolled Back": success_metrics["rolled_back_deployments"],
                "Success Rate": f"{success_metrics['success_rate']}%",
                "Average Duration": f"{success_metrics['average_duration']} minutes",
            },
        }

    def _create_performance_section(
        self, summary_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create performance section"""
        performance_metrics = summary_report["performance_metrics"]

        return {
            "title": "Performance Metrics",
            "summary": f"Average deployment time is {performance_metrics['average_deployment_time']} minutes with {performance_metrics['throughput_per_day']} deployments per day.",
            "metrics": {
                "Average Duration": f"{performance_metrics['average_deployment_time']} minutes",
                "Median Duration": f"{performance_metrics['median_deployment_time']} minutes",
                "Fastest Deployment": f"{performance_metrics['fastest_deployment']} minutes",
                "Slowest Deployment": f"{performance_metrics['slowest_deployment']} minutes",
                "P95 Duration": f"{performance_metrics['p95_deployment_time']} minutes",
                "Throughput": f"{performance_metrics['throughput_per_day']} deployments/day",
            },
        }

    def _create_trends_section(self, summary_report: Dict[str, Any]) -> Dict[str, Any]:
        """Create trends section"""
        trends = summary_report["trends"]

        return {
            "title": "Trend Analysis",
            "summary": f"Success rate trend is {trends['success_rate']['trend_direction']} and deployment duration trend is {trends['deployment_duration']['trend_direction']}.",
            "trends": {
                "Success Rate": {
                    "direction": trends["success_rate"]["trend_direction"],
                    "strength": trends["success_rate"]["trend_strength"],
                    "forecast": trends["success_rate"]["forecast_next_period"],
                },
                "Deployment Duration": {
                    "direction": trends["deployment_duration"]["trend_direction"],
                    "strength": trends["deployment_duration"]["trend_strength"],
                    "forecast": trends["deployment_duration"]["forecast_next_period"],
                },
            },
        }

    def _create_alerts_section(self, summary_report: Dict[str, Any]) -> Dict[str, Any]:
        """Create alerts section"""
        alert_stats = summary_report["alert_statistics"]

        return {
            "title": "Alert Summary",
            "summary": f"There are {alert_stats['active_alerts']} active alerts with a {alert_stats['resolution_rate']}% resolution rate.",
            "metrics": {
                "Active Alerts": alert_stats["active_alerts"],
                "Total Alerts": alert_stats["total_alerts"],
                "Resolved Alerts": alert_stats["resolved_alerts"],
                "Resolution Rate": f"{alert_stats['resolution_rate']}%",
            },
            "severity_breakdown": alert_stats.get("severity_breakdown", {}),
        }

    def _create_recommendations_section(
        self, summary_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create recommendations section"""
        insights = summary_report.get("key_insights", [])

        return {
            "title": "Key Insights & Recommendations",
            "insights": insights,
            "action_items": [
                "Review deployment processes for failed deployments",
                "Optimize deployment duration for better performance",
                "Monitor alert trends and resolution times",
                "Consider automation improvements for high-frequency issues",
            ],
        }

    def _save_dashboard(self, dashboard: Dict[str, Any]):
        """Save dashboard to storage"""
        try:
            dashboard_file = (
                self.reports_storage_path
                / f"dashboard_{dashboard['dashboard_id']}.json"
            )

            with open(dashboard_file, "w") as f:
                json.dump(dashboard, f, indent=2, default=str)

            self.logger.info(f"Saved dashboard {dashboard['dashboard_id']}")

        except Exception as e:
            self.logger.error(f"Failed to save dashboard: {e}")

    def generate_report(
        self,
        report_type: str,
        time_range: TimeRange = TimeRange.LAST_30D,
        format_type: str = "json",
    ) -> Dict[str, Any]:
        """Generate specific report type"""

        if report_type not in self.report_templates:
            raise ValueError(f"Unknown report type: {report_type}")

        template = self.report_templates[report_type]

        self.logger.info(f"Generating {template['name']} report")

        # Get base data
        if template["format"] == "summary":
            base_data = self.analytics_engine.generate_summary_report(time_range)
        else:
            base_data = self.analytics_engine.generate_detailed_report(time_range)

        # Create report structure
        report = {
            "report_id": f"report_{int(datetime.now().timestamp())}",
            "report_type": report_type,
            "report_name": template["name"],
            "description": template["description"],
            "generated_at": datetime.now().isoformat(),
            "time_range": time_range.value,
            "format": format_type,
        }

        # Add requested sections
        for section in template["sections"]:
            if section in base_data:
                report[section] = base_data[section]

        # Add executive summary for executive reports
        if report_type == "executive_summary":
            report["executive_summary"] = self._create_executive_summary(base_data)

        # Save report
        self._save_report(report)

        return report

    def _create_executive_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create executive summary"""
        success_metrics = data["success_metrics"]
        performance_metrics = data["performance_metrics"]

        return {
            "headline": f"{success_metrics['success_rate']}% deployment success rate with {success_metrics['total_deployments']} total deployments",
            "key_metrics": {
                "Success Rate": f"{success_metrics['success_rate']}%",
                "Average Duration": f"{performance_metrics['average_deployment_time']} minutes",
                "Throughput": f"{performance_metrics['throughput_per_day']} deployments/day",
            },
            "status": self._get_overall_status(success_metrics, performance_metrics),
            "top_insights": data.get("key_insights", [])[:3],  # Top 3 insights
        }

    def _get_overall_status(
        self, success_metrics: Dict[str, Any], performance_metrics: Dict[str, Any]
    ) -> str:
        """Determine overall system status"""
        success_rate = success_metrics["success_rate"]
        avg_duration = performance_metrics["average_deployment_time"]

        if success_rate >= 95 and avg_duration <= 30:
            return "excellent"
        elif success_rate >= 85 and avg_duration <= 60:
            return "good"
        elif success_rate >= 75:
            return "fair"
        else:
            return "needs_attention"

    def _save_report(self, report: Dict[str, Any]):
        """Save report to storage"""
        try:
            report_file = (
                self.reports_storage_path / f"report_{report['report_id']}.json"
            )

            with open(report_file, "w") as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.info(f"Saved report {report['report_id']}")

        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")

    def list_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent reports"""
        reports = []

        try:
            for report_file in sorted(
                self.reports_storage_path.glob("report_*.json"), reverse=True
            )[:limit]:
                with open(report_file, "r") as f:
                    report_data = json.load(f)

                    reports.append(
                        {
                            "report_id": report_data["report_id"],
                            "report_name": report_data["report_name"],
                            "report_type": report_data["report_type"],
                            "generated_at": report_data["generated_at"],
                            "time_range": report_data["time_range"],
                            "file_path": str(report_file),
                        }
                    )

        except Exception as e:
            self.logger.error(f"Failed to list reports: {e}")

        return reports

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get specific report by ID"""
        try:
            report_file = self.reports_storage_path / f"report_{report_id}.json"

            if report_file.exists():
                with open(report_file, "r") as f:
                    return json.load(f)

        except Exception as e:
            self.logger.error(f"Failed to get report {report_id}: {e}")

        return None

    def export_dashboard_html(self, dashboard: Dict[str, Any]) -> str:
        """Export dashboard as HTML"""

        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #007bff; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .kpi-card {{ background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .kpi-value {{ font-size: 2em; font-weight: bold; }}
        .kpi-label {{ color: #666; margin-top: 5px; }}
        .section {{ background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .section h2 {{ margin-top: 0; color: #333; }}
        .status-success {{ color: #28a745; }}
        .status-warning {{ color: #ffc107; }}
        .status-danger {{ color: #dc3545; }}
        .status-info {{ color: #007bff; }}
        .insights {{ list-style-type: none; padding: 0; }}
        .insights li {{ padding: 10px; margin: 5px 0; background: #f8f9fa; border-left: 4px solid #007bff; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p>Generated: {generated_at} | Time Range: {time_range}</p>
        </div>
        
        <div class="kpi-grid">
            {kpi_cards}
        </div>
        
        {sections}
    </div>
</body>
</html>
        """

        # Generate KPI cards
        kpi_cards = ""
        for kpi_name, kpi_data in dashboard["kpis"].items():
            status_class = f"status-{kpi_data['status']}"
            kpi_cards += f"""
            <div class="kpi-card">
                <div class="kpi-value {status_class}">{kpi_data['value']}{kpi_data['unit']}</div>
                <div class="kpi-label">{kpi_name.replace('_', ' ').title()}</div>
            </div>
            """

        # Generate sections
        sections_html = ""
        for section_name, section_data in dashboard["sections"].items():
            if section_name == "recommendations":
                insights_html = ""
                for insight in section_data.get("insights", []):
                    insights_html += f"<li>{insight}</li>"

                sections_html += f"""
                <div class="section">
                    <h2>{section_data['title']}</h2>
                    <ul class="insights">{insights_html}</ul>
                </div>
                """
            else:
                sections_html += f"""
                <div class="section">
                    <h2>{section_data['title']}</h2>
                    <p>{section_data.get('summary', '')}</p>
                </div>
                """

        return html_template.format(
            title=dashboard["title"],
            generated_at=dashboard["generated_at"],
            time_range=dashboard["time_range"].replace("_", " ").title(),
            kpi_cards=kpi_cards,
            sections=sections_html,
        )
