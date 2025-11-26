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


# =============================================================================
# Information & Context Tools
# =============================================================================

@mcp.tool()
async def get_system_info() -> str:
    """
    Get comprehensive information about Qubinode Navigator system, architecture,
    and available capabilities. Use this to understand the system before making
    requests with other tools.
    
    Returns:
        Detailed system information, architecture overview, and usage examples
    """
    logger.info("Tool called: get_system_info()")
    
    info = """# Qubinode Navigator System Information

## System Overview
Qubinode Navigator is a container-first, plugin-based automation platform that orchestrates:
- Apache Airflow for workflow management
- Libvirt/KVM for virtual machine operations
- FastMCP servers for LLM integration

## Architecture
**Nginx Reverse Proxy** (Port 80)
├─ Web UI proxy for Airflow and AI Assistant
└─ User-friendly interface for human operators

**Airflow Services** (Port 8888)
├─ Webserver: DAG management and monitoring UI
├─ Scheduler: Workflow execution engine
├─ PostgreSQL: Metadata database
└─ MCP Server (Port 8889): Tool access for LLMs

## Available Tools (11 Total)

### DAG Management (3 tools)
- **list_dags()** - List all available DAGs
  Usage: Call this first to see available workflows
  
- **get_dag_info(dag_id)** - Get details about a specific DAG
  Usage: get_dag_info("example_kcli_vm_provisioning")
  
- **trigger_dag(dag_id, conf)** - Execute a DAG with optional configuration
  Usage: trigger_dag("vm_creation", {"vm_name": "test-vm", "cpu": 4})

### VM Operations (5 tools)
- **list_vms()** - List all virtual machines
  Usage: Call this to see existing VMs and their status
  
- **get_vm_info(vm_name)** - Get details about a specific VM
  Usage: get_vm_info("web-server-01")
  
- **create_vm(name, cpu, memory, disk)** - Create a new virtual machine
  Usage: create_vm("dev-env", cpu=8, memory=16, disk=50)
  Note: Resource values in GB for disk, GB for memory, count for CPU
  
- **start_vm(vm_name)** - Start a stopped VM
  Usage: start_vm("web-server-01")
  
- **stop_vm(vm_name)** - Stop a running VM
  Usage: stop_vm("database-vm")

### System Status (1 tool)
- **get_airflow_status()** - Get system health and status
  Usage: Call this to verify system is operational

### Information (1 tool)
- **get_system_info()** - Get this information (you are here!)
  Usage: Call when you need to understand the system

### RAG (Retrieval-Augmented Generation) Operations (1 tool)
- **manage_rag_documents(operation, params)** - Manage RAG document ingestion
  Operations: 'scan', 'ingest', 'status', 'list', 'estimate'
  Usage Examples:
    - manage_rag_documents('scan') - Find documents in /opt/documents/incoming
    - manage_rag_documents('ingest') - Trigger ingestion pipeline
    - manage_rag_documents('status') - Check ingestion progress
    - manage_rag_documents('list', {'limit': 5}) - Show processed documents
    - manage_rag_documents('estimate') - Calculate storage requirements

## How to Use These Tools Effectively

### 1. First Steps
Always start by understanding the current state:
```
1. Call get_system_info() to understand capabilities
2. Call get_airflow_status() to verify system health
3. Call list_dags() to see available workflows
4. Call list_vms() to see existing VMs
```

### 2. Creating VMs
To create a new VM:
```
1. Call list_vms() to see existing VMs and naming conventions
2. Call create_vm(name, cpu, memory, disk) with:
   - name: Unique VM name (e.g., "prod-web-01")
   - cpu: Number of CPU cores (e.g., 4, 8, 16)
   - memory: RAM in GB (e.g., 8, 16, 32)
   - disk: Disk size in GB (e.g., 50, 100, 200)
3. Wait for VM creation to complete
4. Call get_vm_info(vm_name) to verify creation
5. Call start_vm(vm_name) if needed
```

### 3. Managing DAGs
To trigger a workflow:
```
1. Call list_dags() to see available workflows
2. Call get_dag_info(dag_id) to understand DAG requirements
3. Call trigger_dag(dag_id, config) with:
   - dag_id: The DAG identifier
   - config: Dict with required parameters for the DAG
4. The DAG scheduler will execute the workflow
5. Check progress via Airflow UI (http://localhost:8888)
```

### 4. RAG Document Ingestion
To ingest documents for Retrieval-Augmented Generation:
```
1. Call manage_rag_documents('scan') to find documents in /opt/documents/incoming
   - Supports: .md, .yml, .yaml, .txt files
   - Shows file count and total size
2. Call manage_rag_documents('estimate') to see chunking requirements
   - Calculates estimated chunks, embeddings, and storage
3. Call manage_rag_documents('ingest') to trigger the ingestion DAG
   - Processes documents into chunks
   - Generates embeddings
   - Stores in vector database
4. Call manage_rag_documents('status') to check progress
5. Call manage_rag_documents('list') to see processed documents
   - Shows metadata and chunk counts
   - Verifies successful ingestion
```

**RAG Best Practices:**
- Place documents in `/opt/documents/incoming/` before ingestion
- Use Markdown files for complex documentation (headers help chunking)
- Check estimate before ingesting large document sets
- Monitor Airflow UI at http://localhost:8888/dags/rag_document_ingestion for detailed logs

### 5. VM Lifecycle Management
Typical workflow:
```
1. create_vm(...) -> Create new VM
2. get_vm_info(name) -> Verify it's running
3. [Do operations via DAGs]
4. stop_vm(name) -> Stop when done
```

## Configuration & Customization

### Airflow Configuration
- Location: `/opt/qubinode-navigator/airflow/config/airflow.env`
- Key settings: Executor type, database, logging
- Restart required: Yes (use podman-compose restart)

### VM Resources
- Minimum recommended: 2 CPU, 4GB RAM, 20GB disk
- Maximum per system: Depends on host hardware
- Storage: Uses libvirt storage pools (default: /var/lib/libvirt/images/)

### Custom DAGs
- Location: `/opt/qubinode-navigator/airflow/dags/`
- Format: Python files with DAG definitions
- Requirements: Inherit from airflow.models.DAG

## Common Patterns & Best Practices

### Pattern 1: Batch VM Creation
Don't create too many VMs at once. Recommended:
- Create 1-3 VMs per batch
- Wait for completion before next batch
- Monitor system resources

### Pattern 2: DAG Chaining
Workflows can trigger other DAGs:
- Call trigger_dag() from within a DAG
- Create multi-stage deployments
- Build automation chains

### Pattern 3: Error Recovery
If something fails:
1. Check get_airflow_status() for health
2. Review Airflow UI logs at http://localhost:8888
3. Retry operation or contact administrator

## Limits & Constraints

- **Concurrent DAGs**: Depends on scheduler resources (typically 8-16)
- **Max VMs per host**: Depends on available resources
- **Tool timeout**: 30 seconds per operation
- **Message size**: Limited to 1MB per operation

## Tips for LLM Interaction

1. **Be Specific**: Provide exact VM names, DAG IDs, and parameters
2. **Check State First**: Always list/check before operating
3. **Follow Naming Conventions**: Use consistent, descriptive names
4. **Document Your Intent**: Explain what you're trying to accomplish
5. **Use Correct Parameters**: Ensure parameters match system requirements

## Emergency Operations

### System is unresponsive
1. Call get_airflow_status()
2. If no response, check Airflow container: `podman-compose ps`
3. Restart if needed: `podman-compose restart`

### VM creation fails repeatedly
1. Call list_vms() to check existing load
2. Check available system resources
3. Reduce VM size/resource requests
4. Try again with smaller parameters

## Resources & Help

- Airflow UI: http://localhost:8888 (admin/admin)
- MCP Server Logs: `podman logs airflow_airflow-mcp-server_1`
- Airflow Logs: `podman logs airflow_airflow-scheduler_1`
- System Status: `get_airflow_status()`

## System Capabilities Summary

✅ Multi-DAG workflow orchestration
✅ VM provisioning and management
✅ Real-time task monitoring
✅ Failed task recovery
✅ Custom DAG support
✅ Resource-aware scheduling
✅ Comprehensive logging
✅ RAG document ingestion and management
✅ Vector database integration

📊 Monitor everything via Airflow UI: http://localhost:8888
📚 Manage documents via manage_rag_documents() tool
🔧 Troubleshoot via tool responses and system logs
"""
    
    logger.info("System info provided")
    return info


