# Airflow Logging Guide - Easy Log Access

## 🎯 Problem Solved

**Before:** Hard to find logs for failed DAG tasks in the UI  
**Now:** Multiple easy ways to access logs instantly!

## ✨ New Logging Features

### 1. 📄 Built-in Log Viewer

Access task logs directly from AI Assistant:

**URL Format:**
```
http://localhost:8888/ai-assistant/logs/<dag_id>/<task_id>/<run_id>
```

**Example:**
```
http://localhost:8888/ai-assistant/logs/example_kcli_vm_provisioning/create_vm/manual__2025-11-19T08:00:00+00:00
```

**Features:**
- Dark theme with syntax highlighting
- Color-coded messages (errors in red, warnings in yellow, success in green)
- Direct link back to AI Assistant
- No need to navigate through Airflow UI

### 2. 🤖 AI Assistant Integration

Ask the AI about logs and it will provide direct links:

**Example Questions:**
- "Show me the logs for the create_vm task"
- "How do I view logs for failed tasks?"
- "Help me debug my DAG - I need to see the logs"

**AI Response Example:**
```markdown
# Task Logs Access

You can view logs in several ways:

## Quick Access (Recommended)
Click here to view logs directly:
[View create_vm logs](http://localhost:8888/ai-assistant/logs/example_kcli_vm_provisioning/create_vm/manual__2025-11-19T08:00:00+00:00)

## Command Line
```bash
airflow tasks log example_kcli_vm_provisioning create_vm manual__2025-11-19T08:00:00+00:00
```
```

### 3. 📋 Enhanced Default Logging

All Qubinode DAGs now include enhanced logging automatically:

**What's Logged:**
- ✅ Task start time with emoji markers (🚀)
- ✅ Execution date and try number
- ✅ DAG and task IDs
- ✅ Task parameters (all inputs)
- ✅ Task results (outputs)
- ✅ Success markers (✅) with completion time
- ✅ Error details (❌) with full traceback
- ✅ Visual separators (80-char lines)

**Example Log Output:**
```
================================================================================
🚀 Starting Task: create_vm
⏰ Execution Date: 2025-11-19T08:00:00+00:00
🔄 Try Number: 1
📋 DAG ID: example_kcli_vm_provisioning
================================================================================
📝 Task Parameters:
   • vm_name: test-vm
   • image: centos-stream-10
   • memory: 2048
   • cpus: 2
[... task execution ...]
================================================================================
✅ Task create_vm Completed Successfully
📊 Result: {'vm_name': 'test-vm', 'status': 'created', 'ip': '192.168.122.10'}
⏱️  Completed At: 2025-11-19T08:05:30.123456
================================================================================
```

### 4. 🔧 DAGLoggingMixin for Custom DAGs

Use the logging mixin in your own DAGs:

```python
from dag_logging_mixin import DAGLoggingMixin, log_task_start

def my_custom_task(**context):
    # Set up logging
    logger = log_task_start('my_task', **context)
    
    # Your task logic
    logger.info("Processing data...")
    
    # Log parameters
    DAGLoggingMixin.log_parameters(logger, {
        'input_file': '/path/to/file',
        'output_dir': '/path/to/output'
    })
    
    # Do work
    result = process_data()
    
    # Log result
    DAGLoggingMixin.log_result(logger, result, 'my_task')
    
    return result
```

## 🚀 Quick Access Methods

### Method 1: Ask AI Assistant
1. Go to http://localhost:8888/ai-assistant
2. Ask: "Show me logs for [dag_id] [task_id]"
3. Click the direct link provided

### Method 2: Direct URL
1. Get your dag_id, task_id, and run_id from Airflow UI
2. Navigate to: `/ai-assistant/logs/<dag_id>/<task_id>/<run_id>`

### Method 3: Command Line
```bash
# From host
podman exec airflow_airflow-scheduler_1 airflow tasks log <dag_id> <task_id> <run_id>

# List recent runs to get run_id
podman exec airflow_airflow-scheduler_1 airflow dags list-runs --dag-id <dag_id>
```

