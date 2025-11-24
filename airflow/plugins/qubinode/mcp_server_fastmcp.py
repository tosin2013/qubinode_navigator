#!/usr/bin/env python3
"""
FastMCP Implementation for Qubinode Airflow MCP Server
Simple, reliable MCP server for Airflow DAG and VM management
"""

import os
import sys
import logging
import subprocess
from typing import Optional, Dict, Any
from datetime import datetime
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fastmcp-airflow")

# Configuration
MCP_ENABLED = os.getenv("AIRFLOW_MCP_ENABLED", "false").lower() == "true"
MCP_PORT = int(os.getenv("AIRFLOW_MCP_PORT", "8889"))
MCP_HOST = os.getenv("AIRFLOW_MCP_HOST", "0.0.0.0")
READ_ONLY = os.getenv("AIRFLOW_MCP_TOOLS_READ_ONLY", "false").lower() == "true"

# Create FastMCP server
mcp = FastMCP(name="qubinode-airflow-mcp")

logger.info("=" * 60)
logger.info("Initializing FastMCP Airflow Server")
logger.info(f"Port: {MCP_PORT}")
logger.info(f"Read-only mode: {READ_ONLY}")
logger.info(f"Enabled: {MCP_ENABLED}")
logger.info("=" * 60)

# Import Airflow components (may fail if not in Airflow context)
try:
    from airflow.models import DagBag
    from airflow.api.common.experimental.trigger_dag import trigger_dag as trigger_dag_api
    AIRFLOW_AVAILABLE = True
    dag_bag = DagBag()
except ImportError:
    AIRFLOW_AVAILABLE = False
    logger.warning("Airflow not available - DAG tools will return errors")


# =============================================================================
# DAG Management Tools
# =============================================================================

@mcp.tool()
async def list_dags() -> str:
    """
    List all available Airflow DAGs with their schedules, tags, and owners.
    
    Returns:
        Formatted list of all DAGs with metadata
    """
    logger.info("Tool called: list_dags()")
    
    if not AIRFLOW_AVAILABLE:
        return "Error: Airflow is not available in this environment"
    
    try:
        dags = dag_bag.dags
        output = f"# Airflow DAGs ({len(dags)} total)\n\n"
        
        for dag_id, dag in sorted(dags.items()):
            output += f"## {dag_id}\n"
            output += f"**Description:** {dag.description or 'No description'}\n"
            output += f"**Schedule:** {dag.schedule_interval}\n"
            output += f"**Tags:** {', '.join(dag.tags) if dag.tags else 'None'}\n"
            output += f"**Owner:** {dag.owner}\n\n"
        
        logger.info(f"Listed {len(dags)} DAGs")
        return output
    except Exception as e:
        error_msg = f"Error listing DAGs: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
async def get_dag_info(dag_id: str) -> str:
    """
    Get detailed information about a specific DAG including tasks and configuration.
    
    Args:
        dag_id: The ID of the DAG to query
    
    Returns:
        Detailed DAG information including tasks, schedule, and metadata
    """
    logger.info(f"Tool called: get_dag_info(dag_id='{dag_id}')")
    
    if not AIRFLOW_AVAILABLE:
        return "Error: Airflow is not available"
    
    try:
        if dag_id not in dag_bag.dags:
            return f"Error: DAG '{dag_id}' not found"
        
        dag = dag_bag.dags[dag_id]
        
        output = f"# DAG: {dag_id}\n\n"
        output += f"**Description:** {dag.description or 'No description'}\n"
        output += f"**Schedule:** {dag.schedule_interval}\n"
        output += f"**Start Date:** {dag.start_date}\n"
        output += f"**Tags:** {', '.join(dag.tags) if dag.tags else 'None'}\n"
        output += f"**Owner:** {dag.owner}\n"
        output += f"**Catchup:** {dag.catchup}\n\n"
        
        output += f"## Tasks ({len(dag.tasks)})\n\n"
        for task in dag.tasks:
            output += f"- **{task.task_id}** ({task.task_type})\n"
        
        logger.info(f"Retrieved info for DAG: {dag_id}")
        return output
    except Exception as e:
        error_msg = f"Error getting DAG info: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
async def trigger_dag(dag_id: str, conf: Optional[Dict[str, Any]] = None) -> str:
    """
    Trigger an Airflow DAG execution with optional configuration.
    
    Args:
        dag_id: The ID of the DAG to trigger
        conf: Optional configuration dictionary for the DAG run
    
    Returns:
        Success message with run ID or error message
    """
    logger.info(f"Tool called: trigger_dag(dag_id='{dag_id}', conf={conf})")
    
    if READ_ONLY:
        return "Error: Cannot trigger DAG in read-only mode"
    
    if not AIRFLOW_AVAILABLE:
        return "Error: Airflow is not available"
    
    try:
        run_id = trigger_dag_api(dag_id, conf=conf)
        logger.info(f"Triggered DAG '{dag_id}' with run_id: {run_id}")
        return f"Successfully triggered DAG '{dag_id}'\nRun ID: {run_id}"
    except Exception as e:
        error_msg = f"Error triggering DAG: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


