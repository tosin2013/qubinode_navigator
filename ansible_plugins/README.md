# Qubinode Navigator Ansible Callback Plugin

## Overview

The Qubinode Navigator monitoring callback plugin provides real-time monitoring, logging, and AI-powered analysis for Ansible deployments. It integrates seamlessly with the AI Assistant to provide intelligent troubleshooting and deployment insights.

## Features

### 🔍 **Real-Time Monitoring**

- **Deployment Tracking**: Monitor playbook, play, and task execution
- **Performance Metrics**: Track task duration and identify slow operations
- **Failure Detection**: Automatic failure counting and alert thresholds
- **Host Status**: Monitor host reachability and connection issues

### 🤖 **AI Assistant Integration**

- **Intelligent Analysis**: Automatic AI analysis of deployment failures
- **Diagnostic Tools**: Integration with diagnostic tools framework
- **Context-Aware**: Provides deployment context to AI for better analysis
- **Real-Time Feedback**: Immediate AI insights during deployment

### 📊 **Comprehensive Logging**

- **Structured Logging**: JSON-formatted deployment logs
- **Event Tracking**: Complete audit trail of deployment events
- **Performance Data**: Task timing and resource usage metrics
- **Error Analysis**: Detailed error messages and stack traces

### 🚨 **Alert System**

- **Configurable Thresholds**: Customizable failure count alerts
- **Automatic Diagnostics**: Trigger diagnostic scans on alert conditions
- **Visual Indicators**: Color-coded console output for different event types
- **Summary Reports**: Deployment completion summaries with statistics

## Installation

### 1. Copy Plugin Files

```bash
# Copy callback plugin to your Ansible plugins directory
cp ansible_plugins/callback_plugins/qubinode_monitoring.py /path/to/your/ansible/plugins/callback_plugins/

# Or use the included ansible.cfg
export ANSIBLE_CONFIG=/path/to/qubinode_navigator/ansible_plugins/ansible.cfg
```

### 2. Configure Ansible

Add to your `ansible.cfg`:

```ini
[defaults]
callback_plugins = /path/to/callback_plugins
callbacks_enabled = qubinode_monitoring

[callback_qubinode_monitoring]
ai_assistant_url = http://localhost:8080
enable_ai_analysis = true
log_file = /tmp/qubinode_deployment.log
alert_threshold = 3
```

### 3. Environment Variables (Optional)

```bash
export QUBINODE_AI_ASSISTANT_URL=http://localhost:8080
export QUBINODE_ENABLE_AI_ANALYSIS=true
export QUBINODE_LOG_FILE=/tmp/qubinode_deployment.log
export QUBINODE_ALERT_THRESHOLD=3
```

## Usage

### Basic Usage

```bash
# Run any Ansible playbook with monitoring enabled
ansible-playbook -i inventory playbook.yml

# The callback plugin will automatically:
# - Monitor deployment progress
# - Log events to configured file
# - Integrate with AI Assistant for analysis
# - Display real-time feedback
```

### Test the Plugin

#### **Development System Testing** (Current)

```bash
# Use the included basic test playbook (development system)
cd ansible_plugins
ansible-playbook test_monitoring.yml

# Expected output:
# 🚀 Starting Qubinode Navigator deployment: test_monitoring.yml
# 📋 Starting play: Qubinode Navigator Monitoring Test
# ✅ Task completed: Display deployment start message
# 🤖 AI Analysis: [AI insights if available]
# 🏁 Deployment completed in X.XXs
```

**⚠️ Note**: This test validates **framework integration** and **AI connectivity** but runs on a development system without full Qubinode Navigator infrastructure components (kcli, cockpit, KVM/libvirt, etc.).

#### **Production System Testing** (Full Deployment)

For testing on a **real Qubinode Navigator deployment**, the plugin would monitor:

```bash
# Example: Full hypervisor deployment with real infrastructure
ansible-playbook -i inventories/production site.yml

# Would monitor real tasks like:
# 🔧 Installing kcli and dependencies
# 🖥️ Configuring cockpit web console
# 🌐 Setting up KVM/libvirt hypervisor
# 🔒 Configuring firewall rules
# 💾 Creating storage pools and networks
# 🚨 [FAILURE] kcli installation failed - missing virtualization support
# 🤖 AI Analysis: System lacks hardware virtualization. Enable VT-x/AMD-V in BIOS...
```

## Configuration Options

### AI Assistant Integration

| Option               | Default                 | Description                 |
| -------------------- | ----------------------- | --------------------------- |
| `ai_assistant_url`   | `http://localhost:8080` | URL of AI Assistant service |
| `enable_ai_analysis` | `true`                  | Enable AI-powered analysis  |

### Logging Configuration

| Option     | Default                        | Description              |
| ---------- | ------------------------------ | ------------------------ |
| `log_file` | `/tmp/qubinode_deployment.log` | Path for deployment logs |

### Alert Settings

| Option            | Default | Description                            |
| ----------------- | ------- | -------------------------------------- |
| `alert_threshold` | `3`     | Failure count before triggering alerts |

## Output Examples

### Console Output

