"""
RAG Bootstrap DAG for Qubinode Navigator
ADR-0049: Multi-Agent LLM Memory Architecture - Phase 5

This DAG initializes and populates the RAG knowledge base with:
- ADRs (Architecture Decision Records)
- Existing DAG examples
- Provider documentation
- Troubleshooting guides

Run this DAG after initial deployment to bootstrap the knowledge base,
or periodically to keep documentation up to date.

Usage:
    # Trigger manually
    airflow dags trigger rag_bootstrap

    # Or via MCP
    trigger_dag("rag_bootstrap")
"""

from datetime import datetime, timedelta
from pathlib import Path
import logging
import os

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

# Configuration
QUBINODE_ROOT = os.getenv("QUBINODE_ROOT", "/opt/qubinode_navigator")
AIRFLOW_HOME = os.getenv("AIRFLOW_HOME", "/opt/airflow")
DAGS_PATH = os.path.join(AIRFLOW_HOME, "dags")
PLUGINS_PATH = os.path.join(AIRFLOW_HOME, "plugins")

logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    "owner": "qubinode-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def get_rag_store():
    """Get RAG store instance."""
    try:
        from qubinode.rag_store import get_rag_store as _get_rag_store

        return _get_rag_store()
    except ImportError as e:
        logger.error(f"RAG store not available: {e}")
        raise


def ingest_adrs(**context):
    """
    Ingest all ADR markdown files into RAG.

    ADRs provide architectural context and decision rationale
    that helps the LLM understand project patterns.
    """
    logger.info("Starting ADR ingestion...")

    store = get_rag_store()
    adr_path = Path(QUBINODE_ROOT) / "docs" / "adrs"

    if not adr_path.exists():
        logger.warning(f"ADR path not found: {adr_path}")
        return {"status": "skipped", "reason": "ADR path not found"}

    ingested = 0
    errors = 0

    for adr_file in adr_path.glob("*.md"):
        try:
            logger.info(f"Ingesting ADR: {adr_file.name}")

            content = adr_file.read_text(encoding="utf-8")

            # Extract title from first heading
            title = adr_file.stem
            for line in content.split("\n"):
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            # Ingest with metadata
            store.ingest_document(
                content=content,
                doc_type="adr",
                source_path=str(adr_file),
                metadata={
                    "title": title,
                    "filename": adr_file.name,
                    "category": "architecture",
                },
            )
            ingested += 1

        except Exception as e:
            logger.error(f"Failed to ingest {adr_file.name}: {e}")
            errors += 1

    result = {
        "status": "completed",
        "ingested": ingested,
        "errors": errors,
        "path": str(adr_path),
    }

    logger.info(f"ADR ingestion complete: {result}")
    context["ti"].xcom_push(key="adr_result", value=result)
    return result


def ingest_dag_examples(**context):
    """
    Ingest existing DAG files as examples.

    DAG examples help the LLM understand project patterns
    and generate consistent new DAGs.
    """
    logger.info("Starting DAG examples ingestion...")

    store = get_rag_store()
    dags_path = Path(DAGS_PATH)

    if not dags_path.exists():
        logger.warning(f"DAGs path not found: {dags_path}")
        return {"status": "skipped", "reason": "DAGs path not found"}

    ingested = 0
    errors = 0
    skipped = 0

    # Files to skip
    skip_patterns = ["__init__", "__pycache__", "rag_bootstrap", ".lineage"]

    for dag_file in dags_path.glob("*.py"):
        # Skip certain files
        if any(pattern in dag_file.name for pattern in skip_patterns):
            skipped += 1
            continue

        try:
            logger.info(f"Ingesting DAG example: {dag_file.name}")

            content = dag_file.read_text(encoding="utf-8")

            # Extract docstring for description
            description = ""
            if '"""' in content:
                start = content.find('"""') + 3
                end = content.find('"""', start)
                if end > start:
                    description = content[start:end].strip()[:500]

            # Ingest with metadata
            store.ingest_document(
                content=content,
                doc_type="dag",
                source_path=str(dag_file),
                metadata={
                    "filename": dag_file.name,
                    "description": description,
                    "category": "example",
                },
            )
            ingested += 1

        except Exception as e:
            logger.error(f"Failed to ingest {dag_file.name}: {e}")
            errors += 1

    result = {
        "status": "completed",
        "ingested": ingested,
        "errors": errors,
        "skipped": skipped,
        "path": str(dags_path),
    }

    logger.info(f"DAG examples ingestion complete: {result}")
    context["ti"].xcom_push(key="dag_result", value=result)
    return result


