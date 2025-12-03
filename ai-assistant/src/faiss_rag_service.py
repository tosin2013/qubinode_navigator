"""
FAISS-based RAG (Retrieval-Augmented Generation) Service
Lightweight CPU-optimized RAG using FAISS and sentence-transformers
Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture
"""

import json
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np

try:
    import faiss
    from sentence_transformers import SentenceTransformer

    FAISS_AVAILABLE = True
except ImportError as e:
    FAISS_AVAILABLE = False
    logging.warning(f"FAISS or sentence-transformers not available: {e}")


@dataclass
class RetrievalResult:
    """Result from document retrieval"""

    chunk_id: str
    content: str
    title: str
    source_file: str
    score: float
    metadata: Dict[str, Any]


class FAISSRAGService:
    """FAISS-based RAG service optimized for CPU deployment"""

    def __init__(self, data_dir: str = "/app/data"):
        self.data_dir = Path(data_dir)
        self.rag_docs_dir = self.data_dir / "rag-docs"
        self.vector_db_dir = self.data_dir / "faiss-db"
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.embeddings_model = None
        self.faiss_index = None
        self.documents = []
        self.document_metadata = []
        self.documents_loaded = False

        # Create directories
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> bool:
        """Initialize the FAISS RAG service"""
        if not FAISS_AVAILABLE:
            self.logger.warning("FAISS not available - RAG service disabled")
            return False

        try:
            self.logger.info("Initializing FAISS RAG service...")

            # Initialize lightweight embeddings model
            self.logger.info("Loading embeddings model (all-MiniLM-L6-v2)...")
            self.embeddings_model = SentenceTransformer("all-MiniLM-L6-v2")

            # Try to load existing index
            if await self._load_existing_index():
                self.logger.info("Loaded existing FAISS index")
            else:
                # Build new index from documents
                await self._build_index_from_documents()

            self.documents_loaded = len(self.documents) > 0
            self.logger.info(
                f"FAISS RAG service initialized with {len(self.documents)} documents"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize FAISS RAG service: {e}")
            return False

    async def _load_existing_index(self) -> bool:
        """Load existing FAISS index if available"""
        try:
            index_file = self.vector_db_dir / "faiss.index"
            metadata_file = self.vector_db_dir / "metadata.pkl"
            documents_file = self.vector_db_dir / "documents.pkl"

            if not (
                index_file.exists()
                and metadata_file.exists()
                and documents_file.exists()
            ):
                return False

            # Load FAISS index
            self.faiss_index = faiss.read_index(str(index_file))

            # Load metadata and documents
            with open(metadata_file, "rb") as f:
                self.document_metadata = pickle.load(f)

            with open(documents_file, "rb") as f:
                self.documents = pickle.load(f)

            self.logger.info(
                f"Loaded existing index with {len(self.documents)} documents"
            )
            return True

        except Exception as e:
            self.logger.warning(f"Failed to load existing index: {e}")
            return False

    async def _build_index_from_documents(self) -> None:
        """Build FAISS index from processed document chunks"""
        try:
            # Load documents from processed chunks
            chunks_file = self.rag_docs_dir / "document_chunks.json"
            if not chunks_file.exists():
                self.logger.warning(f"No processed chunks found at {chunks_file}")
                return

            self.logger.info("Loading and processing documents...")
            with open(chunks_file, "r", encoding="utf-8") as f:
                chunks = json.load(f)

            # Filter and prepare documents
            valid_chunks = []
            for chunk in chunks:
                content = chunk.get("content", "").strip()
                if len(content) < 20:  # Skip very short content
                    continue
                valid_chunks.append(chunk)

            if not valid_chunks:
                self.logger.warning("No valid documents found")
                return

            self.logger.info(f"Processing {len(valid_chunks)} documents...")

            # Extract text content for embedding
            texts = [chunk["content"] for chunk in valid_chunks]

            # Generate embeddings in batches to manage memory
            batch_size = 32
            all_embeddings = []

            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]
                batch_embeddings = self.embeddings_model.encode(
                    batch_texts, convert_to_numpy=True, show_progress_bar=True
                )
                all_embeddings.append(batch_embeddings)

                if i % 100 == 0:
                    self.logger.info(
                        f"Processed {i + len(batch_texts)}/{len(texts)} documents"
                    )

            # Combine all embeddings
            embeddings_matrix = np.vstack(all_embeddings)

            # Create FAISS index
            dimension = embeddings_matrix.shape[1]
            self.logger.info(f"Creating FAISS index with dimension {dimension}")

            # Use IndexFlatIP for cosine similarity (after normalization)
            faiss.normalize_L2(embeddings_matrix)
            self.faiss_index = faiss.IndexFlatIP(dimension)
            self.faiss_index.add(embeddings_matrix)

            # Store document data
            self.documents = valid_chunks
            self.document_metadata = [
                {
                    "id": chunk["id"],
                    "title": chunk.get("title", ""),
                    "source_file": chunk.get("source_file", ""),
                    "metadata": chunk.get("metadata", {}),
                }
                for chunk in valid_chunks
            ]

            # Save index and metadata
            await self._save_index()

            self.logger.info(f"Built FAISS index with {len(self.documents)} documents")

        except Exception as e:
            self.logger.error(f"Failed to build index: {e}")

    async def _save_index(self) -> None:
        """Save FAISS index and metadata to disk"""
        try:
            # Save FAISS index
            index_file = self.vector_db_dir / "faiss.index"
            faiss.write_index(self.faiss_index, str(index_file))

            # Save metadata
            metadata_file = self.vector_db_dir / "metadata.pkl"
            with open(metadata_file, "wb") as f:
                pickle.dump(self.document_metadata, f)

            # Save documents
            documents_file = self.vector_db_dir / "documents.pkl"
            with open(documents_file, "wb") as f:
                pickle.dump(self.documents, f)

            self.logger.info("Saved FAISS index and metadata")

        except Exception as e:
            self.logger.error(f"Failed to save index: {e}")

    async def search_documents(
        self, query: str, n_results: int = 5, document_types: Optional[List[str]] = None
    ) -> List[RetrievalResult]:
        """Search for relevant documents using FAISS"""
        if not self.documents_loaded or not self.faiss_index:
            self.logger.warning("FAISS RAG service not properly initialized")
            return []

        try:
            # Generate query embedding
            query_embedding = self.embeddings_model.encode(
                [query], convert_to_numpy=True
            )
            faiss.normalize_L2(query_embedding)

            # Search FAISS index
            search_k = min(
                n_results * 3, len(self.documents)
            )  # Get more candidates for filtering
            scores, indices = self.faiss_index.search(query_embedding, search_k)

            # Convert results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # Invalid index
                    continue

                doc = self.documents[idx]
                metadata = self.document_metadata[idx]

                # Filter by document type if specified
                if document_types:
                    doc_type = metadata["metadata"].get("document_type", "")
                    if doc_type not in document_types:
                        continue

                result = RetrievalResult(
                    chunk_id=metadata["id"],
                    content=doc["content"],
                    title=metadata["title"],
                    source_file=metadata["source_file"],
                    score=float(score),
                    metadata=metadata["metadata"],
                )
                results.append(result)

                if len(results) >= n_results:
                    break

            self.logger.info(
                f"Retrieved {len(results)} documents for query: {query[:50]}..."
            )
            return results

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
            context_entry += f"Relevance: {result.score:.3f}\n\n"
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
        """Get health status of FAISS RAG service"""
        status = {
            "available": FAISS_AVAILABLE,
            "initialized": self.faiss_index is not None,
            "documents_loaded": self.documents_loaded,
            "document_count": len(self.documents),
            "embeddings_model": "all-MiniLM-L6-v2" if self.embeddings_model else None,
            "index_type": "FAISS IndexFlatIP" if self.faiss_index else None,
        }

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


# Mock RAG service for when FAISS is not available
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
            "index_type": "mock",
        }

    async def search_by_document_type(
        self, query: str, doc_type: str, n_results: int = 3
    ) -> List[RetrievalResult]:
        return await self.search_documents(query, n_results)

    async def get_adr_context(self, query: str) -> Tuple[str, List[str]]:
        return await self.get_context_for_query(query)

    async def get_config_context(self, query: str) -> Tuple[str, List[str]]:
        return await self.get_context_for_query(query)


def create_rag_service(data_dir: str = "/app/data"):
    """Factory function to create appropriate RAG service"""
    if FAISS_AVAILABLE:
        return FAISSRAGService(data_dir)
    else:
        return MockRAGService(data_dir)