```
🚀 Starting Qubinode Navigator deployment: site.yml
📋 Starting play: Configure RHEL 10 Hypervisor
✅ Task completed: Install required packages (2.3s)
⚠️  Slow task detected: Download large files took 65.2s
❌ Task failed: Configure firewall on host1
🤖 AI Analysis: Firewall configuration failed due to missing iptables service.
   Recommendation: Install iptables-services package or use firewalld instead.
🚨 Alert threshold reached (3 failures)
🔧 Running diagnostic analysis...
📊 Diagnostic Analysis: System shows high CPU usage and network connectivity issues...
🏁 Deployment completed in 245.7s
⚠️  Total failures: 3
```

### Log File Format

```json
{"timestamp": "2025-11-08T10:30:00", "event_type": "deployment_start", "data": {"playbook": "site.yml", "start_time": 1699440600}}
{"timestamp": "2025-11-08T10:30:01", "event_type": "play_start", "data": {"play_name": "Configure RHEL 10", "hosts": ["host1", "host2"]}}
{"timestamp": "2025-11-08T10:30:05", "event_type": "task_success", "data": {"task_name": "Install packages", "host": "host1", "duration": 2.3}}
{"timestamp": "2025-11-08T10:30:10", "event_type": "task_failed", "data": {"task_name": "Configure firewall", "host": "host1", "error_msg": "Service not found"}}
{"timestamp": "2025-11-08T10:30:11", "event_type": "ai_analysis", "data": {"ai_response": {"text": "Firewall configuration analysis..."}}}
```

## AI Assistant Integration

### Automatic Analysis Triggers

The plugin automatically sends events to the AI Assistant for analysis when:

- Tasks fail (`task_failed`)
- Hosts become unreachable (`host_unreachable`)
- Alert thresholds are reached (`alert_triggered`)
- Deployments complete with failures (`deployment_summary`)

### AI Analysis Features

- **Context-Aware**: Includes deployment context (current play, task, failure count)
- **Intelligent Insights**: Leverages RAG knowledge base for infrastructure-specific guidance
- **Actionable Recommendations**: Provides specific steps to resolve issues
- **Performance Analysis**: Identifies bottlenecks and optimization opportunities

### Diagnostic Tools Integration

When alert thresholds are reached, the plugin automatically:

1. Calls AI Assistant diagnostic endpoint (`/diagnostics`)
1. Runs comprehensive system analysis
1. Displays key findings and recommendations
1. Logs diagnostic results for future reference

## Troubleshooting

### Common Issues

#### AI Assistant Not Available

```
Failed to send event to AI Assistant: Connection refused
```

**Solution**: Ensure AI Assistant is running on configured URL

```bash
# Check AI Assistant status
curl http://localhost:8080/health

# Start AI Assistant if needed
cd ai-assistant && ./scripts/run.sh
```

#### Permission Denied on Log File

```
Failed to write to log file: Permission denied
```

**Solution**: Ensure write permissions for log directory

```bash
sudo mkdir -p /tmp
sudo chmod 755 /tmp
```

#### Plugin Not Loading

```
Callback plugin not found
```

**Solution**: Check callback plugin path configuration

```bash
# Verify plugin path
ls -la /path/to/callback_plugins/qubinode_monitoring.py

# Check ansible.cfg
grep callback_plugins ansible.cfg
```

### Debug Mode

Enable debug logging by setting:

```bash
export ANSIBLE_DEBUG=1
ansible-playbook playbook.yml -vvv
```

## Development

### Running Tests

```bash
# Run callback plugin tests
cd /root/qubinode_navigator
python3 -m pytest tests/test_ansible_callback_plugin.py -v

# Expected: 16 tests pass
```

### Extending the Plugin

The callback plugin is designed for extensibility:

1. **Custom Event Types**: Add new event types in `_log_event()`
1. **Additional Metrics**: Extend performance tracking in task handlers
1. **Custom AI Prompts**: Modify AI analysis requests in `_send_to_ai_assistant()`
1. **Alert Integrations**: Add webhook or notification integrations

### Plugin Architecture

```
CallbackModule
├── Configuration Management
├── Event Logging System
├── AI Assistant Integration
├── Diagnostic Tools Interface
├── Performance Monitoring
├── Alert System
└── Summary Reporting
```

## Integration with Qubinode Navigator

### Plugin Framework Integration

The callback plugin integrates with the Qubinode Navigator plugin framework:

- **AIAssistantPlugin**: Direct integration for analysis and diagnostics
- **OS Plugins**: Monitors RHEL 10/CentOS 10 specific deployments
- **Cloud Plugins**: Tracks multi-cloud deployment patterns
- **Service Plugins**: Monitors service configuration and status

### Deployment Workflows

Optimized for Qubinode Navigator deployment patterns:

- **Hypervisor Setup**: Monitors KVM/libvirt configuration
- **Multi-Cloud**: Tracks Hetzner, Equinix Metal, AWS deployments
- **RHEL 10 Support**: Specialized monitoring for next-gen OS features
- **AI-Powered Troubleshooting**: Leverages infrastructure knowledge base

## License

This callback plugin is part of the Qubinode Navigator project and follows the same licensing terms.
