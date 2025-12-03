"""
RAG Store for Qubinode Multi-Agent LLM System
ADR-0049: Multi-Agent LLM Memory Architecture

Provides persistent storage and retrieval of:
- Document embeddings for semantic search
- Troubleshooting history for learning
- Agent decisions for auditing

Uses PgVector extension in PostgreSQL for efficient vector similarity search.

Usage:
    from qubinode.rag_store import RAGStore

    store = RAGStore()

    # Ingest a document
    doc_id = store.ingest_document(
        content="FreeIPA deployment guide...",
        doc_type="guide",
        source_path="/docs/freeipa.md"
    )

    # Search for similar documents
    results = store.search_documents("How to configure DNS for FreeIPA?")

    # Log troubleshooting attempt
    store.log_troubleshooting(
        session_id=session_id,
        task="Deploy FreeIPA",
        error="DNS resolution failed",
        solution="Opened port 53 in firewall",
        result="success"
    )
"""

import os
import logging
import uuid
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN",
    "postgresql+psycopg2://airflow:airflow@localhost/airflow",
)

# Convert SQLAlchemy URL to psycopg2 format if needed
if DATABASE_URL.startswith("postgresql+psycopg2://"):
    PSYCOPG2_URL = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
else:
    PSYCOPG2_URL = DATABASE_URL

# Lazy imports
_psycopg2 = None
_connection_pool = None


def _get_psycopg2():
    """Lazy import psycopg2."""
    global _psycopg2
    if _psycopg2 is None:
        import psycopg2
        import psycopg2.pool

        _psycopg2 = psycopg2
    return _psycopg2


def _get_connection_pool():
    """Get or create connection pool."""
    global _connection_pool
    if _connection_pool is None:
        psycopg2 = _get_psycopg2()
        _connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1, maxconn=10, dsn=PSYCOPG2_URL
        )
        logger.info("Database connection pool created")
    return _connection_pool