# =============================================================================
# VM Management Tools
# =============================================================================

@mcp.tool()
async def list_vms() -> str:
    """
    List all virtual machines managed by kcli/virsh.
    
    Returns:
        Formatted list of VMs with their states
    """
    logger.info("Tool called: list_vms()")
    
    try:
        result = subprocess.run(
            ["virsh", "-c", "qemu:///system", "list", "--all"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = f"# Virtual Machines\n\n```\n{result.stdout}\n```"
            logger.info("Successfully listed VMs")
            return output
        else:
            return f"Error listing VMs: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
async def get_vm_info(vm_name: str) -> str:
    """
    Get detailed information about a specific virtual machine.
    
    Args:
        vm_name: Name of the virtual machine
    
    Returns:
        Detailed VM information including resources and state
    """
    logger.info(f"Tool called: get_vm_info(vm_name='{vm_name}')")
    
    try:
        result = subprocess.run(
            ["virsh", "-c", "qemu:///system", "dominfo", vm_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = f"# VM Info: {vm_name}\n\n```\n{result.stdout}\n```"
            logger.info(f"Retrieved info for VM: {vm_name}")
            return output
        else:
            return f"Error getting VM info: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
async def create_vm(
    name: str,
    image: str = "centos10stream",
    memory: int = 2048,
    cpus: int = 2,
    disk_size: int = 10
) -> str:
    """
    Create a new virtual machine using kcli.
    
    Args:
        name: Name for the new VM
        image: Base image (default: centos10stream)
        memory: Memory in MB (default: 2048)
        cpus: Number of CPUs (default: 2)
        disk_size: Disk size in GB (default: 10)
    
    Returns:
        Success message with VM details or error
    """
    logger.info(f"Tool called: create_vm(name='{name}', image='{image}', memory={memory}, cpus={cpus}, disk_size={disk_size})")
    
    if READ_ONLY:
        return "Error: Cannot create VM in read-only mode"
    
    try:
        cmd = [
            "kcli", "create", "vm", name,
            "-i", image,
            "-P", f"memory={memory}",
            "-P", f"numcpus={cpus}",
            "-P", f"disks=[{disk_size}]"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            output = f"# VM Created Successfully\n\n"
            output += f"**Name:** {name}\n"
            output += f"**Image:** {image}\n"
            output += f"**Memory:** {memory}MB\n"
            output += f"**CPUs:** {cpus}\n"
            output += f"**Disk:** {disk_size}GB\n\n"
            output += f"```\n{result.stdout}\n```"
            logger.info(f"Created VM: {name}")
            return output
        else:
            return f"Error creating VM:\n```\n{result.stderr}\n```"
    except subprocess.TimeoutExpired:
        return "Error: VM creation timed out (5 minutes)"
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
async def delete_vm(name: str) -> str:
    """
    Delete a virtual machine.
    
    Args:
        name: Name of the VM to delete
    
    Returns:
        Success message or error
    """
    logger.info(f"Tool called: delete_vm(name='{name}')")
    
    if READ_ONLY:
        return "Error: Cannot delete VM in read-only mode"
    
    try:
        result = subprocess.run(
            ["kcli", "delete", "vm", name, "-y"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            output = f"Successfully deleted VM '{name}'\n\n```\n{result.stdout}\n```"
            logger.info(f"Deleted VM: {name}")
            return output
        else:
            return f"Error deleting VM:\n```\n{result.stderr}\n```"
    except subprocess.TimeoutExpired:
        return "Error: Delete operation timed out"
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


# =============================================================================
# Health & Status Tools
# =============================================================================

@mcp.tool()
async def get_airflow_status() -> str:
    """
    Get Airflow system status including scheduler and webserver health.
    
    Returns:
        Formatted status report
    """
    logger.info("Tool called: get_airflow_status()")
    
    output = "# Airflow System Status\n\n"
    output += f"**Timestamp:** {datetime.now().isoformat()}\n"
    output += f"**MCP Server:** Running on port {MCP_PORT}\n"
    output += f"**Read-only Mode:** {READ_ONLY}\n\n"
    
    if AIRFLOW_AVAILABLE:
        output += f"## DAGs\n"
        output += f"Total DAGs: {len(dag_bag.dags)}\n\n"
    else:
        output += "## Status\n"
        output += "⚠️ Airflow context not available\n"
    
    return output


def main():
    """Main entry point"""
    if not MCP_ENABLED:
        logger.warning("=" * 60)
        logger.warning("Airflow MCP Server is DISABLED")
        logger.warning("To enable: export AIRFLOW_MCP_ENABLED=true")
        logger.warning("=" * 60)
        sys.exit(0)
    
    logger.info("=" * 60)
    logger.info("Starting FastMCP Airflow Server")
    logger.info(f"Host: {MCP_HOST}")
    logger.info(f"Port: {MCP_PORT}")
    logger.info("Tools: 9 total (DAGs: 3, VMs: 5, Status: 1)")
    logger.info("=" * 60)
    
    # FastMCP handles everything!
    mcp.run(transport="sse", host=MCP_HOST, port=MCP_PORT)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
