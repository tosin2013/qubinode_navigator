"""
Tests for Qubinode Navigator Analytics Engine

Tests analytics calculations, success rate metrics, performance analysis,
and trend detection for deployment reporting.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.analytics_engine import (
    AnalyticsEngine,
    SuccessRateMetrics,
    PerformanceMetrics,
    TrendAnalysis,
    TimeRange,
    ReportType,
)


class TestAnalyticsEngine:
    """Test cases for analytics engine"""

    def setup_method(self):
        """Setup test environment"""
        # Create temporary storage
        self.temp_dir = tempfile.mkdtemp()

        # Engine configuration
        self.config = {
            "pipeline_storage_path": f"{self.temp_dir}/pipelines",
            "metrics_storage_path": f"{self.temp_dir}/metrics",
            "alerts_storage_path": f"{self.temp_dir}/alerts",
            "rollback_storage_path": f"{self.temp_dir}/rollbacks",
            "data_retention_days": 90,
            "cache_ttl_minutes": 15,
        }

        # Create directories
        Path(self.config["pipeline_storage_path"]).mkdir(parents=True, exist_ok=True)

        # Create analytics engine
        self.analytics_engine = AnalyticsEngine(self.config)

        # Create sample pipeline data
        self._create_sample_pipeline_data()

    def _create_sample_pipeline_data(self):
        """Create sample pipeline data for testing"""
        pipelines_dir = Path(self.config["pipeline_storage_path"])

        # Create sample pipelines with different statuses and durations
        sample_pipelines = [
            {
                "pipeline_id": "pipeline_001",
                "pipeline_name": "Test Pipeline 1",
                "strategy": "rolling",
                "status": "completed",
                "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
                "completed_at": (
                    datetime.now() - timedelta(days=1) + timedelta(minutes=45)
                ).isoformat(),
                "total_duration": "45 minutes",
                "phases": [{"phase_id": "phase_1", "status": "completed"}],
                "created_by": "test_user",
            },
            {
                "pipeline_id": "pipeline_002",
                "pipeline_name": "Test Pipeline 2",
                "strategy": "canary",
                "status": "failed",
                "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
                "completed_at": (
                    datetime.now() - timedelta(days=2) + timedelta(minutes=30)
                ).isoformat(),
                "total_duration": "30 minutes",
                "phases": [{"phase_id": "phase_2", "status": "failed"}],
                "created_by": "test_user",
            },
            {
                "pipeline_id": "pipeline_003",
                "pipeline_name": "Test Pipeline 3",
                "strategy": "blue_green",
                "status": "rolled_back",
                "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
                "completed_at": (
                    datetime.now() - timedelta(days=3) + timedelta(minutes=60)
                ).isoformat(),
                "total_duration": "60 minutes",
                "phases": [{"phase_id": "phase_3", "status": "rolled_back"}],
                "created_by": "test_user",
            },
            {
                "pipeline_id": "pipeline_004",
                "pipeline_name": "Test Pipeline 4",
                "strategy": "rolling",
                "status": "completed",
                "created_at": (datetime.now() - timedelta(days=4)).isoformat(),
                "completed_at": (
                    datetime.now() - timedelta(days=4) + timedelta(minutes=35)
                ).isoformat(),
                "total_duration": "35 minutes",
                "phases": [{"phase_id": "phase_4", "status": "completed"}],
                "created_by": "test_user",
            },
            {
                "pipeline_id": "pipeline_005",
                "pipeline_name": "Test Pipeline 5",
                "strategy": "all_at_once",
                "status": "completed",
                "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
                "completed_at": (
                    datetime.now() - timedelta(days=5) + timedelta(minutes=25)
                ).isoformat(),
                "total_duration": "25 minutes",
                "phases": [{"phase_id": "phase_5", "status": "completed"}],
                "created_by": "test_user",
            },
        ]

        # Save pipeline files
        for pipeline in sample_pipelines:
            pipeline_file = pipelines_dir / f"pipeline_{pipeline['pipeline_id']}.json"
            with open(pipeline_file, "w") as f:
                json.dump(pipeline, f, indent=2)

    def test_analytics_engine_initialization(self):
        """Test analytics engine initialization"""
        assert self.analytics_engine.data_retention_days == 90
        assert self.analytics_engine.cache_ttl_minutes == 15
        assert self.analytics_engine.pipeline_storage_path == Path(
            self.config["pipeline_storage_path"]
        )
        assert len(self.analytics_engine._cache) == 0
        assert len(self.analytics_engine._cache_timestamps) == 0

    def test_cache_functionality(self):
        """Test caching functionality"""
        cache_key = "test_key"
        test_value = {"test": "data"}

        # Test cache miss
        assert self.analytics_engine._get_cache(cache_key) is None

        # Test cache set and hit
        self.analytics_engine._set_cache(cache_key, test_value)
        assert self.analytics_engine._get_cache(cache_key) == test_value

        # Test cache validity
        assert self.analytics_engine._is_cache_valid(cache_key) is True

        # Test cache expiry (simulate old timestamp)
        old_time = datetime.now() - timedelta(minutes=20)
        self.analytics_engine._cache_timestamps[cache_key] = old_time
        assert self.analytics_engine._is_cache_valid(cache_key) is False

    def test_load_pipelines(self):
        """Test pipeline loading functionality"""
        pipelines = self.analytics_engine._load_pipelines(TimeRange.LAST_7D)

        assert len(pipelines) == 5  # All sample pipelines within 7 days
        assert all("pipeline_id" in p for p in pipelines)
        assert all("status" in p for p in pipelines)
        assert all("created_at" in p for p in pipelines)

    def test_calculate_success_rates(self):
        """Test success rate calculation"""
        success_metrics = self.analytics_engine.calculate_success_rates(
            TimeRange.LAST_7D
        )

        assert isinstance(success_metrics, SuccessRateMetrics)
        assert success_metrics.total_deployments == 5
        assert success_metrics.successful_deployments == 3  # 3 completed
        assert success_metrics.failed_deployments == 1  # 1 failed
        assert success_metrics.rolled_back_deployments == 1  # 1 rolled back
        assert success_metrics.success_rate == 60.0  # 3/5 * 100
        assert success_metrics.failure_rate == 20.0  # 1/5 * 100
        assert success_metrics.rollback_rate == 20.0  # 1/5 * 100
        assert success_metrics.time_period == "last_7d"

    def test_calculate_success_rates_empty_data(self):
        """Test success rate calculation with no data"""
        # Create engine with empty data directory
        empty_config = self.config.copy()
        empty_config["pipeline_storage_path"] = f"{self.temp_dir}/empty_pipelines"
        Path(empty_config["pipeline_storage_path"]).mkdir(parents=True, exist_ok=True)

        empty_engine = AnalyticsEngine(empty_config)
        success_metrics = empty_engine.calculate_success_rates(TimeRange.LAST_7D)

        assert success_metrics.total_deployments == 0
        assert success_metrics.success_rate == 0.0
        assert success_metrics.failure_rate == 0.0
        assert success_metrics.rollback_rate == 0.0
        assert success_metrics.average_duration == 0.0

    def test_calculate_performance_metrics(self):
        """Test performance metrics calculation"""
        performance_metrics = self.analytics_engine.calculate_performance_metrics(
            TimeRange.LAST_7D
        )

        assert isinstance(performance_metrics, PerformanceMetrics)
        assert performance_metrics.average_deployment_time > 0
        assert performance_metrics.median_deployment_time > 0
        assert performance_metrics.fastest_deployment > 0
        assert performance_metrics.slowest_deployment > 0
        assert performance_metrics.p95_deployment_time > 0
        assert performance_metrics.p99_deployment_time > 0
        assert performance_metrics.throughput_per_day > 0

        # Verify duration calculations (based on sample data)
        # Sample durations: 45, 30, 60, 35, 25 minutes
        expected_avg = (45 + 30 + 60 + 35 + 25) / 5  # 39 minutes
        assert abs(performance_metrics.average_deployment_time - expected_avg) < 1

        assert performance_metrics.fastest_deployment == 25  # min value
        assert performance_metrics.slowest_deployment == 60  # max value

    def test_analyze_trends(self):
        """Test trend analysis"""
        trend_analysis = self.analytics_engine.analyze_trends(
            "success_rate", TimeRange.LAST_7D
        )

        assert isinstance(trend_analysis, TrendAnalysis)
        assert trend_analysis.metric_name == "success_rate"
        assert trend_analysis.trend_direction in ["increasing", "decreasing", "stable"]
        assert 0 <= trend_analysis.trend_strength <= 1
        assert len(trend_analysis.time_series) > 0

        # Test with different metric
        duration_trend = self.analytics_engine.analyze_trends(
            "deployment_duration", TimeRange.LAST_30D
        )
        assert duration_trend.metric_name == "deployment_duration"

    def test_generate_summary_report(self):
        """Test summary report generation"""
        summary_report = self.analytics_engine.generate_summary_report(
            TimeRange.LAST_7D
        )

        assert "report_type" in summary_report
        assert summary_report["report_type"] == "summary"
        assert "time_range" in summary_report
        assert "generated_at" in summary_report
        assert "success_metrics" in summary_report
        assert "performance_metrics" in summary_report
        assert "alert_statistics" in summary_report
        assert "rollback_statistics" in summary_report
        assert "approval_statistics" in summary_report
        assert "trends" in summary_report
        assert "key_insights" in summary_report

        # Verify insights generation
        insights = summary_report["key_insights"]
        assert isinstance(insights, list)
        assert len(insights) > 0

    def test_generate_detailed_report(self):
        """Test detailed report generation"""
        detailed_report = self.analytics_engine.generate_detailed_report(
            TimeRange.LAST_7D
        )

        assert "report_type" in detailed_report
        assert detailed_report["report_type"] == "detailed"
        assert "strategy_breakdown" in detailed_report
        assert "daily_statistics" in detailed_report
        assert "component_analysis" in detailed_report
        assert "failure_analysis" in detailed_report
        assert "recommendations" in detailed_report

        # Verify strategy breakdown
        strategy_breakdown = detailed_report["strategy_breakdown"]
        assert "rolling" in strategy_breakdown
        assert "canary" in strategy_breakdown
        assert "blue_green" in strategy_breakdown
        assert "all_at_once" in strategy_breakdown

        # Verify rolling strategy stats (2 pipelines, both completed)
        rolling_stats = strategy_breakdown["rolling"]
        assert rolling_stats["total"] == 2
        assert rolling_stats["successful"] == 2
        assert rolling_stats["success_rate"] == 100.0

    def test_calculate_daily_statistics(self):
        """Test daily statistics calculation"""
        pipelines = self.analytics_engine._load_pipelines(TimeRange.LAST_7D)
        daily_stats = self.analytics_engine._calculate_daily_statistics(pipelines)

        assert isinstance(daily_stats, dict)
        assert len(daily_stats) > 0

        # Check structure of daily stats
        for date, stats in daily_stats.items():
            assert "total" in stats
            assert "successful" in stats
            assert "failed" in stats
            assert "rolled_back" in stats
            assert "success_rate" in stats
            assert "deployments" in stats
            assert stats["total"] >= 0
            assert 0 <= stats["success_rate"] <= 100

    def test_analyze_component_updates(self):
        """Test component update analysis"""
        pipelines = self.analytics_engine._load_pipelines(TimeRange.LAST_7D)
        component_stats = self.analytics_engine._analyze_component_updates(pipelines)

        assert isinstance(component_stats, dict)
        # Component analysis depends on phase data structure
        # For our sample data, this might be empty or contain basic stats

    def test_analyze_failures(self):
        """Test failure analysis"""
        pipelines = self.analytics_engine._load_pipelines(TimeRange.LAST_7D)
        failure_analysis = self.analytics_engine._analyze_failures(pipelines)

        assert "total_failures" in failure_analysis
        assert "failure_rate" in failure_analysis
        assert "common_failure_patterns" in failure_analysis
        assert "failure_by_strategy" in failure_analysis
        assert "failure_recovery_time" in failure_analysis

        # Based on sample data: 1 failed pipeline out of 5
        assert failure_analysis["total_failures"] == 1
        assert failure_analysis["failure_rate"] == 20.0
        assert "canary" in failure_analysis["failure_by_strategy"]
        assert failure_analysis["failure_by_strategy"]["canary"] == 1

    def test_generate_recommendations(self):
        """Test recommendation generation"""
        strategy_stats = {
            "rolling": {"total": 2, "successful": 2, "success_rate": 100.0},
            "canary": {"total": 1, "successful": 0, "success_rate": 0.0},
        }
        daily_stats = {
            "2025-11-07": {"total": 2, "successful": 2},
            "2025-11-06": {"total": 1, "successful": 0},
        }

        recommendations = self.analytics_engine._generate_recommendations(
            strategy_stats, daily_stats
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert all(isinstance(rec, str) for rec in recommendations)

        # Should recommend the best performing strategy
        assert any("rolling" in rec for rec in recommendations)

    def test_generate_key_insights(self):
        """Test key insights generation"""
        success_metrics = SuccessRateMetrics(
            total_deployments=10,
            successful_deployments=9,
            failed_deployments=1,
            rolled_back_deployments=0,
            success_rate=90.0,
            failure_rate=10.0,
            rollback_rate=0.0,
            average_duration=45.0,
            median_duration=40.0,
            time_period="last_7d",
        )

        performance_metrics = PerformanceMetrics(
            average_deployment_time=45.0,
            median_deployment_time=40.0,
            fastest_deployment=25.0,
            slowest_deployment=60.0,
            p95_deployment_time=55.0,
            p99_deployment_time=58.0,
            throughput_per_day=2.5,
            resource_utilization={},
        )

        alert_stats = {"active_alerts": 2, "total_alerts": 10}

        insights = self.analytics_engine._generate_key_insights(
            success_metrics, performance_metrics, alert_stats
        )

        assert isinstance(insights, list)
        assert len(insights) > 0

        # Should contain insights about good success rate
        assert any("success rate" in insight.lower() for insight in insights)

    def test_time_range_filtering(self):
        """Test time range filtering"""
        # Test different time ranges
        last_24h = self.analytics_engine._load_pipelines(TimeRange.LAST_24H)
        last_7d = self.analytics_engine._load_pipelines(TimeRange.LAST_7D)
        last_30d = self.analytics_engine._load_pipelines(TimeRange.LAST_30D)

        # 24h should have fewer or equal pipelines than 7d
        assert len(last_24h) <= len(last_7d)
        # 7d should have fewer or equal pipelines than 30d
        assert len(last_7d) <= len(last_30d)

    def test_custom_time_range(self):
        """Test custom time range filtering"""
        start_date = datetime.now() - timedelta(days=3)
        end_date = datetime.now() - timedelta(days=1)

        pipelines = self.analytics_engine._load_pipelines(
            TimeRange.CUSTOM, start_date, end_date
        )

        # Should include pipelines within the custom range
        for pipeline in pipelines:
            created_at = pipeline["created_at"]
            assert start_date <= created_at <= end_date

    def test_deserialize_pipeline_data(self):
        """Test pipeline data deserialization"""
        sample_data = {
            "pipeline_id": "test_123",
            "pipeline_name": "Test Pipeline",
            "strategy": "rolling",
            "status": "completed",
            "created_at": "2025-11-08T10:00:00",
            "completed_at": "2025-11-08T10:45:00",
            "total_duration": "45 minutes",
            "phases": [{"phase_id": "phase_1"}],
            "created_by": "test_user",
        }

        deserialized = self.analytics_engine._deserialize_pipeline_data(sample_data)

        assert deserialized["pipeline_id"] == "test_123"
        assert deserialized["strategy"] == "rolling"
        assert deserialized["status"] == "completed"
        assert isinstance(deserialized["created_at"], datetime)
        assert isinstance(deserialized["completed_at"], datetime)

    def test_get_resource_utilization(self):
        """Test resource utilization retrieval"""
        resource_util = self.analytics_engine._get_resource_utilization()

        assert isinstance(resource_util, dict)
        # Should contain basic resource metrics
        expected_keys = [
            "cpu_usage_avg",
            "memory_usage_avg",
            "disk_usage_avg",
            "network_usage_avg",
        ]
        for key in expected_keys:
            assert key in resource_util
            assert isinstance(resource_util[key], (int, float))

    def test_get_metric_time_series(self):
        """Test metric time series generation"""
        time_series = self.analytics_engine._get_metric_time_series(
            "success_rate", TimeRange.LAST_24H
        )

        assert isinstance(time_series, list)
        assert len(time_series) > 0

        # Each point should be a tuple of (datetime, float)
        for timestamp, value in time_series:
            assert isinstance(timestamp, datetime)
            assert isinstance(value, (int, float))
            assert value >= 0


class TestSuccessRateMetrics:
    """Test success rate metrics data class"""

    def test_success_rate_metrics_creation(self):
        """Test success rate metrics creation"""
        metrics = SuccessRateMetrics(
            total_deployments=100,
            successful_deployments=85,
            failed_deployments=10,
            rolled_back_deployments=5,
            success_rate=85.0,
            failure_rate=10.0,
            rollback_rate=5.0,
            average_duration=45.5,
            median_duration=42.0,
            time_period="last_30d",
        )

        assert metrics.total_deployments == 100
        assert metrics.successful_deployments == 85
        assert metrics.failed_deployments == 10
        assert metrics.rolled_back_deployments == 5
        assert metrics.success_rate == 85.0
        assert metrics.failure_rate == 10.0
        assert metrics.rollback_rate == 5.0
        assert metrics.average_duration == 45.5
        assert metrics.median_duration == 42.0
        assert metrics.time_period == "last_30d"


class TestPerformanceMetrics:
    """Test performance metrics data class"""

    def test_performance_metrics_creation(self):
        """Test performance metrics creation"""
        metrics = PerformanceMetrics(
            average_deployment_time=45.0,
            median_deployment_time=40.0,
            fastest_deployment=20.0,
            slowest_deployment=90.0,
            p95_deployment_time=75.0,
            p99_deployment_time=85.0,
            throughput_per_day=5.2,
            resource_utilization={"cpu": 65.0, "memory": 78.0},
        )

        assert metrics.average_deployment_time == 45.0
        assert metrics.median_deployment_time == 40.0
        assert metrics.fastest_deployment == 20.0
        assert metrics.slowest_deployment == 90.0
        assert metrics.p95_deployment_time == 75.0
        assert metrics.p99_deployment_time == 85.0
        assert metrics.throughput_per_day == 5.2
        assert metrics.resource_utilization["cpu"] == 65.0


class TestTrendAnalysis:
    """Test trend analysis data class"""

    def test_trend_analysis_creation(self):
        """Test trend analysis creation"""
        time_series = [
            (datetime.now() - timedelta(hours=2), 85.0),
            (datetime.now() - timedelta(hours=1), 87.0),
            (datetime.now(), 89.0),
        ]

        analysis = TrendAnalysis(
            metric_name="success_rate",
            time_series=time_series,
            trend_direction="increasing",
            trend_strength=0.8,
            correlation_coefficient=0.95,
            forecast_next_period=91.0,
        )

        assert analysis.metric_name == "success_rate"
        assert len(analysis.time_series) == 3
        assert analysis.trend_direction == "increasing"
        assert analysis.trend_strength == 0.8
        assert analysis.correlation_coefficient == 0.95
        assert analysis.forecast_next_period == 91.0


class TestEnums:
    """Test enumeration classes"""

    def test_report_type_enum(self):
        """Test report type enum"""
        assert ReportType.SUCCESS_RATES.value == "success_rates"
        assert ReportType.PERFORMANCE.value == "performance"
        assert ReportType.TRENDS.value == "trends"
        assert ReportType.SUMMARY.value == "summary"
        assert ReportType.DETAILED.value == "detailed"

    def test_time_range_enum(self):
        """Test time range enum"""
        assert TimeRange.LAST_24H.value == "last_24h"
        assert TimeRange.LAST_7D.value == "last_7d"
        assert TimeRange.LAST_30D.value == "last_30d"
        assert TimeRange.LAST_90D.value == "last_90d"
        assert TimeRange.CUSTOM.value == "custom"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
