"""
Embedding Service for Qubinode RAG System
ADR-0049: Multi-Agent LLM Memory Architecture

Provides text embedding generation using local models (sentence-transformers)
or remote APIs (OpenAI) based on configuration.

Usage:
    from qubinode.embedding_service import EmbeddingService

    service = EmbeddingService()
    embedding = service.embed("Some text to embed")
    embeddings = service.embed_batch(["Text 1", "Text 2"])
"""

import os
import logging
import hashlib
from typing import List, Optional

logger = logging.getLogger(__name__)

# Configuration from environment
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")  # 'local' or 'openai'
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "384"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Lazy loading for models
_local_model = None
_openai_client = None


def _get_local_model():
    """Lazy load the local sentence-transformers model."""
    global _local_model
    if _local_model is None:
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading local embedding model: {EMBEDDING_MODEL}")
            _local_model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info(f"Model loaded successfully. Dimensions: {_local_model.get_sentence_embedding_dimension()}")
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    return _local_model


def _get_openai_client():
    """Lazy load the OpenAI client."""
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI

            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            _openai_client = OpenAI(api_key=OPENAI_API_KEY)
            logger.info("OpenAI client initialized")
        except ImportError:
            logger.error("openai not installed. Run: pip install openai")
            raise
    return _openai_client


class EmbeddingService:
    """
    Service for generating text embeddings.

    Supports:
    - Local models via sentence-transformers (default, works offline)
    - OpenAI API for ada-002 embeddings (requires API key)

    Configuration via environment variables:
    - EMBEDDING_PROVIDER: 'local' or 'openai'
    - EMBEDDING_MODEL: Model name/path
    - EMBEDDING_DIMENSIONS: Vector dimensions (384 for MiniLM, 1536 for ada-002)
    - OPENAI_API_KEY: Required if using OpenAI
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
    ):
        """
        Initialize the embedding service.

        Args:
            provider: Override EMBEDDING_PROVIDER env var
            model: Override EMBEDDING_MODEL env var
            dimensions: Override EMBEDDING_DIMENSIONS env var
        """
        self.provider = provider or EMBEDDING_PROVIDER
        self.model = model or EMBEDDING_MODEL
        self.dimensions = dimensions or EMBEDDING_DIMENSIONS

        logger.info(f"EmbeddingService initialized: provider={self.provider}, model={self.model}")

    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * self.dimensions

        if self.provider == "local":
            return self._embed_local(text)
        elif self.provider == "openai":
            return self._embed_openai(text)
        else:
            raise ValueError(f"Unknown embedding provider: {self.provider}")

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Filter empty texts but track positions
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            return [[0.0] * self.dimensions] * len(texts)

        # Generate embeddings for valid texts
        if self.provider == "local":
            valid_embeddings = self._embed_batch_local(valid_texts, batch_size)
        elif self.provider == "openai":
            valid_embeddings = self._embed_batch_openai(valid_texts, batch_size)
        else:
            raise ValueError(f"Unknown embedding provider: {self.provider}")

        # Reconstruct full list with zeros for empty texts
        results = [[0.0] * self.dimensions] * len(texts)
        for idx, embedding in zip(valid_indices, valid_embeddings):
            results[idx] = embedding

        return results

    def _embed_local(self, text: str) -> List[float]:
        """Generate embedding using local sentence-transformers model."""
        model = _get_local_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def _embed_batch_local(self, texts: List[str], batch_size: int) -> List[List[float]]:
        """Generate batch embeddings using local model."""
        model = _get_local_model()
        embeddings = model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
        return [emb.tolist() for emb in embeddings]

    def _embed_openai(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        client = _get_openai_client()
        response = client.embeddings.create(model="text-embedding-ada-002", input=text)
        return response.data[0].embedding

    def _embed_batch_openai(self, texts: List[str], batch_size: int) -> List[List[float]]:
        """Generate batch embeddings using OpenAI API."""
        client = _get_openai_client()
        results = []

        # OpenAI has limits, process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = client.embeddings.create(model="text-embedding-ada-002", input=batch)
            results.extend([d.embedding for d in response.data])

        return results

    @staticmethod
    def content_hash(text: str) -> str:
        """
        Generate SHA256 hash of text for deduplication.

        Args:
            text: Text to hash

        Returns:
            Hex string of SHA256 hash
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get_dimensions(self) -> int:
        """Return the embedding dimensions for this service."""
        return self.dimensions


# Singleton instance for convenience
_default_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the default embedding service singleton."""
    global _default_service
    if _default_service is None:
        _default_service = EmbeddingService()
    return _default_service


def embed_text(text: str) -> List[float]:
    """
    Convenience function to embed text using default service.

    Args:
        text: Text to embed

    Returns:
        Embedding vector
    """
    return get_embedding_service().embed(text)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Convenience function to embed multiple texts using default service.

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    return get_embedding_service().embed_batch(texts)


# =============================================================================
# Text Chunking Utilities
# =============================================================================


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50, separator: str = "\n\n") -> List[str]:
    """
    Split text into overlapping chunks for embedding.

    Args:
        text: Text to chunk
        chunk_size: Maximum characters per chunk
        chunk_overlap: Overlap between chunks
        separator: Preferred split point

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Find a good break point
        if end < len(text):
            # Try to break at separator
            sep_pos = text.rfind(separator, start, end)
            if sep_pos > start:
                end = sep_pos + len(separator)
            else:
                # Try to break at sentence
                for punct in [". ", "! ", "? ", "\n"]:
                    punct_pos = text.rfind(punct, start, end)
                    if punct_pos > start:
                        end = punct_pos + len(punct)
                        break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start with overlap
        start = end - chunk_overlap
        if start >= len(text):
            break

    return chunks


# =============================================================================
# Module Info
# =============================================================================

__version__ = "1.0.0"
__all__ = [
    "EmbeddingService",
    "get_embedding_service",
    "embed_text",
    "embed_texts",
    "chunk_text",
]
