"""
Tests for Qdrant RAG Service (qdrant_rag_service.py)
Tests document retrieval, embedding, and context generation

Note: Tests run with real classes when Qdrant client is available.
"""

import pytest
import os
import sys
import json
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import dataclass
from typing import Dict, Any

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# Define RetrievalResult dataclass for testing without importing
@dataclass
class MockRetrievalResult:
    """Result from document retrieval for testing"""

    chunk_id: str
    content: str
    title: str
    source_file: str
    score: float
    metadata: Dict[str, Any]


# Try to import Qdrant service
QDRANT_AVAILABLE = False
QdrantRAGService = None
MockRAGService = None
create_rag_service = None
RetrievalResult = None

try:
    from qdrant_rag_service import (
        QdrantRAGService,
        MockRAGService,
        RetrievalResult,
        create_rag_service,
    )

    QDRANT_AVAILABLE = True
except ImportError:
    pass


class TestRetrievalResultDataclass:
    """Test RetrievalResult dataclass structure"""

    def test_retrieval_result_creation(self):
        """Test creating a RetrievalResult instance"""
        result = MockRetrievalResult(
            chunk_id="chunk_001",
            content="Test content for retrieval",
            title="Test Title",
            source_file="docs/test.md",
            score=0.95,
            metadata={"document_type": "guide"},
        )

        assert result.chunk_id == "chunk_001"
        assert result.content == "Test content for retrieval"
        assert result.title == "Test Title"
        assert result.source_file == "docs/test.md"
        assert result.score == 0.95
        assert result.metadata["document_type"] == "guide"


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant client not available")
class TestQdrantRAGServiceInit:
    """Test QdrantRAGService initialization"""

    def test_service_creation(self, tmp_path):
        """Test creating QdrantRAGService instance"""
        from pathlib import Path

        service = QdrantRAGService(data_dir=str(tmp_path))

        assert service.data_dir == Path(tmp_path)
        assert service.client is None
        assert service.collection_name == "qubinode_docs"
        assert service.documents_loaded is False

    def test_service_directories_created(self, tmp_path):
        """Test that required directories are created"""
        service = QdrantRAGService(data_dir=str(tmp_path))

        assert service.vector_db_dir.exists()

    def test_model_name(self, tmp_path):
        """Test embedding model name is set"""
        service = QdrantRAGService(data_dir=str(tmp_path))

        assert "bge-small" in service.model_name.lower()


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant client not available")
class TestMockRAGService:
    """Test MockRAGService for development/testing"""

    @pytest.mark.asyncio
    async def test_mock_initialize(self, tmp_path):
        """Test mock service initialization"""
        service = MockRAGService(data_dir=str(tmp_path))
        result = await service.initialize()

        assert result is True

    @pytest.mark.asyncio
    async def test_mock_search(self, tmp_path):
        """Test mock service search returns results"""
        service = MockRAGService(data_dir=str(tmp_path))
        results = await service.search_documents("test query", n_results=3)

        assert len(results) >= 1
        assert results[0].score > 0

    @pytest.mark.asyncio
    async def test_mock_get_context(self, tmp_path):
        """Test mock service get_context_for_query"""
        service = MockRAGService(data_dir=str(tmp_path))
        context, sources = await service.get_context_for_query("test query")

        assert len(context) > 0
        assert len(sources) > 0

    @pytest.mark.asyncio
    async def test_mock_health_status(self, tmp_path):
        """Test mock service health status"""
        service = MockRAGService(data_dir=str(tmp_path))
        status = await service.get_health_status()

        assert status["available"] is False
        assert "Mock" in status.get("vector_db_type", "Mock")


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant client not available")
class TestQdrantRAGServiceSearch:
    """Test document search functionality"""

    @pytest.mark.asyncio
    async def test_search_not_initialized(self, tmp_path):
        """Test search returns empty when not initialized"""
        service = QdrantRAGService(data_dir=str(tmp_path))
        results = await service.search_documents("test query")

        assert results == []

    def test_get_document_count_not_initialized(self, tmp_path):
        """Test document count when not initialized"""
        service = QdrantRAGService(data_dir=str(tmp_path))
        count = service._get_document_count()

        assert count == 0


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant client not available")
class TestQdrantRAGServiceContext:
    """Test context retrieval functionality"""

    @pytest.mark.asyncio
    async def test_get_context_empty_results(self, tmp_path):
        """Test context retrieval with no results"""
        service = QdrantRAGService(data_dir=str(tmp_path))
        context, sources = await service.get_context_for_query("obscure query")

        assert context == ""
        assert sources == []


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant client not available")
class TestQdrantRAGServiceSpecializedMethods:
    """Test specialized retrieval methods"""

    @pytest.mark.asyncio
    async def test_search_by_document_type(self, tmp_path):
        """Test searching by document type"""
        service = MockRAGService(data_dir=str(tmp_path))
        results = await service.search_by_document_type("architecture", "adr", 3)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_adr_context(self, tmp_path):
        """Test getting ADR-specific context"""
        service = MockRAGService(data_dir=str(tmp_path))
        context, sources = await service.get_adr_context("deployment architecture")

        assert isinstance(context, str)
        assert isinstance(sources, list)

    @pytest.mark.asyncio
    async def test_get_config_context(self, tmp_path):
        """Test getting config-specific context"""
        service = MockRAGService(data_dir=str(tmp_path))
        context, sources = await service.get_config_context("network settings")

        assert isinstance(context, str)
        assert isinstance(sources, list)


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant client not available")
class TestQdrantRAGServiceHealth:
    """Test health status reporting"""

    @pytest.mark.asyncio
    async def test_health_status_not_initialized(self, tmp_path):
        """Test health status when not initialized"""
        service = QdrantRAGService(data_dir=str(tmp_path))
        status = await service.get_health_status()

        assert status["initialized"] is False
        assert status["documents_loaded"] is False


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant client not available")
class TestQdrantRAGServiceFactory:
    """Test factory function"""

    def test_create_rag_service_mock_mode(self, tmp_path):
        """Test creating RAG service in mock mode"""
        with patch("qdrant_rag_service.QDRANT_AVAILABLE", False):
            service = create_rag_service(str(tmp_path))

        # Should return MockRAGService when Qdrant not available
        assert service is not None


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant client not available")
class TestQdrantRAGServiceDocumentLoading:
    """Test document loading functionality"""

    @pytest.mark.asyncio
    async def test_build_collection_no_chunks(self, tmp_path):
        """Test building collection when no chunks file exists"""
        service = QdrantRAGService(data_dir=str(tmp_path))

        # Should not raise, just log warning
        await service._build_collection_from_documents()

        assert service.documents_loaded is False


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant client not available")
class TestQdrantRAGServiceEnrichment:
    """Test result enrichment"""

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
            RetrievalResult(
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


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant client not available")
class TestQdrantRAGServiceIntegration:
    """Integration tests for Qdrant RAG service"""

    @pytest.mark.asyncio
    async def test_mock_service_full_workflow(self, tmp_path):
        """Test complete workflow with mock service"""
        service = MockRAGService(data_dir=str(tmp_path))

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
        assert "available" in status or "vector_db_type" in status


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant client not available")
class TestQdrantRAGServiceRetrieveContext:
    """Test retrieve_relevant_context method"""

    @pytest.mark.asyncio
    async def test_retrieve_relevant_context_empty(self, tmp_path):
        """Test retrieve_relevant_context with no results"""
        service = QdrantRAGService(data_dir=str(tmp_path))
        
        result = await service.retrieve_relevant_context("test query", top_k=5)
        
        assert hasattr(result, 'contexts')
        assert hasattr(result, 'sources')
        assert isinstance(result.contexts, list)
        assert isinstance(result.sources, list)

    @pytest.mark.asyncio
    async def test_retrieve_relevant_context_mock_service(self, tmp_path):
        """Test retrieve_relevant_context with mock service"""
        service = MockRAGService(data_dir=str(tmp_path))
        await service.initialize()
        
        # MockRAGService doesn't implement retrieve_relevant_context
        # Check that real QdrantRAGService has it
        real_service = QdrantRAGService(data_dir=str(tmp_path))
        assert hasattr(real_service, 'retrieve_relevant_context')


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant client not available")
class TestQdrantRAGServiceBuildCollection:
    """Test collection building"""

    @pytest.mark.asyncio
    async def test_build_collection_with_valid_chunks(self, tmp_path):
        """Test building collection with valid chunks file"""
        service = QdrantRAGService(data_dir=str(tmp_path))
        
        # Create rag-docs directory and chunks file
        rag_docs_dir = tmp_path / "rag-docs"
        rag_docs_dir.mkdir(parents=True)
        chunks_file = rag_docs_dir / "document_chunks.json"
        
        # Create valid chunks
        chunks_data = [
            {
                "id": "chunk_001",
                "content": "This is a test document about KVM virtualization with enough content to be valid.",
                "title": "KVM Guide",
                "source_file": "docs/kvm.md",
                "chunk_type": "markdown",
                "word_count": 15,
                "metadata": {"document_type": "guide"},
                "created_at": "2024-01-01T00:00:00"
            },
            {
                "id": "chunk_002",
                "content": "This is another test document about RHEL deployment with enough content.",
                "title": "RHEL Guide",
                "source_file": "docs/rhel.md",
                "chunk_type": "markdown",
                "word_count": 12,
                "metadata": {"document_type": "guide"},
                "created_at": "2024-01-01T00:00:00"
            }
        ]
        
        chunks_file.write_text(json.dumps(chunks_data))
        
        # Mock Qdrant client to avoid actual DB operations
        with patch("qdrant_rag_service.QdrantClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_embedding_size.return_value = 384
            mock_client.create_collection = MagicMock()
            mock_client.upload_collection = MagicMock()
            mock_client_class.return_value = mock_client
            
            service.client = mock_client
            
            await service._build_collection_from_documents()
            
            # Should have called create_collection and upload_collection
            mock_client.create_collection.assert_called_once()
            assert mock_client.upload_collection.call_count > 0


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant client not available")
class TestQdrantRAGServiceInitialize:
    """Test initialize method with various scenarios"""

    @pytest.mark.asyncio
    async def test_initialize_qdrant_not_available(self, tmp_path):
        """Test initialize when Qdrant not available"""
        with patch("qdrant_rag_service.QDRANT_AVAILABLE", False):
            service = QdrantRAGService(data_dir=str(tmp_path))
            
            result = await service.initialize()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_initialize_with_existing_collection(self, tmp_path):
        """Test initialize with existing collection"""
        service = QdrantRAGService(data_dir=str(tmp_path))
        
        # Mock Qdrant client
        with patch("qdrant_rag_service.QdrantClient") as mock_client_class:
            mock_client = MagicMock()
            
            # Mock get_collections to return existing collection
            mock_collection = MagicMock()
            mock_collection.name = "qubinode_docs"
            mock_collections = MagicMock()
            mock_collections.collections = [mock_collection]
            mock_client.get_collections.return_value = mock_collections
            
            # Mock get_collection
            mock_collection_info = MagicMock()
            mock_collection_info.points_count = 100
            mock_client.get_collection.return_value = mock_collection_info
            
            mock_client_class.return_value = mock_client
            
            result = await service.initialize()
            
            assert result is True
            assert service.documents_loaded is True

    @pytest.mark.asyncio
    async def test_initialize_error_handling(self, tmp_path):
        """Test initialize error handling"""
        service = QdrantRAGService(data_dir=str(tmp_path))
        
        # Mock Qdrant client to raise error
        with patch("qdrant_rag_service.QdrantClient") as mock_client_class:
            mock_client_class.side_effect = Exception("Connection error")
            
            result = await service.initialize()
            
            assert result is False


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant client not available")
class TestQdrantRAGServiceSearchWithFilters:
    """Test search with document type filters"""

    @pytest.mark.asyncio
    async def test_search_with_document_types_filter(self, tmp_path):
        """Test search with document type filtering"""
        service = QdrantRAGService(data_dir=str(tmp_path))
        service.documents_loaded = True
        
        # Mock client
        mock_client = MagicMock()
        mock_point = MagicMock()
        mock_point.id = "point_1"
        mock_point.score = 0.9
        mock_point.payload = {
            "original_id": "chunk_001",
            "content": "",
            "title": "Test Title",
            "source_file": "test.md",
            "document_type": "adr",
            "chunk_type": "markdown",
            "word_count": 100,
            "created_at": "2024-01-01T00:00:00"
        }
        
        mock_results = MagicMock()
        mock_results.points = [mock_point]
        mock_client.query_points.return_value = mock_results
        
        service.client = mock_client
        
        # Create chunks file for enrichment
        rag_docs_dir = tmp_path / "rag-docs"
        rag_docs_dir.mkdir(parents=True)
        chunks_file = rag_docs_dir / "document_chunks.json"
        chunks_data = [{"id": "chunk_001", "content": "Test content for ADR"}]
        chunks_file.write_text(json.dumps(chunks_data))
        
        results = await service.search_documents("test query", n_results=5, document_types=["adr"])
        
        # Should have applied filter
        assert mock_client.query_points.called
        call_args = mock_client.query_points.call_args
        assert "query_filter" in call_args[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