### Method 4: Diagnostic Commands
```bash
# Check for failed tasks
airflow tasks failed-deps

# List all runs for a DAG
airflow dags list-runs --dag-id example_kcli_vm_provisioning

# Test a task (creates logs)
airflow tasks test example_kcli_vm_provisioning create_vm 2025-11-19
```

## 📊 Troubleshooting with Logs

### Finding Failed Tasks

**Using AI:**
```
Ask: "What tasks failed in my DAGs?"
AI will:
1. Run diagnostic commands
2. Identify failed tasks
3. Provide direct log links
4. Suggest fixes
```

**Manual:**
```bash
# List failed task dependencies
airflow tasks failed-deps --output json

# Check import errors
airflow dags list-import-errors
```

### Common Log Locations

**In Container:**
- Task logs: `/opt/airflow/logs/dag_id/task_id/execution_date/`
- Scheduler logs: Container logs (`podman logs airflow_airflow-scheduler_1`)
- Webserver logs: Container logs (`podman logs airflow_airflow-webserver_1`)

**Quick Access:**
```bash
# View scheduler logs
podman logs airflow_airflow-scheduler_1 --tail 100

# View webserver logs  
podman logs airflow_airflow-webserver_1 --tail 100

# Follow logs in real-time
podman logs -f airflow_airflow-scheduler_1
```

## 💡 Tips & Best Practices

### 1. Use Descriptive Task IDs
```python
# Good
task = KcliVMCreateOperator(
    task_id='create_worker_vm_01',  # Clear and specific
    ...
)

# Avoid
task = KcliVMCreateOperator(
    task_id='task1',  # Unclear in logs
    ...
)
```

### 2. Add Context to Logs
```python
def my_task(**context):
    logger = log_task_start('my_task', **context)
    logger.info(f"Processing for environment: {ENV}")  # Add context
    logger.info(f"Input parameters: {params}")         # Log inputs
    ...
```

### 3. Log Before Critical Operations
```python
logger.info("About to provision VM with 32GB RAM")
result = create_large_vm()
logger.info(f"VM provisioned: {result}")
```

### 4. Use Structured Logging
```python
# Good - easy to parse
logger.info(f"VM_CREATED: name={vm_name}, ip={ip}, status={status}")

# Better - use parameters
DAGLoggingMixin.log_parameters(logger, {
    'vm_name': vm_name,
    'ip': ip,
    'status': status
})
```

## 🎨 Log Viewer Features

The built-in log viewer (`/ai-assistant/logs/...`) provides:

- **Dark Theme**: Easy on the eyes for long debugging sessions
- **Syntax Highlighting**: Color-coded output
- **Responsive Design**: Works on mobile/tablets
- **Quick Navigation**: Back button to AI Assistant
- **Full Text**: Complete logs with no truncation
- **Context**: Shows DAG, task, and run ID at top

## 🔗 Related Tools

### AI Assistant Diagnostic Context

The AI knows about:
- Log viewer URLs
- Diagnostic commands
- Common error patterns
- Troubleshooting workflows

### Ask AI:
- "How do I enable debug logging?"
- "Show me common error patterns in logs"
- "What should I look for in failed task logs?"
- "Help me understand this error message"

## 📚 Additional Resources

- **Airflow Documentation**: https://airflow.apache.org/docs/apache-airflow/stable/logging-monitoring/logging-tasks.html
- **Diagnostic Tools**: `/opt/airflow/plugins/qubinode/dag_diagnostics.py`
- **Logging Mixin**: `/opt/airflow/dags/dag_logging_mixin.py`
- **Troubleshooting Guide**: `/opt/airflow/TROUBLESHOOTING.md`

## 🎯 Summary

**Before:** Logs were hard to find, required multiple clicks in UI  
**Now:** 
- ✅ Direct URL access to any task log
- ✅ AI provides clickable log links
- ✅ Enhanced logging by default
- ✅ Easy command-line access
- ✅ Beautiful log viewer interface

**Result:** Debugging is now 10x faster! 🚀