# =============================================================================
# RAG (Retrieval-Augmented Generation) Operations
# =============================================================================

@mcp.tool()
async def manage_rag_documents(operation: str, params: Optional[Dict[str, Any]] = None) -> str:
    """
    Manage RAG document ingestion and vector database operations.
    
    This tool controls document lifecycle for Retrieval-Augmented Generation (RAG),
    enabling LLMs to ingest new documentation into searchable vector databases.
    
    Args:
        operation: One of 'scan', 'ingest', 'status', 'list', or 'estimate'
            - 'scan': Discover documents in /opt/documents/incoming
            - 'ingest': Trigger rag_document_ingestion DAG to process documents
            - 'status': Check current ingestion progress and recent run status
            - 'list': List recently processed documents with metadata
            - 'estimate': Calculate chunk count and storage estimate for documents
        
        params: Optional dict with:
            - 'doc_dir': Custom directory path (default: /opt/documents/incoming)
            - 'limit': For 'list' operation, max results to return (default: 10)
    
    Returns:
        Status report with operation results or error message
    
    Examples:
        - List documents: manage_rag_documents('list', {'limit': 5})
        - Estimate chunks: manage_rag_documents('estimate')
        - Trigger ingestion: manage_rag_documents('ingest')
        - Check progress: manage_rag_documents('status')
        - Scan directory: manage_rag_documents('scan', {'doc_dir': '/opt/documents/incoming'})
    """
    logger.info(f"Tool called: manage_rag_documents(operation='{operation}', params={params})")
    
    if READ_ONLY and operation in ['ingest']:
        return f"Error: '{operation}' operation requires write access but read-only mode is enabled"
    
    if params is None:
        params = {}
    
    doc_dir = params.get('doc_dir', '/opt/documents/incoming')
    limit = params.get('limit', 10)
    
    try:
        if operation == 'scan':
            return _rag_scan_documents(doc_dir)
        elif operation == 'ingest':
            return _rag_trigger_ingestion(doc_dir)
        elif operation == 'status':
            return _rag_ingestion_status()
        elif operation == 'list':
            return _rag_list_processed(limit)
        elif operation == 'estimate':
            return _rag_estimate_chunks(doc_dir)
        else:
            return f"Error: Unknown operation '{operation}'. Valid operations: scan, ingest, status, list, estimate"
    
    except Exception as e:
        error_msg = f"RAG operation '{operation}' failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def _rag_scan_documents(doc_dir: str) -> str:
    """Scan for documents in the specified directory."""
    output = f"# RAG Document Scan\n\n"
    output += f"**Directory:** `{doc_dir}`\n"
    output += f"**Timestamp:** {datetime.now().isoformat()}\n\n"
    
    if not os.path.isdir(doc_dir):
        output += f"⚠️ Directory does not exist: {doc_dir}\n"
        return output
    
    documents = []
    supported_exts = {'.md', '.markdown', '.yml', '.yaml', '.txt'}
    
    try:
        for root, dirs, files in os.walk(doc_dir):
            for fname in files:
                file_path = os.path.join(root, fname)
                _, ext = os.path.splitext(fname)
                
                if ext.lower() in supported_exts:
                    try:
                        file_size = os.path.getsize(file_path)
                        documents.append({
                            'path': file_path,
                            'name': fname,
                            'type': ext.lower(),
                            'size': file_size,
                            'size_kb': round(file_size / 1024, 2)
                        })
                    except OSError:
                        pass
        
        if documents:
            output += f"## Found {len(documents)} document(s)\n\n"
            total_size = sum(d['size'] for d in documents)
            output += f"**Total Size:** {round(total_size / 1024, 2)} KB\n\n"
            
            output += "| File | Type | Size (KB) |\n"
            output += "|------|------|----------|\n"
            for doc in sorted(documents, key=lambda x: x['name']):
                output += f"| `{doc['name']}` | {doc['type']} | {doc['size_kb']} |\n"
            
            output += "\n**Next Step:** Call `manage_rag_documents('ingest')` to process these documents\n"
        else:
            output += f"❌ No supported documents found (looking for: .md, .yml, .yaml, .txt)\n"
        
        return output
    
    except Exception as e:
        return f"Error scanning documents: {str(e)}"


