"""
RAG Document Ingestion DAG

This DAG provides a simple, safe starting point for ingesting documents into the
Qubinode RAG pipeline. It is intentionally lightweight and focuses on:

1. Scanning an input directory for documents.
2. Recording basic metadata about discovered files.
3. Providing a place to extend chunking/embedding logic in future iterations.

It is referenced by the documentation in:
- docs/tutorials/rag-document-ingestion.md
- docs/how-to/rag-ingest-new-docs.md
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import List

from airflow.operators.python import PythonOperator

from airflow import DAG

# Directory to scan for documents. Can be overridden via environment variable.
DOC_ROOT = os.environ.get("RAG_DOC_DIR", "/opt/documents/incoming")


def _scan_documents(**context) -> int:
    """Scan DOC_ROOT recursively and record discovered files.

    This task only logs file paths and pushes them to XCom. It does **not**
    perform any heavy processing so it is safe in default environments.
    """

    ti = context["ti"]
    discovered: List[str] = []

    if not os.path.isdir(DOC_ROOT):
        print(f"[RAG] Document root does not exist: {DOC_ROOT}")
        ti.xcom_push(key="documents", value=[])
        return 0

    print(f"[RAG] Scanning documents under: {DOC_ROOT}")

    for root, _dirs, files in os.walk(DOC_ROOT):
        for fname in files:
            path = os.path.join(root, fname)
            discovered.append(path)
            print(f"[RAG] Found document: {path}")

    ti.xcom_push(key="documents", value=discovered)
    print(f"[RAG] Total documents discovered: {len(discovered)}")
    return len(discovered)


def _chunk_documents(**context) -> int:
    """Placeholder chunking step.

    For now, this simply wraps each file as a single logical "chunk" with
    basic metadata and pushes it to XCom. Real chunking/embedding logic can be
    added later without breaking existing deployments.
    """

    ti = context["ti"]
    docs: List[str] = ti.xcom_pull(key="documents", default=[]) or []

    chunks = [
        {
            "path": path,
            "source": os.path.basename(path),
            "doc_root": DOC_ROOT,
        }
        for path in docs
    ]

    ti.xcom_push(key="chunks", value=chunks)
    print(f"[RAG] Prepared {len(chunks)} chunks (1 per file).")
    return len(chunks)


def _store_metadata(**context) -> int:
    """Placeholder storage step.

    In a future version this can write into a vector database or call the AI
    Assistant's ingestion API. For now, it logs basic information so the DAG is
    safe and immediately runnable.
    """

    ti = context["ti"]
    chunks = ti.xcom_pull(key="chunks", default=[]) or []

    print("[RAG] Storing metadata for chunks (placeholder, no external calls).")
    for idx, chunk in enumerate(chunks, start=1):
        print(f"[RAG] Chunk {idx}: {chunk['path']}")

    print(f"[RAG] Total chunks processed: {len(chunks)}")
    return len(chunks)


default_args = {
    "owner": "qubinode",
    "depends_on_past": False,
    "start_date": datetime(2025, 11, 21),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


dag = DAG(
    dag_id="rag_document_ingestion",
    default_args=default_args,
    description="Scan and record documents for RAG ingestion (placeholder pipeline)",
    schedule_interval=None,  # Manual trigger
    catchup=False,
    tags=["rag", "documentation", "qubinode"],
)


scan_documents = PythonOperator(
    task_id="scan_documents",
    python_callable=_scan_documents,
    provide_context=True,
    dag=dag,
)

chunk_documents = PythonOperator(
    task_id="chunk_documents",
    python_callable=_chunk_documents,
    provide_context=True,
    dag=dag,
)

store_metadata = PythonOperator(
    task_id="store_metadata",
    python_callable=_store_metadata,
    provide_context=True,
    dag=dag,
)

scan_documents >> chunk_documents >> store_metadata


dag.doc_md = """# RAG Document Ingestion

This DAG is a minimal, safe starting point for RAG ingestion.

## Purpose

- Discover documents under `RAG_DOC_DIR` (default: `/opt/documents/incoming`).
- Prepare basic chunk metadata (one chunk per file).
- Log chunk information as a placeholder for future vector DB / AI ingestion.

It is referenced by:

- `docs/tutorials/rag-document-ingestion.md`
- `docs/how-to/rag-ingest-new-docs.md`

You can extend this DAG to:

- Perform real text chunking.
- Call embedding models.
- Write into a vector database.
- Notify the AI Assistant that new content is available.
"""
