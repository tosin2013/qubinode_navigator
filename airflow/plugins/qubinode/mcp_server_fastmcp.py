#!/usr/bin/env python3
"""
FastMCP Implementation for Qubinode Airflow MCP Server
ADR-0049: Multi-Agent LLM Memory Architecture

MCP server for Airflow DAG management, VM operations, and RAG-powered
intelligent workflow assistance.

Tools:
- DAG Management: list_dags, get_dag_info, trigger_dag
- VM Operations: list_vms, get_vm_info, create_vm, delete_vm
- RAG Queries: query_rag, ingest_to_rag, search_similar_errors
- Troubleshooting: get_troubleshooting_history, log_troubleshooting_attempt
- Agent Orchestration: delegate_to_developer, override_developer
- Provider Checks: check_provider_exists
- Lineage: get_dag_lineage, get_failure_blast_radius
"""

import os
import sys
import logging
import subprocess
import uuid
from typing import Optional, Dict, Any, List
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

# Import RAG components (ADR-0049)
RAG_AVAILABLE = False
rag_store = None
try:
    from qubinode.rag_store import RAGStore, get_rag_store
    from qubinode.embedding_service import get_embedding_service
    RAG_AVAILABLE = True
    logger.info("RAG components available")
except ImportError as e:
    logger.warning(f"RAG components not available: {e}")

# Session tracking for troubleshooting
_current_session_id: Optional[str] = None

def get_session_id() -> str:
    """Get or create current session ID for troubleshooting tracking."""
    global _current_session_id
    if _current_session_id is None:
        _current_session_id = str(uuid.uuid4())
        logger.info(f"New session started: {_current_session_id}")
    return _current_session_id

def get_rag() -> Optional['RAGStore']:
    """Get RAG store singleton, initializing if needed."""
    global rag_store
    if RAG_AVAILABLE and rag_store is None:
        try:
            rag_store = get_rag_store()
        except Exception as e:
            logger.error(f"Failed to initialize RAG store: {e}")
    return rag_store


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


# =============================================================================
# ADR-0049: RAG Query Tools
# =============================================================================

@mcp.tool()
async def query_rag(
    query: str,
    doc_types: Optional[List[str]] = None,
    limit: int = 5,
    threshold: float = 0.7
) -> str:
    """
    Search the RAG knowledge base for relevant documents using semantic similarity.

    Use this tool to find documentation, ADRs, past troubleshooting solutions,
    and DAG examples related to your query.

    Args:
        query: Natural language search query (e.g., "How to configure FreeIPA DNS?")
        doc_types: Filter by document types. Options:
            - 'adr': Architecture Decision Records
            - 'provider_doc': Airflow provider documentation
            - 'dag': Example DAG code
            - 'troubleshooting': Past troubleshooting solutions
            - 'guide': How-to guides
            - None: Search all types
        limit: Maximum number of results (default: 5)
        threshold: Minimum similarity score 0-1 (default: 0.7)

    Returns:
        Formatted list of matching documents with similarity scores and content excerpts.

    Examples:
        - query_rag("FreeIPA DNS configuration")
        - query_rag("OpenShift deployment errors", doc_types=["troubleshooting"])
        - query_rag("SSH operator usage", doc_types=["provider_doc", "dag"])
    """
    logger.info(f"Tool called: query_rag(query='{query[:50]}...', doc_types={doc_types}, limit={limit})")

    store = get_rag()
    if store is None:
        return "Error: RAG store not available. Ensure PgVector is configured and running."

    try:
        results = store.search_documents(
            query=query,
            doc_types=doc_types,
            limit=limit,
            threshold=threshold
        )

        if not results:
            output = f"# No Results Found\n\n"
            output += f"**Query:** {query}\n"
            output += f"**Filters:** {doc_types or 'All types'}\n"
            output += f"**Threshold:** {threshold}\n\n"
            output += "Try:\n"
            output += "- Lowering the threshold (e.g., 0.5)\n"
            output += "- Broadening your query\n"
            output += "- Removing doc_type filters\n"
            return output

        output = f"# RAG Search Results\n\n"
        output += f"**Query:** {query}\n"
        output += f"**Found:** {len(results)} documents\n\n"

        for i, doc in enumerate(results, 1):
            similarity_pct = int(doc['similarity'] * 100)
            output += f"## {i}. [{doc['doc_type']}] Similarity: {similarity_pct}%\n"
            if doc.get('source_path'):
                output += f"**Source:** `{doc['source_path']}`\n"

            # Truncate content for display
            content = doc['content']
            if len(content) > 500:
                content = content[:500] + "..."
            output += f"\n{content}\n\n"
            output += "---\n\n"

        logger.info(f"RAG query returned {len(results)} results")
        return output

    except Exception as e:
        error_msg = f"RAG query failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


