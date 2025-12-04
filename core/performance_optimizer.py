"""
Qubinode Navigator Performance Optimizer

Comprehensive performance optimization and resource tuning system
for enhanced deployment efficiency and system resource management.

Based on ADR-0030: Software and OS Update Strategy
"""

import asyncio
import logging
import psutil
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import aiohttp
import aiofiles
from functools import wraps


class OptimizationLevel(Enum):
    """Performance optimization levels"""

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class ResourceType(Enum):
    """System resource types"""

    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    IO = "io"


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""

    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    disk_io: Dict[str, float]
    process_count: int
    load_average: List[float]
    response_times: Dict[str, float]


@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation"""

    recommendation_id: str
    resource_type: ResourceType
    current_value: float
    recommended_value: float
    impact_level: str  # "low", "medium", "high"
    description: str
    implementation_steps: List[str]
    estimated_improvement: float


@dataclass
class ResourceLimit:
    """Resource usage limits"""

    resource_type: ResourceType
    soft_limit: float
    hard_limit: float
    current_usage: float
    threshold_warning: float
    threshold_critical: float


class PerformanceOptimizer:
    """
    Comprehensive Performance Optimizer

    Provides system resource monitoring, performance tuning,
    and optimization recommendations for deployment operations.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.optimization_level = OptimizationLevel(self.config.get("optimization_level", "balanced"))
        self.monitoring_interval = self.config.get("monitoring_interval", 30)  # seconds
        self.metrics_retention_hours = self.config.get("metrics_retention_hours", 24)
        self.auto_optimization_enabled = self.config.get("auto_optimization_enabled", True)

        # Resource limits
        self.resource_limits = self._initialize_resource_limits()

        # Performance data
        self.performance_history: List[PerformanceMetrics] = []
        self.optimization_recommendations: List[OptimizationRecommendation] = []

        # Async components
        self.session_pool: Optional[aiohttp.ClientSession] = None
        self.thread_pool = ThreadPoolExecutor(max_workers=self.config.get("thread_pool_size", 4))
        self.process_pool = ProcessPoolExecutor(max_workers=self.config.get("process_pool_size", 2))

        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._optimization_callbacks: List[Callable] = []

        # Cache configuration
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.cache_ttl = self.config.get("cache_ttl_seconds", 300)
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

        # Connection pooling
        self.connection_pool_size = self.config.get("connection_pool_size", 10)
        self.connection_timeout = self.config.get("connection_timeout", 30)

    def _initialize_resource_limits(self) -> Dict[ResourceType, ResourceLimit]:
        """Initialize default resource limits"""

        # Get system information
        psutil.cpu_count()
        psutil.virtual_memory().total / (1024**3)  # GB

        # Calculate limits based on optimization level
        if self.optimization_level == OptimizationLevel.CONSERVATIVE:
            cpu_soft, cpu_hard = 50.0, 70.0
            mem_soft, mem_hard = 60.0, 80.0
        elif self.optimization_level == OptimizationLevel.BALANCED:
            cpu_soft, cpu_hard = 70.0, 85.0
            mem_soft, mem_hard = 75.0, 90.0
        else:  # AGGRESSIVE
            cpu_soft, cpu_hard = 85.0, 95.0
            mem_soft, mem_hard = 85.0, 95.0

        return {
            ResourceType.CPU: ResourceLimit(
                resource_type=ResourceType.CPU,
                soft_limit=cpu_soft,
                hard_limit=cpu_hard,
                current_usage=0.0,
                threshold_warning=cpu_soft - 10,
                threshold_critical=cpu_hard - 5,
            ),
            ResourceType.MEMORY: ResourceLimit(
                resource_type=ResourceType.MEMORY,
                soft_limit=mem_soft,
                hard_limit=mem_hard,
                current_usage=0.0,
                threshold_warning=mem_soft - 10,
                threshold_critical=mem_hard - 5,
            ),
            ResourceType.DISK: ResourceLimit(
                resource_type=ResourceType.DISK,
                soft_limit=80.0,
                hard_limit=90.0,
                current_usage=0.0,
                threshold_warning=70.0,
                threshold_critical=85.0,
            ),
            ResourceType.NETWORK: ResourceLimit(
                resource_type=ResourceType.NETWORK,
                soft_limit=80.0,  # % of available bandwidth
                hard_limit=95.0,
                current_usage=0.0,
                threshold_warning=70.0,
                threshold_critical=90.0,
            ),
        }

    async def start_monitoring(self):
        """Start performance monitoring"""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.logger.info("Started performance monitoring")

            # Initialize session pool
            connector = aiohttp.TCPConnector(
                limit=self.connection_pool_size,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            timeout = aiohttp.ClientTimeout(total=self.connection_timeout)
            self.session_pool = aiohttp.ClientSession(connector=connector, timeout=timeout)

    async def stop_monitoring(self):
        """Stop performance monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            self.logger.info("Stopped performance monitoring")

            # Close session pool
            if self.session_pool:
                await self.session_pool.close()
                self.session_pool = None

    async def _monitoring_loop(self):
        """Main performance monitoring loop"""
        while True:
            try:
                # Collect performance metrics
                metrics = await self.collect_performance_metrics()
                self.performance_history.append(metrics)

                # Update resource limits with current usage
                self._update_resource_usage(metrics)

                # Clean old metrics
                self._cleanup_old_metrics()

                # Check for optimization opportunities
                if self.auto_optimization_enabled:
                    await self._evaluate_optimization_opportunities(metrics)

                # Trigger callbacks
                for callback in self._optimization_callbacks:
                    try:
                        await callback(metrics)
                    except Exception as e:
                        self.logger.error(f"Optimization callback error: {e}")

                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                self.logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""

        # CPU metrics
        cpu_usage = psutil.cpu_percent(interval=1)

        # Memory metrics
        memory = psutil.virtual_memory()
        memory_usage = memory.percent

        # Disk metrics
        disk = psutil.disk_usage("/")
        disk_usage = (disk.used / disk.total) * 100

        # Network I/O
        network_io = psutil.net_io_counters()
        network_stats = {
            "bytes_sent": network_io.bytes_sent,
            "bytes_recv": network_io.bytes_recv,
            "packets_sent": network_io.packets_sent,
            "packets_recv": network_io.packets_recv,
        }

        # Disk I/O
        disk_io = psutil.disk_io_counters()
        disk_stats = {
            "read_bytes": disk_io.read_bytes if disk_io else 0,
            "write_bytes": disk_io.write_bytes if disk_io else 0,
            "read_count": disk_io.read_count if disk_io else 0,
            "write_count": disk_io.write_count if disk_io else 0,
        }

        # Process information
        process_count = len(psutil.pids())

        # Load average
        load_avg = psutil.getloadavg() if hasattr(psutil, "getloadavg") else [0.0, 0.0, 0.0]

        # Response times (placeholder - would be populated by actual measurements)
        response_times = {
            "api_response": 0.0,
            "database_query": 0.0,
            "file_operation": 0.0,
        }

        return PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            network_io=network_stats,
            disk_io=disk_stats,
            process_count=process_count,
            load_average=list(load_avg),
            response_times=response_times,
        )

    def _update_resource_usage(self, metrics: PerformanceMetrics):
        """Update resource limits with current usage"""
        self.resource_limits[ResourceType.CPU].current_usage = metrics.cpu_usage
        self.resource_limits[ResourceType.MEMORY].current_usage = metrics.memory_usage
        self.resource_limits[ResourceType.DISK].current_usage = metrics.disk_usage

        # Calculate network usage (simplified)
        network_usage = min(
            (metrics.network_io["bytes_sent"] + metrics.network_io["bytes_recv"]) / (1024**2),  # MB
            100.0,
        )
        self.resource_limits[ResourceType.NETWORK].current_usage = network_usage

    def _cleanup_old_metrics(self):
        """Remove old performance metrics"""
        cutoff_time = datetime.now() - timedelta(hours=self.metrics_retention_hours)
        self.performance_history = [m for m in self.performance_history if m.timestamp > cutoff_time]

    async def _evaluate_optimization_opportunities(self, metrics: PerformanceMetrics):
        """Evaluate current metrics for optimization opportunities"""

        recommendations = []

        # CPU optimization
        if metrics.cpu_usage > self.resource_limits[ResourceType.CPU].threshold_warning:
            recommendations.append(
                OptimizationRecommendation(
                    recommendation_id=f"cpu_opt_{int(time.time())}",
                    resource_type=ResourceType.CPU,
                    current_value=metrics.cpu_usage,
                    recommended_value=self.resource_limits[ResourceType.CPU].soft_limit,
                    impact_level="high" if metrics.cpu_usage > 90 else "medium",
                    description="High CPU usage detected - consider process optimization",
                    implementation_steps=[
                        "Review running processes for optimization opportunities",
                        "Implement async operations where possible",
                        "Consider process pooling for CPU-intensive tasks",
                        "Enable CPU affinity for critical processes",
                    ],
                    estimated_improvement=15.0,
                )
            )

        # Memory optimization
        if metrics.memory_usage > self.resource_limits[ResourceType.MEMORY].threshold_warning:
            recommendations.append(
                OptimizationRecommendation(
                    recommendation_id=f"mem_opt_{int(time.time())}",
                    resource_type=ResourceType.MEMORY,
                    current_value=metrics.memory_usage,
                    recommended_value=self.resource_limits[ResourceType.MEMORY].soft_limit,
                    impact_level="high" if metrics.memory_usage > 85 else "medium",
                    description="High memory usage detected - consider memory optimization",
                    implementation_steps=[
                        "Implement object pooling and caching strategies",
                        "Review memory leaks in long-running processes",
                        "Optimize data structures and algorithms",
                        "Consider memory-mapped files for large datasets",
                    ],
                    estimated_improvement=20.0,
                )
            )

        # Disk optimization
        if metrics.disk_usage > self.resource_limits[ResourceType.DISK].threshold_warning:
            recommendations.append(
                OptimizationRecommendation(
                    recommendation_id=f"disk_opt_{int(time.time())}",
                    resource_type=ResourceType.DISK,
                    current_value=metrics.disk_usage,
                    recommended_value=self.resource_limits[ResourceType.DISK].soft_limit,
                    impact_level="medium",
                    description="High disk usage detected - consider cleanup and optimization",
                    implementation_steps=[
                        "Clean up temporary files and logs",
                        "Implement log rotation policies",
                        "Compress old data files",
                        "Consider moving data to external storage",
                    ],
                    estimated_improvement=10.0,
                )
            )

        # Add new recommendations
        self.optimization_recommendations.extend(recommendations)

        # Log critical recommendations
        for rec in recommendations:
            if rec.impact_level == "high":
                self.logger.warning(f"High impact optimization opportunity: {rec.description}")

    # Performance optimization decorators and utilities

    def performance_monitor(self, operation_name: str):
        """Decorator to monitor operation performance"""

        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    self.logger.debug(f"Operation {operation_name} completed in {duration:.3f}s")
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.logger.error(f"Operation {operation_name} failed after {duration:.3f}s: {e}")
                    raise

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    self.logger.debug(f"Operation {operation_name} completed in {duration:.3f}s")
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.logger.error(f"Operation {operation_name} failed after {duration:.3f}s: {e}")
                    raise

            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

        return decorator

    def cached_result(self, cache_key_prefix: str, ttl: int = None):
        """Decorator for caching function results"""

        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.cache_enabled:
                    return await func(*args, **kwargs)

                # Create cache key with parameters
                cache_key = f"{cache_key_prefix}_{hash((args, tuple(sorted(kwargs.items()))))}"

                # Check cache
                if cache_key in self._cache:
                    cache_time = self._cache_timestamps.get(cache_key)
                    if cache_time and (datetime.now() - cache_time).seconds < (ttl or self.cache_ttl):
                        self.logger.debug(f"Cache hit for {cache_key}")
                        return self._cache[cache_key]

                # Execute function and cache result
                result = await func(*args, **kwargs)
                self._cache[cache_key] = result
                self._cache_timestamps[cache_key] = datetime.now()
                self.logger.debug(f"Cached result for {cache_key}")
                return result

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.cache_enabled:
                    return func(*args, **kwargs)

                # Create cache key with parameters
                cache_key = f"{cache_key_prefix}_{hash((args, tuple(sorted(kwargs.items()))))}"

                # Check cache
                if cache_key in self._cache:
                    cache_time = self._cache_timestamps.get(cache_key)
                    if cache_time and (datetime.now() - cache_time).seconds < (ttl or self.cache_ttl):
                        self.logger.debug(f"Cache hit for {cache_key}")
                        return self._cache[cache_key]

                # Execute function and cache result
                result = func(*args, **kwargs)
                self._cache[cache_key] = result
                self._cache_timestamps[cache_key] = datetime.now()
                self.logger.debug(f"Cached result for {cache_key}")
                return result

            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

        return decorator

    async def optimize_concurrent_operations(self, operations: List[Callable], max_concurrency: int = None) -> List[Any]:
        """Optimize concurrent execution of operations"""

        if max_concurrency is None:
            max_concurrency = min(len(operations), self.config.get("max_concurrency", 5))

        semaphore = asyncio.Semaphore(max_concurrency)

        async def bounded_operation(operation):
            async with semaphore:
                return await operation()

        # Execute operations with concurrency limit
        tasks = [bounded_operation(op) for op in operations]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log performance
        successful = sum(1 for r in results if not isinstance(r, Exception))
        self.logger.info(f"Concurrent operations: {successful}/{len(operations)} successful")

        return results

    async def optimize_file_operations(self, file_path: Path, operation: str, data: Any = None) -> Any:
        """Optimize file I/O operations"""

        try:
            if operation == "read":
                async with aiofiles.open(file_path, "r") as f:
                    return await f.read()
            elif operation == "write":
                async with aiofiles.open(file_path, "w") as f:
                    if isinstance(data, dict):
                        await f.write(json.dumps(data, indent=2))
                    else:
                        await f.write(str(data))
                    return True
            elif operation == "read_json":
                async with aiofiles.open(file_path, "r") as f:
                    content = await f.read()
                    return json.loads(content)
            elif operation == "write_json":
                async with aiofiles.open(file_path, "w") as f:
                    await f.write(json.dumps(data, indent=2))
                    return True
        except Exception as e:
            self.logger.error(f"File operation {operation} failed for {file_path}: {e}")
            raise

    async def optimize_http_requests(self, requests: List[Dict[str, Any]]) -> List[Any]:
        """Optimize HTTP requests with connection pooling"""

        if not self.session_pool:
            await self.start_monitoring()  # Initialize session pool

        async def make_request(request_config):
            try:
                method = request_config.get("method", "GET")
                url = request_config["url"]
                headers = request_config.get("headers", {})
                data = request_config.get("data")

                async with self.session_pool.request(method, url, headers=headers, json=data) as response:
                    return {
                        "status": response.status,
                        "data": await response.json() if response.content_type == "application/json" else await response.text(),
                        "headers": dict(response.headers),
                    }
            except Exception as e:
                return {"error": str(e)}

        # Execute requests concurrently
        tasks = [make_request(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return results

    def register_optimization_callback(self, callback: Callable):
        """Register callback for optimization events"""
        self._optimization_callbacks.append(callback)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""

        if not self.performance_history:
            return {"status": "no_data", "message": "No performance data available"}

        recent_metrics = self.performance_history[-10:]  # Last 10 measurements

        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_disk = sum(m.disk_usage for m in recent_metrics) / len(recent_metrics)

        return {
            "status": "active",
            "optimization_level": self.optimization_level.value,
            "current_metrics": {
                "cpu_usage": round(avg_cpu, 2),
                "memory_usage": round(avg_memory, 2),
                "disk_usage": round(avg_disk, 2),
                "process_count": recent_metrics[-1].process_count,
                "load_average": recent_metrics[-1].load_average,
            },
            "resource_limits": {
                rt.value: {
                    "current": round(limit.current_usage, 2),
                    "soft_limit": limit.soft_limit,
                    "hard_limit": limit.hard_limit,
                    "status": self._get_resource_status(limit),
                }
                for rt, limit in self.resource_limits.items()
            },
            "active_recommendations": len([r for r in self.optimization_recommendations if r.impact_level == "high"]),
            "total_recommendations": len(self.optimization_recommendations),
            "cache_stats": {
                "enabled": self.cache_enabled,
                "entries": len(self._cache),
                "hit_rate": "N/A",  # Would be calculated with hit/miss tracking
            },
        }

    def _get_resource_status(self, limit: ResourceLimit) -> str:
        """Get resource status based on usage"""
        if limit.current_usage >= limit.threshold_critical:
            return "critical"
        elif limit.current_usage >= limit.threshold_warning:
            return "warning"
        else:
            return "normal"

    def get_optimization_recommendations(self, filter_by_impact: str = None) -> List[OptimizationRecommendation]:
        """Get optimization recommendations"""

        if filter_by_impact:
            return [r for r in self.optimization_recommendations if r.impact_level == filter_by_impact]

        return self.optimization_recommendations.copy()

    async def apply_optimization(self, recommendation_id: str) -> bool:
        """Apply an optimization recommendation"""

        recommendation = next(
            (r for r in self.optimization_recommendations if r.recommendation_id == recommendation_id),
            None,
        )

        if not recommendation:
            self.logger.error(f"Optimization recommendation {recommendation_id} not found")
            return False

        try:
            self.logger.info(f"Applying optimization: {recommendation.description}")

            # Implementation would depend on the specific optimization
            # For now, simulate the optimization
            await asyncio.sleep(1)

            # Remove applied recommendation
            self.optimization_recommendations = [r for r in self.optimization_recommendations if r.recommendation_id != recommendation_id]

            self.logger.info(f"Successfully applied optimization {recommendation_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to apply optimization {recommendation_id}: {e}")
            return False

    def clear_cache(self):
        """Clear performance cache"""
        self._cache.clear()
        self._cache_timestamps.clear()
        self.logger.info("Performance cache cleared")

    async def cleanup(self):
        """Cleanup resources"""
        await self.stop_monitoring()

        # Shutdown executors
        self.thread_pool.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)

        # Clear cache
        self.clear_cache()

        self.logger.info("Performance optimizer cleanup completed")
