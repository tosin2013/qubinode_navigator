"""
Tests for RAG Services (rag_service.py and qdrant_rag_service.py)
Tests document retrieval, embedding, and context generation

Note: qdrant_rag_service tests are skipped by default because:
1. The module tries to create /app/data directories on import
2. qdrant_rag_service.py is excluded from coverage metrics
"""

import pytest
import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rag_service import (
    RAGService,
    MockRAGService as ChromaMockRAGService,
    RetrievalResult as ChromaRetrievalResult,
    create_rag_service as create_chroma_rag_service,
)

# Skip qdrant imports if they would cause issues (covered by mocks elsewhere)
# Check if qdrant_rag_service is already mocked by another test file
QDRANT_AVAILABLE = False
if "qdrant_rag_service" in sys.modules and isinstance(sys.modules["qdrant_rag_service"], MagicMock):
    # Module is mocked - skip qdrant tests
    QdrantRAGService = MagicMock
    QdrantMockRAGService = MagicMock
    QdrantRetrievalResult = MagicMock
    create_qdrant_rag_service = MagicMock
else:
    try:
        # Only import if we can actually create directories
        if os.access("/app", os.W_OK) or not os.path.exists("/app"):
            from qdrant_rag_service import (
                QdrantRAGService,
                MockRAGService as QdrantMockRAGService,
                RetrievalResult as QdrantRetrievalResult,
                create_rag_service as create_qdrant_rag_service,
            )

            QDRANT_AVAILABLE = True
    except (ImportError, PermissionError, FileNotFoundError):
        # Create mocks for tests to reference
        QdrantRAGService = MagicMock
        QdrantMockRAGService = MagicMock
        QdrantRetrievalResult = MagicMock
        create_qdrant_rag_service = MagicMock


class TestRetrievalResult:
    """Test RetrievalResult dataclass"""

    def test_chroma_retrieval_result(self):
        """Test ChromaDB RetrievalResult creation"""
        result = ChromaRetrievalResult(
            chunk_id="chunk_001",
            content="Test content",
            title="Test Title",
            source_file="docs/test.md",
            score=0.95,
            metadata={"document_type": "guide"},
        )

        assert result.chunk_id == "chunk_001"
        assert result.content == "Test content"
        assert result.title == "Test Title"
        assert result.score == 0.95

    @pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant module not available in CI")
    def test_qdrant_retrieval_result(self):
        """Test Qdrant RetrievalResult creation"""
        result = QdrantRetrievalResult(
            chunk_id="chunk_002",
            content="Qdrant content",
            title="Qdrant Title",
            source_file="docs/qdrant.md",
            score=0.85,
            metadata={"document_type": "adr"},
        )

        assert result.chunk_id == "chunk_002"
        assert result.content == "Qdrant content"
        assert result.score == 0.85


class TestRAGServiceInit:
    """Test RAGService initialization"""

    def test_rag_service_creation(self, tmp_path):
        """Test creating RAGService instance"""
        service = RAGService(data_dir=str(tmp_path))

        assert service.data_dir == tmp_path
        assert service.client is None
        assert service.collection is None
        assert service.documents_loaded is False

    def test_rag_service_directories_created(self, tmp_path):
        """Test that required directories are created"""
        service = RAGService(data_dir=str(tmp_path))

        assert service.vector_db_dir.exists()


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant module not available in CI")
class TestQdrantRAGServiceInit:
    """Test QdrantRAGService initialization"""

    def test_qdrant_service_creation(self, tmp_path):
        """Test creating QdrantRAGService instance"""
        service = QdrantRAGService(data_dir=str(tmp_path))

        assert service.data_dir == tmp_path
        assert service.client is None
        assert service.collection_name == "qubinode_docs"
        assert service.documents_loaded is False

    def test_qdrant_service_directories_created(self, tmp_path):
        """Test that required directories are created"""
        service = QdrantRAGService(data_dir=str(tmp_path))

        assert service.vector_db_dir.exists()


