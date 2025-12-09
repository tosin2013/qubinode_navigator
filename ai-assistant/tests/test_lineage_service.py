"""
Tests for Marquez Context Service (lineage_service.py)
Tests OpenLineage integration and lineage context retrieval
"""

import pytest
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from marquez_context_service import (
    MarquezContextService,
    get_marquez_service,
    create_marquez_service,
)


class TestMarquezContextServiceInit:
    """Test MarquezContextService initialization"""

    def test_service_creation_with_url(self):
        """Test creating service with explicit URL"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        assert service.marquez_url == "http://test.com:5001"
        assert service.namespace == "qubinode"
        assert service.client is not None

    def test_service_creation_default(self):
        """Test creating service with defaults"""
        with patch.dict(os.environ, {}, clear=True):
            service = MarquezContextService()
            
            assert service.marquez_url is None
            assert service.namespace == "qubinode"

    def test_service_creation_with_env_vars(self):
        """Test creating service with environment variables"""
        with patch.dict(os.environ, {
            "MARQUEZ_API_URL": "http://env.com:5001",
            "OPENLINEAGE_NAMESPACE": "test_namespace"
        }):
            service = MarquezContextService()
            
            assert service.marquez_url == "http://env.com:5001"
            assert service.namespace == "test_namespace"

    def test_default_hosts_configured(self):
        """Test that default hosts are configured"""
        service = MarquezContextService()
        
        assert len(service.DEFAULT_HOSTS) > 0
        assert "localhost" in service.DEFAULT_HOSTS


class TestMarquezContextServiceDiscovery:
    """Test Marquez URL discovery"""

    @pytest.mark.asyncio
    async def test_discover_marquez_url_success(self):
        """Test successful URL discovery"""
        service = MarquezContextService()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            url = await service._discover_marquez_url()
            
            assert url is not None
            assert service._discovered_url == url

    @pytest.mark.asyncio
    async def test_discover_marquez_url_cached(self):
        """Test that discovered URL is cached"""
        service = MarquezContextService()
        service._discovered_url = "http://cached.com:5001"
        
        url = await service._discover_marquez_url()
        
        assert url == "http://cached.com:5001"

    @pytest.mark.asyncio
    async def test_discover_marquez_url_explicit_url(self):
        """Test discovery returns explicit URL"""
        service = MarquezContextService(marquez_url="http://explicit.com:5001")
        
        url = await service._discover_marquez_url()
        
        assert url == "http://explicit.com:5001"

    @pytest.mark.asyncio
    async def test_discover_marquez_url_not_found(self):
        """Test URL discovery when Marquez not available"""
        service = MarquezContextService()
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            
            url = await service._discover_marquez_url()
            
            assert url is None


class TestMarquezContextServiceAvailability:
    """Test is_available checks"""

    @pytest.mark.asyncio
    async def test_is_available_true(self):
        """Test when Marquez is available"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            available = await service.is_available()
            
            assert available is True

    @pytest.mark.asyncio
    async def test_is_available_false_no_url(self):
        """Test when no URL discovered"""
        service = MarquezContextService()
        
        with patch.object(service, '_discover_marquez_url', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = None
            
            available = await service.is_available()
            
            assert available is False

    @pytest.mark.asyncio
    async def test_is_available_false_error(self):
        """Test when connection fails"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection error")
            
            available = await service.is_available()
            
            assert available is False


class TestMarquezContextServiceRecentRuns:
    """Test recent runs retrieval"""

    @pytest.mark.asyncio
    async def test_get_recent_runs_success(self):
        """Test getting recent runs"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        mock_jobs_response = MagicMock()
        mock_jobs_response.status_code = 200
        mock_jobs_response.json.return_value = {
            "jobs": [
                {"name": "test_job_1"},
                {"name": "test_job_2"}
            ]
        }
        
        mock_runs_response = MagicMock()
        mock_runs_response.status_code = 200
        mock_runs_response.json.return_value = {
            "runs": [
                {
                    "id": "run_1",
                    "state": "COMPLETED",
                    "startedAt": "2024-01-01T00:00:00Z",
                    "endedAt": "2024-01-01T00:01:00Z",
                    "durationMs": 60000
                }
            ]
        }
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [mock_jobs_response, mock_runs_response, mock_runs_response]
            
            runs = await service.get_recent_runs(limit=2)
            
            assert len(runs) <= 2
            if len(runs) > 0:
                assert "job_name" in runs[0]
                assert "state" in runs[0]

    @pytest.mark.asyncio
    async def test_get_recent_runs_empty(self):
        """Test getting recent runs when none exist"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jobs": []}
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            runs = await service.get_recent_runs()
            
            assert runs == []

    @pytest.mark.asyncio
    async def test_get_recent_runs_error(self):
        """Test error handling in get_recent_runs"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API error")
            
            runs = await service.get_recent_runs()
            
            assert runs == []


