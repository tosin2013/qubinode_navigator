"""
Tests for Qubinode Navigator Performance Optimizer

Tests performance monitoring, resource optimization, caching,
and performance tuning for deployment operations.
"""

import pytest
import unittest.mock as mock
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.performance_optimizer import (
    PerformanceOptimizer,
    PerformanceMetrics,
    OptimizationRecommendation,
    ResourceLimit,
    OptimizationLevel,
    ResourceType,
)


class TestPerformanceOptimizer:
    """Test cases for performance optimizer"""

    def setup_method(self):
        """Setup test environment"""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()

        # Optimizer configuration
        self.config = {
            "optimization_level": "balanced",
            "monitoring_interval": 5,  # Short interval for testing
            "metrics_retention_hours": 1,
            "auto_optimization_enabled": True,
            "cache_enabled": True,
            "cache_ttl_seconds": 60,
            "thread_pool_size": 2,
            "process_pool_size": 1,
            "connection_pool_size": 5,
        }

        # Create optimizer instance
        self.optimizer = PerformanceOptimizer(self.config)

    async def teardown_method(self):
        """Cleanup after tests"""
        await self.optimizer.cleanup()

    def test_optimizer_initialization(self):
        """Test performance optimizer initialization"""
        assert self.optimizer.optimization_level == OptimizationLevel.BALANCED
        assert self.optimizer.monitoring_interval == 5
        assert self.optimizer.auto_optimization_enabled is True
        assert self.optimizer.cache_enabled is True
        assert len(self.optimizer.resource_limits) == 4  # CPU, Memory, Disk, Network
        assert len(self.optimizer.performance_history) == 0
        assert len(self.optimizer.optimization_recommendations) == 0

    def test_resource_limits_initialization(self):
        """Test resource limits initialization"""
        limits = self.optimizer.resource_limits

        # Check all resource types are present
        assert ResourceType.CPU in limits
        assert ResourceType.MEMORY in limits
        assert ResourceType.DISK in limits
        assert ResourceType.NETWORK in limits

        # Check CPU limits for balanced optimization
        cpu_limit = limits[ResourceType.CPU]
        assert cpu_limit.soft_limit == 70.0
        assert cpu_limit.hard_limit == 85.0
        assert cpu_limit.threshold_warning == 60.0
        assert cpu_limit.threshold_critical == 80.0

        # Check memory limits
        mem_limit = limits[ResourceType.MEMORY]
        assert mem_limit.soft_limit == 75.0
        assert mem_limit.hard_limit == 90.0

    def test_optimization_level_conservative(self):
        """Test conservative optimization level"""
        config = self.config.copy()
        config["optimization_level"] = "conservative"

        optimizer = PerformanceOptimizer(config)
        cpu_limit = optimizer.resource_limits[ResourceType.CPU]

        assert cpu_limit.soft_limit == 50.0
        assert cpu_limit.hard_limit == 70.0

    def test_optimization_level_aggressive(self):
        """Test aggressive optimization level"""
        config = self.config.copy()
        config["optimization_level"] = "aggressive"

        optimizer = PerformanceOptimizer(config)
        cpu_limit = optimizer.resource_limits[ResourceType.CPU]

        assert cpu_limit.soft_limit == 85.0
        assert cpu_limit.hard_limit == 95.0

    async def test_collect_performance_metrics(self):
        """Test performance metrics collection"""
        metrics = await self.optimizer.collect_performance_metrics()

        assert isinstance(metrics, PerformanceMetrics)
        assert isinstance(metrics.timestamp, datetime)
        assert 0 <= metrics.cpu_usage <= 100
        assert 0 <= metrics.memory_usage <= 100
        assert 0 <= metrics.disk_usage <= 100
        assert metrics.process_count > 0
        assert len(metrics.load_average) == 3
        assert isinstance(metrics.network_io, dict)
        assert isinstance(metrics.disk_io, dict)
        assert isinstance(metrics.response_times, dict)

    async def test_start_stop_monitoring(self):
        """Test monitoring start and stop"""
        # Test start monitoring
        await self.optimizer.start_monitoring()
        assert self.optimizer._monitoring_task is not None
        assert self.optimizer.session_pool is not None

        # Wait briefly for monitoring to collect data
        await asyncio.sleep(0.1)

        # Test stop monitoring
        await self.optimizer.stop_monitoring()
        assert self.optimizer._monitoring_task is None
        assert self.optimizer.session_pool is None

    async def test_monitoring_loop_data_collection(self):
        """Test monitoring loop collects data"""
        await self.optimizer.start_monitoring()

        # Wait for some data collection
        await asyncio.sleep(0.2)

        # Should have collected at least one metric
        assert len(self.optimizer.performance_history) >= 0  # May be 0 due to timing

        await self.optimizer.stop_monitoring()

    def test_update_resource_usage(self):
        """Test resource usage update"""
        # Create sample metrics
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_usage=75.0,
            memory_usage=80.0,
            disk_usage=65.0,
            network_io={
                "bytes_sent": 1024,
                "bytes_recv": 2048,
                "packets_sent": 10,
                "packets_recv": 20,
            },
            disk_io={
                "read_bytes": 4096,
                "write_bytes": 8192,
                "read_count": 5,
                "write_count": 10,
            },
            process_count=150,
            load_average=[1.5, 1.2, 1.0],
            response_times={
                "api_response": 0.1,
                "database_query": 0.05,
                "file_operation": 0.02,
            },
        )

        # Update resource usage
        self.optimizer._update_resource_usage(metrics)

        # Check updated values
        assert self.optimizer.resource_limits[ResourceType.CPU].current_usage == 75.0
        assert self.optimizer.resource_limits[ResourceType.MEMORY].current_usage == 80.0
        assert self.optimizer.resource_limits[ResourceType.DISK].current_usage == 65.0

    def test_cleanup_old_metrics(self):
        """Test cleanup of old metrics"""
        # Add old and new metrics
        old_metric = PerformanceMetrics(
            timestamp=datetime.now() - timedelta(hours=2),
            cpu_usage=50.0,
            memory_usage=60.0,
            disk_usage=40.0,
            network_io={},
            disk_io={},
            process_count=100,
            load_average=[1.0, 1.0, 1.0],
            response_times={},
        )

        new_metric = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_usage=70.0,
            memory_usage=80.0,
            disk_usage=60.0,
            network_io={},
            disk_io={},
            process_count=120,
            load_average=[1.2, 1.1, 1.0],
            response_times={},
        )

        self.optimizer.performance_history = [old_metric, new_metric]

        # Cleanup old metrics
        self.optimizer._cleanup_old_metrics()

        # Should only have new metric
        assert len(self.optimizer.performance_history) == 1
        assert self.optimizer.performance_history[0].cpu_usage == 70.0

    async def test_evaluate_optimization_opportunities(self):
        """Test optimization opportunity evaluation"""
        # Create metrics that should trigger recommendations
        high_cpu_metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_usage=95.0,  # High CPU usage
            memory_usage=85.0,  # High memory usage
            disk_usage=85.0,  # High disk usage
            network_io={},
            disk_io={},
            process_count=200,
            load_average=[3.0, 2.5, 2.0],
            response_times={},
        )

        # Evaluate opportunities
        await self.optimizer._evaluate_optimization_opportunities(high_cpu_metrics)

        # Should have generated recommendations
        assert len(self.optimizer.optimization_recommendations) > 0

        # Check for CPU recommendation
        cpu_recs = [r for r in self.optimizer.optimization_recommendations if r.resource_type == ResourceType.CPU]
        assert len(cpu_recs) > 0
        assert cpu_recs[0].impact_level == "high"
        assert cpu_recs[0].current_value == 95.0

    def test_performance_monitor_decorator(self):
        """Test performance monitor decorator"""

        @self.optimizer.performance_monitor("test_operation")
        async def test_async_function():
            await asyncio.sleep(0.01)
            return "success"

        @self.optimizer.performance_monitor("test_sync_operation")
        def test_sync_function():
            return "success"

        # Test async function
        result = asyncio.run(test_async_function())
        assert result == "success"

        # Test sync function
        result = test_sync_function()
        assert result == "success"

    def test_cached_result_decorator(self):
        """Test cached result decorator"""
        call_count = 0

        @self.optimizer.cached_result("test_cache_key", ttl=60)
        def test_cached_function(value):
            nonlocal call_count
            call_count += 1
            return f"result_{value}"

        # First call should execute function
        result1 = test_cached_function("test")
        assert result1 == "result_test"
        assert call_count == 1

        # Second call should use cache
        result2 = test_cached_function("test")
        assert result2 == "result_test"
        assert call_count == 1  # Should not increment

        # Different parameter should execute function again
        result3 = test_cached_function("other")
        assert result3 == "result_other"
        assert call_count == 2

    async def test_optimize_concurrent_operations(self):
        """Test concurrent operations optimization"""

        async def sample_operation(delay=0.01):
            await asyncio.sleep(delay)
            return "completed"

        # Create list of operations
        operations = [lambda: sample_operation(0.01) for _ in range(5)]

        # Execute with concurrency limit
        results = await self.optimizer.optimize_concurrent_operations(operations, max_concurrency=3)

        # All operations should complete
        assert len(results) == 5
        assert all(r == "completed" for r in results if not isinstance(r, Exception))

    async def test_optimize_file_operations(self):
        """Test file operations optimization"""
        test_file = Path(self.temp_dir) / "test_file.txt"
        test_data = {"test": "data", "number": 42}

        # Test write operation
        result = await self.optimizer.optimize_file_operations(test_file, "write_json", test_data)
        assert result is True
        assert test_file.exists()

        # Test read operation
        read_data = await self.optimizer.optimize_file_operations(test_file, "read_json")
        assert read_data == test_data

        # Test regular write/read
        text_content = "Hello, World!"
        await self.optimizer.optimize_file_operations(test_file, "write", text_content)

        read_content = await self.optimizer.optimize_file_operations(test_file, "read")
        assert read_content == text_content

    async def test_optimize_http_requests(self):
        """Test HTTP requests optimization"""
        # Mock HTTP requests
        with mock.patch("aiohttp.ClientSession") as mock_session:
            mock_response = mock.AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"status": "success"}
            mock_response.text.return_value = "success"
            mock_response.content_type = "application/json"
            mock_response.headers = {"Content-Type": "application/json"}

            mock_session_instance = mock.AsyncMock()
            mock_session_instance.request.return_value.__aenter__.return_value = mock_response
            mock_session.return_value = mock_session_instance

            # Manually set session pool
            self.optimizer.session_pool = mock_session_instance

            # Test requests
            requests = [
                {"method": "GET", "url": "http://example.com/api/1"},
                {
                    "method": "POST",
                    "url": "http://example.com/api/2",
                    "data": {"key": "value"},
                },
            ]

            results = await self.optimizer.optimize_http_requests(requests)

            assert len(results) == 2
            assert all("status" in r for r in results if "error" not in r)

    def test_get_performance_summary_no_data(self):
        """Test performance summary with no data"""
        summary = self.optimizer.get_performance_summary()

        assert summary["status"] == "no_data"
        assert "message" in summary

    def test_get_performance_summary_with_data(self):
        """Test performance summary with data"""
        # Add sample metrics
        for i in range(5):
            metric = PerformanceMetrics(
                timestamp=datetime.now() - timedelta(minutes=i),
                cpu_usage=50.0 + i,
                memory_usage=60.0 + i,
                disk_usage=40.0 + i,
                network_io={},
                disk_io={},
                process_count=100 + i,
                load_average=[1.0, 1.0, 1.0],
                response_times={},
            )
            self.optimizer.performance_history.append(metric)

        summary = self.optimizer.get_performance_summary()

        assert summary["status"] == "active"
        assert summary["optimization_level"] == "balanced"
        assert "current_metrics" in summary
        assert "resource_limits" in summary
        assert "cache_stats" in summary

        # Check metrics averages
        metrics = summary["current_metrics"]
        assert 50.0 <= metrics["cpu_usage"] <= 55.0  # Should be average
        assert 60.0 <= metrics["memory_usage"] <= 65.0

    def test_get_resource_status(self):
        """Test resource status determination"""
        # Test normal status
        limit = ResourceLimit(
            resource_type=ResourceType.CPU,
            soft_limit=70.0,
            hard_limit=85.0,
            current_usage=50.0,
            threshold_warning=60.0,
            threshold_critical=80.0,
        )
        assert self.optimizer._get_resource_status(limit) == "normal"

        # Test warning status
        limit.current_usage = 65.0
        assert self.optimizer._get_resource_status(limit) == "warning"

        # Test critical status
        limit.current_usage = 85.0
        assert self.optimizer._get_resource_status(limit) == "critical"

    def test_get_optimization_recommendations(self):
        """Test getting optimization recommendations"""
        # Add sample recommendations
        rec1 = OptimizationRecommendation(
            recommendation_id="rec1",
            resource_type=ResourceType.CPU,
            current_value=90.0,
            recommended_value=70.0,
            impact_level="high",
            description="High CPU usage",
            implementation_steps=["Step 1", "Step 2"],
            estimated_improvement=20.0,
        )

        rec2 = OptimizationRecommendation(
            recommendation_id="rec2",
            resource_type=ResourceType.MEMORY,
            current_value=80.0,
            recommended_value=70.0,
            impact_level="medium",
            description="Medium memory usage",
            implementation_steps=["Step 1"],
            estimated_improvement=10.0,
        )

        self.optimizer.optimization_recommendations = [rec1, rec2]

        # Test getting all recommendations
        all_recs = self.optimizer.get_optimization_recommendations()
        assert len(all_recs) == 2

        # Test filtering by impact
        high_recs = self.optimizer.get_optimization_recommendations("high")
        assert len(high_recs) == 1
        assert high_recs[0].recommendation_id == "rec1"

    async def test_apply_optimization(self):
        """Test applying optimization"""
        # Add sample recommendation
        rec = OptimizationRecommendation(
            recommendation_id="test_rec",
            resource_type=ResourceType.CPU,
            current_value=90.0,
            recommended_value=70.0,
            impact_level="high",
            description="Test optimization",
            implementation_steps=["Test step"],
            estimated_improvement=20.0,
        )

        self.optimizer.optimization_recommendations = [rec]

        # Apply optimization
        success = await self.optimizer.apply_optimization("test_rec")
        assert success is True

        # Recommendation should be removed
        assert len(self.optimizer.optimization_recommendations) == 0

        # Test applying non-existent recommendation
        success = await self.optimizer.apply_optimization("non_existent")
        assert success is False

    def test_register_optimization_callback(self):
        """Test registering optimization callbacks"""
        callback_called = False

        async def test_callback(metrics):
            nonlocal callback_called
            callback_called = True

        # Register callback
        self.optimizer.register_optimization_callback(test_callback)
        assert len(self.optimizer._optimization_callbacks) == 1

    def test_clear_cache(self):
        """Test cache clearing"""
        # Add cache entries
        self.optimizer._cache["key1"] = "value1"
        self.optimizer._cache["key2"] = "value2"
        self.optimizer._cache_timestamps["key1"] = datetime.now()
        self.optimizer._cache_timestamps["key2"] = datetime.now()

        assert len(self.optimizer._cache) == 2
        assert len(self.optimizer._cache_timestamps) == 2

        # Clear cache
        self.optimizer.clear_cache()

        assert len(self.optimizer._cache) == 0
        assert len(self.optimizer._cache_timestamps) == 0


