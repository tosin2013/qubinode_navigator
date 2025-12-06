#!/usr/bin/env python3
"""
FastMCP Implementation using CLI tools
Simpler, more reliable approach - MCP tools call scripts directly
instead of making HTTP requests to potentially unavailable services.

Features:
- CLI-based tools for reliable RAG operations
- MCP prompts for guided interactions
- MCP resources for documentation access
"""

import os
import sys
import json
import logging
import subprocess
from typing import Optional
from pathlib import Path

from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fastmcp-cli")

# Configuration
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8081"))
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
MCP_ENABLED = os.getenv("MCP_SERVER_ENABLED", "true").lower() == "true"

# Path to CLI scripts and project
SCRIPT_DIR = Path(__file__).parent / "scripts"
PROJECT_ROOT = Path(__file__).parent.parent
RAG_CLI = SCRIPT_DIR / "rag-cli.py"
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", "/app/data"))

# Create FastMCP server
mcp = FastMCP(name="qubinode-rag-assistant")

logger.info("=" * 60)
logger.info("Initializing FastMCP Server (CLI-based)")
logger.info(f"Script directory: {SCRIPT_DIR}")
logger.info(f"RAG CLI: {RAG_CLI}")
logger.info("=" * 60)


# =============================================================================
# MCP Resources - Static documentation and guides
# =============================================================================


@mcp.resource("rag://guide/getting-started")
def get_getting_started_guide() -> str:
    """Getting started guide for RAG operations."""
    return """# RAG Getting Started Guide

## Overview
The Qubinode RAG (Retrieval-Augmented Generation) system allows you to:
- Ingest documentation into a searchable knowledge base
- Query the knowledge base for relevant information
- Manage and monitor the RAG system

## Quick Start

### 1. Check System Health
First, verify the RAG system is operational:
```
Use the rag_health tool to check system status
```

### 2. View Current Statistics
See what's already in the knowledge base:
```
Use the rag_stats tool to view statistics
```

### 3. Ingest a Document
Add new documentation to the knowledge base:
```
Use rag_ingest with:
- file_path: Path to your markdown/yaml/text file
- category: deployment, troubleshooting, configuration, etc.
- tags: Comma-separated keywords
- auto_approve: true to skip review
```

### 4. Query the Knowledge Base
Search for relevant information:
```
Use rag_query with:
- query: Your question or keywords
- max_results: Number of results (default: 5)
```

## Document Categories
- **deployment**: VM provisioning, infrastructure setup
- **troubleshooting**: Error resolution, debugging guides
- **configuration**: Config files, settings, parameters
- **architecture**: System design, ADRs
- **general**: Other documentation

## Quality Scoring
Documents are scored based on:
- Content length (longer = better)
- Code examples (+0.1)
- Technical terms (+0.1)
- Step-by-step instructions (+0.1)

Score >= 0.8: Auto-approved
Score 0.6-0.8: Pending review
Score < 0.6: Rejected
"""


@mcp.resource("rag://guide/best-practices")
def get_best_practices_guide() -> str:
    """Best practices for RAG ingestion and querying."""
    return """# RAG Best Practices

## Document Ingestion Best Practices

### 1. Structure Your Documents Well
- Use clear markdown headers (# ## ###)
- Include code examples with ``` blocks
- Add step-by-step instructions where applicable
- Use technical terms appropriately

### 2. Choose Appropriate Categories
| Category | Use For |
|----------|---------|
| deployment | VM creation, provisioning, setup guides |
| troubleshooting | Error fixes, debugging steps |
| configuration | Config files, parameters, settings |
| architecture | Design docs, ADRs, system overview |
| general | Everything else |

### 3. Use Descriptive Tags
Good tags: `vm,kcli,centos,libvirt,deployment`
Bad tags: `doc,file,new,test`

### 4. Document Quality Tips
- Include real command examples
- Reference specific file paths
- Mention error messages for troubleshooting docs
- Keep sections focused on one topic

## Query Best Practices

### 1. Be Specific
Instead of: "how to deploy"
Try: "how to deploy a CentOS VM with kcli"

### 2. Include Context
Instead of: "error fix"
Try: "libvirt connection refused error troubleshooting"

### 3. Use Technical Terms
The RAG system is trained on technical documentation.
Using proper terms improves results.

### 4. Adjust Results Count
- Use max_results=3 for focused answers
- Use max_results=10 for broader research

## Common Workflows

### Adding New Documentation
1. rag_health - Verify system is ready
2. rag_ingest - Add the document
3. rag_query - Verify it's searchable

### Researching a Topic
1. rag_stats - Check if relevant docs exist
2. rag_query - Search with keywords
3. rag_query - Refine with more specific terms

### Troubleshooting Issues
1. rag_query with error message
2. rag_query with component name
3. Check results for step-by-step fixes
"""


