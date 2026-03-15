"""
Performance monitoring utilities for PriceSentry system.
Provides comprehensive performance metrics, monitoring, and reporting.
"""

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import psutil


class MetricType(Enum):
    """Types of performance metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """Performance metric data."""

    name: str
    type: MetricType
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "value": self.value,
            "timestamp": self.timestamp,
            "tags": self.tags,
        }


@dataclass
class PerformanceSnapshot:
    """Snapshot of system performance."""

    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    thread_count: int
    open_files: int
    network_connections: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary."""
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_available_mb": self.memory_available_mb,
            "disk_usage_percent": self.disk_usage_percent,
            "thread_count": self.thread_count,
            "open_files": self.open_files,
            "network_connections": self.network_connections,
        }


class PerformanceMonitor:
    """Performance monitoring system."""

    def __init__(self, max_history_size: int = 1000, collection_interval: float = 30.0):
        """
        Initialize performance monitor.

        Args:
            max_history_size: Maximum number of metrics to keep in history
            collection_interval: Interval for automatic system metrics collection
        """
        self.max_history_size = max_history_size
        self.collection_interval = collection_interval
        self.logger = logging.getLogger(__name__)

        # Metrics storage
        self.metrics: deque = deque(maxlen=max_history_size)
        self.system_snapshots: deque = deque(maxlen=max_history_size)

        # Custom metrics
        self.custom_metrics: Dict[str, Metric] = {}

        # Timers
        self.active_timers: Dict[str, float] = {}
        self.timer_history: Dict[str, List[float]] = {}

        # Counters
        self.counters: Dict[str, float] = {}

        # Histograms
        self.histograms: Dict[str, List[float]] = {}

        # Thread control
        self._running = False
        self._collection_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # Process info
        self.process = psutil.Process()
        self.start_time = time.time()

        self.logger.info("PerformanceMonitor initialized")

    def start(self):
        """Start performance monitoring."""
        if self._running:
            return

        self._running = True
        self._collection_thread = threading.Thread(target=self._collect_system_metrics)
        self._collection_thread.daemon = True
        self._collection_thread.start()

        self.logger.info("Performance monitoring started")

    def stop(self):
        """Stop performance monitoring."""
        if not self._running:
            return

        self._running = False
        if self._collection_thread:
            self._collection_thread.join(timeout=5)

        self.logger.info("Performance monitoring stopped")

    def _collect_system_metrics(self):
        """Collect system metrics periodically."""
        while self._running:
            try:
                snapshot = self._take_system_snapshot()
                with self._lock:
                    self.system_snapshots.append(snapshot)

                # Collect memory usage
                memory_info = self.process.memory_info()
                self.record_gauge("memory_usage_mb", memory_info.rss / 1024 / 1024)

                # Collect CPU usage
                cpu_percent = self.process.cpu_percent()
                self.record_gauge("cpu_usage_percent", cpu_percent)

                # Collect thread count
                thread_count = self.process.num_threads()
                self.record_gauge("thread_count", thread_count)

                # Collect open files count
                try:
                    open_files = (
                        self.process.num_handles()
                        if hasattr(self.process, "num_handles")
                        else len(self.process.open_files())
                    )
                    self.record_gauge("open_files_count", open_files)
                except Exception:
                    pass  # Not available on all systems

                # Collect network connections
                try:
                    connections = len(self.process.connections())
                    self.record_gauge("network_connections", connections)
                except Exception:
                    pass  # Not available on all systems

                time.sleep(self.collection_interval)

            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {e}")
                time.sleep(self.collection_interval)

    def _take_system_snapshot(self) -> PerformanceSnapshot:
        """Take a snapshot of system performance."""
        try:
            # CPU usage
            cpu_percent = self.process.cpu_percent()

            # Memory usage
            memory_info = self.process.memory_info()
            virtual_memory = psutil.virtual_memory()

            # Disk usage
            disk_usage = psutil.disk_usage("/")

            # Thread count
            thread_count = self.process.num_threads()

            # Open files
            try:
                open_files = (
                    self.process.num_handles()
                    if hasattr(self.process, "num_handles")
                    else len(self.process.open_files())
                )
            except Exception:
                open_files = 0

            # Network connections
            try:
                network_connections = len(self.process.net_connections())
            except Exception:
                network_connections = 0

            return PerformanceSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=virtual_memory.percent,
                memory_used_mb=memory_info.rss / 1024 / 1024,
                memory_available_mb=virtual_memory.available / 1024 / 1024,
                disk_usage_percent=disk_usage.percent,
                thread_count=thread_count,
                open_files=open_files,
                network_connections=network_connections,
            )
        except Exception as e:
            self.logger.error(f"Error taking system snapshot: {e}")
            # Return empty snapshot on error
            return PerformanceSnapshot(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                thread_count=0,
                open_files=0,
                network_connections=0,
            )

    def record_counter(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        Record a counter metric.

        Args:
            name: Metric name
            value: Counter value (will be added to existing)
            tags: Optional tags for the metric
        """
        with self._lock:
            if name not in self.counters:
                self.counters[name] = 0.0

            self.counters[name] += value

            metric = Metric(
                name=name,
                type=MetricType.COUNTER,
                value=self.counters[name],
                tags=tags or {},
            )

            self.metrics.append(metric)

    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        Record a gauge metric.

        Args:
            name: Metric name
            value: Gauge value (will replace existing)
            tags: Optional tags for the metric
        """
        with self._lock:
            self.custom_metrics[name] = Metric(name=name, type=MetricType.GAUGE, value=value, tags=tags or {})

            self.metrics.append(self.custom_metrics[name])

    def start_timer(self, name: str) -> str:
        """
        Start a timer.

        Args:
            name: Timer name

        Returns:
            Timer ID
        """
        timer_id = f"{name}_{time.time()}"
        with self._lock:
            self.active_timers[timer_id] = time.time()
        return timer_id

    def stop_timer(self, timer_id: str, name: str, tags: Optional[Dict[str, str]] = None):
        """
        Stop a timer and record the duration.

        Args:
            timer_id: Timer ID
            name: Timer name
            tags: Optional tags for the metric
        """
        with self._lock:
            if timer_id not in self.active_timers:
                self.logger.warning(f"Timer {timer_id} not found")
                return

            start_time = self.active_timers.pop(timer_id)
            duration = time.time() - start_time

            # Add to timer history
            if name not in self.timer_history:
                self.timer_history[name] = []
            self.timer_history[name].append(duration)

            # Keep only recent history
            if len(self.timer_history[name]) > 100:
                self.timer_history[name] = self.timer_history[name][-100:]

            # Record as histogram
            self.record_histogram(name, duration, tags)

    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        Record a histogram metric.

        Args:
            name: Metric name
            value: Value to record
            tags: Optional tags for the metric
        """
        with self._lock:
            if name not in self.histograms:
                self.histograms[name] = []

            self.histograms[name].append(value)

            # Keep only recent values
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]

            metric = Metric(name=name, type=MetricType.HISTOGRAM, value=value, tags=tags or {})

            self.metrics.append(metric)

    def time_function(self, name: str):
        """
        Decorator to time function execution.

        Args:
            name: Timer name

        Returns:
            Decorator function
        """

        def decorator(func):
            def wrapper(*args, **kwargs):
                timer_id = self.start_timer(name)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    self.stop_timer(timer_id, name)

            return wrapper

        return decorator

    def get_metrics(self, limit: Optional[int] = None) -> List[Metric]:
        """
        Get recent metrics.

        Args:
            limit: Maximum number of metrics to return

        Returns:
            List of metrics
        """
        with self._lock:
            metrics = list(self.metrics)
            if limit:
                return metrics[-limit:]
            return metrics

    def get_system_snapshots(self, limit: Optional[int] = None) -> List[PerformanceSnapshot]:
        """
        Get recent system snapshots.

        Args:
            limit: Maximum number of snapshots to return

        Returns:
            List of system snapshots
        """
        with self._lock:
            snapshots = list(self.system_snapshots)
            if limit:
                return snapshots[-limit:]
            return snapshots

    def get_timer_stats(self, name: str) -> Dict[str, float]:
        """
        Get timer statistics.

        Args:
            name: Timer name

        Returns:
            Timer statistics
        """
        with self._lock:
            if name not in self.timer_history or not self.timer_history[name]:
                return {}

            times = self.timer_history[name]
            return {
                "count": len(times),
                "min": min(times),
                "max": max(times),
                "avg": sum(times) / len(times),
                "p50": self._percentile(times, 50),
                "p95": self._percentile(times, 95),
                "p99": self._percentile(times, 99),
            }

    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """
        Get histogram statistics.

        Args:
            name: Histogram name

        Returns:
            Histogram statistics
        """
        with self._lock:
            if name not in self.histograms or not self.histograms[name]:
                return {}

            values = self.histograms[name]
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "p50": self._percentile(values, 50),
                "p95": self._percentile(values, 95),
                "p99": self._percentile(values, 99),
            }

    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics (alias for get_system_stats)."""
        # Auto-start if not running
        if not self._running:
            self.start()
            # Give it a moment to collect initial data
            import time

            time.sleep(0.1)
        return self.get_system_stats()

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system performance statistics."""
        with self._lock:
            if not self.system_snapshots:
                return {}

            snapshots = list(self.system_snapshots)

            return {
                "uptime_seconds": time.time() - self.start_time,
                "metrics_collected": len(self.metrics),
                "system_snapshots": len(snapshots),
                "active_timers": len(self.active_timers),
                "custom_metrics": len(self.custom_metrics),
                "counters": len(self.counters),
                "histograms": len(self.histograms),
                "recent_cpu_avg": sum(s.cpu_percent for s in snapshots[-10:]) / min(len(snapshots), 10),
                "recent_memory_avg_mb": sum(s.memory_used_mb for s in snapshots[-10:]) / min(len(snapshots), 10),
                "peak_memory_mb": max(s.memory_used_mb for s in snapshots) if snapshots else 0,
                "peak_cpu_percent": max(s.cpu_percent for s in snapshots) if snapshots else 0,
            }

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        with self._lock:
            report = {
                "timestamp": time.time(),
                "system_stats": self.get_system_stats(),
                "recent_metrics": [m.to_dict() for m in self.get_metrics(50)],
                "recent_system_snapshots": [s.to_dict() for s in self.get_system_snapshots(10)],
                "timer_stats": {},
                "histogram_stats": {},
                "counter_values": self.counters.copy(),
            }

            # Add timer stats
            for name in self.timer_history:
                report["timer_stats"][name] = self.get_timer_stats(name)

            # Add histogram stats
            for name in self.histograms:
                report["histogram_stats"][name] = self.get_histogram_stats(name)

            return report

    def export_metrics(self, format: str = "json") -> str:
        """
        Export metrics in specified format.

        Args:
            format: Export format ("json" or "csv")

        Returns:
            Formatted metrics string
        """
        if format.lower() == "json":
            return json.dumps(self.get_performance_report(), indent=2)
        elif format.lower() == "csv":
            return self._export_csv()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_csv(self) -> str:
        """Export metrics as CSV."""
        lines = ["timestamp,name,type,value,tags"]

        for metric in self.get_metrics():
            tags_str = json.dumps(metric.tags)
            lines.append(f"{metric.timestamp},{metric.name},{metric.type.value},{metric.value},{tags_str}")

        return "\n".join(lines)

    def reset_metrics(self):
        """Reset all metrics."""
        with self._lock:
            self.metrics.clear()
            self.custom_metrics.clear()
            self.counters.clear()
            self.histograms.clear()
            self.timer_history.clear()
            self.system_snapshots.clear()

        self.logger.info("All metrics reset")

    def cleanup_old_data(self, max_age_seconds: float = 3600):
        """
        Clean up old metrics data.

        Args:
            max_age_seconds: Maximum age of data to keep
        """
        cutoff_time = time.time() - max_age_seconds

        with self._lock:
            # Clean up metrics
            self.metrics = deque(
                [m for m in self.metrics if m.timestamp > cutoff_time],
                maxlen=self.max_history_size,
            )

            # Clean up system snapshots
            self.system_snapshots = deque(
                [s for s in self.system_snapshots if s.timestamp > cutoff_time],
                maxlen=self.max_history_size,
            )

        self.logger.info(f"Cleaned up metrics older than {max_age_seconds} seconds")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Note: Performance monitor will start automatically when first accessed
# This prevents blocking during module import