def ingest_provider_docs(**context):
    """
    Ingest Airflow provider documentation.

    Provider docs help the LLM understand available operators
    and follow the Provider-First rule.
    """
    logger.info("Starting provider docs ingestion...")

    store = get_rag_store()

    # Provider documentation summaries (could be expanded with actual docs)
    provider_docs = [
        {
            "name": "SSH Provider",
            "package": "apache-airflow-providers-ssh",
            "content": """# SSH Provider for Apache Airflow

The SSH provider enables Airflow to execute commands on remote hosts via SSH.

## Key Components:
- **SSHOperator**: Execute commands on remote host
- **SSHHook**: Manage SSH connections
- **SFTPOperator**: Transfer files via SFTP

## Usage Example:
```python
from airflow.providers.ssh.operators.ssh import SSHOperator

ssh_task = SSHOperator(
    task_id='remote_command',
    ssh_conn_id='ssh_default',
    command='echo "Hello from remote host"',
    cmd_timeout=300,
)
```

## Connection Configuration:
- Host, Port, Username
- Password or Key file
- Extra options for SSH config

## Best Practices:
1. Use connection IDs from Airflow connections
2. Set appropriate timeouts
3. Handle errors with retries
4. Use do_xcom_push for command output
""",
            "doc_url": "https://airflow.apache.org/docs/apache-airflow-providers-ssh/stable/index.html",
        },
        {
            "name": "PostgreSQL Provider",
            "package": "apache-airflow-providers-postgres",
            "content": """# PostgreSQL Provider for Apache Airflow

The PostgreSQL provider enables database operations within Airflow.

## Key Components:
- **PostgresOperator**: Execute SQL statements
- **PostgresHook**: Direct database access
- **PostgresSensor**: Wait for query results

## Usage Example:
```python
from airflow.providers.postgres.operators.postgres import PostgresOperator

create_table = PostgresOperator(
    task_id='create_table',
    postgres_conn_id='postgres_default',
    sql=\"\"\"
        CREATE TABLE IF NOT EXISTS my_table (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100)
        );
    \"\"\"
)
```

## Best Practices:
1. Use parameterized queries to prevent SQL injection
2. Set appropriate connection pool settings
3. Use transactions for data integrity
4. Consider using PostgresHook for complex operations
""",
            "doc_url": "https://airflow.apache.org/docs/apache-airflow-providers-postgres/stable/index.html",
        },
        {
            "name": "HTTP Provider",
            "package": "apache-airflow-providers-http",
            "content": """# HTTP Provider for Apache Airflow

The HTTP provider enables REST API interactions within Airflow.

## Key Components:
- **SimpleHttpOperator**: Make HTTP requests
- **HttpHook**: Direct HTTP access
- **HttpSensor**: Wait for HTTP endpoint

## Usage Example:
```python
from airflow.providers.http.operators.http import SimpleHttpOperator

api_call = SimpleHttpOperator(
    task_id='call_api',
    http_conn_id='api_default',
    endpoint='/api/v1/resource',
    method='GET',
    headers={'Content-Type': 'application/json'},
    response_check=lambda response: response.status_code == 200,
)
```

## Best Practices:
1. Use connection IDs for base URLs
2. Implement response_check for validation
3. Set appropriate retries for transient failures
4. Use response_filter to extract data
""",
            "doc_url": "https://airflow.apache.org/docs/apache-airflow-providers-http/stable/index.html",
        },
        {
            "name": "OpenLineage Provider",
            "package": "apache-airflow-providers-openlineage",
            "content": """# OpenLineage Provider for Apache Airflow

The OpenLineage provider enables data lineage tracking.

## Features:
- Automatic lineage emission for DAG runs
- Dataset input/output tracking
- Job metadata facets
- Integration with Marquez

## Configuration:
```yaml
# In airflow.cfg or environment
AIRFLOW__OPENLINEAGE__TRANSPORT: '{"type": "http", "url": "http://localhost:5001"}'
AIRFLOW__OPENLINEAGE__NAMESPACE: 'my_namespace'
```

## Custom Facets:
You can add custom metadata to lineage events using facets:
- Job facets: Information about the job
- Run facets: Information about the specific run
- Dataset facets: Information about inputs/outputs

## Best Practices:
1. Set meaningful namespace for your project
2. Use custom facets for code lineage (git info)
3. Configure appropriate transport (HTTP to Marquez)
4. Review lineage in Marquez Web UI
""",
            "doc_url": "https://airflow.apache.org/docs/apache-airflow-providers-openlineage/stable/index.html",
        },
    ]

    ingested = 0
    errors = 0

    for provider in provider_docs:
        try:
            logger.info(f"Ingesting provider doc: {provider['name']}")

            store.ingest_document(
                content=provider["content"],
                doc_type="provider_doc",
                source_url=provider["doc_url"],
                metadata={
                    "provider_name": provider["name"],
                    "package": provider["package"],
                    "category": "provider",
                },
            )
            ingested += 1

        except Exception as e:
            logger.error(f"Failed to ingest {provider['name']}: {e}")
            errors += 1

    result = {
        "status": "completed",
        "ingested": ingested,
        "errors": errors,
        "total_providers": len(provider_docs),
    }

    logger.info(f"Provider docs ingestion complete: {result}")
    context["ti"].xcom_push(key="provider_result", value=result)
    return result