class TestMarquezContextServiceFailedRuns:
    """Test failed runs retrieval"""

    @pytest.mark.asyncio
    async def test_get_failed_runs(self):
        """Test getting failed runs"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        # Mock get_recent_runs
        with patch.object(service, 'get_recent_runs', new_callable=AsyncMock) as mock_recent:
            mock_recent.return_value = [
                {"state": "COMPLETED", "job_name": "job1"},
                {"state": "FAILED", "job_name": "job2"},
                {"state": "ABORTED", "job_name": "job3"},
                {"state": "RUNNING", "job_name": "job4"},
            ]
            
            failed = await service.get_failed_runs(hours=24)
            
            assert len(failed) == 2
            assert all(run["state"] in ["FAILED", "ABORTED"] for run in failed)

    @pytest.mark.asyncio
    async def test_get_failed_runs_error(self):
        """Test error handling in get_failed_runs"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        with patch.object(service, 'get_recent_runs', new_callable=AsyncMock) as mock_recent:
            mock_recent.side_effect = Exception("Error")
            
            failed = await service.get_failed_runs()
            
            assert failed == []


class TestMarquezContextServiceJobDetails:
    """Test job details retrieval"""

    @pytest.mark.asyncio
    async def test_get_job_details_success(self):
        """Test getting job details"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        mock_job_response = MagicMock()
        mock_job_response.status_code = 200
        mock_job_response.json.return_value = {
            "name": "test_job",
            "description": "Test job description",
            "inputs": [{"name": "input1"}],
            "outputs": [{"name": "output1"}],
            "latestRun": {"state": "COMPLETED"},
            "tags": ["tag1"]
        }
        
        mock_runs_response = MagicMock()
        mock_runs_response.status_code = 200
        mock_runs_response.json.return_value = {
            "runs": [
                {"state": "COMPLETED", "startedAt": "2024-01-01T00:00:00Z", "durationMs": 1000}
            ]
        }
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [mock_job_response, mock_runs_response]
            
            details = await service.get_job_details("test_job")
            
            assert details is not None
            assert details["name"] == "test_job"
            assert "recent_runs" in details

    @pytest.mark.asyncio
    async def test_get_job_details_not_found(self):
        """Test getting job details when job not found"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            details = await service.get_job_details("nonexistent_job")
            
            assert details is None

    @pytest.mark.asyncio
    async def test_get_job_details_error(self):
        """Test error handling in get_job_details"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API error")
            
            details = await service.get_job_details("test_job")
            
            assert details is None


class TestMarquezContextServiceLineageSummary:
    """Test lineage summary"""

    @pytest.mark.asyncio
    async def test_get_lineage_summary_success(self):
        """Test getting lineage summary"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        mock_ns_response = MagicMock()
        mock_ns_response.status_code = 200
        
        mock_jobs_response = MagicMock()
        mock_jobs_response.status_code = 200
        mock_jobs_response.json.return_value = {
            "jobs": [
                {
                    "name": "job1",
                    "latestRun": {"state": "COMPLETED"}
                },
                {
                    "name": "job2",
                    "latestRun": {"state": "RUNNING"}
                },
                {
                    "name": "job3",
                    "latestRun": {"state": "FAILED"}
                }
            ]
        }
        
        with patch.object(service, 'is_available', new_callable=AsyncMock) as mock_available:
            mock_available.return_value = True
            
            with patch.object(service, 'get_failed_runs', new_callable=AsyncMock) as mock_failed:
                mock_failed.return_value = [
                    {"job_name": "job3", "state": "FAILED", "started_at": "2024-01-01T00:00:00Z"}
                ]
                
                with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
                    mock_get.side_effect = [mock_ns_response, mock_jobs_response]
                    
                    summary = await service.get_lineage_summary()
                    
                    assert summary["available"] is True
                    assert "job_stats" in summary
                    assert summary["job_stats"]["total"] == 3

    @pytest.mark.asyncio
    async def test_get_lineage_summary_not_available(self):
        """Test lineage summary when service not available"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        with patch.object(service, 'is_available', new_callable=AsyncMock) as mock_available:
            mock_available.return_value = False
            
            summary = await service.get_lineage_summary()
            
            assert summary["available"] is False

    @pytest.mark.asyncio
    async def test_get_lineage_summary_error(self):
        """Test error handling in lineage summary"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        with patch.object(service, 'is_available', new_callable=AsyncMock) as mock_available:
            mock_available.side_effect = Exception("Error")
            
            summary = await service.get_lineage_summary()
            
            assert summary["available"] is False
            assert "error" in summary


