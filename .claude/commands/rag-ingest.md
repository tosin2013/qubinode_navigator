______________________________________________________________________

## description: Ingest a document into the RAG knowledge base allowed-tools: Bash(ls:*), Bash(python3:*), Read argument-hint: \[file-path\]

# Ingest Document to RAG

You are helping ingest documents into Qubinode Navigator's RAG knowledge base.

Document to ingest: $1

First, verify the document exists:
!`ls -la $1 2>/dev/null || echo "File not found"`

Ingest using the RAG CLI:
!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/ai-assistant && python3 scripts/rag-cli.py ingest $1 2>/dev/null || echo "RAG CLI ingest failed"`

Alternative - use the prepare-rag-docs script for bulk ingestion:
!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator} && python3 scripts/prepare-rag-docs.py --help 2>/dev/null | head -20`

Supported document types:

- Markdown (.md)
- Text files (.txt)
- Python files (.py) - for code documentation
- YAML/JSON configuration files

After ingestion:

1. Verify document was indexed
1. Test a query related to the content
1. Check RAG statistics

!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/ai-assistant && python3 scripts/rag-cli.py stats 2>/dev/null || echo "Stats unavailable"`