def ingest_guides(**context):
    """
    Ingest troubleshooting and user guides.

    Guides help the LLM provide better assistance
    for common issues and workflows.
    """
    logger.info("Starting guides ingestion...")

    store = get_rag_store()

    # Built-in guides
    guides = [
        {
            "title": "Qubinode DAG Development Guide",
            "content": """# Qubinode DAG Development Guide

## DAG Factory Pattern (ADR-0046)

All Qubinode DAGs should use the DAG Factory pattern for consistency.

### Creating a New DAG:

1. Add entry to registry.yaml:
```yaml
my_dag:
  description: "My new DAG"
  schedule: "@daily"
  ssh_conn_id: ssh_target
  tasks:
    - name: step1
      command: "echo 'Step 1'"
    - name: step2
      command: "echo 'Step 2'"
      depends_on: [step1]
```

2. Run scaffold script:
```bash
./scripts/scaffold-dag.sh my_dag
```

### Provider-First Rule (ADR-0049):
- Always check for official Airflow providers first
- Use SSHOperator for remote commands
- Use PostgresOperator for database operations
- Only create custom operators when no provider exists

### Task Dependencies:
- Use `>>` operator for sequential tasks
- Use `depends_on` in registry for declarative deps
- Group related tasks with TaskGroups

### Error Handling:
- Set appropriate retries (default: 2)
- Use on_failure_callback for notifications
- Log errors with context for troubleshooting
""",
            "doc_type": "guide",
            "category": "development",
        },
        {
            "title": "Qubinode Troubleshooting Guide",
            "content": """# Qubinode Troubleshooting Guide

## Common Issues and Solutions

### 1. DAG Not Appearing in Airflow UI

**Symptoms:** DAG file exists but not visible in UI

**Solutions:**
1. Check for Python syntax errors: `python -m py_compile my_dag.py`
2. Verify DAG is in correct directory: `/opt/airflow/dags/`
3. Check Airflow scheduler logs: `docker-compose logs airflow-scheduler`
4. Ensure DAG file imports work: `python -c "from my_dag import *"`

### 2. SSH Connection Failures

**Symptoms:** SSHOperator tasks fail with connection errors

**Solutions:**
1. Verify SSH connection in Airflow UI (Admin > Connections)
2. Check host network connectivity: `ping <target_host>`
3. Verify SSH key permissions: `chmod 600 ~/.ssh/id_rsa`
4. Test SSH manually: `ssh -v user@host`

### 3. RAG Queries Return No Results

**Symptoms:** query_rag() returns empty results

**Solutions:**
1. Run RAG bootstrap: `airflow dags trigger rag_bootstrap`
2. Check pgvector is enabled: `SELECT * FROM pg_extension WHERE extname = 'vector'`
3. Verify documents exist: `SELECT COUNT(*) FROM rag_documents`
4. Lower similarity threshold in query

### 4. VM Operations Failing

**Symptoms:** kcli commands fail in DAGs

**Solutions:**
1. Verify libvirt socket is mounted in container
2. Check kcli config: `kcli list vm`
3. Ensure proper permissions on /var/run/libvirt
4. Review VM network configuration

### 5. Lineage Not Tracking

**Symptoms:** No lineage data in Marquez

**Solutions:**
1. Enable lineage profile: `docker-compose --profile lineage up`
2. Set OPENLINEAGE_DISABLED=false
3. Verify Marquez is running: `curl http://localhost:5001/api/v1/namespaces`
4. Check Airflow logs for OpenLineage errors
""",
            "doc_type": "troubleshooting",
            "category": "support",
        },
    ]

    ingested = 0
    errors = 0

    for guide in guides:
        try:
            logger.info(f"Ingesting guide: {guide['title']}")

            store.ingest_document(
                content=guide["content"],
                doc_type=guide["doc_type"],
                metadata={"title": guide["title"], "category": guide["category"]},
            )
            ingested += 1

        except Exception as e:
            logger.error(f"Failed to ingest {guide['title']}: {e}")
            errors += 1

    result = {
        "status": "completed",
        "ingested": ingested,
        "errors": errors,
        "total_guides": len(guides),
    }

    logger.info(f"Guides ingestion complete: {result}")
    context["ti"].xcom_push(key="guides_result", value=result)
    return result