@mcp.resource("rag://status")
def get_rag_status() -> str:
    """Get current RAG system status as a resource."""
    result = run_cli(["stats"])
    return json.dumps(result, indent=2)


# =============================================================================
# MCP Prompts - Guided interactions for common tasks
# =============================================================================


@mcp.prompt()
def ingest_documentation(file_path: str, description: str = "") -> str:
    """
    Prompt for ingesting new documentation into RAG.

    Args:
        file_path: Path to the document to ingest
        description: Brief description of the document content
    """
    return f"""I need to ingest a new document into the RAG knowledge base.

Document: {file_path}
Description: {description or "Not provided"}

Please help me:
1. First, check the RAG system health using rag_health
2. Determine the appropriate category based on the file content:
   - deployment: For setup/provisioning guides
   - troubleshooting: For error fixes and debugging
   - configuration: For config files and settings
   - architecture: For design documents and ADRs
   - general: For other documentation
3. Suggest relevant tags based on the content
4. Ingest the document using rag_ingest with auto_approve=true
5. Verify the ingestion was successful
6. Test that the document is searchable with a relevant query

Please proceed step by step."""


@mcp.prompt()
def search_knowledge_base(topic: str) -> str:
    """
    Prompt for searching the RAG knowledge base.

    Args:
        topic: Topic or question to search for
    """
    return f"""I need to find information about: {topic}

Please help me:
1. First, check RAG stats to see what documents are available
2. Search for relevant documents using rag_query
3. If results are sparse, try alternative keywords
4. Summarize the most relevant findings
5. Suggest follow-up queries if needed

Search topic: {topic}

Please search the knowledge base and provide relevant information."""


@mcp.prompt()
def troubleshoot_issue(error_message: str, component: str = "") -> str:
    """
    Prompt for troubleshooting an issue using RAG.

    Args:
        error_message: The error message or problem description
        component: The component/system involved (optional)
    """
    return f"""I'm encountering an issue and need help troubleshooting.

Error/Problem: {error_message}
Component: {component or "Not specified"}

Please help me:
1. Search the RAG knowledge base for this error message
2. Search for troubleshooting guides related to the component
3. Look for similar issues and their resolutions
4. Provide step-by-step troubleshooting recommendations
5. Suggest preventive measures if applicable

Please search the knowledge base and help resolve this issue."""


@mcp.prompt()
def rag_system_check() -> str:
    """Prompt for comprehensive RAG system health check."""
    return """Please perform a comprehensive RAG system health check:

1. Run rag_health to check system components
2. Run rag_stats to see knowledge base statistics
3. Run rag_list to see what documents are available
4. If the system is healthy, perform a test query
5. Report any issues found and suggest remediation

Please provide a complete status report."""


# =============================================================================
# CLI Helper Functions
# =============================================================================


def run_cli(args: list, timeout: int = 30) -> dict:
    """Run CLI command and return parsed JSON result."""
    try:
        result = subprocess.run(
            ["python3", str(RAG_CLI)] + args, capture_output=True, text=True, timeout=timeout, cwd=str(SCRIPT_DIR.parent), env={**os.environ, "RAG_DATA_DIR": os.getenv("RAG_DATA_DIR", "/app/data")}
        )

        # Try to parse JSON output
        output = result.stdout.strip()
        if output:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return {"status": "success", "output": output}

        if result.returncode != 0:
            return {"status": "error", "message": result.stderr or "Command failed"}

        return {"status": "success", "output": "No output"}

    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Command timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# =============================================================================