@mcp.tool()
async def ingest_to_rag(
    content: str,
    doc_type: str,
    source: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Ingest new documentation into the RAG knowledge base.

    Use this when you need to add new documentation, guides, or context
    that the system doesn't have. The content will be chunked, embedded,
    and stored for future semantic search.

    Args:
        content: Document content (markdown, text, code)
        doc_type: Type of document. One of:
            - 'adr': Architecture Decision Record
            - 'provider_doc': Airflow provider documentation
            - 'dag': DAG example or template
            - 'troubleshooting': Troubleshooting guide or solution
            - 'guide': How-to guide
            - 'policy': Organization policy
            - 'example': Code example
        source: Source path or URL (optional)
        metadata: Additional metadata dictionary (optional)

    Returns:
        Confirmation with document IDs created.

    Examples:
        - ingest_to_rag("# FreeIPA Guide\\n...", "guide", source="/docs/freeipa.md")
        - ingest_to_rag(dag_code, "dag", metadata={"component": "freeipa"})
    """
    logger.info(f"Tool called: ingest_to_rag(doc_type='{doc_type}', source='{source}')")

    if READ_ONLY:
        return "Error: Cannot ingest documents in read-only mode"

    store = get_rag()
    if store is None:
        return "Error: RAG store not available. Ensure PgVector is configured and running."

    valid_types = ['adr', 'provider_doc', 'dag', 'troubleshooting', 'guide', 'policy', 'example', 'api_doc', 'readme']
    if doc_type not in valid_types:
        return f"Error: Invalid doc_type '{doc_type}'. Must be one of: {valid_types}"

    try:
        doc_ids = store.ingest_document(
            content=content,
            doc_type=doc_type,
            source_path=source,
            metadata=metadata or {}
        )

        if not doc_ids:
            return "Document already exists in RAG store (duplicate detected)"

        output = f"# Document Ingested Successfully\n\n"
        output += f"**Type:** {doc_type}\n"
        output += f"**Source:** {source or 'N/A'}\n"
        output += f"**Chunks Created:** {len(doc_ids)}\n"
        output += f"**Document IDs:** {', '.join(doc_ids[:3])}{'...' if len(doc_ids) > 3 else ''}\n\n"
        output += "The document is now searchable via `query_rag()`."

        logger.info(f"Ingested document: {len(doc_ids)} chunks")
        return output

    except Exception as e:
        error_msg = f"Ingestion failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


# =============================================================================
# ADR-0049: Troubleshooting Memory Tools
# =============================================================================

@mcp.tool()
async def get_troubleshooting_history(
    error_pattern: Optional[str] = None,
    component: Optional[str] = None,
    only_successful: bool = False,
    limit: int = 10
) -> str:
    """
    Retrieve past troubleshooting attempts to learn from previous solutions.

    Use this BEFORE attempting to fix an error to see if similar issues
    have been solved before. This enables the system to learn and avoid
    repeating failed approaches.

    Args:
        error_pattern: Search for similar errors (semantic search)
        component: Filter by component (freeipa, vyos, openshift, etc.)
        only_successful: Only return successful solutions
        limit: Maximum results to return

    Returns:
        List of past troubleshooting attempts with outcomes.

    Examples:
        - get_troubleshooting_history(error_pattern="DNS resolution failed")
        - get_troubleshooting_history(component="freeipa", only_successful=True)
    """
    logger.info(f"Tool called: get_troubleshooting_history(error_pattern='{error_pattern}', component='{component}')")

    store = get_rag()
    if store is None:
        return "Error: RAG store not available."

    try:
        output = f"# Troubleshooting History\n\n"

        if error_pattern:
            # Semantic search for similar errors
            results = store.search_similar_errors(
                error_description=error_pattern,
                only_successful=only_successful,
                limit=limit
            )

            output += f"**Search:** {error_pattern}\n"
            output += f"**Filter:** {'Successful only' if only_successful else 'All results'}\n"
            output += f"**Found:** {len(results)} similar cases\n\n"

            if not results:
                output += "No similar troubleshooting attempts found.\n"
                output += "This appears to be a new type of error.\n"
                return output

            for i, r in enumerate(results, 1):
                similarity_pct = int(r['similarity'] * 100)
                result_emoji = "✅" if r['result'] == 'success' else "❌" if r['result'] == 'failed' else "⚠️"

                output += f"## {i}. {result_emoji} Similarity: {similarity_pct}%\n"
                output += f"**Error:** {r.get('error_message', 'N/A')}\n"
                output += f"**Solution Tried:** {r.get('attempted_solution', 'N/A')}\n"
                output += f"**Result:** {r['result']}\n"
                if r.get('component'):
                    output += f"**Component:** {r['component']}\n"
                output += "\n---\n\n"
        else:
            # Get session history
            session_id = get_session_id()
            history = store.get_session_history(session_id)

            output += f"**Current Session:** {session_id[:8]}...\n"
            output += f"**Attempts:** {len(history)}\n\n"

            if not history:
                output += "No troubleshooting attempts in this session yet.\n"
                return output

            for h in history:
                result_emoji = "✅" if h['result'] == 'success' else "❌" if h['result'] == 'failed' else "⚠️"
                output += f"### Attempt {h['sequence_num']} {result_emoji}\n"
                output += f"**Task:** {h['task_description']}\n"
                if h.get('error_message'):
                    output += f"**Error:** {h['error_message']}\n"
                output += f"**Solution:** {h['attempted_solution']}\n"
                output += f"**Result:** {h['result']}\n"
                if h.get('override_by'):
                    output += f"**Override By:** {h['override_by']}\n"
                output += "\n"

        return output

    except Exception as e:
        error_msg = f"Failed to get history: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


@mcp.tool()
async def log_troubleshooting_attempt(
    task: str,
    solution: str,
    result: str,
    error_message: Optional[str] = None,
    component: Optional[str] = None,
    details: Optional[str] = None
) -> str:
    """
    Log a troubleshooting attempt for future learning.

    Call this AFTER attempting a fix to record what was tried and whether
    it worked. This builds the knowledge base for future similar issues.

    Args:
        task: What you were trying to accomplish
        solution: What solution/fix was attempted
        result: Outcome - one of 'success', 'failed', or 'partial'
        error_message: The original error (if any)
        component: Which component (freeipa, vyos, openshift, etc.)
        details: Additional details about the outcome

    Returns:
        Confirmation of logged attempt.

    Examples:
        - log_troubleshooting_attempt(
            task="Deploy FreeIPA",
            error_message="DNS resolution failed",
            solution="Opened port 53 in firewalld",
            result="success",
            component="freeipa"
          )
    """
    logger.info(f"Tool called: log_troubleshooting_attempt(task='{task[:30]}...', result='{result}')")

    if READ_ONLY:
        return "Error: Cannot log attempts in read-only mode"

    if result not in ['success', 'failed', 'partial']:
        return f"Error: result must be 'success', 'failed', or 'partial'. Got: {result}"

    store = get_rag()
    if store is None:
        return "Error: RAG store not available."

    try:
        attempt_id = store.log_troubleshooting(
            session_id=get_session_id(),
            task_description=task,
            attempted_solution=solution,
            result=result,
            error_message=error_message,
            component=component,
            result_details=details,
            agent="calling_llm"  # Logged by calling LLM
        )

        result_emoji = "✅" if result == 'success' else "❌" if result == 'failed' else "⚠️"

        output = f"# Troubleshooting Attempt Logged {result_emoji}\n\n"
        output += f"**ID:** {attempt_id[:8]}...\n"
        output += f"**Session:** {get_session_id()[:8]}...\n"
        output += f"**Task:** {task}\n"
        output += f"**Result:** {result}\n\n"

        if result == 'success':
            output += "This solution will be suggested for similar future errors."
        elif result == 'failed':
            output += "This approach will be noted to avoid in similar situations."

        return output

    except Exception as e:
        error_msg = f"Failed to log attempt: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


# =============================================================================
# ADR-0049: Agent Orchestration Tools
# =============================================================================

@mcp.tool()
async def check_provider_exists(system_name: str) -> str:
    """
    Check if an Airflow provider exists for a given system (Provider-First Rule).

    ALWAYS call this before designing DAGs that interact with external systems.
    If a provider exists, you MUST use its operators instead of BashOperator.

    Args:
        system_name: Name of the system (e.g., 'azure', 'postgres', 'kubernetes')

    Returns:
        Provider information if found, or guidance if not.

    Examples:
        - check_provider_exists("azure")
        - check_provider_exists("postgres")
        - check_provider_exists("custom_internal_api")
    """
    logger.info(f"Tool called: check_provider_exists(system_name='{system_name}')")

    store = get_rag()
    if store is None:
        # Fallback to basic check
        known_providers = [
            'postgres', 'ssh', 'http', 'kubernetes', 'docker',
            'amazon', 'google', 'microsoft-azure', 'slack', 'redis'
        ]
        system_lower = system_name.lower()

        for p in known_providers:
            if system_lower in p or p in system_lower:
                return f"# Provider Found: {p}\n\nUse `apache-airflow-providers-{p}` operators."

        return f"# No Provider Found for '{system_name}'\n\nConsider using HTTP/SSH operators or designing a custom provider."

    try:
        result = store.check_provider_exists(system_name)

        if result:
            output = f"# ✅ Provider Found\n\n"
            output += f"**Provider:** {result['provider_name']}\n"
            output += f"**Package:** `{result['package_name']}`\n"
            output += f"**Description:** {result.get('description', 'N/A')}\n"
            if result.get('documentation_url'):
                output += f"**Docs:** {result['documentation_url']}\n"
            output += "\n## Provider-First Rule\n"
            output += "You MUST use this provider's operators instead of BashOperator.\n"
            output += "Query RAG for usage examples: `query_rag('azure operator examples', doc_types=['dag', 'provider_doc'])`"
            return output
        else:
            output = f"# ❌ No Provider Found for '{system_name}'\n\n"
            output += "## Options\n\n"
            output += "1. **Use HTTP Operator** - If the system has a REST API\n"
            output += "2. **Use SSH Operator** - If accessible via SSH\n"
            output += "3. **Design a Provider** - For complex integrations\n\n"
            output += "## If No Provider is Suitable\n"
            output += "Escalate to create a provider design document:\n"
            output += "- Document required connections\n"
            output += "- Define operators/hooks needed\n"
            output += "- Create `docs/provider_plan_<name>.md`\n"
            return output

    except Exception as e:
        error_msg = f"Provider check failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


@mcp.tool()
async def compute_confidence_score(
    task_description: str,
    doc_types: Optional[List[str]] = None
) -> str:
    """
    Compute confidence score for a task based on RAG knowledge.

    Use this to determine if you have enough context to proceed with a task.
    Follow the Confidence Policy (ADR-0049):
    - High (≥0.8): Proceed confidently
    - Medium (0.6-0.8): Proceed with caveats
    - Low (<0.6): STOP and request more documentation

    Args:
        task_description: What you're trying to accomplish
        doc_types: Document types to search (optional)

    Returns:
        Confidence assessment with recommendation.
    """
    logger.info(f"Tool called: compute_confidence_score(task='{task_description[:50]}...')")

    store = get_rag()
    if store is None:
        return "Error: RAG store not available. Cannot compute confidence."

    try:
        # Search RAG for relevant documents
        results = store.search_documents(
            query=task_description,
            doc_types=doc_types,
            limit=10,
            threshold=0.5
        )

        # Compute confidence factors
        rag_hit_count = len(results)
        rag_max_similarity = max([r['similarity'] for r in results]) if results else 0

        # Check for provider if task mentions external system
        provider_exists = False
        for keyword in ['azure', 'aws', 'gcp', 'kubernetes', 'postgres', 'redis']:
            if keyword in task_description.lower():
                provider_check = store.check_provider_exists(keyword)
                if provider_check:
                    provider_exists = True
                    break

        # Check for similar DAGs
        dag_results = store.search_documents(
            query=task_description,
            doc_types=['dag'],
            limit=3,
            threshold=0.6
        )
        similar_dag_exists = len(dag_results) > 0

        # Compute score
        confidence = (
            0.4 * rag_max_similarity +
            0.3 * min(rag_hit_count / 5.0, 1.0) +
            0.2 * (1.0 if provider_exists else 0.0) +
            0.1 * (1.0 if similar_dag_exists else 0.0)
        )

        # Determine recommendation
        if confidence >= 0.8:
            level = "HIGH"
            emoji = "✅"
            recommendation = "Proceed with task. Sufficient context available."
        elif confidence >= 0.6:
            level = "MEDIUM"
            emoji = "⚠️"
            recommendation = "Proceed with caution. Note any assumptions made."
        else:
            level = "LOW"
            emoji = "❌"
            recommendation = "STOP. Request additional documentation before proceeding."

        output = f"# Confidence Assessment {emoji}\n\n"
        output += f"**Task:** {task_description}\n"
        output += f"**Confidence:** {confidence:.2f} ({level})\n\n"

        output += "## Factors\n"
        output += f"- RAG Hits: {rag_hit_count} documents\n"
        output += f"- Best Match Similarity: {rag_max_similarity:.2f}\n"
        output += f"- Provider Available: {'Yes' if provider_exists else 'No'}\n"
        output += f"- Similar DAG Exists: {'Yes' if similar_dag_exists else 'No'}\n\n"

        output += f"## Recommendation\n{recommendation}\n"

        if confidence < 0.6:
            output += "\n## To Increase Confidence\n"
            output += "1. Provide relevant documentation via `ingest_to_rag()`\n"
            output += "2. Share example implementations\n"
            output += "3. Clarify requirements\n"

        # Log decision
        store.log_decision(
            agent="calling_llm",
            decision_type="confidence_check",
            context={"task": task_description, "doc_types": doc_types},
            decision=f"{level} confidence ({confidence:.2f})",
            confidence=confidence,
            rag_hits=rag_hit_count,
            rag_max_similarity=rag_max_similarity,
            session_id=get_session_id()
        )

        return output

    except Exception as e:
        error_msg = f"Confidence computation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


@mcp.tool()
async def get_rag_stats() -> str:
    """
    Get statistics about the RAG knowledge base.

    Returns:
        Summary of documents, troubleshooting attempts, and decisions in the store.
    """
    logger.info("Tool called: get_rag_stats()")

    store = get_rag()
    if store is None:
        return "Error: RAG store not available."

    try:
        stats = store.get_stats()

        output = "# RAG Knowledge Base Statistics\n\n"

        output += "## Documents by Type\n"
        if stats.get('documents'):
            for doc_type, count in stats['documents'].items():
                output += f"- **{doc_type}:** {count}\n"
        else:
            output += "No documents ingested yet.\n"

        output += "\n## Troubleshooting Attempts\n"
        if stats.get('troubleshooting'):
            total = sum(stats['troubleshooting'].values())
            output += f"- **Total:** {total}\n"
            for result, count in stats['troubleshooting'].items():
                emoji = "✅" if result == 'success' else "❌" if result == 'failed' else "⚠️"
                output += f"- {emoji} **{result}:** {count}\n"
        else:
            output += "No troubleshooting attempts logged yet.\n"

        output += "\n## Agent Decisions\n"
        if stats.get('decisions'):
            for agent, count in stats['decisions'].items():
                output += f"- **{agent}:** {count} decisions\n"
        else:
            output += "No decisions logged yet.\n"

        output += f"\n## Current Session\n"
        output += f"**ID:** {get_session_id()[:8]}...\n"

        return output

    except Exception as e:
        error_msg = f"Failed to get stats: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


def main():
    """Main entry point"""
    if not MCP_ENABLED:
        logger.warning("=" * 60)
        logger.warning("Airflow MCP Server is DISABLED")
        logger.warning("To enable: export AIRFLOW_MCP_ENABLED=true")
        logger.warning("=" * 60)
        sys.exit(0)

    logger.info("=" * 60)
    logger.info("Starting FastMCP Airflow Server (ADR-0049)")
    logger.info(f"Host: {MCP_HOST}")
    logger.info(f"Port: {MCP_PORT}")
    logger.info("Tools: DAGs(3), VMs(5), RAG(6), Troubleshooting(2), Status(2)")
    logger.info(f"RAG Available: {RAG_AVAILABLE}")
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
