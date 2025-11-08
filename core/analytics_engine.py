"""
Qubinode Navigator Analytics Engine

Comprehensive analytics and reporting system for update success rates,
deployment metrics, and system performance analysis.

Based on ADR-0030: Software and OS Update Strategy
"""

import json
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

from core.rollout_pipeline import RolloutPipeline, PipelineStage, RolloutStrategy
from core.monitoring_manager import MonitoringManager, Metric, Alert
from core.rollback_manager import RollbackManager, RollbackStatus
from core.approval_gates import ApprovalGateManager


class ReportType(Enum):
    """Types of reports"""
    SUCCESS_RATES = "success_rates"
    PERFORMANCE = "performance"
    TRENDS = "trends"
    SUMMARY = "summary"
    DETAILED = "detailed"


class TimeRange(Enum):
    """Time range options"""
    LAST_24H = "last_24h"
    LAST_7D = "last_7d"
    LAST_30D = "last_30d"
    LAST_90D = "last_90d"
    CUSTOM = "custom"


@dataclass
class SuccessRateMetrics:
    """Success rate metrics"""
    total_deployments: int
    successful_deployments: int
    failed_deployments: int
    rolled_back_deployments: int
    success_rate: float
    failure_rate: float
    rollback_rate: float
    average_duration: float
    median_duration: float
    time_period: str


@dataclass
class PerformanceMetrics:
    """Performance metrics"""
    average_deployment_time: float
    median_deployment_time: float
    fastest_deployment: float
    slowest_deployment: float
    p95_deployment_time: float
    p99_deployment_time: float
    throughput_per_day: float
    resource_utilization: Dict[str, float]


@dataclass
class TrendAnalysis:
    """Trend analysis data"""
    metric_name: str
    time_series: List[Tuple[datetime, float]]
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_strength: float  # 0-1
    correlation_coefficient: float
    forecast_next_period: Optional[float]