# MCP Tools - RAG Operations
# =============================================================================


@mcp.tool()
async def rag_ingest(file_path: str, category: str = "general", tags: Optional[str] = None, auto_approve: bool = False) -> str:
    """
    Ingest a document into the RAG knowledge base.

    This tool processes documentation files and adds them to the searchable
    knowledge base. Supports markdown, YAML, and text files.

    Args:
        file_path: Path to the document file to ingest
        category: Document category (deployment, troubleshooting, configuration, etc.)
        tags: Comma-separated tags for the document
        auto_approve: Skip manual review and auto-approve the document

    Returns:
        JSON with ingestion status, chunks processed, and quality score

    Example:
        rag_ingest("/docs/vm-guide.md", category="deployment", tags="vm,kcli")
    """
    logger.info(f"Tool called: rag_ingest(file_path='{file_path}')")

    args = ["ingest", file_path, f"--category={category}"]
    if tags:
        args.append(f"--tags={tags}")
    if auto_approve:
        args.append("--auto-approve")

    result = run_cli(args)

    # Format output
    if result.get("status") == "error":
        return f"Error: {result.get('message', 'Unknown error')}"

    output = "# RAG Ingestion Result\n\n"
    output += f"**Status:** {result.get('status', 'unknown')}\n"
    output += f"**File:** {result.get('file', file_path)}\n"
    output += f"**Chunks Processed:** {result.get('chunks_processed', 0)}\n"
    output += f"**Quality Score:** {result.get('quality_score', 0)}\n"
    output += f"**Category:** {result.get('category', category)}\n"

    if result.get("tags"):
        output += f"**Tags:** {', '.join(result['tags'])}\n"

    if result.get("chunks"):
        output += "\n## Chunks\n"
        for chunk in result["chunks"]:
            output += f"- {chunk['title']} ({chunk['words']} words)\n"

    return output


@mcp.tool()
async def rag_query(query: str, max_results: int = 5) -> str:
    """
    Search the RAG knowledge base for relevant documents.

    Use this tool to find documentation about Qubinode, Airflow, kcli,
    VM management, and infrastructure automation.

    Args:
        query: Search query (natural language question or keywords)
        max_results: Maximum number of results to return (1-20)

    Returns:
        Formatted search results with content, scores, and sources

    Example:
        rag_query("How to deploy a VM with kcli?")
        rag_query("troubleshoot libvirt", max_results=3)
    """
    logger.info(f"Tool called: rag_query(query='{query}')")

    if not query or not query.strip():
        return "Error: Query cannot be empty"

    if max_results < 1 or max_results > 20:
        return "Error: max_results must be between 1 and 20"

    result = run_cli(["query", query, f"--max-results={max_results}"], timeout=60)

    if result.get("status") == "error":
        return f"Error: {result.get('message', 'Unknown error')}"

    output = "# RAG Query Results\n\n"
    output += f"**Query:** {result.get('query', query)}\n"
    output += f"**Results Found:** {result.get('total_results', 0)}\n\n"

    results = result.get("results", [])
    if not results:
        output += "*No matching documents found.*\n"
        output += "\nTry:\n"
        output += "- Using different keywords\n"
        output += "- Checking if documents have been ingested with `rag_stats`\n"
        return output

    for i, r in enumerate(results, 1):
        output += f"## Result {i} (Score: {r.get('score', 0):.3f})\n"
        output += f"**Source:** {r.get('source', 'Unknown')}\n"
        output += f"**Title:** {r.get('title', 'Untitled')}\n\n"
        output += f"{r.get('content', '')}\n\n"
        output += "---\n\n"

    return output


