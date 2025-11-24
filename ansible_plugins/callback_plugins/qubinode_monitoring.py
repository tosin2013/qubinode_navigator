"""
Qubinode Navigator Real-Time Monitoring Callback Plugin

This Ansible callback plugin provides real-time monitoring and logging
for Qubinode Navigator deployments, integrating with the AI Assistant
for intelligent analysis and troubleshooting.

Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import time
import datetime
import os
import requests
from collections import defaultdict
from ansible.plugins.callback import CallbackBase
from ansible.module_utils._text import to_text

DOCUMENTATION = '''
    name: qubinode_monitoring
    type: notification
    short_description: Real-time monitoring for Qubinode Navigator deployments
    version_added: "1.0"
    description:
        - Provides real-time monitoring and logging for Qubinode Navigator deployments
        - Integrates with AI Assistant for intelligent analysis and troubleshooting
        - Tracks deployment progress, performance metrics, and error patterns
        - Sends alerts and notifications for critical events
    requirements:
        - requests (for AI Assistant integration)
    options:
        ai_assistant_url:
            description: URL of the AI Assistant service
            default: http://localhost:8080
            env:
                - name: QUBINODE_AI_ASSISTANT_URL
            ini:
                - section: callback_qubinode_monitoring
                  key: ai_assistant_url
        enable_ai_analysis:
            description: Enable AI-powered analysis of deployment events
            default: true
            type: bool
            env:
                - name: QUBINODE_ENABLE_AI_ANALYSIS
            ini:
                - section: callback_qubinode_monitoring
                  key: enable_ai_analysis
        log_file:
            description: Path to write deployment logs
            default: /tmp/qubinode_deployment.log
            env:
                - name: QUBINODE_LOG_FILE
            ini:
                - section: callback_qubinode_monitoring
                  key: log_file
        alert_threshold:
            description: Number of failures before triggering alerts
            default: 3
            type: int
            env:
                - name: QUBINODE_ALERT_THRESHOLD
            ini:
                - section: callback_qubinode_monitoring
                  key: alert_threshold
'''


class CallbackModule(CallbackBase):
    """
    Qubinode Navigator Real-Time Monitoring Callback Plugin
    
    Provides comprehensive monitoring, logging, and AI-powered analysis
    for Ansible deployments in the Qubinode Navigator ecosystem.
    """
    
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'qubinode_monitoring'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self):
        super(CallbackModule, self).__init__()
        
        # Configuration
        self.ai_assistant_url = os.getenv('QUBINODE_AI_ASSISTANT_URL', 'http://localhost:8080')
        self.enable_ai_analysis = os.getenv('QUBINODE_ENABLE_AI_ANALYSIS', 'true').lower() == 'true'
        self.log_file = os.getenv('QUBINODE_LOG_FILE', '/tmp/qubinode_deployment.log')
        self.alert_threshold = int(os.getenv('QUBINODE_ALERT_THRESHOLD', '3'))
        
        # State tracking
        self.deployment_start_time = None
        self.task_stats = defaultdict(dict)
        self.failure_count = 0
        self.error_patterns = []
        self.performance_metrics = {}
        self.current_play = None
        self.current_task = None
        
        # Initialize log file
        self._init_log_file()
        
    def _init_log_file(self):
        """Initialize the deployment log file"""
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            with open(self.log_file, 'a') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Qubinode Navigator Deployment Log - {datetime.datetime.now()}\n")
                f.write(f"{'='*80}\n")
        except Exception as e:
            self._display.warning(f"Failed to initialize log file {self.log_file}: {e}")
    
    def _log_event(self, event_type, data):
        """Log deployment events to file and optionally send to AI Assistant"""
        timestamp = datetime.datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'event_type': event_type,
            'data': data
        }
        
        # Write to log file
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"{json.dumps(log_entry)}\n")
        except Exception as e:
            self._display.warning(f"Failed to write to log file: {e}")
        
        # Send to AI Assistant if enabled
        if self.enable_ai_analysis and event_type in ['task_failed', 'deployment_failed', 'critical_error']:
            self._send_to_ai_assistant(log_entry)
    
    def _send_to_ai_assistant(self, log_entry):
        """Send critical events to AI Assistant for analysis"""
        try:
            # Prepare AI analysis request
            analysis_request = {
                "message": f"Analyze this Qubinode Navigator deployment event: {json.dumps(log_entry)}",
                "context": {
                    "deployment_type": "qubinode_navigator",
                    "event_type": log_entry['event_type'],
                    "failure_count": self.failure_count,
                    "current_play": self.current_play,
                    "current_task": self.current_task
                }
            }
            
            # Send to AI Assistant
            response = requests.post(
                f"{self.ai_assistant_url}/chat",
                json=analysis_request,
                timeout=10
            )
            
            if response.status_code == 200:
                ai_response = response.json()
                self._display.display(
                    f"🤖 AI Analysis: {ai_response.get('text', 'No analysis available')}",
                    color='cyan'
                )
                
                # Log AI response
                self._log_event('ai_analysis', {
                    'original_event': log_entry,
                    'ai_response': ai_response
                })
            
        except Exception as e:
            self._display.warning(f"Failed to send event to AI Assistant: {e}")
    
    def _run_diagnostics(self):
        """Run diagnostic tools when failures occur"""
        if not self.enable_ai_analysis:
            return
            
        try:
            response = requests.post(
                f"{self.ai_assistant_url}/diagnostics",
                json={"include_ai_analysis": True},
                timeout=30
            )
            
            if response.status_code == 200:
                diagnostics = response.json()
                self._display.display(
                    "🔧 Running diagnostic analysis...",
                    color='yellow'
                )
                
                # Log diagnostics results
                self._log_event('diagnostics_run', diagnostics)
                
                # Display key findings
                if 'ai_analysis' in diagnostics:
                    self._display.display(
                        f"📊 Diagnostic Analysis: {diagnostics['ai_analysis'][:200]}...",
                        color='cyan'
                    )
                    
        except Exception as e:
            self._display.warning(f"Failed to run diagnostics: {e}")
    
    def v2_playbook_on_start(self, playbook):
        """Called when the playbook starts"""
        self.deployment_start_time = time.time()
        
        playbook_data = {
            'playbook': str(playbook._file_name),
            'start_time': self.deployment_start_time
        }
        
        self._display.display(
            f"🚀 Starting Qubinode Navigator deployment: {playbook._file_name}",
            color='green'
        )
        
        self._log_event('deployment_start', playbook_data)
    
    def v2_playbook_on_play_start(self, play):
        """Called when a play starts"""
        self.current_play = play.get_name()
        
        play_data = {
            'play_name': self.current_play,
            'hosts': [str(host) for host in play.hosts]
        }
        
        self._display.display(
            f"📋 Starting play: {self.current_play}",
            color='blue'
        )
        
        self._log_event('play_start', play_data)
    
    def v2_playbook_on_task_start(self, task, is_conditional):
        """Called when a task starts"""
        self.current_task = task.get_name()
        
        task_data = {
            'task_name': self.current_task,
            'is_conditional': is_conditional,
            'start_time': time.time()
        }
        
        self.task_stats[self.current_task]['start_time'] = task_data['start_time']
        
        self._log_event('task_start', task_data)
    
    def v2_runner_on_ok(self, result):
        """Called when a task succeeds"""
        task_name = result._task.get_name()
        host = result._host.get_name()
        
        # Calculate task duration
        start_time = self.task_stats[task_name].get('start_time', time.time())
        duration = time.time() - start_time
        
        result_data = {
            'task_name': task_name,
            'host': host,
            'duration': duration,
            'status': 'success'
        }
        
        if duration > 60:  # Log slow tasks
            self._display.display(
                f"⚠️  Slow task detected: {task_name} took {duration:.2f}s",
                color='yellow'
            )
        
        self._log_event('task_success', result_data)
    
    def v2_runner_on_failed(self, result, ignore_errors=False):
        """Called when a task fails"""
        self.failure_count += 1
        task_name = result._task.get_name()
        host = result._host.get_name()
        
        error_msg = to_text(result._result.get('msg', ''))
        stderr = to_text(result._result.get('stderr', ''))
        
        failure_data = {
            'task_name': task_name,
            'host': host,
            'error_msg': error_msg,
            'stderr': stderr,
            'ignore_errors': ignore_errors,
            'failure_count': self.failure_count
        }
        
        self._display.display(
            f"❌ Task failed: {task_name} on {host}",
            color='red'
        )
        
        if error_msg:
            self._display.display(f"   Error: {error_msg}", color='red')
        
        self._log_event('task_failed', failure_data)
        
        # Trigger diagnostics if threshold reached
        if self.failure_count >= self.alert_threshold:
            self._display.display(
                f"🚨 Alert threshold reached ({self.failure_count} failures)",
                color='red'
            )
            self._run_diagnostics()
    
    def v2_runner_on_unreachable(self, result):
        """Called when a host is unreachable"""
        host = result._host.get_name()
        
        unreachable_data = {
            'host': host,
            'msg': to_text(result._result.get('msg', ''))
        }
        
        self._display.display(
            f"🔌 Host unreachable: {host}",
            color='red'
        )
        
        self._log_event('host_unreachable', unreachable_data)
    
    def v2_playbook_on_stats(self, stats):
        """Called when the playbook completes"""
        if self.deployment_start_time:
            total_duration = time.time() - self.deployment_start_time
        else:
            total_duration = 0
        
        # Collect final statistics
        summary_stats = {}
        for host in stats.processed:
            summary_stats[host] = {
                'ok': stats.ok.get(host, 0),
                'changed': stats.changed.get(host, 0),
                'unreachable': stats.dark.get(host, 0),
                'failed': stats.failures.get(host, 0),
                'skipped': stats.skipped.get(host, 0)
            }
        
        deployment_summary = {
            'total_duration': total_duration,
            'total_failures': self.failure_count,
            'host_stats': summary_stats,
            'end_time': time.time()
        }
        
        # Display summary
        self._display.display(
            f"🏁 Deployment completed in {total_duration:.2f}s",
            color='green' if self.failure_count == 0 else 'yellow'
        )
        
        if self.failure_count > 0:
            self._display.display(
                f"⚠️  Total failures: {self.failure_count}",
                color='yellow'
            )
        
        self._log_event('deployment_complete', deployment_summary)
        
        # Final AI analysis if there were issues
        if self.failure_count > 0 and self.enable_ai_analysis:
            self._display.display(
                "🤖 Running final deployment analysis...",
                color='cyan'
            )
            self._send_to_ai_assistant({
                'event_type': 'deployment_summary',
                'data': deployment_summary
            })
