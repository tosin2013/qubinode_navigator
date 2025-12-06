______________________________________________________________________

## description: Show RAG knowledge base statistics allowed-tools: Bash(python3:*), Bash(curl:*), Bash(psql:\*)

# RAG Knowledge Base Statistics

You are helping review Qubinode Navigator's RAG knowledge base statistics.

Get RAG statistics:
!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/ai-assistant && python3 scripts/rag-cli.py stats 2>/dev/null || echo "RAG CLI stats unavailable"`

Check Qdrant vector store (if running):
!`curl -s http://localhost:6333/collections 2>/dev/null | head -20 || echo "Qdrant not accessible"`

Check PostgreSQL pgvector (if using):
!`psql -h localhost -U airflow -d airflow -c "SELECT COUNT(*) FROM rag_documents;" 2>/dev/null || echo "pgvector stats unavailable"`

List indexed documents:
!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/ai-assistant && python3 scripts/rag-cli.py list 2>/dev/null | head -30 || echo "Document list unavailable"`

Provide:

1. Total documents indexed
1. Vector dimensions and count
1. Storage utilization
1. Last update timestamp
1. Recommendations for improving coverage

$ARGUMENTS
