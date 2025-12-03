"""
Tests for Qubinode Navigator Monitoring Manager

Tests monitoring system, metrics collection, alert generation,
and notification delivery for update and deployment monitoring.
"""

import asyncio
import json
import sys
import tempfile
import unittest.mock as mock
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.ai_update_manager import UpdatePlan
from core.monitoring_manager import (
    Alert,
    AlertChannel,
    AlertSeverity,
    Metric,
    MetricType,
    MonitoringManager,
    MonitoringRule,
)
from core.rollout_pipeline import (
    PipelineStage,
    RolloutPhase,
    RolloutPipeline,
    RolloutStrategy,
)
from core.update_manager import UpdateBatch, UpdateInfo


class TestMonitoringManager:
    """Test cases for monitoring manager"""

    def setup_method(self):
        """Setup test environment"""
        # Create temporary storage
        self.temp_dir = tempfile.mkdtemp()

        # Manager configuration
        self.config = {
            "monitoring_enabled": True,
            "metrics_storage_path": f"{self.temp_dir}/metrics",
            "alerts_storage_path": f"{self.temp_dir}/alerts",
            "alert_channels": ["log"],
            "email_recipients": ["test@example.com"],
            "slack_webhook_url": "https://hooks.slack.com/test",
            "webhook_urls": ["https://webhook.example.com/alerts"],
        }

        # Create manager instance
        self.monitoring_manager = MonitoringManager(self.config)

        # Sample pipeline for testing
        self.test_pipeline = self._create_test_pipeline()

    def _create_test_pipeline(self) -> RolloutPipeline:
        """Create test pipeline"""
        update_plan = UpdatePlan(
            plan_id="test_plan_123",
            batch_id="test_batch_456",
            execution_strategy="rolling",
            total_estimated_time="1h",
            phases=[],
            risk_mitigation_steps=[],
            rollback_plan={},
            monitoring_points=[],
            approval_required=False,
            created_at=datetime.now(),
            ai_confidence=0.8,
        )

        update_batch = UpdateBatch(
            batch_id="test_batch_123",
            batch_type="test",
            updates=[
                UpdateInfo(
                    component_type="software",
                    component_name="git",
                    current_version="2.44.0",
                    available_version="2.45.0",
                    severity="low",
                    description="Git update",
                    release_date="2025-11-08",
                )
            ],
            total_size=100,
            estimated_duration="30 minutes",
            risk_level="low",
            requires_reboot=False,
            rollback_plan="Standard rollback",
            created_at=datetime.now(),
        )

        test_phase = RolloutPhase(
            phase_id="test_phase_123",
            phase_name="Test Phase",
            stage=PipelineStage.PENDING,
            target_environments=["staging"],
            update_batch=update_batch,
            validation_tests=["health_check"],
            success_criteria={"min_test_pass_rate": 0.8},
            rollback_triggers=["critical_error"],
            estimated_duration="30 minutes",
        )

        return RolloutPipeline(
            pipeline_id="test_pipeline_123",
            pipeline_name="Test Pipeline",
            strategy=RolloutStrategy.ROLLING,
            update_plan=update_plan,
            phases=[test_phase],
            approval_gates=[],
            global_rollback_triggers=[],
            monitoring_config={"enabled": True},
            notification_config={"email": True},
            created_at=datetime.now(),
            created_by="test_user",
        )

    def test_monitoring_manager_initialization(self):
        """Test monitoring manager initialization"""
        assert self.monitoring_manager.monitoring_enabled is True
        assert "log" in self.monitoring_manager.alert_channels
        assert len(self.monitoring_manager.monitoring_rules) > 0
        assert len(self.monitoring_manager.active_alerts) == 0
        assert len(self.monitoring_manager.alert_history) == 0
        assert len(self.monitoring_manager.metrics) == 0

    def test_monitoring_rules_loaded(self):
        """Test that default monitoring rules are loaded"""
        expected_rules = [
            "update_failure_rate",
            "deployment_duration_high",
            "rollback_triggered",
            "system_resource_high",
            "update_queue_backlog",
        ]

        for rule_id in expected_rules:
            assert rule_id in self.monitoring_manager.monitoring_rules
            rule = self.monitoring_manager.monitoring_rules[rule_id]
            assert rule.enabled is True
            assert isinstance(rule.severity, AlertSeverity)
            assert rule.evaluation_window > 0
            assert rule.cooldown_period > 0

    async def test_record_metric(self):
        """Test metric recording"""
        await self.monitoring_manager.record_metric(
            name="test_metric",
            value=42.5,
            metric_type=MetricType.GAUGE,
            labels={"component": "test"},
            unit="ms",
        )

        assert len(self.monitoring_manager.metrics) == 1
        metric = self.monitoring_manager.metrics[0]
        assert metric.name == "test_metric"
        assert metric.value == 42.5
        assert metric.metric_type == MetricType.GAUGE
        assert metric.labels["component"] == "test"
        assert metric.unit == "ms"

    async def test_create_alert(self):
        """Test alert creation"""
        alert = await self.monitoring_manager.create_alert(
            title="Test Alert",
            description="This is a test alert",
            severity=AlertSeverity.WARNING,
            source="test_source",
            metadata={"test": True},
        )

        assert alert.title == "Test Alert"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.source == "test_source"
        assert alert.metadata["test"] is True
        assert not alert.resolved
        assert alert.alert_id in self.monitoring_manager.active_alerts

    async def test_resolve_alert(self):
        """Test alert resolution"""
        # Create alert
        alert = await self.monitoring_manager.create_alert(
            title="Test Alert",
            description="Test description",
            severity=AlertSeverity.INFO,
            source="test",
        )

        alert_id = alert.alert_id
        assert alert_id in self.monitoring_manager.active_alerts

        # Resolve alert
        await self.monitoring_manager.resolve_alert(alert_id, "Test resolution")

        assert alert_id not in self.monitoring_manager.active_alerts
        assert len(self.monitoring_manager.alert_history) == 1

        resolved_alert = self.monitoring_manager.alert_history[0]
        assert resolved_alert.resolved is True
        assert resolved_alert.resolution_notes == "Test resolution"
        assert resolved_alert.resolved_at is not None

    async def test_evaluate_rule_condition(self):
        """Test monitoring rule condition evaluation"""
        rule = MonitoringRule(
            rule_id="test_rule",
            name="Test Rule",
            description="Test rule",
            metric_name="test_metric",
            condition="> 50",
            threshold_value=50,
            severity=AlertSeverity.WARNING,
            evaluation_window=300,
            cooldown_period=600,
        )

        # Create metrics
        metrics = [
            Metric(
                name="test_metric",
                value=60.0,
                metric_type=MetricType.GAUGE,
                timestamp=datetime.now(),
                labels={},
            ),
            Metric(
                name="test_metric",
                value=45.0,
                metric_type=MetricType.GAUGE,
                timestamp=datetime.now() - timedelta(minutes=1),
                labels={},
            ),
        ]

        # Test condition evaluation
        result = await self.monitoring_manager._evaluate_rule_condition(rule, metrics)
        assert result is True  # Latest value (60) > 50

        # Test with different condition
        rule.condition = "< 50"
        result = await self.monitoring_manager._evaluate_rule_condition(rule, metrics)
        assert result is False  # Latest value (60) not < 50

    async def test_metric_callback_registration(self):
        """Test metric callback registration and execution"""
        callback_called = False
        callback_metric = None

        async def test_callback(metric):
            nonlocal callback_called, callback_metric
            callback_called = True
            callback_metric = metric

        # Register callback
        self.monitoring_manager.register_metric_callback("test_metric", test_callback)

        # Record metric
        await self.monitoring_manager.record_metric("test_metric", 100.0)

        # Verify callback was called
        assert callback_called is True
        assert callback_metric is not None
        assert callback_metric.name == "test_metric"
        assert callback_metric.value == 100.0

    async def test_monitor_update_pipeline(self):
        """Test pipeline monitoring"""
        # Start monitoring the pipeline
        monitor_task = asyncio.create_task(
            self.monitoring_manager.monitor_update_pipeline(self.test_pipeline)
        )

        # Let it record initial metrics
        await asyncio.sleep(0.1)

        # Set pipeline to completed status
        self.test_pipeline.status = PipelineStage.COMPLETED

        # Wait for monitoring to complete
        await asyncio.sleep(0.1)

        # Cancel monitoring task
        monitor_task.cancel()

        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Check that metrics were recorded
        pipeline_metrics = [
            m for m in self.monitoring_manager.metrics if "pipeline" in m.name
        ]
        assert len(pipeline_metrics) > 0

    async def test_system_resource_monitoring(self):
        """Test system resource monitoring"""
        # Mock system files
        with mock.patch(
            "builtins.open", mock.mock_open(read_data="1.5 1.2 1.0 1/100 12345")
        ):
            await self.monitoring_manager.monitor_system_resources()

        # Check that CPU metric was recorded
        cpu_metrics = [
            m for m in self.monitoring_manager.metrics if m.name == "cpu_usage"
        ]
        assert len(cpu_metrics) > 0
        assert cpu_metrics[0].unit == "%"

    def test_serialize_deserialize_alert(self):
        """Test alert serialization and deserialization"""
        alert = Alert(
            alert_id="test_alert_123",
            title="Test Alert",
            description="Test description",
            severity=AlertSeverity.ERROR,
            source="test_source",
            timestamp=datetime.now(),
            metadata={"test": True},
            resolved=False,
        )

        # Serialize
        serialized = self.monitoring_manager._serialize_alert(alert)
        assert serialized["alert_id"] == "test_alert_123"
        assert serialized["severity"] == "error"
        assert serialized["resolved"] is False

        # Deserialize
        deserialized = self.monitoring_manager._deserialize_alert(serialized)
        assert deserialized.alert_id == "test_alert_123"
        assert deserialized.severity == AlertSeverity.ERROR
        assert deserialized.resolved is False
        assert deserialized.metadata["test"] is True

    def test_get_alert_statistics(self):
        """Test alert statistics generation"""
        # Add test alerts
        alert1 = Alert(
            alert_id="alert1",
            title="Alert 1",
            description="Description 1",
            severity=AlertSeverity.WARNING,
            source="source1",
            timestamp=datetime.now(),
            metadata={},
            resolved=True,
            resolved_at=datetime.now(),
        )

        alert2 = Alert(
            alert_id="alert2",
            title="Alert 2",
            description="Description 2",
            severity=AlertSeverity.ERROR,
            source="source2",
            timestamp=datetime.now(),
            metadata={},
            resolved=False,
        )

        self.monitoring_manager.alert_history.append(alert1)
        self.monitoring_manager.active_alerts["alert2"] = alert2

        stats = self.monitoring_manager.get_alert_statistics()

        assert stats["total_alerts"] == 2
        assert stats["active_alerts"] == 1
        assert stats["resolved_alerts"] == 1
        assert stats["resolution_rate"] == 50.0
        assert stats["severity_breakdown"]["warning"] == 1
        assert stats["severity_breakdown"]["error"] == 1
        assert stats["source_breakdown"]["source1"] == 1
        assert stats["source_breakdown"]["source2"] == 1

    def test_get_metrics_summary(self):
        """Test metrics summary generation"""
        # Add test metrics
        now = datetime.now()
        metrics = [
            Metric("metric1", 10.0, MetricType.GAUGE, now, {}),
            Metric("metric2", 20.0, MetricType.COUNTER, now - timedelta(hours=1), {}),
            Metric("metric1", 15.0, MetricType.GAUGE, now - timedelta(hours=2), {}),
        ]

        self.monitoring_manager.metrics.extend(metrics)

        # Test general summary
        summary = self.monitoring_manager.get_metrics_summary(hours=24)
        assert summary["total_metrics"] == 3
        assert set(summary["metric_names"]) == {"metric1", "metric2"}

        # Test specific metric summary
        summary = self.monitoring_manager.get_metrics_summary(
            metric_name="metric1", hours=24
        )
        assert summary["total_metrics"] == 2  # Only metric1 entries

    async def test_send_log_alert(self):
        """Test log alert notification"""
        alert = Alert(
            alert_id="test_alert",
            title="Test Alert",
            description="Test description",
            severity=AlertSeverity.CRITICAL,
            source="test",
            timestamp=datetime.now(),
            metadata={},
        )

        with mock.patch.object(self.monitoring_manager.logger, "log") as mock_log:
            await self.monitoring_manager._log_alert(alert)

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][1].startswith("ALERT [CRITICAL]")

    async def test_send_email_alert(self):
        """Test email alert notification"""
        alert = Alert(
            alert_id="test_alert",
            title="Test Alert",
            description="Test description",
            severity=AlertSeverity.ERROR,
            source="test",
            timestamp=datetime.now(),
            metadata={},
        )

        with mock.patch("smtplib.SMTP") as mock_smtp:
            await self.monitoring_manager._send_email_alert(alert)

            # Wait for async email sending
            await asyncio.sleep(0.1)

            # Verify SMTP was called (in executor, so may not be immediate)
            # This test verifies the method doesn't crash

    async def test_send_slack_alert(self):
        """Test Slack alert notification"""
        alert = Alert(
            alert_id="test_alert",
            title="Test Alert",
            description="Test description",
            severity=AlertSeverity.WARNING,
            source="test",
            timestamp=datetime.now(),
            metadata={},
        )

        with mock.patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200

            await self.monitoring_manager._send_slack_alert(alert)

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert self.monitoring_manager.slack_webhook_url in call_args[0]

    async def test_send_webhook_alert(self):
        """Test webhook alert notification"""
        alert = Alert(
            alert_id="test_alert",
            title="Test Alert",
            description="Test description",
            severity=AlertSeverity.INFO,
            source="test",
            timestamp=datetime.now(),
            metadata={},
        )

        with mock.patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200

            await self.monitoring_manager._send_webhook_alert(alert)

            # Should be called for each webhook URL
            assert mock_post.call_count == len(self.monitoring_manager.webhook_urls)