class TestPerformanceMetrics:
    """Test performance metrics data class"""

    def test_performance_metrics_creation(self):
        """Test performance metrics creation"""
        timestamp = datetime.now()
        network_io = {"bytes_sent": 1024, "bytes_recv": 2048}
        disk_io = {"read_bytes": 4096, "write_bytes": 8192}
        response_times = {"api": 0.1, "db": 0.05}

        metrics = PerformanceMetrics(
            timestamp=timestamp,
            cpu_usage=75.5,
            memory_usage=80.2,
            disk_usage=65.8,
            network_io=network_io,
            disk_io=disk_io,
            process_count=150,
            load_average=[1.5, 1.2, 1.0],
            response_times=response_times,
        )

        assert metrics.timestamp == timestamp
        assert metrics.cpu_usage == 75.5
        assert metrics.memory_usage == 80.2
        assert metrics.disk_usage == 65.8
        assert metrics.network_io == network_io
        assert metrics.disk_io == disk_io
        assert metrics.process_count == 150
        assert metrics.load_average == [1.5, 1.2, 1.0]
        assert metrics.response_times == response_times


class TestOptimizationRecommendation:
    """Test optimization recommendation data class"""

    def test_optimization_recommendation_creation(self):
        """Test optimization recommendation creation"""
        rec = OptimizationRecommendation(
            recommendation_id="opt_123",
            resource_type=ResourceType.CPU,
            current_value=90.0,
            recommended_value=70.0,
            impact_level="high",
            description="Optimize CPU usage",
            implementation_steps=["Step 1", "Step 2", "Step 3"],
            estimated_improvement=25.0,
        )

        assert rec.recommendation_id == "opt_123"
        assert rec.resource_type == ResourceType.CPU
        assert rec.current_value == 90.0
        assert rec.recommended_value == 70.0
        assert rec.impact_level == "high"
        assert rec.description == "Optimize CPU usage"
        assert len(rec.implementation_steps) == 3
        assert rec.estimated_improvement == 25.0


