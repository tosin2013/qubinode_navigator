"""
RAG (Retrieval-Augmented Generation) Service
Provides document retrieval and embedding functionality for the AI assistant
Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer

    CHROMADB_AVAILABLE = True
except ImportError as e:
    CHROMADB_AVAILABLE = False
    logging.warning(
        f"ChromaDB or sentence-transformers not available: {e}. RAG functionality will be limited."
    )
except RuntimeError as e:
    CHROMADB_AVAILABLE = False
    logging.warning(f"ChromaDB runtime error: {e}. Using mock RAG service.")


@dataclass
class RetrievalResult:
    """Result from document retrieval"""

    chunk_id: str
    content: str
    title: str
    source_file: str
    score: float
    metadata: Dict[str, Any]


class RAGService:
    """Service for Retrieval-Augmented Generation using ChromaDB"""

    def __init__(self, data_dir: str = "/app/data"):
        self.data_dir = Path(data_dir)
        self.rag_docs_dir = self.data_dir / "rag-docs"
        self.vector_db_dir = self.data_dir / "vector-db"
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.client = None
        self.collection = None
        self.embeddings_model = None
        self.documents_loaded = False

        # Create directories
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> bool:
        """Initialize the RAG service"""
        if not CHROMADB_AVAILABLE:
            self.logger.warning("ChromaDB not available - using mock RAG service")
            return False

        try:
            self.logger.info("Initializing RAG service...")

            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(self.vector_db_dir),
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="qubinode_docs",
                metadata={"description": "Qubinode Navigator documentation"},
            )

            # Initialize embeddings model (lightweight for CPU)
            self.logger.info("Loading embeddings model...")
            self.embeddings_model = SentenceTransformer("all-MiniLM-L6-v2")

            # Load documents if not already loaded
            await self._ensure_documents_loaded()

            self.logger.info("RAG service initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize RAG service: {e}")
            return False

    async def _ensure_documents_loaded(self) -> None:
        """Ensure documents are loaded into the vector database"""
        try:
            # Check if documents are already loaded
            count = self.collection.count()
            if count > 0:
                self.logger.info(f"Vector database already contains {count} documents")
                self.documents_loaded = True
                return

            # Load documents from processed chunks
            chunks_file = self.rag_docs_dir / "document_chunks.json"
            if not chunks_file.exists():
                self.logger.warning(f"No processed chunks found at {chunks_file}")
                return

            self.logger.info("Loading documents into vector database...")
            with open(chunks_file, "r", encoding="utf-8") as f:
                chunks = json.load(f)

            # Process chunks in batches to avoid memory issues
            batch_size = 100
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                await self._add_batch_to_collection(batch)

                if i % 500 == 0:
                    self.logger.info(
                        f"Processed {i + len(batch)}/{len(chunks)} documents"
                    )

            self.logger.info(
                f"Successfully loaded {len(chunks)} documents into vector database"
            )
            self.documents_loaded = True

        except Exception as e:
            self.logger.error(f"Failed to load documents: {e}")

    async def _add_batch_to_collection(self, chunks: List[Dict[str, Any]]) -> None:
        """Add a batch of chunks to the collection"""
        try:
            # Prepare data for ChromaDB
            documents = []
            metadatas = []
            ids = []

            for chunk in chunks:
                # Skip very short or empty content
                content = chunk.get("content", "").strip()
                if len(content) < 20:
                    continue

                documents.append(content)
                metadatas.append(
                    {
                        "title": chunk.get("title", ""),
                        "source_file": chunk.get("source_file", ""),
                        "chunk_type": chunk.get("chunk_type", ""),
                        "word_count": chunk.get("word_count", 0),
                        "document_type": chunk.get("metadata", {}).get(
                            "document_type", ""
                        ),
                        "created_at": chunk.get("created_at", ""),
                    }
                )
                ids.append(chunk["id"])

            if documents:
                # Generate embeddings
                embeddings = self.embeddings_model.encode(documents).tolist()

                # Add to collection
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings,
                )

        except Exception as e:
            self.logger.error(f"Failed to add batch to collection: {e}")

    async def search_documents(
        self, query: str, n_results: int = 5, document_types: Optional[List[str]] = None
    ) -> List[RetrievalResult]:
        """Search for relevant documents"""
        if not self.documents_loaded or not self.collection:
            self.logger.warning("RAG service not properly initialized")
            return []

        try:
            # Build where clause for filtering
            where_clause = {}
            if document_types:
                where_clause["document_type"] = {"$in": document_types}

            # Perform similarity search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause if where_clause else None,
            )

            # Convert to RetrievalResult objects
            retrieval_results = []

            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i]
                    distance = (
                        results["distances"][0][i] if results.get("distances") else 0.0
                    )

                    # Convert distance to similarity score (lower distance = higher similarity)
                    score = max(0.0, 1.0 - distance)

                    result = RetrievalResult(
                        chunk_id=results["ids"][0][i],
                        content=doc,
                        title=metadata.get("title", ""),
                        source_file=metadata.get("source_file", ""),
                        score=score,
                        metadata=metadata,
                    )
                    retrieval_results.append(result)

            self.logger.info(
                f"Retrieved {len(retrieval_results)} documents for query: {query[:50]}..."
            )
            return retrieval_results

        except Exception as e:
            self.logger.error(f"Failed to search documents: {e}")
            return []

    async def get_context_for_query(
        self,
        query: str,
        max_context_length: int = 4000,
        document_types: Optional[List[str]] = None,
    ) -> Tuple[str, List[str]]:
        """Get relevant context for a query, formatted for AI assistant"""
        results = await self.search_documents(
            query,
            n_results=10,  # Get more results to have options
            document_types=document_types,
        )

        if not results:
            return "", []

        # Build context string within length limit
        context_parts = []
        sources = []
        current_length = 0

        for result in results:
            # Format context entry
            context_entry = f"## {result.title}\n"
            context_entry += f"Source: {result.source_file}\n"
            context_entry += f"Relevance: {result.score:.2f}\n\n"
            context_entry += result.content + "\n\n"

            # Check if adding this would exceed limit
            if current_length + len(context_entry) > max_context_length:
                break

            context_parts.append(context_entry)
            sources.append(result.source_file)
            current_length += len(context_entry)

        context = "# Relevant Documentation Context\n\n" + "".join(context_parts)
        return context, list(set(sources))  # Remove duplicate sources

    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of RAG service"""
        status = {
            "available": CHROMADB_AVAILABLE,
            "initialized": self.client is not None,
            "documents_loaded": self.documents_loaded,
            "document_count": 0,
            "embeddings_model": None,
        }

        if self.collection:
            try:
                status["document_count"] = self.collection.count()
            except:
                pass

        if self.embeddings_model:
            status["embeddings_model"] = "all-MiniLM-L6-v2"

        return status

    async def search_by_document_type(
        self, query: str, doc_type: str, n_results: int = 3
    ) -> List[RetrievalResult]:
        """Search for documents of a specific type"""
        return await self.search_documents(
            query, n_results=n_results, document_types=[doc_type]
        )

    async def get_adr_context(self, query: str) -> Tuple[str, List[str]]:
        """Get ADR-specific context for architectural questions"""
        return await self.get_context_for_query(
            query, document_types=["adr"], max_context_length=3000
        )

    async def get_config_context(self, query: str) -> Tuple[str, List[str]]:
        """Get configuration-specific context"""
        return await self.get_context_for_query(
            query, document_types=["config"], max_context_length=2000
        )


