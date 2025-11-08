"""
Qubinode Navigator Monitoring and Alerting Manager

Comprehensive monitoring system for update issues, deployment health,
and system performance with intelligent alerting capabilities.

Based on ADR-0030: Software and OS Update Strategy
"""

import asyncio
import logging
import time
import json
import smtplib
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from core.rollout_pipeline import RolloutPipeline, PipelineStage
from core.update_manager import UpdateBatch


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert notification channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    LOG = "log"


class MetricType(Enum):
    """Types of metrics to collect"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Alert:
    """Alert definition"""
    alert_id: str
    title: str
    description: str
    severity: AlertSeverity
    source: str
    timestamp: datetime
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


@dataclass
class Metric:
    """Metric data point"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str]
    unit: Optional[str] = None


@dataclass
class MonitoringRule:
    """Monitoring rule definition"""
    rule_id: str
    name: str
    description: str
    metric_name: str
    condition: str  # e.g., "> 0.05", "< 95", "== 0"
    threshold_value: float
    severity: AlertSeverity
    evaluation_window: int  # seconds
    cooldown_period: int  # seconds to wait before re-alerting
    enabled: bool = True
    last_triggered: Optional[datetime] = None


class MonitoringManager:
    """
    Comprehensive Monitoring and Alerting Manager
    
    Provides metrics collection, rule evaluation, alert generation,
    and notification delivery for update and deployment monitoring.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.metrics_storage_path = Path(self.config.get('metrics_storage_path', 'data/metrics'))
        self.alerts_storage_path = Path(self.config.get('alerts_storage_path', 'data/alerts'))
        self.monitoring_enabled = self.config.get('monitoring_enabled', True)
        self.alert_channels = self.config.get('alert_channels', ['log', 'email'])
        
        # Email configuration
        self.smtp_server = self.config.get('smtp_server', 'localhost')
        self.smtp_port = self.config.get('smtp_port', 587)
        self.smtp_username = self.config.get('smtp_username', '')
        self.smtp_password = self.config.get('smtp_password', '')
        self.email_from = self.config.get('email_from', 'qubinode@localhost')
        self.email_recipients = self.config.get('email_recipients', [])
        
        # Slack configuration
        self.slack_webhook_url = self.config.get('slack_webhook_url', '')
        self.slack_channel = self.config.get('slack_channel', '#alerts')
        
        # Webhook configuration
        self.webhook_urls = self.config.get('webhook_urls', [])
        
        # State
        self.metrics: List[Metric] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.monitoring_rules: Dict[str, MonitoringRule] = {}
        self.metric_callbacks: Dict[str, List[Callable]] = {}
        
        # Initialize storage
        self.metrics_storage_path.mkdir(parents=True, exist_ok=True)
        self.alerts_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing data
        self._load_monitoring_rules()
        self._load_alerts()
        
        # Monitoring loop task (started separately)
        self._monitoring_task = None
    
    async def start_monitoring(self):
        """Start the monitoring loop"""
        if self.monitoring_enabled and self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.logger.info("Started monitoring loop")
    
    async def stop_monitoring(self):
        """Stop the monitoring loop"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            self.logger.info("Stopped monitoring loop")
    
    def _load_monitoring_rules(self):
        """Load monitoring rules from configuration"""
        # Default monitoring rules for update issues
        default_rules = [
            MonitoringRule(
                rule_id="update_failure_rate",
                name="Update Failure Rate High",
                description="Update failure rate exceeds threshold",
                metric_name="update_failure_rate",
                condition="> 0.1",
                threshold_value=0.1,
                severity=AlertSeverity.ERROR,
                evaluation_window=300,  # 5 minutes
                cooldown_period=900     # 15 minutes
            ),
            MonitoringRule(
                rule_id="deployment_duration_high",
                name="Deployment Duration Excessive",
                description="Deployment taking longer than expected",
                metric_name="deployment_duration",
                condition="> 3600",
                threshold_value=3600,  # 1 hour
                severity=AlertSeverity.WARNING,
                evaluation_window=60,
                cooldown_period=1800   # 30 minutes
            ),
            MonitoringRule(
                rule_id="rollback_triggered",
                name="Rollback Triggered",
                description="Automatic rollback has been triggered",
                metric_name="rollback_count",
                condition="> 0",
                threshold_value=0,
                severity=AlertSeverity.CRITICAL,
                evaluation_window=60,
                cooldown_period=300    # 5 minutes
            ),
            MonitoringRule(
                rule_id="system_resource_high",
                name="System Resources High",
                description="System resource usage is high during updates",
                metric_name="cpu_usage",
                condition="> 90",
                threshold_value=90,
                severity=AlertSeverity.WARNING,
                evaluation_window=180,
                cooldown_period=600    # 10 minutes
            ),
            MonitoringRule(
                rule_id="update_queue_backlog",
                name="Update Queue Backlog",
                description="Too many updates pending in queue",
                metric_name="pending_updates",
                condition="> 50",
                threshold_value=50,
                severity=AlertSeverity.WARNING,
                evaluation_window=300,
                cooldown_period=1800
            )
        ]
        
        for rule in default_rules:
            self.monitoring_rules[rule.rule_id] = rule
        
        self.logger.info(f"Loaded {len(self.monitoring_rules)} monitoring rules")
    
    def _load_alerts(self):
        """Load existing alerts from storage"""
        try:
            for alert_file in self.alerts_storage_path.glob("alert_*.json"):
                with open(alert_file, 'r') as f:
                    alert_data = json.load(f)
                    alert = self._deserialize_alert(alert_data)
                    
                    if not alert.resolved:
                        self.active_alerts[alert.alert_id] = alert
                    else:
                        self.alert_history.append(alert)
            
            self.logger.info(f"Loaded {len(self.active_alerts)} active alerts and {len(self.alert_history)} resolved alerts")
            
        except Exception as e:
            self.logger.error(f"Failed to load alerts: {e}")
    
    def _save_alert(self, alert: Alert):
        """Save alert to storage"""
        try:
            alert_file = self.alerts_storage_path / f"alert_{alert.alert_id}.json"
            alert_data = self._serialize_alert(alert)
            
            with open(alert_file, 'w') as f:
                json.dump(alert_data, f, indent=2, default=str)
            
            self.logger.debug(f"Saved alert {alert.alert_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to save alert {alert.alert_id}: {e}")
    
    def _serialize_alert(self, alert: Alert) -> Dict[str, Any]:
        """Serialize alert to JSON format"""
        return {
            'alert_id': alert.alert_id,
            'title': alert.title,
            'description': alert.description,
            'severity': alert.severity.value,
            'source': alert.source,
            'timestamp': alert.timestamp.isoformat(),
            'metadata': alert.metadata,
            'resolved': alert.resolved,
            'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
            'resolution_notes': alert.resolution_notes
        }
    
    def _deserialize_alert(self, data: Dict[str, Any]) -> Alert:
        """Deserialize alert from JSON format"""
        return Alert(
            alert_id=data['alert_id'],
            title=data['title'],
            description=data['description'],
            severity=AlertSeverity(data['severity']),
            source=data['source'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data['metadata'],
            resolved=data['resolved'],
            resolved_at=datetime.fromisoformat(data['resolved_at']) if data.get('resolved_at') else None,
            resolution_notes=data.get('resolution_notes')
        )
    
    async def record_metric(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE, 
                           labels: Dict[str, str] = None, unit: str = None):
        """Record a metric value"""
        if not self.monitoring_enabled:
            return
        
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=datetime.now(),
            labels=labels or {},
            unit=unit
        )
        
        self.metrics.append(metric)
        
        # Keep only recent metrics (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
        
        # Trigger callbacks
        if name in self.metric_callbacks:
            for callback in self.metric_callbacks[name]:
                try:
                    await callback(metric)
                except Exception as e:
                    self.logger.error(f"Metric callback error for {name}: {e}")
        
        self.logger.debug(f"Recorded metric: {name}={value} {unit or ''}")
    
    def register_metric_callback(self, metric_name: str, callback: Callable):
        """Register callback for metric updates"""
        if metric_name not in self.metric_callbacks:
            self.metric_callbacks[metric_name] = []
        self.metric_callbacks[metric_name].append(callback)
    
    async def create_alert(self, title: str, description: str, severity: AlertSeverity, 
                          source: str, metadata: Dict[str, Any] = None) -> Alert:
        """Create and process a new alert"""
        alert_id = f"alert_{int(time.time())}_{source}"
        
        alert = Alert(
            alert_id=alert_id,
            title=title,
            description=description,
            severity=severity,
            source=source,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        self._save_alert(alert)
        
        # Send notifications
        await self._send_alert_notifications(alert)
        
        self.logger.info(f"Created {severity.value} alert: {title}")
        
        return alert
    
    async def resolve_alert(self, alert_id: str, resolution_notes: str = None):
        """Resolve an active alert"""
        if alert_id not in self.active_alerts:
            self.logger.warning(f"Alert {alert_id} not found in active alerts")
            return
        
        alert = self.active_alerts[alert_id]
        alert.resolved = True
        alert.resolved_at = datetime.now()
        alert.resolution_notes = resolution_notes
        
        # Move to history
        self.alert_history.append(alert)
        del self.active_alerts[alert_id]
        
        # Save updated alert
        self._save_alert(alert)
        
        self.logger.info(f"Resolved alert: {alert.title}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for rule evaluation"""
        while True:
            try:
                await self._evaluate_monitoring_rules()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _evaluate_monitoring_rules(self):
        """Evaluate all monitoring rules against current metrics"""
        for rule in self.monitoring_rules.values():
            if not rule.enabled:
                continue
            
            # Check cooldown period
            if rule.last_triggered:
                time_since_last = (datetime.now() - rule.last_triggered).total_seconds()
                if time_since_last < rule.cooldown_period:
                    continue
            
            # Get recent metrics for this rule
            cutoff_time = datetime.now() - timedelta(seconds=rule.evaluation_window)
            relevant_metrics = [
                m for m in self.metrics 
                if m.name == rule.metric_name and m.timestamp > cutoff_time
            ]
            
            if not relevant_metrics:
                continue
            
            # Evaluate condition
            if await self._evaluate_rule_condition(rule, relevant_metrics):
                await self._trigger_rule_alert(rule, relevant_metrics)
    
    async def _evaluate_rule_condition(self, rule: MonitoringRule, metrics: List[Metric]) -> bool:
        """Evaluate if rule condition is met"""
        if not metrics:
            return False
        
        # Use the most recent metric value
        latest_metric = max(metrics, key=lambda m: m.timestamp)
        value = latest_metric.value
        
        # Parse condition
        condition = rule.condition.strip()
        threshold = rule.threshold_value
        
        if condition.startswith('>'):
            return value > threshold
        elif condition.startswith('<'):
            return value < threshold
        elif condition.startswith('>='):
            return value >= threshold
        elif condition.startswith('<='):
            return value <= threshold
        elif condition.startswith('=='):
            return value == threshold
        elif condition.startswith('!='):
            return value != threshold
        else:
            self.logger.warning(f"Unknown condition format: {condition}")
            return False
    
    async def _trigger_rule_alert(self, rule: MonitoringRule, metrics: List[Metric]):
        """Trigger alert for monitoring rule"""
        rule.last_triggered = datetime.now()
        
        latest_metric = max(metrics, key=lambda m: m.timestamp)
        
        alert_metadata = {
            'rule_id': rule.rule_id,
            'metric_name': rule.metric_name,
            'metric_value': latest_metric.value,
            'threshold': rule.threshold_value,
            'condition': rule.condition,
            'evaluation_window': rule.evaluation_window
        }
        
        await self.create_alert(
            title=rule.name,
            description=f"{rule.description}. Current value: {latest_metric.value}, Threshold: {rule.threshold_value}",
            severity=rule.severity,
            source=f"monitoring_rule_{rule.rule_id}",
            metadata=alert_metadata
        )
    
    async def _send_alert_notifications(self, alert: Alert):
        """Send alert notifications through configured channels"""
        for channel in self.alert_channels:
            try:
                if channel == 'email':
                    await self._send_email_alert(alert)
                elif channel == 'slack':
                    await self._send_slack_alert(alert)
                elif channel == 'webhook':
                    await self._send_webhook_alert(alert)
                elif channel == 'log':
                    await self._log_alert(alert)
                else:
                    self.logger.warning(f"Unknown alert channel: {channel}")
            except Exception as e:
                self.logger.error(f"Failed to send alert via {channel}: {e}")
    
    async def _send_email_alert(self, alert: Alert):
        """Send alert via email"""
        if not self.email_recipients:
            return
        
        subject = f"[{alert.severity.value.upper()}] Qubinode Navigator Alert: {alert.title}"
        
        body = f"""
Alert Details:
- Title: {alert.title}
- Severity: {alert.severity.value.upper()}
- Source: {alert.source}
- Time: {alert.timestamp}
- Description: {alert.description}

Metadata:
{json.dumps(alert.metadata, indent=2)}

--
Qubinode Navigator Monitoring System
        """.strip()
        
        msg = MIMEMultipart()
        msg['From'] = self.email_from
        msg['To'] = ', '.join(self.email_recipients)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email (in a separate thread to avoid blocking)
        def send_email():
            try:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.smtp_username and self.smtp_password:
                        server.starttls()
                        server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
            except Exception as e:
                self.logger.error(f"Failed to send email: {e}")
        
        asyncio.get_event_loop().run_in_executor(None, send_email)
    
    async def _send_slack_alert(self, alert: Alert):
        """Send alert via Slack webhook"""
        if not self.slack_webhook_url:
            return
        
        severity_colors = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9900",
            AlertSeverity.ERROR: "#ff0000",
            AlertSeverity.CRITICAL: "#8B0000"
        }
        
        payload = {
            "channel": self.slack_channel,
            "username": "Qubinode Navigator",
            "icon_emoji": ":warning:",
            "attachments": [
                {
                    "color": severity_colors.get(alert.severity, "#36a64f"),
                    "title": f"{alert.severity.value.upper()}: {alert.title}",
                    "text": alert.description,
                    "fields": [
                        {"title": "Source", "value": alert.source, "short": True},
                        {"title": "Time", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "short": True}
                    ],
                    "footer": "Qubinode Navigator Monitoring",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }
        
        async with asyncio.timeout(10):
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: requests.post(self.slack_webhook_url, json=payload)
            )
            
            if response.status_code != 200:
                self.logger.error(f"Slack webhook failed: {response.status_code}")
    
    async def _send_webhook_alert(self, alert: Alert):
        """Send alert via webhook"""
        if not self.webhook_urls:
            return
        
        payload = {
            "alert_id": alert.alert_id,
            "title": alert.title,
            "description": alert.description,
            "severity": alert.severity.value,
            "source": alert.source,
            "timestamp": alert.timestamp.isoformat(),
            "metadata": alert.metadata
        }
        
        for webhook_url in self.webhook_urls:
            try:
                async with asyncio.timeout(10):
                    response = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: requests.post(webhook_url, json=payload)
                    )
                    
                    if response.status_code not in [200, 201, 202]:
                        self.logger.error(f"Webhook {webhook_url} failed: {response.status_code}")
            except Exception as e:
                self.logger.error(f"Webhook {webhook_url} error: {e}")
    
    async def _log_alert(self, alert: Alert):
        """Log alert to system logs"""
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }.get(alert.severity, logging.INFO)
        
        self.logger.log(
            log_level,
            f"ALERT [{alert.severity.value.upper()}] {alert.title}: {alert.description} (Source: {alert.source})"
        )
    
    # Monitoring methods for specific update issues
    
    async def monitor_update_pipeline(self, pipeline: RolloutPipeline):
        """Monitor update pipeline execution"""
        pipeline_id = pipeline.pipeline_id
        
        # Record pipeline start
        await self.record_metric(
            "pipeline_started",
            1,
            MetricType.COUNTER,
            labels={"pipeline_id": pipeline_id, "strategy": pipeline.strategy.value}
        )
        
        start_time = time.time()
        
        # Monitor pipeline progress
        while pipeline.status in [PipelineStage.PENDING, PipelineStage.APPROVED, PipelineStage.DEPLOYING, PipelineStage.VALIDATING]:
            # Record current duration
            current_duration = time.time() - start_time
            await self.record_metric(
                "deployment_duration",
                current_duration,
                MetricType.GAUGE,
                labels={"pipeline_id": pipeline_id}
            )
            
            # Check for failures
            failed_phases = [p for p in pipeline.phases if p.stage == PipelineStage.FAILED]
            if failed_phases:
                await self.record_metric(
                    "update_failure_rate",
                    len(failed_phases) / len(pipeline.phases),
                    MetricType.GAUGE,
                    labels={"pipeline_id": pipeline_id}
                )
            
            await asyncio.sleep(30)
        
        # Record final metrics
        total_duration = time.time() - start_time
        await self.record_metric(
            "deployment_duration",
            total_duration,
            MetricType.HISTOGRAM,
            labels={"pipeline_id": pipeline_id, "status": pipeline.status.value}
        )
        
        if pipeline.status == PipelineStage.COMPLETED:
            await self.record_metric("pipeline_success", 1, MetricType.COUNTER, labels={"pipeline_id": pipeline_id})
        elif pipeline.status == PipelineStage.FAILED:
            await self.record_metric("pipeline_failure", 1, MetricType.COUNTER, labels={"pipeline_id": pipeline_id})
        elif pipeline.status == PipelineStage.ROLLED_BACK:
            await self.record_metric("rollback_count", 1, MetricType.COUNTER, labels={"pipeline_id": pipeline_id})
    
    async def monitor_system_resources(self):
        """Monitor system resource usage during updates"""
        try:
            # CPU usage
            with open('/proc/loadavg', 'r') as f:
                load_avg = float(f.read().split()[0])
                cpu_usage = min(load_avg * 100, 100)  # Rough approximation
            
            await self.record_metric("cpu_usage", cpu_usage, MetricType.GAUGE, unit="%")
            
            # Memory usage
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                total_mem = int([line for line in meminfo.split('\n') if 'MemTotal' in line][0].split()[1])
                available_mem = int([line for line in meminfo.split('\n') if 'MemAvailable' in line][0].split()[1])
                memory_usage = ((total_mem - available_mem) / total_mem) * 100
            
            await self.record_metric("memory_usage", memory_usage, MetricType.GAUGE, unit="%")
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        all_alerts = list(self.active_alerts.values()) + self.alert_history
        
        if not all_alerts:
            return {
                'total_alerts': 0,
                'active_alerts': 0,
                'resolved_alerts': 0,
                'severity_breakdown': {},
                'source_breakdown': {},
                'resolution_rate': 0.0
            }
        
        # Calculate statistics
        severity_counts = {}
        source_counts = {}
        
        for alert in all_alerts:
            severity_counts[alert.severity.value] = severity_counts.get(alert.severity.value, 0) + 1
            source_counts[alert.source] = source_counts.get(alert.source, 0) + 1
        
        resolution_rate = len(self.alert_history) / len(all_alerts) * 100 if all_alerts else 0
        
        return {
            'total_alerts': len(all_alerts),
            'active_alerts': len(self.active_alerts),
            'resolved_alerts': len(self.alert_history),
            'severity_breakdown': severity_counts,
            'source_breakdown': source_counts,
            'resolution_rate': round(resolution_rate, 1)
        }
    
    def get_metrics_summary(self, metric_name: str = None, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        if metric_name:
            metrics = [m for m in self.metrics if m.name == metric_name and m.timestamp > cutoff_time]
        else:
            metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
        
        if not metrics:
            return {'total_metrics': 0, 'metric_names': [], 'time_range_hours': hours}
        
        metric_names = list(set(m.name for m in metrics))
        
        return {
            'total_metrics': len(metrics),
            'metric_names': metric_names,
            'time_range_hours': hours,
            'oldest_metric': min(m.timestamp for m in metrics).isoformat(),
            'newest_metric': max(m.timestamp for m in metrics).isoformat()
        }