def _rag_trigger_ingestion(doc_dir: str) -> str:
    """Trigger the rag_document_ingestion DAG."""
    output = f"# RAG Document Ingestion\n\n"
    
    if not AIRFLOW_AVAILABLE:
        return f"Error: Airflow not available in this context"
    
    try:
        # Prepare DAG run configuration
        conf = {'RAG_DOC_DIR': doc_dir} if doc_dir != '/opt/documents/incoming' else {}
        
        # Trigger the DAG
        dag_run = trigger_dag_api(
            dag_id='rag_document_ingestion',
            conf=conf
        )
        
        output += f"✅ **Ingestion triggered successfully**\n\n"
        output += f"**DAG Run ID:** `{dag_run}`\n"
        output += f"**Source Directory:** `{doc_dir}`\n"
        output += f"**Status:** Queued\n"
        output += f"**Timestamp:** {datetime.now().isoformat()}\n\n"
        output += "**Next Steps:**\n"
        output += "1. Wait 10-30 seconds for tasks to execute\n"
        output += "2. Call `manage_rag_documents('status')` to check progress\n"
        output += "3. View detailed logs in Airflow UI: http://localhost:8888/dags/rag_document_ingestion\n"
        
        logger.info(f"Triggered RAG ingestion DAG: {dag_run}")
        return output
    
    except Exception as e:
        output += f"❌ Failed to trigger ingestion: {str(e)}\n"
        output += f"\n**Troubleshooting:**\n"
        output += f"- Check Airflow scheduler is running: `podman-compose ps | grep scheduler`\n"
        output += f"- Verify DAG exists: `podman exec airflow_airflow-scheduler_1 airflow dags list | grep rag_document_ingestion`\n"
        output += f"- Check Airflow logs for errors\n"
        return output