def verify_rag_health(**context):
    """
    Verify RAG system health after bootstrap.

    Checks:
    - Document counts by type
    - Embedding dimensions
    - Query functionality
    """
    logger.info("Verifying RAG health...")

    store = get_rag_store()

    # Get statistics
    stats = store.get_stats()

    # Test query
    test_query = "How do I create a new DAG?"
    test_results = store.search_documents(query=test_query, limit=3, threshold=0.3)

    # Collect results from previous tasks
    ti = context["ti"]
    adr_result = ti.xcom_pull(key="adr_result", task_ids="ingest_adrs") or {}
    dag_result = ti.xcom_pull(key="dag_result", task_ids="ingest_dag_examples") or {}
    provider_result = ti.xcom_pull(key="provider_result", task_ids="ingest_provider_docs") or {}
    guides_result = ti.xcom_pull(key="guides_result", task_ids="ingest_guides") or {}

    health_report = {
        "status": "healthy" if test_results else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "statistics": stats,
        "test_query": {
            "query": test_query,
            "results_count": len(test_results),
            "top_similarity": test_results[0].get("similarity", 0) if test_results else 0,
        },
        "ingestion_summary": {
            "adrs": adr_result.get("ingested", 0),
            "dags": dag_result.get("ingested", 0),
            "providers": provider_result.get("ingested", 0),
            "guides": guides_result.get("ingested", 0),
        },
        "total_documents": sum(
            [
                adr_result.get("ingested", 0),
                dag_result.get("ingested", 0),
                provider_result.get("ingested", 0),
                guides_result.get("ingested", 0),
            ]
        ),
    }

    logger.info(f"RAG Health Report: {health_report}")

    # Store health report
    context["ti"].xcom_push(key="health_report", value=health_report)

    return health_report


# DAG Definition
with DAG(
    dag_id="rag_bootstrap",
    default_args=default_args,
    description="Bootstrap RAG knowledge base with ADRs, DAG examples, and documentation",
    schedule_interval=None,  # Manual trigger only
    start_date=days_ago(1),
    catchup=False,
    tags=["rag", "bootstrap", "adr-0049"],
    doc_md=__doc__,
) as dag:
    # Task: Ingest ADRs
    ingest_adrs_task = PythonOperator(
        task_id="ingest_adrs",
        python_callable=ingest_adrs,
        doc_md="Ingest Architecture Decision Records from docs/adrs/",
    )

    # Task: Ingest DAG Examples
    ingest_dags_task = PythonOperator(
        task_id="ingest_dag_examples",
        python_callable=ingest_dag_examples,
        doc_md="Ingest existing DAG files as examples",
    )

    # Task: Ingest Provider Docs
    ingest_providers_task = PythonOperator(
        task_id="ingest_provider_docs",
        python_callable=ingest_provider_docs,
        doc_md="Ingest Airflow provider documentation",
    )

    # Task: Ingest Guides
    ingest_guides_task = PythonOperator(
        task_id="ingest_guides",
        python_callable=ingest_guides,
        doc_md="Ingest troubleshooting and development guides",
    )

    # Task: Verify RAG Health
    verify_health_task = PythonOperator(
        task_id="verify_rag_health",
        python_callable=verify_rag_health,
        doc_md="Verify RAG system health and generate report",
    )

    # Task: Generate Lineage Facets
    generate_facets_task = BashOperator(
        task_id="generate_lineage_facets",
        bash_command="/opt/airflow/scripts/generate-lineage-facets.sh || true",
        doc_md="Generate OpenLineage facets for all DAGs",
    )

    # Dependencies: Parallel ingestion, then verification
    [
        ingest_adrs_task,
        ingest_dags_task,
        ingest_providers_task,
        ingest_guides_task,
    ] >> verify_health_task
    verify_health_task >> generate_facets_task