@mcp.tool()
async def rag_stats() -> str:
    """
    Get RAG knowledge base statistics.

    Returns information about:
    - Total contributions/documents
    - Documents pending review
    - Categories breakdown
    - RAG service status

    Returns:
        Formatted statistics about the RAG system
    """
    logger.info("Tool called: rag_stats()")

    result = run_cli(["stats"])

    if result.get("status") == "error":
        return f"Error: {result.get('message', 'Unknown error')}"

    output = "# RAG Statistics\n\n"
    output += f"**Data Directory:** {result.get('data_directory', 'Unknown')}\n"
    output += f"**RAG Service Available:** {result.get('rag_service_available', False)}\n\n"

    output += "## Contributions\n"
    output += f"- Total: {result.get('total_contributions', 0)}\n"
    output += f"- Pending Reviews: {result.get('pending_reviews', 0)}\n\n"

    categories = result.get("categories", {})
    if categories:
        output += "## Categories\n"
        for cat, count in categories.items():
            output += f"- {cat}: {count}\n"
    else:
        output += "*No documents ingested yet.*\n"

    return output


@mcp.tool()
async def rag_list() -> str:
    """
    List all documents in the RAG knowledge base.

    Returns a list of all contributed documents with their metadata.

    Returns:
        List of documents with IDs, filenames, and categories
    """
    logger.info("Tool called: rag_list()")

    result = run_cli(["list"])

    if result.get("status") == "error":
        return f"Error: {result.get('message', 'Unknown error')}"

    output = "# RAG Documents\n\n"
    output += f"**Total Documents:** {result.get('total', 0)}\n\n"

    contributions = result.get("contributions", [])
    if not contributions:
        output += "*No documents in the knowledge base.*\n"
        output += "\nUse `rag_ingest` to add documents.\n"
        return output

    output += "| Document ID | Filename | Category | Submitted |\n"
    output += "|-------------|----------|----------|----------|\n"

    for c in contributions:
        doc_id = c.get("document_id", "Unknown")[:20]
        filename = c.get("filename", "Unknown")
        category = c.get("category", "Unknown")
        submitted = c.get("submitted_at", "Unknown")[:10]
        output += f"| {doc_id}... | {filename} | {category} | {submitted} |\n"

    return output


@mcp.tool()
async def rag_health() -> str:
    """
    Check RAG system health.

    Performs health checks on:
    - Data directory accessibility
    - RAG service availability
    - Embedding service configuration

    Returns:
        Health status and any issues detected
    """
    logger.info("Tool called: rag_health()")

    result = run_cli(["health"])

    status = result.get("status", "unknown")
    output = "# RAG Health Check\n\n"
    output += f"**Overall Status:** {status.upper()}\n\n"

    checks = result.get("checks", {})
    output += "## Checks\n\n"

    for check_name, check_data in checks.items():
        output += f"### {check_name.replace('_', ' ').title()}\n"
        if isinstance(check_data, dict):
            for key, value in check_data.items():
                output += f"- {key}: {value}\n"
        else:
            output += f"- {check_data}\n"
        output += "\n"

    if status != "healthy":
        output += "## Recommendations\n"
        if not checks.get("data_directory", {}).get("exists"):
            output += "- Create data directory: `mkdir -p /app/data`\n"
        if not checks.get("rag_service", {}).get("available"):
            output += "- Install RAG dependencies: `pip install qdrant-client fastembed`\n"

    return output


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Main entry point"""
    if not MCP_ENABLED:
        logger.warning("=" * 60)
        logger.warning("MCP Server is DISABLED")
        logger.warning("To enable: export MCP_SERVER_ENABLED=true")
        logger.warning("=" * 60)
        sys.exit(0)

    logger.info("=" * 60)
    logger.info("Starting FastMCP RAG Assistant Server")
    logger.info(f"Host: {MCP_SERVER_HOST}")
    logger.info(f"Port: {MCP_SERVER_PORT}")
    logger.info("Tools: rag_ingest, rag_query, rag_stats, rag_list, rag_health")
    logger.info("Prompts: ingest_documentation, search_knowledge_base, troubleshoot_issue, rag_system_check")
    logger.info("Resources: rag://guide/getting-started, rag://guide/best-practices, rag://status")
    logger.info("=" * 60)

    mcp.run(transport="sse", host=MCP_SERVER_HOST, port=MCP_SERVER_PORT)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