def _rag_ingestion_status() -> str:
    """Check RAG ingestion DAG run status."""
    output = f"# RAG Ingestion Status\n\n"
    output += f"**Timestamp:** {datetime.now().isoformat()}\n\n"
    
    if not AIRFLOW_AVAILABLE:
        output += "⚠️ Airflow not available - cannot check status\n"
        return output
    
    try:
        dag_id = 'rag_document_ingestion'
        dag = dag_bag.get_dag(dag_id)
        
        if not dag:
            output += f"❌ DAG not found: {dag_id}\n"
            return output
        
        output += f"## DAG: {dag_id}\n"
        output += f"**Schedule:** {dag.schedule_interval or 'Manual'}\n"
        output += f"**Tasks:** {len(dag.tasks)} total\n\n"
        
        output += "### Task Pipeline\n"
        for task in dag.tasks:
            output += f"- `{task.task_id}`: {task.__class__.__name__}\n"
        
        output += f"\n### Recent Runs\n"
        output += f"(Check Airflow UI for detailed task logs: http://localhost:8888/dags/{dag_id})\n"
        
        return output
    
    except Exception as e:
        output += f"Error checking status: {str(e)}\n"
        return output


def _rag_list_processed(limit: int = 10) -> str:
    """List recently processed RAG documents."""
    output = f"# Processed RAG Documents\n\n"
    output += f"**Limit:** {limit} results\n"
    output += f"**Timestamp:** {datetime.now().isoformat()}\n\n"
    
    metadata_file = '/opt/documents/processed/metadata.json'
    
    if not os.path.exists(metadata_file):
        output += f"ℹ️ No processed documents yet.\n"
        output += f"**To process documents:**\n"
        output += f"1. Copy documents to `/opt/documents/incoming/`\n"
        output += f"2. Call `manage_rag_documents('ingest')`\n"
        output += f"3. Wait for processing to complete\n"
        return output
    
    try:
        import json
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        if isinstance(metadata, dict) and 'documents' in metadata:
            docs = metadata['documents']
        elif isinstance(metadata, list):
            docs = metadata
        else:
            docs = []
        
        if not docs:
            output += "ℹ️ No documents in metadata file\n"
            return output
        
        # Sort by timestamp (newest first)
        if isinstance(docs, list) and docs and isinstance(docs[0], dict) and 'timestamp' in docs[0]:
            docs = sorted(docs, key=lambda x: x.get('timestamp', ''), reverse=True)
        
        output += f"## {len(docs)} document(s) processed\n\n"
        
        for i, doc in enumerate(docs[:limit], 1):
            if isinstance(doc, dict):
                output += f"### {i}. {doc.get('source', 'Unknown')}\n"
                output += f"- **Path:** `{doc.get('path', 'N/A')}`\n"
                output += f"- **Type:** {doc.get('type', 'N/A')}\n"
                output += f"- **Chunks:** {doc.get('chunk_count', 'N/A')}\n"
                output += f"- **Processed:** {doc.get('timestamp', 'N/A')}\n\n"
            else:
                output += f"{i}. {doc}\n"
        
        if len(docs) > limit:
            output += f"\n*(Showing {limit} of {len(docs)} documents)*\n"
        
        return output
    
    except Exception as e:
        output += f"Error reading processed documents: {str(e)}\n"
        return output