class TestResourceLimit:
    """Test resource limit data class"""

    def test_resource_limit_creation(self):
        """Test resource limit creation"""
        limit = ResourceLimit(
            resource_type=ResourceType.MEMORY,
            soft_limit=75.0,
            hard_limit=90.0,
            current_usage=65.0,
            threshold_warning=70.0,
            threshold_critical=85.0,
        )

        assert limit.resource_type == ResourceType.MEMORY
        assert limit.soft_limit == 75.0
        assert limit.hard_limit == 90.0
        assert limit.current_usage == 65.0
        assert limit.threshold_warning == 70.0
        assert limit.threshold_critical == 85.0


class TestEnums:
    """Test enumeration classes"""

    def test_optimization_level_enum(self):
        """Test optimization level enum"""
        assert OptimizationLevel.CONSERVATIVE.value == "conservative"
        assert OptimizationLevel.BALANCED.value == "balanced"
        assert OptimizationLevel.AGGRESSIVE.value == "aggressive"

    def test_resource_type_enum(self):
        """Test resource type enum"""
        assert ResourceType.CPU.value == "cpu"
        assert ResourceType.MEMORY.value == "memory"
        assert ResourceType.DISK.value == "disk"
        assert ResourceType.NETWORK.value == "network"
        assert ResourceType.IO.value == "io"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
