______________________________________________________________________

## description: Query the RAG knowledge base allowed-tools: Bash(python3:*), Bash(curl:*) argument-hint: \[question\]

# Query RAG Knowledge Base

You are helping query Qubinode Navigator's RAG knowledge base.

Query: $ARGUMENTS

Query the RAG system:
!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/ai-assistant && python3 -c "from src.rag_store import RAGStore; r=RAGStore(); print(r.query('$ARGUMENTS', top_k=5))" 2>/dev/null || echo "RAG query via Python failed"`

Alternative - use the AI assistant endpoint:
!`curl -s -X POST http://localhost:8080/api/query -H "Content-Type: application/json" -d '{"query": "$ARGUMENTS"}' 2>/dev/null | head -50`

The RAG system contains:

- Architecture Decision Records (ADRs)
- Deployment documentation
- Troubleshooting guides
- Configuration references

Analyze the results and provide:

1. Direct answers from the knowledge base
1. Relevant document references
1. Related topics to explore
1. Confidence level of the answer
