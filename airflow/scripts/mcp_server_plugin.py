"""
Airflow MCP Server Plugin
Exposes Airflow and VM management tools to external LLMs via Model Context Protocol
"""

import asyncio
import logging
import os
import subprocess
import sys
from datetime import datetime
from typing import Any, List, Optional

try:
    from mcp.server import Server
    from mcp.types import TextContent, Tool
except ImportError:
    print(
        "Warning: mcp package not installed. MCP server will not be available.",
        file=sys.stderr,
    )
    Server = None
    Tool = None
    TextContent = None

from airflow.api.common.experimental.trigger_dag import trigger_dag as trigger_dag_api
from airflow.models import DagBag, DagRun, TaskInstance
from airflow.plugins_manager import AirflowPlugin
from airflow.utils import timezone
from airflow.utils.state import State

# Configure logging
logger = logging.getLogger("qubinode-airflow-mcp")


class AirflowMCPServer:
    """MCP Server for Airflow - exposes workflow and VM management tools"""

    def __init__(self):
        if Server is None:
            raise ImportError("mcp package not installed. Run: pip install mcp")

        self.enabled = os.getenv("AIRFLOW_MCP_ENABLED", "false").lower() == "true"
        self.api_key = os.getenv("AIRFLOW_MCP_API_KEY")
        self.read_only = (
            os.getenv("AIRFLOW_MCP_TOOLS_READ_ONLY", "false").lower() == "true"
        )
        self.dag_bag = DagBag()

        logger.info("Initializing Airflow MCP Server")
        logger.info(f"Enabled: {self.enabled}")
        logger.info(f"Read-only mode: {self.read_only}")

        if self.enabled and not self.api_key:
            raise ValueError(
                "AIRFLOW_MCP_API_KEY required when AIRFLOW_MCP_ENABLED=true"
            )

    def get_tools(self) -> List[dict]:
        """Get list of available tools based on configuration"""
        tools = []

        # DAG Management Tools
        dag_mgmt = os.getenv("AIRFLOW_MCP_TOOLS_DAG_MGMT", "true").lower() == "true"
        if dag_mgmt:
            tools.extend(
                [
                    {
                        "name": "list_dags",
                        "description": "List all available Airflow DAGs with their schedules and tags",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    },
                    {
                        "name": "get_dag_info",
                        "description": "Get detailed information about a specific DAG",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "dag_id": {
                                    "type": "string",
                                    "description": "The ID of the DAG",
                                }
                            },
                            "required": ["dag_id"],
                        },
                    },
                    {
                        "name": "get_dag_runs",
                        "description": "Get recent execution runs for a DAG",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "dag_id": {
                                    "type": "string",
                                    "description": "The ID of the DAG",
                                },
                                "limit": {
                                    "type": "integer",
                                    "default": 5,
                                    "description": "Number of recent runs to return",
                                },
                            },
                            "required": ["dag_id"],
                        },
                    },
                ]
            )

            if not self.read_only:
                tools.append(
                    {
                        "name": "trigger_dag",
                        "description": "Trigger an Airflow DAG execution with optional configuration",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "dag_id": {
                                    "type": "string",
                                    "description": "The ID of the DAG to trigger",
                                },
                                "conf": {
                                    "type": "object",
                                    "description": "Configuration dictionary for the DAG run",
                                },
                            },
                            "required": ["dag_id"],
                        },
                    }
                )

        # VM Operations Tools
        vm_ops = os.getenv("AIRFLOW_MCP_TOOLS_VM_OPS", "true").lower() == "true"
        if vm_ops:
            tools.extend(
                [
                    {
                        "name": "list_vms",
                        "description": "List all virtual machines managed by kcli/virsh",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    },
                    {
                        "name": "get_vm_info",
                        "description": "Get detailed information about a specific VM",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "vm_name": {
                                    "type": "string",
                                    "description": "Name of the virtual machine",
                                }
                            },
                            "required": ["vm_name"],
                        },
                    },
                ]
            )

            if not self.read_only:
                tools.extend(
                    [
                        {
                            "name": "create_vm",
                            "description": "Create a new virtual machine using kcli",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Name for the new VM",
                                    },
                                    "image": {
                                        "type": "string",
                                        "default": "centos10stream",
                                        "description": "Base image (e.g., centos10stream)",
                                    },
                                    "memory": {
                                        "type": "integer",
                                        "default": 2048,
                                        "description": "Memory in MB",
                                    },
                                    "cpus": {
                                        "type": "integer",
                                        "default": 2,
                                        "description": "Number of CPUs",
                                    },
                                    "disk_size": {
                                        "type": "integer",
                                        "default": 10,
                                        "description": "Disk size in GB",
                                    },
                                },
                                "required": ["name"],
                            },
                        },
                        {
                            "name": "delete_vm",
                            "description": "Delete a virtual machine",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Name of the VM to delete",
                                    }
                                },
                                "required": ["name"],
                            },
                        },
                    ]
                )

        # Log Access Tools
        log_access = os.getenv("AIRFLOW_MCP_TOOLS_LOG_ACCESS", "true").lower() == "true"
        if log_access:
            tools.append(
                {
                    "name": "get_task_logs",
                    "description": "Get logs for a specific task execution",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "dag_id": {"type": "string", "description": "DAG ID"},
                            "task_id": {"type": "string", "description": "Task ID"},
                            "execution_date": {
                                "type": "string",
                                "description": "Execution date (ISO format)",
                            },
                        },
                        "required": ["dag_id", "task_id"],
                    },
                }
            )

        logger.info(f"Registered {len(tools)} MCP tools")
        return tools

    async def call_tool(self, name: str, arguments: dict) -> str:
        """Execute a tool"""
        logger.info(f"Tool called: {name} with arguments: {arguments}")

        try:
            if name == "list_dags":
                return await self._list_dags()
            elif name == "get_dag_info":
                return await self._get_dag_info(arguments["dag_id"])
            elif name == "get_dag_runs":
                return await self._get_dag_runs(
                    arguments["dag_id"], arguments.get("limit", 5)
                )
            elif name == "trigger_dag":
                if self.read_only:
                    return "Error: Cannot trigger DAG in read-only mode"
                return await self._trigger_dag(
                    arguments["dag_id"], arguments.get("conf")
                )
            elif name == "list_vms":
                return await self._list_vms()
            elif name == "get_vm_info":
                return await self._get_vm_info(arguments["vm_name"])
            elif name == "create_vm":
                if self.read_only:
                    return "Error: Cannot create VM in read-only mode"
                return await self._create_vm(**arguments)
            elif name == "delete_vm":
                if self.read_only:
                    return "Error: Cannot delete VM in read-only mode"
                return await self._delete_vm(arguments["name"])
            elif name == "get_task_logs":
                return await self._get_task_logs(
                    arguments["dag_id"],
                    arguments["task_id"],
                    arguments.get("execution_date"),
                )
            else:
                return f"Error: Unknown tool '{name}'"

        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}", exc_info=True)
            return f"Error executing tool: {str(e)}"

    async def _list_dags(self) -> str:
        """List all DAGs"""
        dags = self.dag_bag.dags

        result = f"# Airflow DAGs ({len(dags)} total)\n\n"

        for dag_id, dag in sorted(dags.items()):
            result += f"## {dag_id}\n"
            result += f"**Description:** {dag.description or 'No description'}\n"
            result += f"**Schedule:** {dag.schedule_interval}\n"
            result += f"**Tags:** {', '.join(dag.tags) if dag.tags else 'None'}\n"
            result += f"**Owner:** {dag.owner}\n\n"

        return result

    async def _get_dag_info(self, dag_id: str) -> str:
        """Get detailed DAG information"""
        if dag_id not in self.dag_bag.dags:
            return f"Error: DAG '{dag_id}' not found"

        dag = self.dag_bag.dags[dag_id]

        result = f"# DAG: {dag_id}\n\n"
        result += f"**Description:** {dag.description or 'No description'}\n"
        result += f"**Schedule:** {dag.schedule_interval}\n"
        result += f"**Start Date:** {dag.start_date}\n"
        result += f"**Tags:** {', '.join(dag.tags) if dag.tags else 'None'}\n"
        result += f"**Owner:** {dag.owner}\n"
        result += f"**Catchup:** {dag.catchup}\n\n"

        result += f"## Tasks ({len(dag.tasks)})\n\n"
        for task in dag.tasks:
            result += f"- **{task.task_id}** ({task.task_type})\n"

        return result

    async def _get_dag_runs(self, dag_id: str, limit: int = 5) -> str:
        """Get recent DAG runs"""
        from airflow.models import DagRun
        from airflow.utils.session import create_session

        with create_session() as session:
            dag_runs = (
                session.query(DagRun)
                .filter(DagRun.dag_id == dag_id)
                .order_by(DagRun.execution_date.desc())
                .limit(limit)
                .all()
            )

        if not dag_runs:
            return f"No runs found for DAG '{dag_id}'"

        result = f"# Recent Runs for DAG: {dag_id}\n\n"

        for run in dag_runs:
            result += f"## Run {run.run_id}\n"
            result += f"**Execution Date:** {run.execution_date}\n"
            result += f"**State:** {run.state}\n"
            result += f"**Start Date:** {run.start_date}\n"
            result += f"**End Date:** {run.end_date or 'Running'}\n\n"

        return result

    async def _trigger_dag(self, dag_id: str, conf: Optional[dict] = None) -> str:
        """Trigger a DAG"""
        try:
            run_id = trigger_dag_api(dag_id, conf=conf)
            return f"Successfully triggered DAG '{dag_id}'\nRun ID: {run_id}"
        except Exception as e:
            return f"Error triggering DAG: {str(e)}"

    async def _list_vms(self) -> str:
        """List all VMs"""
        try:
            # Try virsh first
            result = subprocess.run(
                ["virsh", "-c", "qemu:///system", "list", "--all"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return f"# Virtual Machines\n\n```\n{result.stdout}\n```"
            else:
                return f"Error listing VMs: {result.stderr}"

        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _get_vm_info(self, vm_name: str) -> str:
        """Get VM information"""
        try:
            result = subprocess.run(
                ["virsh", "-c", "qemu:///system", "dominfo", vm_name],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return f"# VM Info: {vm_name}\n\n```\n{result.stdout}\n```"
            else:
                return f"Error getting VM info: {result.stderr}"

        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _create_vm(
        self,
        name: str,
        image: str = "centos10stream",
        memory: int = 2048,
        cpus: int = 2,
        disk_size: int = 10,
    ) -> str:
        """Create a VM using kcli"""
        try:
            cmd = [
                "kcli",
                "create",
                "vm",
                name,
                "-i",
                image,
                "-P",
                f"memory={memory}",
                "-P",
                f"numcpus={cpus}",
                "-P",
                f"disks=[{disk_size}]",
            ]

            logger.info(f"Creating VM with command: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                return f"# VM Created Successfully\n\n**Name:** {name}\n**Image:** {image}\n**Memory:** {memory}MB\n**CPUs:** {cpus}\n**Disk:** {disk_size}GB\n\n```\n{result.stdout}\n```"
            else:
                return f"Error creating VM:\n```\n{result.stderr}\n```"

        except subprocess.TimeoutExpired:
            return "Error: VM creation timed out (5 minutes)"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _delete_vm(self, name: str) -> str:
        """Delete a VM"""
        try:
            result = subprocess.run(
                ["kcli", "delete", "vm", name, "-y"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                return f"Successfully deleted VM '{name}'\n\n```\n{result.stdout}\n```"
            else:
                return f"Error deleting VM:\n```\n{result.stderr}\n```"

        except subprocess.TimeoutExpired:
            return "Error: Delete operation timed out"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _get_task_logs(
        self, dag_id: str, task_id: str, execution_date: Optional[str] = None
    ) -> str:
        """Get task logs"""
        # This is a simplified version
        # In production, you'd read from the Airflow log files or database
        return f"# Task Logs\n\n**DAG:** {dag_id}\n**Task:** {task_id}\n\nLog retrieval not yet implemented. Use Airflow UI for full logs."


class QuibinodeMCPPlugin(AirflowPlugin):
    """Airflow plugin for MCP server"""

    name = "qubinode_mcp_server"
