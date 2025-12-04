"""
Qubinode AI Assistant Chat Plugin for Airflow UI
Embeds AI Assistant chat interface directly into Airflow webserver
Based on: ADR-0036 (Chat Interface Integration)
"""

from airflow.plugins_manager import AirflowPlugin
from flask import Blueprint, jsonify, request, render_template_string
from flask_appbuilder import BaseView, expose
from airflow.www.app import csrf
import requests
import logging
import subprocess
from qubinode.dag_diagnostics import DIAGNOSTIC_COMMANDS

logger = logging.getLogger(__name__)

# AI Assistant API configuration
# Using container name for communication within the same Podman network
AI_ASSISTANT_URL = "http://qubinode-ai-assistant:8080"  # Container name on airflow_default network

# Safe commands that can be executed (read-only operations)
SAFE_COMMANDS = {
    "airflow": ["dags", "list", "tasks", "pools", "connections"],
    "kcli": ["list", "info"],
    "virsh": [
        "list",
        "dominfo",
        "net-list",
        "pool-list",
        "nodeinfo",
        "version",
        "capabilities",
    ],
    "system": ["ls", "cat", "grep", "find", "df", "free", "uptime", "date"],
}


def execute_safe_command(command_parts):
    """
    Execute safe read-only commands as airflow user
    Returns: dict with stdout, stderr, returncode
    """
    if not command_parts or len(command_parts) == 0:
        return {"error": "No command provided", "returncode": 1}

    base_cmd = command_parts[0]

    # Security check: only allow whitelisted commands
    allowed = False
    for cmd_category, allowed_cmds in SAFE_COMMANDS.items():
        if base_cmd in allowed_cmds or any(base_cmd.startswith(ac) for ac in allowed_cmds):
            allowed = True
            break

    if not allowed:
        return {
            "error": f"Command '{base_cmd}' not allowed. Only read-only commands are permitted.",
            "returncode": 1,
            "allowed_commands": SAFE_COMMANDS,
        }

    try:
        # Execute as current user (airflow user in container, not root)
        result = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,  # Prevent shell injection
        )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 30 seconds", "returncode": 124}
    except Exception as e:
        return {"error": str(e), "returncode": 1}