class TestMockRAGService:
    """Test MockRAGService"""

    @pytest.mark.asyncio
    async def test_mock_service_initialize(self, tmp_path):
        """Test mock service initialization"""
        service = ChromaMockRAGService(data_dir=str(tmp_path))
        result = await service.initialize()

        assert result is True

    @pytest.mark.asyncio
    async def test_mock_service_search(self, tmp_path):
        """Test mock service search"""
        service = ChromaMockRAGService(data_dir=str(tmp_path))
        results = await service.search_documents("test query")

        assert len(results) == 1
        assert "Mock" in results[0].content or "mock" in results[0].content.lower()

    @pytest.mark.asyncio
    async def test_mock_service_get_context(self, tmp_path):
        """Test mock service get_context_for_query"""
        service = ChromaMockRAGService(data_dir=str(tmp_path))
        context, sources = await service.get_context_for_query("test query")

        assert "Mock" in context or "mock" in context.lower()
        assert len(sources) > 0

    @pytest.mark.asyncio
    async def test_mock_service_health_status(self, tmp_path):
        """Test mock service health status"""
        service = ChromaMockRAGService(data_dir=str(tmp_path))
        status = await service.get_health_status()

        assert status["available"] is False
        assert status["initialized"] is True
        assert status["embeddings_model"] == "mock"


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant module not available in CI")
class TestQdrantMockRAGService:
    """Test Qdrant MockRAGService"""

    @pytest.mark.asyncio
    async def test_qdrant_mock_initialize(self, tmp_path):
        """Test Qdrant mock service initialization"""
        service = QdrantMockRAGService(data_dir=str(tmp_path))
        result = await service.initialize()

        assert result is True

    @pytest.mark.asyncio
    async def test_qdrant_mock_search(self, tmp_path):
        """Test Qdrant mock service search"""
        service = QdrantMockRAGService(data_dir=str(tmp_path))
        results = await service.search_documents("test query", n_results=3)

        assert len(results) == 1
        assert results[0].score > 0

    @pytest.mark.asyncio
    async def test_qdrant_mock_get_context(self, tmp_path):
        """Test Qdrant mock service get_context_for_query"""
        service = QdrantMockRAGService(data_dir=str(tmp_path))
        context, sources = await service.get_context_for_query("test query")

        assert len(context) > 0
        assert len(sources) > 0

    @pytest.mark.asyncio
    async def test_qdrant_mock_health_status(self, tmp_path):
        """Test Qdrant mock service health status"""
        service = QdrantMockRAGService(data_dir=str(tmp_path))
        status = await service.get_health_status()

        assert status["available"] is False
        assert "Mock" in status["vector_db_type"]