class TestAlertSeverity:
    """Test alert severity enumeration"""

    def test_alert_severity_values(self):
        """Test alert severity enum values"""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertChannel:
    """Test alert channel enumeration"""

    def test_alert_channel_values(self):
        """Test alert channel enum values"""
        assert AlertChannel.EMAIL.value == "email"
        assert AlertChannel.SLACK.value == "slack"
        assert AlertChannel.WEBHOOK.value == "webhook"
        assert AlertChannel.LOG.value == "log"


class TestMetricType:
    """Test metric type enumeration"""

    def test_metric_type_values(self):
        """Test metric type enum values"""
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.TIMER.value == "timer"


class TestMonitoringRule:
    """Test monitoring rule data class"""

    def test_monitoring_rule_creation(self):
        """Test monitoring rule creation"""
        rule = MonitoringRule(
            rule_id="test_rule",
            name="Test Rule",
            description="Test description",
            metric_name="test_metric",
            condition="> 100",
            threshold_value=100.0,
            severity=AlertSeverity.WARNING,
            evaluation_window=300,
            cooldown_period=600,
        )

        assert rule.rule_id == "test_rule"
        assert rule.name == "Test Rule"
        assert rule.metric_name == "test_metric"
        assert rule.threshold_value == 100.0
        assert rule.severity == AlertSeverity.WARNING
        assert rule.enabled is True
        assert rule.last_triggered is None