class AIAssistantChatView(BaseView):
    """
    Custom view that provides AI Assistant chat interface in Airflow UI
    """

    default_view = "chat"
    route_base = "/ai-assistant"

    @expose("/")
    def chat(self):
        """Render the AI Assistant chat interface"""

        chat_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Qubinode AI Assistant</title>
            <!-- Markdown rendering -->
            <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .chat-container {
                    max-width: 1000px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    display: flex;
                    flex-direction: column;
                    height: calc(100vh - 40px);
                }
                .chat-header {
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 12px 12px 0 0;
                }
                .chat-header h1 {
                    margin: 0;
                    font-size: 24px;
                }
                .chat-header p {
                    margin: 5px 0 0;
                    opacity: 0.9;
                    font-size: 14px;
                }
                .chat-messages {
                    flex: 1;
                    padding: 20px;
                    overflow-y: auto;
                }
                .message {
                    margin-bottom: 15px;
                    display: flex;
                    gap: 10px;
                }
                .message.user {
                    justify-content: flex-end;
                }
                .message-content {
                    max-width: 70%;
                    padding: 12px 16px;
                    border-radius: 12px;
                    line-height: 1.5;
                }
                .message.assistant .message-content {
                    background: #f0f0f0;
                    color: #333;
                }
                .message.user .message-content {
                    background: #667eea;
                    color: white;
                }
                .message-label {
                    font-size: 12px;
                    color: #666;
                    margin-bottom: 4px;
                    font-weight: 600;
                }
                /* Markdown styles */
                .message-content pre {
                    background: #282c34;
                    color: #abb2bf;
                    padding: 12px;
                    border-radius: 6px;
                    overflow-x: auto;
                    margin: 10px 0;
                }
                .message-content code {
                    background: #282c34;
                    color: #e06c75;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                    font-size: 13px;
                }
                .message-content pre code {
                    background: transparent;
                    color: #abb2bf;
                    padding: 0;
                }
                .message-content ul, .message-content ol {
                    margin: 10px 0;
                    padding-left: 20px;
                }
                .message-content li {
                    margin: 5px 0;
                }
                .message-content blockquote {
                    border-left: 4px solid #667eea;
                    margin: 10px 0;
                    padding-left: 16px;
                    color: #666;
                    font-style: italic;
                }
                .message-content table {
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                }
                .message-content th, .message-content td {
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }
                .message-content th {
                    background-color: #f0f0f0;
                    font-weight: 600;
                }
                .chat-input {
                    padding: 20px;
                    border-top: 1px solid #e0e0e0;
                    display: flex;
                    gap: 10px;
                }
                .chat-input input {
                    flex: 1;
                    padding: 12px 16px;
                    border: 2px solid #e0e0e0;
                    border-radius: 8px;
                    font-size: 14px;
                    outline: none;
                    transition: border-color 0.2s;
                }
                .chat-input input:focus {
                    border-color: #667eea;
                }
                .chat-input button {
                    padding: 12px 24px;
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: background 0.2s;
                }
                .chat-input button:hover {
                    background: #5568d3;
                }
                .chat-input button:disabled {
                    background: #ccc;
                    cursor: not-allowed;
                }
                .suggestions {
                    padding: 10px 20px;
                    background: #f9f9f9;
                    border-top: 1px solid #e0e0e0;
                }
                .suggestion-chip {
                    display: inline-block;
                    padding: 6px 12px;
                    margin: 4px;
                    background: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 16px;
                    font-size: 12px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .suggestion-chip:hover {
                    background: #667eea;
                    color: white;
                    border-color: #667eea;
                }
                .loading {
                    padding: 12px 16px;
                    color: #666;
                    font-style: italic;
                }
                .error-message {
                    padding: 12px 16px;
                    background: #ffebee;
                    color: #c62828;
                    border-radius: 8px;
                    margin: 10px 0;
                }
            </style>
        </head>
        <body>
            <div class="chat-container">
                <div class="chat-header">
                    <h1>🤖 Qubinode AI Assistant</h1>
                    <p>Ask questions about DAGs, troubleshoot issues, or get guidance on building workflows</p>
                </div>

                <div class="suggestions">
                    <strong style="color: #666; font-size: 13px;">Quick Actions:</strong>
                    <span class="suggestion-chip" onclick="sendSuggestion('List all available DAGs')">📋 List DAGs</span>
                    <span class="suggestion-chip" onclick="sendSuggestion('How do I create a new DAG?')">➕ Create DAG</span>
                    <span class="suggestion-chip" onclick="sendSuggestion('Show me how to create a VM using KcliVMCreateOperator')">�️ Create VM</span>
                    <span class="suggestion-chip" onclick="sendSuggestion('What virsh commands are available in Airflow?')">� Virsh Commands</span>
                    <span class="suggestion-chip" onclick="sendSuggestion('Build a DAG that provisions 3 VMs in parallel')">⚡ Multi-VM DAG</span>
                    <span class="suggestion-chip" onclick="sendSuggestion('Help me troubleshoot a failed VM provisioning task')">🔧 Troubleshoot</span>
                </div>

                <div class="chat-messages" id="chatMessages">
                    <div class="message assistant">
                        <div>
                            <div class="message-label">AI Assistant</div>
                            <div class="message-content">
                                Hello! I'm your Qubinode AI Assistant, integrated directly into Airflow with full system context. I can help you with:
                                <ul style="margin: 10px 0; padding-left: 20px;">
                                    <li><strong>Building Airflow DAGs</strong> - I know your available operators (kcli + virsh)</li>
                                    <li><strong>VM Provisioning</strong> - Using kcli and virsh commands and operators</li>
                                    <li><strong>Troubleshooting</strong> - Debugging failed tasks and workflows</li>
                                    <li><strong>Examples</strong> - Code examples for KcliVMCreateOperator, VirshCommandOperator, etc.</li>
                                    <li><strong>Documentation</strong> - Guidance on libvirt, KVM, kcli, and Airflow</li>
                                </ul>
                                <em style="color: #666; font-size: 0.9em;">💡 I have context about your environment: Airflow 2.10.4, kcli 99.0, virsh/libvirt 9.0.0, and all available operators.</em><br><br>
                                What would you like to know?
                            </div>
                        </div>
                    </div>
                </div>

                <div class="chat-input">
                    <input
                        type="text"
                        id="messageInput"
                        placeholder="Ask me anything about Airflow, DAGs, or Qubinode..."
                        onkeypress="handleKeyPress(event)"
                    >
                    <button onclick="sendMessage()" id="sendButton">Send</button>
                </div>
            </div>

            <script>
                const AI_API_URL = '/ai-assistant/api/chat';

                function sendSuggestion(text) {
                    document.getElementById('messageInput').value = text;
                    sendMessage();
                }

                function handleKeyPress(event) {
                    if (event.key === 'Enter') {
                        sendMessage();
                    }
                }

                async function sendMessage() {
                    const input = document.getElementById('messageInput');
                    const message = input.value.trim();

                    if (!message) return;

                    // Clear input
                    input.value = '';

                    // Add user message to chat
                    addMessage('user', message);

                    // Show loading (LLM inference can take 30-90 seconds)
                    const loadingDiv = document.createElement('div');
                    loadingDiv.className = 'message assistant';
                    loadingDiv.id = 'loading';
                    loadingDiv.innerHTML = '<div><div class="message-label">AI Assistant</div><div class="loading">🤔 Thinking... (this may take 30-60 seconds for AI inference)</div></div>';
                    document.getElementById('chatMessages').appendChild(loadingDiv);
                    scrollToBottom();

                    // Disable send button
                    document.getElementById('sendButton').disabled = true;

                    try {
                        const response = await fetch(AI_API_URL, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                message: message,
                                context: {
                                    source: 'airflow_ui',
                                    current_page: window.location.pathname
                                }
                            })
                        });

                        // Remove loading
                        const loadingEl = document.getElementById('loading');
                        if (loadingEl) loadingEl.remove();

                        if (!response.ok) {
                            throw new Error('Failed to get response from AI Assistant');
                        }

                        const data = await response.json();
                        addMessage('assistant', data.response);

                    } catch (error) {
                        const loadingEl = document.getElementById('loading');
                        if (loadingEl) loadingEl.remove();
                        addError('Sorry, I encountered an error: ' + error.message);
                    } finally {
                        document.getElementById('sendButton').disabled = false;
                        input.focus();
                    }
                }

                function addMessage(type, content) {
                    const messagesDiv = document.getElementById('chatMessages');
                    const messageDiv = document.createElement('div');
                    messageDiv.className = `message ${type}`;

                    const label = type === 'user' ? 'You' : 'AI Assistant';

                    // Render markdown for AI responses, plain text for user messages
                    let renderedContent;
                    if (type === 'assistant') {
                        // Use marked.js to render markdown
                        renderedContent = marked.parse(content);
                    } else {
                        // Escape HTML for user messages
                        renderedContent = escapeHtml(content);
                    }

                    messageDiv.innerHTML = `
                        <div>
                            <div class="message-label">${label}</div>
                            <div class="message-content">${renderedContent}</div>
                        </div>
                    `;

                    messagesDiv.appendChild(messageDiv);
                    scrollToBottom();
                }

                function addError(message) {
                    const messagesDiv = document.getElementById('chatMessages');
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'error-message';
                    errorDiv.textContent = message;
                    messagesDiv.appendChild(errorDiv);
                    scrollToBottom();
                }

                function escapeHtml(text) {
                    const div = document.createElement('div');
                    div.textContent = text;
                    return div.innerHTML;
                }

                function scrollToBottom() {
                    const messagesDiv = document.getElementById('chatMessages');
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }
            </script>
        </body>
        </html>
        """

        return render_template_string(chat_html)

    @expose("/logs/<dag_id>/<task_id>/<run_id>")
    def view_logs(self, dag_id, task_id, run_id):
        """Quick log viewer for task logs"""
        try:
            # Get task logs
            result = subprocess.run(
                ["airflow", "tasks", "log", dag_id, task_id, run_id],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/opt/airflow",
            )

            logs = result.stdout if result.returncode == 0 else result.stderr

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Task Logs: {dag_id} - {task_id}</title>
                <style>
                    body {{
                        font-family: 'Courier New', monospace;
                        background: #1e1e1e;
                        color: #d4d4d4;
                        padding: 20px;
                        margin: 0;
                    }}
                    .header {{
                        background: #2d2d30;
                        padding: 20px;
                        border-radius: 8px;
                        margin-bottom: 20px;
                    }}
                    .header h1 {{
                        margin: 0 0 10px 0;
                        color: #4ec9b0;
                    }}
                    .header p {{
                        margin: 5px 0;
                        color: #9cdcfe;
                    }}
                    .logs {{
                        background: #252526;
                        padding: 20px;
                        border-radius: 8px;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                        line-height: 1.5;
                    }}
                    .error {{ color: #f48771; }}
                    .warning {{ color: #dcdcaa; }}
                    .success {{ color: #4ec9b0; }}
                    .info {{ color: #9cdcfe; }}
                    .back-button {{
                        background: #0e639c;
                        color: white;
                        padding: 10px 20px;
                        text-decoration: none;
                        border-radius: 4px;
                        display: inline-block;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📋 Task Logs</h1>
                    <p><strong>DAG:</strong> {dag_id}</p>
                    <p><strong>Task:</strong> {task_id}</p>
                    <p><strong>Run ID:</strong> {run_id}</p>
                </div>
                <div class="logs">{logs}</div>
                <a href="/ai-assistant" class="back-button">← Back to AI Assistant</a>
            </body>
            </html>
            """

            return html

        except Exception as e:
            return f"<html><body><h1>Error</h1><pre>{str(e)}</pre></body></html>"

    @expose("/api/chat", methods=["POST"])
    @csrf.exempt  # Exempt from CSRF protection for API endpoint
    def chat_api(self):
        """API endpoint for chat messages"""
        try:
            data = request.get_json()
            message = data.get("message", "")
            context = data.get("context", {})

            if not message:
                return jsonify({"error": "Message is required"}), 400

            # Add comprehensive Airflow and system context
            context["airflow_integration"] = True
            context["environment"] = {
                "platform": "Apache Airflow 2.10.4",
                "deployment": "Qubinode Navigator - Podman containerized",
                "hypervisor": "KVM/libvirt (qemu:///system)",
                "container_runtime": "Podman",
                "network": "airflow_default (shared with AI Assistant)",
            }
            context["tools_available"] = {
                "kcli": {
                    "version": "99.0",
                    "description": "KVM Cloud Instances CLI for VM provisioning",
                    "capabilities": [
                        "Create VMs from cloud images",
                        "Manage VM lifecycle (start, stop, delete)",
                        "List VMs and images",
                        "SSH into VMs",
                        "Use profiles for templated deployments",
                    ],
                    "example_commands": [
                        "kcli list vm",
                        "kcli create vm myvm --image centos-stream-10",
                        "kcli delete vm myvm",
                    ],
                },
                "virsh": {
                    "version": "libvirt 9.0.0 / QEMU 10.1.0",
                    "description": "Libvirt virtualization management tool",
                    "capabilities": [
                        "List VMs (virsh list --all)",
                        "VM info and diagnostics (virsh dominfo)",
                        "Network management (virsh net-list)",
                        "Storage pool management (virsh pool-list)",
                        "Snapshot management",
                        "XML configuration editing",
                    ],
                    "example_commands": [
                        "virsh list --all",
                        "virsh dominfo <vm>",
                        "virsh net-list --all",
                        "virsh nodeinfo",
                    ],
                },
                "airflow": {
                    "version": "2.10.4",
                    "description": "Workflow orchestration platform",
                    "ui_url": "http://localhost:8888",
                    "credentials": "admin/admin",
                },
            }
            context["available_operators"] = {
                "kcli_operators": [
                    {
                        "name": "KcliVMCreateOperator",
                        "description": "Create VMs using kcli with optional AI assistance",
                        "parameters": [
                            "vm_name",
                            "image",
                            "memory",
                            "cpus",
                            "profile",
                            "ai_assisted",
                        ],
                    },
                    {
                        "name": "KcliVMDeleteOperator",
                        "description": "Delete VMs using kcli",
                        "parameters": ["vm_name", "force"],
                    },
                    {
                        "name": "KcliVMListOperator",
                        "description": "List all VMs managed by kcli",
                        "parameters": [],
                    },
                ],
                "virsh_operators": [
                    {
                        "name": "VirshCommandOperator",
                        "description": "Run any virsh command",
                        "parameters": ["command (list of args)"],
                    },
                    {
                        "name": "VirshVMStartOperator",
                        "description": "Start a VM using virsh",
                        "parameters": ["vm_name"],
                    },
                    {
                        "name": "VirshVMStopOperator",
                        "description": "Stop a VM (graceful or force)",
                        "parameters": ["vm_name", "force"],
                    },
                    {
                        "name": "VirshVMInfoOperator",
                        "description": "Get detailed VM information",
                        "parameters": ["vm_name"],
                    },
                    {
                        "name": "VirshNetworkListOperator",
                        "description": "List libvirt networks",
                        "parameters": ["show_inactive"],
                    },
                ],
                "sensors": [
                    {
                        "name": "KcliVMStatusSensor",
                        "description": "Wait for VM to reach specific status",
                        "parameters": ["vm_name", "expected_status", "timeout"],
                    }
                ],
            }
            context["example_dags"] = [
                {
                    "name": "example_kcli_vm_provisioning",
                    "description": "Full VM lifecycle: create, validate, cleanup",
                    "path": "/opt/airflow/dags/example_kcli_vm_provisioning.py",
                },
                {
                    "name": "example_kcli_virsh_combined",
                    "description": "Demonstrates using both kcli and virsh operators",
                    "path": "/opt/airflow/dags/example_kcli_virsh_combined.py",
                },
            ]
            context["documentation"] = {
                "main_readme": "/opt/airflow/README.md",
                "tools_reference": "/opt/airflow/TOOLS-AVAILABLE.md",
                "troubleshooting": "/opt/airflow/TROUBLESHOOTING.md",
                "architecture": "/opt/airflow/ARCHITECTURE.md",
            }
            context["command_execution"] = {
                "enabled": True,
                "description": "AI Assistant can execute safe read-only commands on the system",
                "execution_user": "airflow (non-root)",
                "allowed_commands": SAFE_COMMANDS,
                "examples": [
                    "airflow dags list",
                    "kcli list vm",
                    "virsh list --all",
                    "virsh nodeinfo",
                    "df -h",
                    "free -h",
                ],
                "note": "When providing command suggestions, use markdown code blocks with syntax highlighting. Commands will be executed as airflow user (non-root) for security.",
            }
            context["response_format"] = {
                "format": "markdown",
                "description": "All responses should be formatted in markdown for beautiful rendering",
                "features_available": [
                    "**Bold text** and *italic text*",
                    "```language\\ncode blocks\\n```",
                    "- Bullet lists",
                    "1. Numbered lists",
                    "| Tables | With | Columns |",
                    "> Blockquotes",
                    "[Links](url)",
                ],
                "recommendation": "Use code blocks for commands, tables for structured data, and lists for step-by-step instructions",
            }
            context["diagnostics"] = {
                "available": True,
                "description": "Advanced DAG diagnostics and troubleshooting capabilities",
                "log_viewer": {
                    "enabled": True,
                    "url_format": "/ai-assistant/logs/<dag_id>/<task_id>/<run_id>",
                    "description": "Direct log viewer for easy access to task logs",
                    "note": "When providing log help, include the direct URL for the user to click",
                },
                "commands": DIAGNOSTIC_COMMANDS,
                "capabilities": [
                    "Check DAG import errors: airflow dags list-import-errors",
                    "List failed task dependencies: airflow tasks failed-deps",
                    "View task logs: airflow tasks log <dag_id> <task_id> <run_id>",
                    "Test task execution: airflow tasks test <dag_id> <task_id> <date>",
                    "Check DAG state: airflow dags state <dag_id>",
                    "List DAG runs: airflow dags list-runs --dag-id <dag_id>",
                    "Quick log access: /ai-assistant/logs/<dag_id>/<task_id>/<run_id>",
                ],
                "troubleshooting_tips": [
                    "Always check import errors first - they prevent DAGs from loading",
                    "Use 'airflow tasks test' to debug individual tasks without running the full DAG",
                    "Check scheduler logs for system-level issues",
                    "Verify task dependencies with 'airflow tasks failed-deps'",
                    "When debugging failed tasks, provide direct log viewer links for easy access",
                ],
                "logging_features": [
                    "All Qubinode DAGs include enhanced logging by default",
                    "Task start/end timestamps logged automatically",
                    "Parameters and results logged for debugging",
                    "Errors logged with full context and traceback",
                    "Use DAGLoggingMixin for consistent logging across custom DAGs",
                ],
            }
            context["datasets"] = {
                "airflow_version": "2.10.4",
                "datasets_supported": True,
                "description": "Airflow Datasets enable data-aware DAG scheduling",
                "features": [
                    "Data-aware scheduling: DAGs trigger when datasets are updated",
                    "Dataset producers and consumers",
                    "Cross-DAG dependencies based on data",
                    "Dataset versioning and lineage tracking",
                ],
                "example_usage": """
from airflow.datasets import Dataset

# Define a dataset
my_dataset = Dataset("s3://bucket/path/data.csv")

# Producer DAG - updates the dataset
with DAG(..., schedule=None) as producer_dag:
    task = BashOperator(..., outlets=[my_dataset])

# Consumer DAG - runs when dataset is updated
with DAG(..., schedule=[my_dataset]) as consumer_dag:
    task = BashOperator(...)
""",
                "integration_ideas": [
                    "VM provisioning completion as dataset (triggers deployment DAGs)",
                    "kcli image download completion as dataset",
                    "Libvirt storage pool changes as dataset events",
                    "Configuration file updates as dataset triggers",
                ],
                "note": "Not yet implemented in Qubinode operators, but can be added for data-driven workflows",
            }
            context["user_intent"] = "User is accessing AI Assistant from Airflow UI for help with workflow orchestration, VM provisioning, or troubleshooting"

            # Connect to AI Assistant on the same Podman network
            # AI Assistant can take 30-60 seconds to respond due to LLM processing
            response = requests.post(
                f"{AI_ASSISTANT_URL}/chat",
                json={"message": message, "context": context},
                timeout=90,  # Extended timeout for LLM inference
            )

            response.raise_for_status()
            ai_response = response.json()

            return jsonify(
                {
                    "response": ai_response.get("response", "I'm not sure how to help with that."),
                    "status": "success",
                }
            )

        except requests.RequestException as e:
            logger.error(f"AI Assistant API error: {e}")
            return jsonify(
                {
                    "response": f"I'm having trouble connecting to the AI Assistant service. Please ensure it's running.\n\nError: {str(e)}",
                    "status": "error",
                }
            ), 500
        except Exception as e:
            logger.error(f"Chat API error: {e}")
            return jsonify(
                {
                    "response": f"An unexpected error occurred: {str(e)}",
                    "status": "error",
                }
            ), 500


# Create Flask Blueprint for the chat view
ai_chat_blueprint = Blueprint(
    "ai_assistant_chat",
    __name__,
    template_folder="templates",
    static_folder="static",
)


class AIAssistantChatPlugin(AirflowPlugin):
    """
    Airflow plugin that adds AI Assistant chat interface to the UI
    """

    name = "ai_assistant_chat"
    flask_blueprints = [ai_chat_blueprint]
    appbuilder_views = [{"name": "AI Assistant", "category": "Qubinode", "view": AIAssistantChatView()}]