class TestMarquezContextServiceSearchJobs:
    """Test job search"""

    @pytest.mark.asyncio
    async def test_search_jobs_success(self):
        """Test searching for jobs"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jobs": [
                {"name": "freeipa_deployment", "latestRun": {"state": "COMPLETED"}},
                {"name": "freeipa_test", "latestRun": {"state": "RUNNING"}},
                {"name": "other_job", "latestRun": {"state": "COMPLETED"}},
            ]
        }
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            matches = await service.search_jobs("freeipa")
            
            assert len(matches) == 2
            assert all("freeipa" in match["name"] for match in matches)

    @pytest.mark.asyncio
    async def test_search_jobs_no_matches(self):
        """Test searching with no matches"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jobs": []}
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            matches = await service.search_jobs("nonexistent")
            
            assert matches == []

    @pytest.mark.asyncio
    async def test_search_jobs_error(self):
        """Test error handling in search"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API error")
            
            matches = await service.search_jobs("test")
            
            assert matches == []


class TestMarquezContextServicePromptContext:
    """Test context generation for AI prompts"""

    @pytest.mark.asyncio
    async def test_get_context_for_prompt_available(self):
        """Test generating context for prompt"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        mock_summary = {
            "available": True,
            "job_stats": {"total": 5, "running": 1, "completed": 3, "failed": 1},
            "recent_failures": [
                {"job": "failed_job", "state": "FAILED"}
            ]
        }
        
        with patch.object(service, 'get_lineage_summary', new_callable=AsyncMock) as mock_summary_call:
            mock_summary_call.return_value = mock_summary
            
            with patch.object(service, 'search_jobs', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = [
                    {"name": "freeipa_deployment", "latest_state": "COMPLETED"}
                ]
                
                context = await service.get_context_for_prompt("How is freeipa deployment going?")
                
                assert len(context) > 0
                assert "Infrastructure Lineage Context" in context
                assert "freeipa" in context.lower()

    @pytest.mark.asyncio
    async def test_get_context_for_prompt_not_available(self):
        """Test context when service not available"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        mock_summary = {"available": False}
        
        with patch.object(service, 'get_lineage_summary', new_callable=AsyncMock) as mock_summary_call:
            mock_summary_call.return_value = mock_summary
            
            context = await service.get_context_for_prompt("Test message")
            
            assert context == ""

    @pytest.mark.asyncio
    async def test_get_context_for_prompt_keyword_matching(self):
        """Test that context includes relevant job matches"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        mock_summary = {
            "available": True,
            "job_stats": {"total": 1, "running": 0, "completed": 1, "failed": 0},
            "recent_failures": []
        }
        
        with patch.object(service, 'get_lineage_summary', new_callable=AsyncMock) as mock_summary_call:
            mock_summary_call.return_value = mock_summary
            
            with patch.object(service, 'search_jobs', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = [
                    {"name": "vm_deployment", "latest_state": "COMPLETED"}
                ]
                
                context = await service.get_context_for_prompt("Tell me about VM deployments")
                
                assert "vm_deployment" in context

    @pytest.mark.asyncio
    async def test_get_context_for_prompt_error(self):
        """Test error handling in context generation"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        with patch.object(service, 'get_lineage_summary', new_callable=AsyncMock) as mock_summary:
            mock_summary.side_effect = Exception("Error")
            
            context = await service.get_context_for_prompt("Test")
            
            assert context == ""


class TestMarquezContextServiceClose:
    """Test service cleanup"""

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing the service"""
        service = MarquezContextService(marquez_url="http://test.com:5001")
        
        with patch.object(service.client, 'aclose', new_callable=AsyncMock) as mock_close:
            await service.close()
            
            mock_close.assert_called_once()


class TestMarquezContextServiceFactory:
    """Test factory functions"""

    def test_get_marquez_service_singleton(self):
        """Test that get_marquez_service returns singleton"""
        service1 = get_marquez_service()
        service2 = get_marquez_service()
        
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_create_marquez_service(self):
        """Test creating new service instance"""
        service = await create_marquez_service("http://test.com:5001")
        
        assert service is not None
        assert service.marquez_url == "http://test.com:5001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