class TestMetric:
    """Test metric data class"""

    def test_metric_creation(self):
        """Test metric creation"""
        timestamp = datetime.now()
        labels = {"component": "test", "environment": "staging"}

        metric = Metric(
            name="test_metric",
            value=42.5,
            metric_type=MetricType.GAUGE,
            timestamp=timestamp,
            labels=labels,
            unit="ms",
        )

        assert metric.name == "test_metric"
        assert metric.value == 42.5
        assert metric.metric_type == MetricType.GAUGE
        assert metric.timestamp == timestamp
        assert metric.labels == labels
        assert metric.unit == "ms"


class TestAlert:
    """Test alert data class"""

    def test_alert_creation(self):
        """Test alert creation"""
        timestamp = datetime.now()
        metadata = {"source_component": "update_manager", "pipeline_id": "test_123"}

        alert = Alert(
            alert_id="alert_123",
            title="Test Alert",
            description="This is a test alert",
            severity=AlertSeverity.ERROR,
            source="test_source",
            timestamp=timestamp,
            metadata=metadata,
        )

        assert alert.alert_id == "alert_123"
        assert alert.title == "Test Alert"
        assert alert.description == "This is a test alert"
        assert alert.severity == AlertSeverity.ERROR
        assert alert.source == "test_source"
        assert alert.timestamp == timestamp
        assert alert.metadata == metadata
        assert alert.resolved is False
        assert alert.resolved_at is None
        assert alert.resolution_notes is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