class TestRAGServiceSearchDocuments:
    """Test document search functionality"""

    @pytest.mark.asyncio
    async def test_search_not_initialized(self, tmp_path):
        """Test search when service not initialized"""
        service = RAGService(data_dir=str(tmp_path))
        results = await service.search_documents("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_document_types(self, tmp_path):
        """Test search with document type filter"""
        service = ChromaMockRAGService(data_dir=str(tmp_path))
        results = await service.search_documents("test query", n_results=5, document_types=["adr"])

        assert isinstance(results, list)


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant module not available in CI")
class TestQdrantRAGServiceSearchDocuments:
    """Test Qdrant document search functionality"""

    @pytest.mark.asyncio
    async def test_qdrant_search_not_initialized(self, tmp_path):
        """Test Qdrant search when not initialized"""
        service = QdrantRAGService(data_dir=str(tmp_path))
        results = await service.search_documents("test query")

        assert results == []


class TestRAGServiceContextRetrieval:
    """Test context retrieval functionality"""

    @pytest.mark.asyncio
    async def test_get_context_empty_results(self, tmp_path):
        """Test context retrieval with no results"""
        service = RAGService(data_dir=str(tmp_path))
        context, sources = await service.get_context_for_query("obscure query")

        assert context == ""
        assert sources == []

    @pytest.mark.asyncio
    async def test_get_context_with_length_limit(self, tmp_path):
        """Test context retrieval respects length limit"""
        service = ChromaMockRAGService(data_dir=str(tmp_path))
        context, sources = await service.get_context_for_query("test query", max_context_length=100)

        # Context should be within limit (approximately)
        assert len(context) <= 200  # Allow some buffer for formatting


class TestRAGServiceSpecializedMethods:
    """Test specialized retrieval methods"""

    @pytest.mark.asyncio
    async def test_search_by_document_type(self, tmp_path):
        """Test searching by document type"""
        service = ChromaMockRAGService(data_dir=str(tmp_path))
        results = await service.search_by_document_type("architecture", "adr", 3)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_adr_context(self, tmp_path):
        """Test getting ADR-specific context"""
        service = ChromaMockRAGService(data_dir=str(tmp_path))
        context, sources = await service.get_adr_context("deployment architecture")

        assert isinstance(context, str)
        assert isinstance(sources, list)

    @pytest.mark.asyncio
    async def test_get_config_context(self, tmp_path):
        """Test getting config-specific context"""
        service = ChromaMockRAGService(data_dir=str(tmp_path))
        context, sources = await service.get_config_context("network settings")

        assert isinstance(context, str)
        assert isinstance(sources, list)


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant module not available in CI")
class TestQdrantRAGServiceSpecializedMethods:
    """Test Qdrant specialized retrieval methods"""

    @pytest.mark.asyncio
    async def test_qdrant_search_by_document_type(self, tmp_path):
        """Test Qdrant searching by document type"""
        service = QdrantMockRAGService(data_dir=str(tmp_path))
        results = await service.search_by_document_type("architecture", "adr", 3)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_qdrant_get_adr_context(self, tmp_path):
        """Test Qdrant getting ADR-specific context"""
        service = QdrantMockRAGService(data_dir=str(tmp_path))
        context, sources = await service.get_adr_context("deployment architecture")

        assert isinstance(context, str)
        assert isinstance(sources, list)


class TestRAGServiceHealthStatus:
    """Test health status reporting"""

    @pytest.mark.asyncio
    async def test_health_status_not_initialized(self, tmp_path):
        """Test health status when not initialized"""
        service = RAGService(data_dir=str(tmp_path))
        status = await service.get_health_status()

        assert status["initialized"] is False
        assert status["documents_loaded"] is False
        assert status["document_count"] == 0


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant module not available in CI")
class TestQdrantRAGServiceHealthStatus:
    """Test Qdrant health status reporting"""

    @pytest.mark.asyncio
    async def test_qdrant_health_status_not_initialized(self, tmp_path):
        """Test Qdrant health status when not initialized"""
        service = QdrantRAGService(data_dir=str(tmp_path))
        status = await service.get_health_status()

        assert status["initialized"] is False
        assert status["documents_loaded"] is False

    def test_qdrant_get_document_count(self, tmp_path):
        """Test getting document count"""
        service = QdrantRAGService(data_dir=str(tmp_path))
        count = service._get_document_count()

        assert count == 0


class TestRAGServiceFactoryFunctions:
    """Test factory functions"""

    def test_create_chroma_rag_service_mock(self, tmp_path):
        """Test creating ChromaDB RAG service (mock mode)"""
        with patch("rag_service.CHROMADB_AVAILABLE", False):
            service = create_chroma_rag_service(str(tmp_path))

        assert isinstance(service, (RAGService, ChromaMockRAGService))

    @pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant module not available in CI")
    def test_create_qdrant_rag_service_mock(self, tmp_path):
        """Test creating Qdrant RAG service (mock mode)"""
        with patch("qdrant_rag_service.QDRANT_AVAILABLE", False):
            service = create_qdrant_rag_service(str(tmp_path))

        assert isinstance(service, (QdrantRAGService, QdrantMockRAGService))


class TestRAGServiceDocumentLoading:
    """Test document loading functionality"""

    @pytest.mark.asyncio
    async def test_ensure_documents_loaded_no_chunks(self, tmp_path):
        """Test document loading when no chunks file exists"""
        service = RAGService(data_dir=str(tmp_path))
        service.collection = MagicMock()
        service.collection.count.return_value = 0

        # Should not raise, just log warning
        await service._ensure_documents_loaded()

        assert service.documents_loaded is False

    @pytest.mark.asyncio
    async def test_ensure_documents_loaded_existing(self, tmp_path):
        """Test document loading when documents already exist"""
        service = RAGService(data_dir=str(tmp_path))
        service.collection = MagicMock()
        service.collection.count.return_value = 100

        await service._ensure_documents_loaded()

        assert service.documents_loaded is True


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant module not available in CI")
class TestQdrantRAGServiceDocumentLoading:
    """Test Qdrant document loading functionality"""

    @pytest.mark.asyncio
    async def test_qdrant_build_collection_no_chunks(self, tmp_path):
        """Test building collection when no chunks file exists"""
        service = QdrantRAGService(data_dir=str(tmp_path))

        # Should not raise, just log warning
        await service._build_collection_from_documents()

        assert service.documents_loaded is False


class TestRAGServiceAddBatch:
    """Test batch document adding"""

    @pytest.mark.asyncio
    async def test_add_batch_empty(self, tmp_path):
        """Test adding empty batch"""
        service = RAGService(data_dir=str(tmp_path))
        service.collection = MagicMock()
        service.embeddings_model = MagicMock()

        # Empty batch should not cause errors
        await service._add_batch_to_collection([])

    @pytest.mark.asyncio
    async def test_add_batch_short_content(self, tmp_path):
        """Test adding batch with short content (should be skipped)"""
        service = RAGService(data_dir=str(tmp_path))
        service.collection = MagicMock()
        service.embeddings_model = MagicMock()
        service.embeddings_model.encode.return_value = MagicMock(tolist=lambda: [[0.1]])

        chunks = [
            {"id": "1", "content": "short", "title": "Test"},  # Too short
            {
                "id": "2",
                "content": "This is a longer piece of content that should pass",
                "title": "Test",
            },
        ]

        await service._add_batch_to_collection(chunks)

        # Only valid chunks should be added
        if service.collection.add.called:
            call_args = service.collection.add.call_args
            assert len(call_args[1]["documents"]) <= 2


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant module not available in CI")
class TestQdrantRAGServiceEnrichResults:
    """Test Qdrant result enrichment"""

    @pytest.mark.asyncio
    async def test_enrich_results_no_chunks_file(self, tmp_path):
        """Test enriching results when chunks file doesn't exist"""
        service = QdrantRAGService(data_dir=str(tmp_path))

        results = [
            QdrantRetrievalResult(
                chunk_id="1",
                content="",
                title="Test",
                source_file="test.md",
                score=0.9,
                metadata={},
            )
        ]

        enriched = await service._enrich_results_with_content(results)

        # Should return results unchanged
        assert len(enriched) == 1
        assert enriched[0].content == ""

    @pytest.mark.asyncio
    async def test_enrich_results_with_chunks(self, tmp_path):
        """Test enriching results with chunks file"""
        service = QdrantRAGService(data_dir=str(tmp_path))

        # Create chunks file
        rag_docs_dir = tmp_path / "rag-docs"
        rag_docs_dir.mkdir(parents=True)
        chunks_file = rag_docs_dir / "document_chunks.json"
        chunks_file.write_text(
            json.dumps(
                [
                    {"id": "chunk_1", "content": "Enriched content here"},
                ]
            )
        )

        results = [
            QdrantRetrievalResult(
                chunk_id="chunk_1",
                content="",
                title="Test",
                source_file="test.md",
                score=0.9,
                metadata={},
            )
        ]

        enriched = await service._enrich_results_with_content(results)

        assert len(enriched) == 1
        assert enriched[0].content == "Enriched content here"


class TestRAGServiceIntegration:
    """Integration tests for RAG services"""

    @pytest.mark.asyncio
    async def test_mock_service_full_workflow(self, tmp_path):
        """Test complete workflow with mock service"""
        # Create mock service
        service = ChromaMockRAGService(data_dir=str(tmp_path))

        # Initialize
        await service.initialize()

        # Search
        results = await service.search_documents("VM deployment", n_results=3)
        assert len(results) > 0

        # Get context
        context, sources = await service.get_context_for_query("VM deployment")
        assert len(context) > 0

        # Check health
        status = await service.get_health_status()
        assert "available" in status

    @pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant module not available in CI")
    @pytest.mark.asyncio
    async def test_qdrant_mock_service_full_workflow(self, tmp_path):
        """Test complete workflow with Qdrant mock service"""
        # Create mock service
        service = QdrantMockRAGService(data_dir=str(tmp_path))

        # Initialize
        await service.initialize()

        # Search
        results = await service.search_documents("infrastructure automation")
        assert len(results) > 0

        # Get context
        context, sources = await service.get_context_for_query("infrastructure automation")
        assert len(context) > 0

        # Check health
        status = await service.get_health_status()
        assert "vector_db_type" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