class RAGStore:
    """
    Persistent RAG storage using PgVector.

    Provides:
    - Document ingestion with chunking and embedding
    - Semantic similarity search
    - Troubleshooting history logging and retrieval
    - Agent decision logging
    """

    def __init__(self, embedding_service=None):
        """
        Initialize RAG store.

        Args:
            embedding_service: Optional custom embedding service.
                              Uses default if not provided.
        """
        if embedding_service is None:
            from qubinode.embedding_service import get_embedding_service

            embedding_service = get_embedding_service()

        self.embedding_service = embedding_service
        self._pool = None

    @property
    def pool(self):
        """Lazy-load connection pool."""
        if self._pool is None:
            self._pool = _get_connection_pool()
        return self._pool

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = self.pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self.pool.putconn(conn)

    # =========================================================================
    # Document Operations
    # =========================================================================

    def ingest_document(
        self,
        content: str,
        doc_type: str,
        source_path: Optional[str] = None,
        source_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> List[str]:
        """
        Ingest a document into the RAG store.

        Chunks the document, generates embeddings, and stores in PgVector.

        Args:
            content: Document content
            doc_type: Type of document ('adr', 'provider_doc', 'dag', etc.)
            source_path: File path of source
            source_url: URL of source
            metadata: Additional metadata
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks

        Returns:
            List of document IDs created
        """
        from qubinode.embedding_service import chunk_text

        # Check for duplicate
        content_hash = self.embedding_service.content_hash(content)
        if self._document_exists(content_hash):
            logger.info(f"Document already exists (hash: {content_hash[:16]}...)")
            return []

        # Chunk the content
        chunks = chunk_text(content, chunk_size, chunk_overlap)
        logger.info(f"Chunked document into {len(chunks)} parts")

        # Generate embeddings
        embeddings = self.embedding_service.embed_batch(chunks)

        # Store chunks
        doc_ids = []
        parent_id = str(uuid.uuid4()) if len(chunks) > 1 else None

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    doc_id = str(uuid.uuid4())

                    cur.execute(
                        """
                        INSERT INTO rag_documents
                        (id, content, content_hash, embedding, doc_type, source_path,
                         source_url, metadata, chunk_index, parent_doc_id)
                        VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s, %s, %s)
                    """,
                        (
                            doc_id,
                            chunk,
                            content_hash
                            if i == 0
                            else None,  # Only first chunk gets hash
                            embedding,
                            doc_type,
                            source_path,
                            source_url,
                            metadata or {},
                            i,
                            parent_id,
                        ),
                    )
                    doc_ids.append(doc_id)

        logger.info(f"Ingested {len(doc_ids)} document chunks")
        return doc_ids

    def _document_exists(self, content_hash: str) -> bool:
        """Check if document with given hash already exists."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM rag_documents WHERE content_hash = %s LIMIT 1",
                    (content_hash,),
                )
                return cur.fetchone() is not None

    def search_documents(
        self,
        query: str,
        doc_types: Optional[List[str]] = None,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Search for documents similar to query.

        Args:
            query: Search query
            doc_types: Filter by document types
            limit: Maximum results
            threshold: Minimum similarity threshold

        Returns:
            List of matching documents with similarity scores
        """
        # Generate query embedding
        query_embedding = self.embedding_service.embed(query)

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if doc_types:
                    cur.execute(
                        """
                        SELECT id, content, doc_type, source_path, metadata,
                               1 - (embedding <=> %s::vector) as similarity
                        FROM rag_documents
                        WHERE doc_type = ANY(%s)
                          AND 1 - (embedding <=> %s::vector) > %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """,
                        (
                            query_embedding,
                            doc_types,
                            query_embedding,
                            threshold,
                            query_embedding,
                            limit,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, content, doc_type, source_path, metadata,
                               1 - (embedding <=> %s::vector) as similarity
                        FROM rag_documents
                        WHERE 1 - (embedding <=> %s::vector) > %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """,
                        (
                            query_embedding,
                            query_embedding,
                            threshold,
                            query_embedding,
                            limit,
                        ),
                    )

                rows = cur.fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "id": str(row[0]),
                    "content": row[1],
                    "doc_type": row[2],
                    "source_path": row[3],
                    "metadata": row[4],
                    "similarity": float(row[5]),
                }
            )

        logger.info(f"Found {len(results)} documents matching query")
        return results

    def list_documents(
        self, doc_type: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List documents in the store.

        Args:
            doc_type: Filter by type
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of document metadata
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if doc_type:
                    cur.execute(
                        """
                        SELECT id, doc_type, source_path, metadata, created_at,
                               LENGTH(content) as content_length
                        FROM rag_documents
                        WHERE doc_type = %s AND chunk_index = 0
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """,
                        (doc_type, limit, offset),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, doc_type, source_path, metadata, created_at,
                               LENGTH(content) as content_length
                        FROM rag_documents
                        WHERE chunk_index = 0
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """,
                        (limit, offset),
                    )

                rows = cur.fetchall()

        return [
            {
                "id": str(row[0]),
                "doc_type": row[1],
                "source_path": row[2],
                "metadata": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "content_length": row[5],
            }
            for row in rows
        ]

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document and its chunks.

        Args:
            doc_id: Document ID to delete

        Returns:
            True if deleted, False if not found
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Delete chunks if this is a parent
                cur.execute(
                    "DELETE FROM rag_documents WHERE parent_doc_id = %s", (doc_id,)
                )

                # Delete the document itself
                cur.execute("DELETE FROM rag_documents WHERE id = %s", (doc_id,))
                return cur.rowcount > 0

    # =========================================================================
    # Troubleshooting Operations
    # =========================================================================

    def log_troubleshooting(
        self,
        session_id: str,
        task_description: str,
        attempted_solution: str,
        result: str,
        error_message: Optional[str] = None,
        error_category: Optional[str] = None,
        result_details: Optional[str] = None,
        confidence_score: Optional[float] = None,
        agent: str = "developer",
        override_by: Optional[str] = None,
        override_reason: Optional[str] = None,
        dag_id: Optional[str] = None,
        component: Optional[str] = None,
    ) -> str:
        """
        Log a troubleshooting attempt for future learning.

        Args:
            session_id: Session identifier
            task_description: What was being attempted
            attempted_solution: Solution that was tried
            result: 'success', 'failed', or 'partial'
            error_message: Error that occurred
            error_category: Category of error ('dns', 'firewall', etc.)
            result_details: Details of the outcome
            confidence_score: Confidence when attempting
            agent: Which agent made the attempt
            override_by: If overridden, by whom
            override_reason: Why override was needed
            dag_id: Related DAG
            component: Related component

        Returns:
            ID of the logged attempt
        """
        # Create embedding from error + solution for similarity search
        embed_text = f"{error_message or ''} {task_description} {attempted_solution}"
        embedding = self.embedding_service.embed(embed_text)

        attempt_id = str(uuid.uuid4())

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Get next sequence number for session
                cur.execute(
                    "SELECT COALESCE(MAX(sequence_num), 0) + 1 FROM troubleshooting_attempts WHERE session_id = %s",
                    (session_id,),
                )
                sequence_num = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO troubleshooting_attempts
                    (id, session_id, sequence_num, task_description, error_message,
                     error_category, attempted_solution, result, result_details,
                     embedding, confidence_score, agent, override_by, override_reason,
                     dag_id, component)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        attempt_id,
                        session_id,
                        sequence_num,
                        task_description,
                        error_message,
                        error_category,
                        attempted_solution,
                        result,
                        result_details,
                        embedding,
                        confidence_score,
                        agent,
                        override_by,
                        override_reason,
                        dag_id,
                        component,
                    ),
                )

        logger.info(f"Logged troubleshooting attempt: {attempt_id} (result: {result})")
        return attempt_id

    def search_similar_errors(
        self,
        error_description: str,
        only_successful: bool = False,
        limit: int = 5,
        threshold: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar past errors and their solutions.

        Args:
            error_description: Description of current error
            only_successful: Only return successful solutions
            limit: Maximum results
            threshold: Minimum similarity threshold

        Returns:
            List of similar troubleshooting attempts
        """
        embedding = self.embedding_service.embed(error_description)

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if only_successful:
                    cur.execute(
                        """
                        SELECT id, error_message, attempted_solution, result,
                               component, dag_id, confidence_score,
                               1 - (embedding <=> %s::vector) as similarity
                        FROM troubleshooting_attempts
                        WHERE result = 'success'
                          AND 1 - (embedding <=> %s::vector) > %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """,
                        (embedding, embedding, threshold, embedding, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, error_message, attempted_solution, result,
                               component, dag_id, confidence_score,
                               1 - (embedding <=> %s::vector) as similarity
                        FROM troubleshooting_attempts
                        WHERE 1 - (embedding <=> %s::vector) > %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """,
                        (embedding, embedding, threshold, embedding, limit),
                    )

                rows = cur.fetchall()

        return [
            {
                "id": str(row[0]),
                "error_message": row[1],
                "attempted_solution": row[2],
                "result": row[3],
                "component": row[4],
                "dag_id": row[5],
                "confidence_score": row[6],
                "similarity": float(row[7]),
            }
            for row in rows
        ]

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all troubleshooting attempts for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of attempts in order
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, sequence_num, task_description, error_message,
                           attempted_solution, result, result_details,
                           confidence_score, agent, override_by, created_at
                    FROM troubleshooting_attempts
                    WHERE session_id = %s
                    ORDER BY sequence_num
                """,
                    (session_id,),
                )

                rows = cur.fetchall()

        return [
            {
                "id": str(row[0]),
                "sequence_num": row[1],
                "task_description": row[2],
                "error_message": row[3],
                "attempted_solution": row[4],
                "result": row[5],
                "result_details": row[6],
                "confidence_score": row[7],
                "agent": row[8],
                "override_by": row[9],
                "created_at": row[10].isoformat() if row[10] else None,
            }
            for row in rows
        ]

    # =========================================================================
    # Agent Decision Operations
    # =========================================================================

    def log_decision(
        self,
        agent: str,
        decision_type: str,
        context: Dict[str, Any],
        decision: str,
        reasoning: Optional[str] = None,
        confidence: Optional[float] = None,
        rag_hits: Optional[int] = None,
        rag_max_similarity: Optional[float] = None,
        session_id: Optional[str] = None,
        parent_decision_id: Optional[str] = None,
    ) -> str:
        """
        Log an agent decision for auditing.

        Args:
            agent: Which agent made decision
            decision_type: Type of decision
            context: Full context at decision time
            decision: The decision made
            reasoning: Why this decision
            confidence: Confidence score
            rag_hits: Number of RAG results found
            rag_max_similarity: Best similarity score
            session_id: Session identifier
            parent_decision_id: Parent decision for chains

        Returns:
            Decision ID
        """
        import json

        decision_id = str(uuid.uuid4())

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_decisions
                    (id, agent, decision_type, context, decision, reasoning,
                     confidence, rag_hits, rag_max_similarity, session_id,
                     parent_decision_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        decision_id,
                        agent,
                        decision_type,
                        json.dumps(context),
                        decision,
                        reasoning,
                        confidence,
                        rag_hits,
                        rag_max_similarity,
                        session_id,
                        parent_decision_id,
                    ),
                )

        logger.info(
            f"Logged {agent} decision: {decision_type} (confidence: {confidence})"
        )
        return decision_id

    def update_decision_outcome(
        self, decision_id: str, outcome: str, outcome_details: Optional[str] = None
    ) -> bool:
        """
        Update the outcome of a decision.

        Args:
            decision_id: Decision to update
            outcome: 'success', 'failed', or 'pending'
            outcome_details: Details of outcome

        Returns:
            True if updated
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE agent_decisions
                    SET outcome = %s, outcome_details = %s, completed_at = NOW()
                    WHERE id = %s
                """,
                    (outcome, outcome_details, decision_id),
                )
                return cur.rowcount > 0

    # =========================================================================
    # Provider Operations
    # =========================================================================

    def check_provider_exists(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Check if an Airflow provider exists.

        Args:
            provider_name: Name to search for (e.g., 'azure', 'postgres')

        Returns:
            Provider info if found, None otherwise
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT provider_name, package_name, description,
                           documentation_url, operators, hooks, sensors
                    FROM airflow_providers
                    WHERE provider_name ILIKE %s
                       OR package_name ILIKE %s
                """,
                    (f"%{provider_name}%", f"%{provider_name}%"),
                )

                row = cur.fetchone()

        if row:
            return {
                "provider_name": row[0],
                "package_name": row[1],
                "description": row[2],
                "documentation_url": row[3],
                "operators": row[4],
                "hooks": row[5],
                "sensors": row[6],
            }
        return None

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG store."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Document counts by type
                cur.execute(
                    """
                    SELECT doc_type, COUNT(*) as count
                    FROM rag_documents
                    WHERE chunk_index = 0
                    GROUP BY doc_type
                """
                )
                doc_counts = {row[0]: row[1] for row in cur.fetchall()}

                # Troubleshooting stats
                cur.execute(
                    """
                    SELECT result, COUNT(*) as count
                    FROM troubleshooting_attempts
                    GROUP BY result
                """
                )
                troubleshooting_counts = {row[0]: row[1] for row in cur.fetchall()}

                # Decision stats
                cur.execute(
                    """
                    SELECT agent, COUNT(*) as count
                    FROM agent_decisions
                    GROUP BY agent
                """
                )
                decision_counts = {row[0]: row[1] for row in cur.fetchall()}

        return {
            "documents": doc_counts,
            "troubleshooting": troubleshooting_counts,
            "decisions": decision_counts,
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_default_store: Optional[RAGStore] = None


def get_rag_store() -> RAGStore:
    """Get or create the default RAG store singleton."""
    global _default_store
    if _default_store is None:
        _default_store = RAGStore()
    return _default_store


# =============================================================================
# Module Info
# =============================================================================

__version__ = "1.0.0"
__all__ = [
    "RAGStore",
    "get_rag_store",
]
