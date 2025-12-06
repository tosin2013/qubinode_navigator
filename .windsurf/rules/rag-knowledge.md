# RAG Knowledge Base Operations

Apply when working with RAG, knowledge base, or embedding-related files.

## Overview

Qubinode Navigator includes a RAG (Retrieval-Augmented Generation) system for querying documentation and troubleshooting knowledge.

## Components

- **Vector Store**: PostgreSQL with pgvector extension
- **Embedding Service**: Host service on port 8891
- **Knowledge Sources**: ADRs, deployment docs, troubleshooting guides

## Query the Knowledge Base

```bash
# Via AI Assistant API
curl -s -X POST http://localhost:8080/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "how to deploy OpenShift disconnected"}'

# Via RAG CLI
cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/ai-assistant
python3 scripts/rag-cli.py query "your question here"
```

## Ingest Documents

```bash
# Single document
python3 scripts/rag-cli.py ingest /path/to/document.md

# Bulk ingestion
cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}
python3 scripts/prepare-rag-docs.py
```

## Check RAG Statistics

```bash
# Get stats
python3 scripts/rag-cli.py stats

# List indexed documents
python3 scripts/rag-cli.py list
```

## Supported Document Types

- Markdown (.md) - Primary format
- Text files (.txt)
- Python files (.py) - For code documentation
- YAML/JSON - Configuration references

## RAG Store Location

The RAG store implementation is in:

- `ai-assistant/src/rag_store.py` - Core RAG functionality
- `airflow/plugins/qubinode/rag_store.py` - Airflow integration