# Mock RAG service for when ChromaDB is not available
class MockRAGService:
    """Mock RAG service for development/testing"""

    def __init__(self, data_dir: str = "/app/data"):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Using mock RAG service")

    async def initialize(self) -> bool:
        return True

    async def search_documents(
        self, query: str, n_results: int = 5, document_types: Optional[List[str]] = None
    ) -> List[RetrievalResult]:
        # Return mock results
        return [
            RetrievalResult(
                chunk_id="mock_001",
                content=f"Mock documentation content related to: {query}",
                title="Mock Documentation",
                source_file="docs/mock.md",
                score=0.85,
                metadata={"document_type": "mock"},
            )
        ]

    async def get_context_for_query(
        self,
        query: str,
        max_context_length: int = 4000,
        document_types: Optional[List[str]] = None,
    ) -> Tuple[str, List[str]]:
        context = f"# Mock Context for: {query}\n\nThis is mock documentation context for development purposes."
        return context, ["docs/mock.md"]

    async def get_health_status(self) -> Dict[str, Any]:
        return {
            "available": False,
            "initialized": True,
            "documents_loaded": False,
            "document_count": 0,
            "embeddings_model": "mock",
        }

    async def search_by_document_type(
        self, query: str, doc_type: str, n_results: int = 3
    ) -> List[RetrievalResult]:
        return await self.search_documents(query, n_results)

    async def get_adr_context(self, query: str) -> Tuple[str, List[str]]:
        return await self.get_context_for_query(query)

    async def get_config_context(self, query: str) -> Tuple[str, List[str]]:
        return await self.get_context_for_query(query)


def create_rag_service(data_dir: str = "/app/data") -> RAGService:
    """Factory function to create appropriate RAG service"""
    if CHROMADB_AVAILABLE:
        return RAGService(data_dir)
    else:
        return MockRAGService(data_dir)