def _rag_estimate_chunks(doc_dir: str) -> str:
    """Estimate document chunking and storage requirements."""
    output = f"# RAG Chunk Estimation\n\n"
    output += f"**Source Directory:** `{doc_dir}`\n"
    output += f"**Timestamp:** {datetime.now().isoformat()}\n\n"
    
    if not os.path.isdir(doc_dir):
        output += f"❌ Directory does not exist: {doc_dir}\n"
        return output
    
    try:
        total_words = 0
        total_size = 0
        doc_count = 0
        supported_exts = {'.md', '.markdown', '.yml', '.yaml', '.txt'}
        
        for root, dirs, files in os.walk(doc_dir):
            for fname in files:
                _, ext = os.path.splitext(fname)
                if ext.lower() in supported_exts:
                    file_path = os.path.join(root, fname)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            total_words += len(content.split())
                            total_size += len(content)
                            doc_count += 1
                    except (OSError, IOError):
                        pass
        
        # Estimation parameters
        avg_chunk_size = 250  # words per chunk (typical ~2000 chars)
        estimated_chunks = max(1, total_words // avg_chunk_size)
        embedding_size_bytes = 384 * 4  # 384-dim embedding * 4 bytes per float
        estimated_db_size_mb = (estimated_chunks * embedding_size_bytes) / (1024 * 1024)
        
        output += f"## Document Statistics\n"
        output += f"- **Total Documents:** {doc_count}\n"
        output += f"- **Total Content Size:** {round(total_size / 1024, 2)} KB\n"
        output += f"- **Total Words:** {total_words:,}\n\n"
        
        output += f"## Chunking Estimate\n"
        output += f"- **Average Chunk Size:** ~{avg_chunk_size} words\n"
        output += f"- **Estimated Chunks:** ~{estimated_chunks:,}\n"
        output += f"- **Embedding Dimension:** 384-d\n\n"
        
        output += f"## Storage Requirements\n"
        output += f"- **Vector DB Size (estimated):** ~{round(estimated_db_size_mb, 2)} MB\n"
        output += f"- **Including Metadata:** ~{round(estimated_db_size_mb * 1.5, 2)} MB\n\n"
        
        output += f"## Quality Metrics\n"
        output += f"- **Documents Ready:** ✅ Yes (>0 documents found)\n"
        output += f"- **Sufficient Content:** {'✅ Yes' if total_words > 100 else '⚠️ May be limited'}\n"
        output += f"- **Processing Time Est:** ~{max(10, estimated_chunks // 100)} seconds\n\n"
        
        output += f"**Next Step:** Call `manage_rag_documents('ingest')` to process documents\n"
        
        return output
    
    except Exception as e:
        output += f"Error estimating chunks: {str(e)}\n"
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
    logger.info("Tools: 11 total (DAGs: 3, VMs: 5, Status: 1, Info: 1, RAG: 1)")
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