class AnalyticsEngine:
    """
    Comprehensive Analytics Engine
    
    Provides analytics and reporting capabilities for update success rates,
    deployment performance, and system trends.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.data_retention_days = self.config.get('data_retention_days', 90)
        self.cache_ttl_minutes = self.config.get('cache_ttl_minutes', 15)
        
        # Data sources
        self.pipeline_storage_path = Path(self.config.get('pipeline_storage_path', 'data/pipelines'))
        self.metrics_storage_path = Path(self.config.get('metrics_storage_path', 'data/metrics'))
        self.alerts_storage_path = Path(self.config.get('alerts_storage_path', 'data/alerts'))
        self.rollback_storage_path = Path(self.config.get('rollback_storage_path', 'data/rollbacks'))
        
        # Cache
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # Initialize managers
        self.monitoring_manager = MonitoringManager(config)
        self.rollback_manager = RollbackManager(config)
        self.approval_manager = ApprovalGateManager(config)
    
    def _get_cache_key(self, method: str, **kwargs) -> str:
        """Generate cache key for method and parameters"""
        key_parts = [method]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return "_".join(key_parts)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[cache_key]
        expiry_time = cache_time + timedelta(minutes=self.cache_ttl_minutes)
        return datetime.now() < expiry_time
    
    def _set_cache(self, cache_key: str, value: Any):
        """Set cache value"""
        self._cache[cache_key] = value
        self._cache_timestamps[cache_key] = datetime.now()
    
    def _get_cache(self, cache_key: str) -> Optional[Any]:
        """Get cache value if valid"""
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        return None
    
    def _load_pipelines(self, time_range: TimeRange = TimeRange.LAST_30D, 
                       start_date: datetime = None, end_date: datetime = None) -> List[RolloutPipeline]:
        """Load pipeline data for analysis"""
        pipelines = []
        
        # Determine time range
        if time_range == TimeRange.CUSTOM and start_date and end_date:
            range_start, range_end = start_date, end_date
        else:
            range_end = datetime.now()
            if time_range == TimeRange.LAST_24H:
                range_start = range_end - timedelta(hours=24)
            elif time_range == TimeRange.LAST_7D:
                range_start = range_end - timedelta(days=7)
            elif time_range == TimeRange.LAST_30D:
                range_start = range_end - timedelta(days=30)
            elif time_range == TimeRange.LAST_90D:
                range_start = range_end - timedelta(days=90)
            else:
                range_start = range_end - timedelta(days=30)
        
        # Load pipeline files
        try:
            for pipeline_file in self.pipeline_storage_path.glob("pipeline_*.json"):
                with open(pipeline_file, 'r') as f:
                    pipeline_data = json.load(f)
                    
                    # Parse creation date
                    created_at = datetime.fromisoformat(pipeline_data['created_at'].replace('T', ' ').replace('Z', ''))
                    
                    # Filter by time range
                    if range_start <= created_at <= range_end:
                        # Convert to pipeline object (simplified)
                        pipeline = self._deserialize_pipeline_data(pipeline_data)
                        pipelines.append(pipeline)
        
        except Exception as e:
            self.logger.error(f"Failed to load pipelines: {e}")
        
        return pipelines
    
    def _deserialize_pipeline_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize pipeline data for analysis"""
        return {
            'pipeline_id': data['pipeline_id'],
            'pipeline_name': data['pipeline_name'],
            'strategy': data['strategy'],
            'status': data['status'],
            'created_at': datetime.fromisoformat(data['created_at'].replace('T', ' ').replace('Z', '')),
            'completed_at': datetime.fromisoformat(data['completed_at'].replace('T', ' ').replace('Z', '')) if data.get('completed_at') else None,
            'total_duration': data.get('total_duration'),
            'phases': data.get('phases', []),
            'created_by': data.get('created_by')
        }
    
    def calculate_success_rates(self, time_range: TimeRange = TimeRange.LAST_30D,
                               start_date: datetime = None, end_date: datetime = None) -> SuccessRateMetrics:
        """Calculate deployment success rates"""
        
        cache_key = self._get_cache_key("success_rates", time_range=time_range.value, 
                                       start_date=start_date, end_date=end_date)
        cached_result = self._get_cache(cache_key)
        if cached_result:
            return cached_result
        
        pipelines = self._load_pipelines(time_range, start_date, end_date)
        
        if not pipelines:
            result = SuccessRateMetrics(
                total_deployments=0,
                successful_deployments=0,
                failed_deployments=0,
                rolled_back_deployments=0,
                success_rate=0.0,
                failure_rate=0.0,
                rollback_rate=0.0,
                average_duration=0.0,
                median_duration=0.0,
                time_period=time_range.value
            )
            self._set_cache(cache_key, result)
            return result
        
        # Calculate metrics
        total = len(pipelines)
        successful = len([p for p in pipelines if p['status'] == 'completed'])
        failed = len([p for p in pipelines if p['status'] == 'failed'])
        rolled_back = len([p for p in pipelines if p['status'] == 'rolled_back'])
        
        success_rate = (successful / total * 100) if total > 0 else 0
        failure_rate = (failed / total * 100) if total > 0 else 0
        rollback_rate = (rolled_back / total * 100) if total > 0 else 0
        
        # Calculate duration metrics
        durations = []
        for pipeline in pipelines:
            if pipeline['completed_at'] and pipeline['created_at']:
                duration = (pipeline['completed_at'] - pipeline['created_at']).total_seconds() / 60
                durations.append(duration)
        
        avg_duration = statistics.mean(durations) if durations else 0
        median_duration = statistics.median(durations) if durations else 0
        
        result = SuccessRateMetrics(
            total_deployments=total,
            successful_deployments=successful,
            failed_deployments=failed,
            rolled_back_deployments=rolled_back,
            success_rate=round(success_rate, 2),
            failure_rate=round(failure_rate, 2),
            rollback_rate=round(rollback_rate, 2),
            average_duration=round(avg_duration, 2),
            median_duration=round(median_duration, 2),
            time_period=time_range.value
        )
        
        self._set_cache(cache_key, result)
        return result
    
    def calculate_performance_metrics(self, time_range: TimeRange = TimeRange.LAST_30D) -> PerformanceMetrics:
        """Calculate deployment performance metrics"""
        
        cache_key = self._get_cache_key("performance", time_range=time_range.value)
        cached_result = self._get_cache(cache_key)
        if cached_result:
            return cached_result
        
        pipelines = self._load_pipelines(time_range)
        
        # Extract duration data
        durations = []
        for pipeline in pipelines:
            if pipeline['completed_at'] and pipeline['created_at']:
                duration = (pipeline['completed_at'] - pipeline['created_at']).total_seconds() / 60
                durations.append(duration)
        
        if not durations:
            result = PerformanceMetrics(
                average_deployment_time=0.0,
                median_deployment_time=0.0,
                fastest_deployment=0.0,
                slowest_deployment=0.0,
                p95_deployment_time=0.0,
                p99_deployment_time=0.0,
                throughput_per_day=0.0,
                resource_utilization={}
            )
            self._set_cache(cache_key, result)
            return result
        
        # Calculate percentiles
        durations_sorted = sorted(durations)
        p95_index = int(0.95 * len(durations_sorted))
        p99_index = int(0.99 * len(durations_sorted))
        
        # Calculate throughput
        if time_range == TimeRange.LAST_24H:
            days = 1
        elif time_range == TimeRange.LAST_7D:
            days = 7
        elif time_range == TimeRange.LAST_30D:
            days = 30
        elif time_range == TimeRange.LAST_90D:
            days = 90
        else:
            days = 30
        
        throughput = len(pipelines) / days
        
        # Get resource utilization from monitoring
        resource_util = self._get_resource_utilization()
        
        result = PerformanceMetrics(
            average_deployment_time=round(statistics.mean(durations), 2),
            median_deployment_time=round(statistics.median(durations), 2),
            fastest_deployment=round(min(durations), 2),
            slowest_deployment=round(max(durations), 2),
            p95_deployment_time=round(durations_sorted[p95_index], 2),
            p99_deployment_time=round(durations_sorted[p99_index], 2),
            throughput_per_day=round(throughput, 2),
            resource_utilization=resource_util
        )
        
        self._set_cache(cache_key, result)
        return result
    
    def _get_resource_utilization(self) -> Dict[str, float]:
        """Get average resource utilization"""
        try:
            metrics_summary = self.monitoring_manager.get_metrics_summary(hours=24)
            
            # This would typically aggregate CPU, memory, disk usage metrics
            # For now, return sample data
            return {
                'cpu_usage_avg': 45.2,
                'memory_usage_avg': 62.8,
                'disk_usage_avg': 78.1,
                'network_usage_avg': 23.4
            }
        except Exception as e:
            self.logger.error(f"Failed to get resource utilization: {e}")
            return {}
    
    def analyze_trends(self, metric_name: str, time_range: TimeRange = TimeRange.LAST_30D) -> TrendAnalysis:
        """Analyze trends for a specific metric"""
        
        cache_key = self._get_cache_key("trends", metric=metric_name, time_range=time_range.value)
        cached_result = self._get_cache(cache_key)
        if cached_result:
            return cached_result
        
        # Get time series data
        time_series = self._get_metric_time_series(metric_name, time_range)
        
        if len(time_series) < 2:
            result = TrendAnalysis(
                metric_name=metric_name,
                time_series=time_series,
                trend_direction="stable",
                trend_strength=0.0,
                correlation_coefficient=0.0,
                forecast_next_period=None
            )
            self._set_cache(cache_key, result)
            return result
        
        # Calculate trend
        values = [point[1] for point in time_series]
        x_values = list(range(len(values)))
        
        # Simple linear regression
        n = len(values)
        sum_x = sum(x_values)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(x_values, values))
        sum_x2 = sum(x * x for x in x_values)
        
        # Calculate slope and correlation
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
        
        # Determine trend direction
        if abs(slope) < 0.01:
            trend_direction = "stable"
            trend_strength = 0.0
        elif slope > 0:
            trend_direction = "increasing"
            trend_strength = min(abs(slope) * 10, 1.0)
        else:
            trend_direction = "decreasing"
            trend_strength = min(abs(slope) * 10, 1.0)
        
        # Simple forecast (next period = last value + slope)
        forecast = values[-1] + slope if values else None
        
        result = TrendAnalysis(
            metric_name=metric_name,
            time_series=time_series,
            trend_direction=trend_direction,
            trend_strength=round(trend_strength, 3),
            correlation_coefficient=round(slope, 3),
            forecast_next_period=round(forecast, 2) if forecast else None
        )
        
        self._set_cache(cache_key, result)
        return result
    
    def _get_metric_time_series(self, metric_name: str, time_range: TimeRange) -> List[Tuple[datetime, float]]:
        """Get time series data for a metric"""
        # This would typically query the monitoring system
        # For now, generate sample time series data
        
        if time_range == TimeRange.LAST_24H:
            hours = 24
            interval = 1  # hourly
        elif time_range == TimeRange.LAST_7D:
            hours = 24 * 7
            interval = 6  # every 6 hours
        elif time_range == TimeRange.LAST_30D:
            hours = 24 * 30
            interval = 24  # daily
        else:
            hours = 24 * 30
            interval = 24
        
        time_series = []
        current_time = datetime.now() - timedelta(hours=hours)
        
        # Generate sample data points
        for i in range(0, hours, interval):
            timestamp = current_time + timedelta(hours=i)
            
            # Generate sample values based on metric name
            if metric_name == "success_rate":
                value = 85.0 + (i % 10) - 5  # Varies between 80-90%
            elif metric_name == "deployment_duration":
                value = 45.0 + (i % 20) - 10  # Varies between 35-55 minutes
            elif metric_name == "failure_rate":
                value = 5.0 + (i % 6) - 3  # Varies between 2-8%
            else:
                value = 50.0 + (i % 20) - 10  # Default variation
            
            time_series.append((timestamp, max(0, value)))
        
        return time_series
    
    def generate_summary_report(self, time_range: TimeRange = TimeRange.LAST_30D) -> Dict[str, Any]:
        """Generate comprehensive summary report"""
        
        cache_key = self._get_cache_key("summary_report", time_range=time_range.value)
        cached_result = self._get_cache(cache_key)
        if cached_result:
            return cached_result
        
        # Gather all metrics
        success_metrics = self.calculate_success_rates(time_range)
        performance_metrics = self.calculate_performance_metrics(time_range)
        
        # Get additional statistics
        alert_stats = self.monitoring_manager.get_alert_statistics()
        rollback_stats = self.rollback_manager.get_rollback_statistics()
        approval_stats = self.approval_manager.get_approval_statistics()
        
        # Analyze key trends
        success_trend = self.analyze_trends("success_rate", time_range)
        duration_trend = self.analyze_trends("deployment_duration", time_range)
        
        report = {
            'report_type': 'summary',
            'time_range': time_range.value,
            'generated_at': datetime.now().isoformat(),
            'success_metrics': asdict(success_metrics),
            'performance_metrics': asdict(performance_metrics),
            'alert_statistics': alert_stats,
            'rollback_statistics': rollback_stats,
            'approval_statistics': approval_stats,
            'trends': {
                'success_rate': asdict(success_trend),
                'deployment_duration': asdict(duration_trend)
            },
            'key_insights': self._generate_key_insights(success_metrics, performance_metrics, alert_stats)
        }
        
        self._set_cache(cache_key, report)
        return report
    
    def _generate_key_insights(self, success_metrics: SuccessRateMetrics, 
                              performance_metrics: PerformanceMetrics,
                              alert_stats: Dict[str, Any]) -> List[str]:
        """Generate key insights from metrics"""
        insights = []
        
        # Success rate insights
        if success_metrics.success_rate >= 95:
            insights.append(f"Excellent success rate of {success_metrics.success_rate}% indicates stable deployment process")
        elif success_metrics.success_rate >= 85:
            insights.append(f"Good success rate of {success_metrics.success_rate}% with room for improvement")
        else:
            insights.append(f"Low success rate of {success_metrics.success_rate}% requires immediate attention")
        
        # Performance insights
        if performance_metrics.average_deployment_time < 30:
            insights.append("Fast deployment times indicate efficient automation")
        elif performance_metrics.average_deployment_time > 60:
            insights.append("Long deployment times may indicate bottlenecks")
        
        # Rollback insights
        if success_metrics.rollback_rate > 10:
            insights.append(f"High rollback rate of {success_metrics.rollback_rate}% suggests stability issues")
        elif success_metrics.rollback_rate < 2:
            insights.append("Low rollback rate indicates reliable deployments")
        
        # Alert insights
        if alert_stats.get('active_alerts', 0) > 5:
            insights.append("High number of active alerts requires attention")
        
        # Throughput insights
        if performance_metrics.throughput_per_day > 5:
            insights.append("High deployment throughput indicates active development")
        elif performance_metrics.throughput_per_day < 1:
            insights.append("Low deployment frequency may indicate process barriers")
        
        return insights
    
    def generate_detailed_report(self, time_range: TimeRange = TimeRange.LAST_30D) -> Dict[str, Any]:
        """Generate detailed analytics report"""
        
        pipelines = self._load_pipelines(time_range)
        
        # Strategy breakdown
        strategy_stats = {}
        for pipeline in pipelines:
            strategy = pipeline['strategy']
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {'total': 0, 'successful': 0, 'failed': 0}
            
            strategy_stats[strategy]['total'] += 1
            if pipeline['status'] == 'completed':
                strategy_stats[strategy]['successful'] += 1
            elif pipeline['status'] == 'failed':
                strategy_stats[strategy]['failed'] += 1
        
        # Calculate success rates by strategy
        for strategy, stats in strategy_stats.items():
            if stats['total'] > 0:
                stats['success_rate'] = round((stats['successful'] / stats['total']) * 100, 2)
            else:
                stats['success_rate'] = 0.0
        
        # Time-based analysis
        daily_stats = self._calculate_daily_statistics(pipelines)
        
        # Component analysis
        component_stats = self._analyze_component_updates(pipelines)
        
        report = {
            'report_type': 'detailed',
            'time_range': time_range.value,
            'generated_at': datetime.now().isoformat(),
            'strategy_breakdown': strategy_stats,
            'daily_statistics': daily_stats,
            'component_analysis': component_stats,
            'failure_analysis': self._analyze_failures(pipelines),
            'recommendations': self._generate_recommendations(strategy_stats, daily_stats)
        }
        
        return report
    
    def _calculate_daily_statistics(self, pipelines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate daily deployment statistics"""
        daily_stats = {}
        
        for pipeline in pipelines:
            date_key = pipeline['created_at'].strftime('%Y-%m-%d')
            
            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    'total': 0,
                    'successful': 0,
                    'failed': 0,
                    'rolled_back': 0,
                    'total_duration': 0,
                    'deployments': []
                }
            
            stats = daily_stats[date_key]
            stats['total'] += 1
            stats['deployments'].append(pipeline['pipeline_id'])
            
            if pipeline['status'] == 'completed':
                stats['successful'] += 1
            elif pipeline['status'] == 'failed':
                stats['failed'] += 1
            elif pipeline['status'] == 'rolled_back':
                stats['rolled_back'] += 1
            
            # Add duration if available
            if pipeline['completed_at'] and pipeline['created_at']:
                duration = (pipeline['completed_at'] - pipeline['created_at']).total_seconds() / 60
                stats['total_duration'] += duration
        
        # Calculate success rates
        for date, stats in daily_stats.items():
            if stats['total'] > 0:
                stats['success_rate'] = round((stats['successful'] / stats['total']) * 100, 2)
                stats['average_duration'] = round(stats['total_duration'] / stats['total'], 2)
            else:
                stats['success_rate'] = 0.0
                stats['average_duration'] = 0.0
        
        return daily_stats
    
    def _analyze_component_updates(self, pipelines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze updates by component type"""
        component_stats = {}
        
        for pipeline in pipelines:
            # Extract component information from phases
            for phase in pipeline.get('phases', []):
                update_batch = phase.get('update_batch', {})
                for update in update_batch.get('updates', []):
                    component = update.get('component_name', 'unknown')
                    
                    if component not in component_stats:
                        component_stats[component] = {
                            'total_updates': 0,
                            'successful_updates': 0,
                            'failed_updates': 0,
                            'success_rate': 0.0
                        }
                    
                    component_stats[component]['total_updates'] += 1
                    
                    if pipeline['status'] == 'completed':
                        component_stats[component]['successful_updates'] += 1
                    elif pipeline['status'] == 'failed':
                        component_stats[component]['failed_updates'] += 1
        
        # Calculate success rates
        for component, stats in component_stats.items():
            if stats['total_updates'] > 0:
                stats['success_rate'] = round((stats['successful_updates'] / stats['total_updates']) * 100, 2)
        
        return component_stats
    
    def _analyze_failures(self, pipelines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze failure patterns"""
        failed_pipelines = [p for p in pipelines if p['status'] == 'failed']
        
        failure_analysis = {
            'total_failures': len(failed_pipelines),
            'failure_rate': round((len(failed_pipelines) / len(pipelines) * 100), 2) if pipelines else 0,
            'common_failure_patterns': [],
            'failure_by_strategy': {},
            'failure_recovery_time': 0.0
        }
        
        # Analyze by strategy
        for pipeline in failed_pipelines:
            strategy = pipeline['strategy']
            if strategy not in failure_analysis['failure_by_strategy']:
                failure_analysis['failure_by_strategy'][strategy] = 0
            failure_analysis['failure_by_strategy'][strategy] += 1
        
        return failure_analysis
    
    def _generate_recommendations(self, strategy_stats: Dict[str, Any], 
                                 daily_stats: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # Strategy recommendations
        best_strategy = max(strategy_stats.items(), key=lambda x: x[1]['success_rate']) if strategy_stats else None
        if best_strategy and best_strategy[1]['success_rate'] > 90:
            recommendations.append(f"Consider using {best_strategy[0]} strategy more frequently (success rate: {best_strategy[1]['success_rate']}%)")
        
        # Timing recommendations
        if daily_stats:
            avg_daily_deployments = sum(stats['total'] for stats in daily_stats.values()) / len(daily_stats)
            if avg_daily_deployments > 10:
                recommendations.append("High deployment frequency detected - consider batch optimization")
            elif avg_daily_deployments < 1:
                recommendations.append("Low deployment frequency - consider automation improvements")
        
        # General recommendations
        recommendations.extend([
            "Monitor deployment duration trends to identify performance bottlenecks",
            "Implement automated rollback triggers for faster failure recovery",
            "Consider A/B testing for deployment strategies",
            "Review and update approval processes based on success patterns"
        ])
        
        return recommendations
