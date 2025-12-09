"""
Parallel processing optimization for the image base64 converter.

This module provides parallel processing capabilities including:
- Multiprocessing for CPU-intensive image operations
- Thread pool optimization for I/O operations
- Adaptive concurrency control based on system resources
- Performance monitoring and benchmarking
"""

import multiprocessing as mp
import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import psutil
from PIL import Image

from ..models.models import ConversionError, ConversionResult
from ..models.processing_options import ProcessingOptions
from .memory_optimizer import get_memory_monitor, optimized_memory_context


@dataclass
class ProcessingTask:
    """
    Represents a single processing task for parallel execution.

    Attributes:
        task_id: Unique identifier for the task
        file_path: Path to the file to process
        options: Processing options
        priority: Task priority (higher = more important)
        created_time: When the task was created
        started_time: When processing started (None if not started)
        completed_time: When processing completed (None if not completed)
        result: Processing result (None if not completed)
        error: Error message if processing failed
        worker_id: ID of the worker that processed this task
    """

    task_id: str
    file_path: str
    options: ProcessingOptions
    priority: int = 0
    created_time: float = 0.0
    started_time: Optional[float] = None
    completed_time: Optional[float] = None
    result: Optional[ConversionResult] = None
    error: Optional[str] = None
    worker_id: Optional[str] = None

    def __post_init__(self):
        if self.created_time == 0.0:
            self.created_time = time.time()


@dataclass
class WorkerStats:
    """
    Statistics for a parallel worker.

    Attributes:
        worker_id: Unique worker identifier
        worker_type: Type of worker ('thread' or 'process')
        tasks_completed: Number of tasks completed
        total_processing_time: Total time spent processing
        average_processing_time: Average time per task
        errors: Number of errors encountered
        created_time: When the worker was created
        last_active_time: Last time the worker processed a task
    """

    worker_id: str
    worker_type: str
    tasks_completed: int = 0
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0
    errors: int = 0
    created_time: float = 0.0
    last_active_time: Optional[float] = None

    def __post_init__(self):
        if self.created_time == 0.0:
            self.created_time = time.time()

    def update_stats(self, processing_time: float, success: bool = True):
        """Update worker statistics after completing a task."""
        self.tasks_completed += 1
        self.total_processing_time += processing_time
        self.average_processing_time = self.total_processing_time / self.tasks_completed
        self.last_active_time = time.time()

        if not success:
            self.errors += 1


class AdaptiveConcurrencyController:
    """
    Adaptive concurrency controller that adjusts the number of workers
    based on system resources and performance metrics.
    """

    def __init__(self, min_workers: int = 1, max_workers: Optional[int] = None):
        """
        Initialize the adaptive concurrency controller.

        Args:
            min_workers: Minimum number of workers to maintain
            max_workers: Maximum number of workers (None for auto-detect)
        """
        self.min_workers = min_workers
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)

        # Current optimal worker count
        self.current_workers = min_workers

        # Performance tracking
        self.performance_history = []
        self.adjustment_history = []

        # System resource monitoring
        self.memory_monitor = get_memory_monitor()

        # Adjustment parameters
        self.adjustment_interval = 30.0  # seconds
        self.last_adjustment_time = time.time()
        self.performance_window_size = 10

        # Thresholds for adjustments
        self.cpu_threshold_high = 90.0  # % CPU usage
        self.cpu_threshold_low = 50.0  # % CPU usage
        self.memory_threshold_high = 80.0  # % Memory usage
        self.throughput_improvement_threshold = 0.1  # 10% improvement

    def should_adjust_workers(self) -> bool:
        """Check if worker count should be adjusted."""
        current_time = time.time()
        return (current_time - self.last_adjustment_time) >= self.adjustment_interval

    def get_system_metrics(self) -> Dict[str, float]:
        """Get current system resource metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_info.percent,
                "available_memory_mb": memory_info.available / (1024 * 1024),
                "load_average": (
                    os.getloadavg()[0]
                    if hasattr(os, "getloadavg")
                    else cpu_percent / 100
                ),
            }
        except Exception:
            # Fallback values if monitoring fails
            return {
                "cpu_percent": 50.0,
                "memory_percent": 50.0,
                "available_memory_mb": 1000.0,
                "load_average": 0.5,
            }

    def calculate_throughput(self, worker_stats: List[WorkerStats]) -> float:
        """Calculate current throughput (tasks per second)."""
        if not worker_stats:
            return 0.0

        total_tasks = sum(stats.tasks_completed for stats in worker_stats)
        total_time = sum(stats.total_processing_time for stats in worker_stats)

        if total_time == 0:
            return 0.0

        return total_tasks / total_time

    def adjust_worker_count(self, worker_stats: List[WorkerStats]) -> int:
        """
        Adjust worker count based on performance and system metrics.

        Args:
            worker_stats: Current worker statistics

        Returns:
            New optimal worker count
        """
        if not self.should_adjust_workers():
            return self.current_workers

        system_metrics = self.get_system_metrics()
        current_throughput = self.calculate_throughput(worker_stats)

        # Record performance
        self.performance_history.append(
            {
                "timestamp": time.time(),
                "workers": self.current_workers,
                "throughput": current_throughput,
                "cpu_percent": system_metrics["cpu_percent"],
                "memory_percent": system_metrics["memory_percent"],
            }
        )

        # Keep only recent history
        if len(self.performance_history) > self.performance_window_size:
            self.performance_history.pop(0)

        new_worker_count = self._calculate_optimal_workers(
            system_metrics, current_throughput
        )

        # Record adjustment
        if new_worker_count != self.current_workers:
            self.adjustment_history.append(
                {
                    "timestamp": time.time(),
                    "old_workers": self.current_workers,
                    "new_workers": new_worker_count,
                    "reason": self._get_adjustment_reason(
                        system_metrics, current_throughput
                    ),
                }
            )

        self.current_workers = new_worker_count
        self.last_adjustment_time = time.time()

        return self.current_workers

    def _calculate_optimal_workers(
        self, system_metrics: Dict[str, float], current_throughput: float
    ) -> int:
        """Calculate optimal worker count based on metrics."""
        cpu_percent = system_metrics["cpu_percent"]
        memory_percent = system_metrics["memory_percent"]

        # Start with current worker count
        optimal_workers = self.current_workers

        # Check if we should increase workers
        if (
            cpu_percent < self.cpu_threshold_low
            and memory_percent < self.memory_threshold_high
            and optimal_workers < self.max_workers
        ):

            # Check if increasing workers historically improved throughput
            if self._would_increase_improve_throughput():
                optimal_workers = min(self.max_workers, optimal_workers + 1)

        # Check if we should decrease workers
        elif (
            cpu_percent > self.cpu_threshold_high
            or memory_percent > self.memory_threshold_high
            or self._is_throughput_declining()
        ):

            if optimal_workers > self.min_workers:
                optimal_workers = max(self.min_workers, optimal_workers - 1)

        return optimal_workers

    def _would_increase_improve_throughput(self) -> bool:
        """Check if increasing workers would likely improve throughput."""
        if len(self.performance_history) < 3:
            return True  # Not enough data, assume it would help

        # Look for patterns where more workers led to better throughput
        recent_performance = self.performance_history[-3:]

        for i in range(1, len(recent_performance)):
            prev = recent_performance[i - 1]
            curr = recent_performance[i]

            if curr["workers"] > prev["workers"] and curr["throughput"] > prev[
                "throughput"
            ] * (1 + self.throughput_improvement_threshold):
                return True

        return False

    def _is_throughput_declining(self) -> bool:
        """Check if throughput is declining with current worker count."""
        if len(self.performance_history) < 2:
            return False

        recent = self.performance_history[-2:]
        return recent[1]["throughput"] < recent[0]["throughput"] * 0.9  # 10% decline

    def _get_adjustment_reason(
        self, system_metrics: Dict[str, float], current_throughput: float
    ) -> str:
        """Get human-readable reason for worker count adjustment."""
        cpu_percent = system_metrics["cpu_percent"]
        memory_percent = system_metrics["memory_percent"]

        if cpu_percent > self.cpu_threshold_high:
            return f"High CPU usage ({cpu_percent:.1f}%)"
        elif memory_percent > self.memory_threshold_high:
            return f"High memory usage ({memory_percent:.1f}%)"
        elif self._is_throughput_declining():
            return "Declining throughput"
        elif (
            cpu_percent < self.cpu_threshold_low
            and memory_percent < self.memory_threshold_high
        ):
            return "Low resource usage, can increase workers"
        else:
            return "Performance optimization"

    def get_stats(self) -> Dict[str, Any]:
        """Get controller statistics."""
        return {
            "current_workers": self.current_workers,
            "min_workers": self.min_workers,
            "max_workers": self.max_workers,
            "performance_history": self.performance_history.copy(),
            "adjustment_history": self.adjustment_history.copy(),
            "last_adjustment_time": self.last_adjustment_time,
        }


class ParallelProcessor:
    """
    Parallel processor for handling CPU-intensive and I/O operations efficiently.

    This class provides both multiprocessing for CPU-bound tasks and
    threading for I/O-bound tasks with adaptive concurrency control.
    """

    def __init__(
        self,
        cpu_workers: Optional[int] = None,
        io_workers: Optional[int] = None,
        enable_adaptive_concurrency: bool = True,
        max_memory_mb: int = 1000,
    ):
        """
        Initialize the parallel processor.

        Args:
            cpu_workers: Number of CPU workers (None for auto-detect)
            io_workers: Number of I/O workers (None for auto-detect)
            enable_adaptive_concurrency: Whether to enable adaptive concurrency
            max_memory_mb: Maximum memory usage threshold
        """
        # Determine optimal worker counts
        cpu_count = os.cpu_count() or 1
        self.cpu_workers = cpu_workers or max(1, cpu_count - 1)
        self.io_workers = io_workers or min(32, cpu_count * 4)

        self.enable_adaptive_concurrency = enable_adaptive_concurrency
        self.max_memory_mb = max_memory_mb

        # Executors
        self.process_executor: Optional[ProcessPoolExecutor] = None
        self.thread_executor: Optional[ThreadPoolExecutor] = None

        # Adaptive concurrency controller
        if enable_adaptive_concurrency:
            self.cpu_controller = AdaptiveConcurrencyController(
                min_workers=1, max_workers=cpu_count * 2
            )
            self.io_controller = AdaptiveConcurrencyController(
                min_workers=2, max_workers=64
            )
        else:
            self.cpu_controller = None
            self.io_controller = None

        # Worker statistics
        self.worker_stats: Dict[str, WorkerStats] = {}
        self.stats_lock = threading.Lock()

        # Task tracking
        self.active_tasks: Dict[str, ProcessingTask] = {}
        self.completed_tasks: List[ProcessingTask] = []

        # Performance metrics
        self.performance_metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
            "peak_concurrent_tasks": 0,
            "throughput_tasks_per_second": 0.0,
        }

        self.metrics_lock = threading.Lock()

    def _initialize_executors(self):
        """Initialize the executor pools."""
        if self.process_executor is None:
            self.process_executor = ProcessPoolExecutor(
                max_workers=self.cpu_workers,
                mp_context=mp.get_context(
                    "spawn"
                ),  # Use spawn for better compatibility
            )

        if self.thread_executor is None:
            self.thread_executor = ThreadPoolExecutor(
                max_workers=self.io_workers, thread_name_prefix="ImageProcessor"
            )

    def process_cpu_intensive_batch(
        self,
        tasks: List[ProcessingTask],
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
    ) -> List[ConversionResult]:
        """
        Process a batch of CPU-intensive tasks using multiprocessing.

        Args:
            tasks: List of processing tasks
            processor_func: Function to process individual files

        Returns:
            List of conversion results
        """
        if not tasks:
            return []

        self._initialize_executors()

        # Adjust worker count if adaptive concurrency is enabled
        if self.enable_adaptive_concurrency and self.cpu_controller:
            current_stats = list(self.worker_stats.values())
            optimal_workers = self.cpu_controller.adjust_worker_count(current_stats)

            if optimal_workers != self.cpu_workers:
                self._resize_process_executor(optimal_workers)

        results = []

        try:
            with optimized_memory_context(self.max_memory_mb) as memory_context:
                # Submit all tasks
                future_to_task = {}

                for task in tasks:
                    future = self.process_executor.submit(
                        self._process_single_task_cpu,
                        task.file_path,
                        task.options,
                        processor_func,
                        task.task_id,
                    )
                    future_to_task[future] = task
                    task.started_time = time.time()
                    self.active_tasks[task.task_id] = task

                # Collect results as they complete
                for future in as_completed(future_to_task):
                    task = future_to_task[future]

                    try:
                        result = future.result()
                        task.result = result
                        task.completed_time = time.time()
                        results.append(result)

                        # Update statistics
                        self._update_task_stats(task, success=True)

                    except Exception as e:
                        task.error = str(e)
                        task.completed_time = time.time()

                        # Create error result
                        error_result = ConversionResult(
                            file_path=task.file_path,
                            success=False,
                            error_message=str(e),
                        )
                        task.result = error_result
                        results.append(error_result)

                        # Update statistics
                        self._update_task_stats(task, success=False)

                    finally:
                        # Move task from active to completed
                        if task.task_id in self.active_tasks:
                            del self.active_tasks[task.task_id]
                        self.completed_tasks.append(task)

        except Exception as e:
            raise ConversionError(f"CPU batch processing failed: {str(e)}")

        return results

    def process_io_intensive_batch(
        self,
        tasks: List[ProcessingTask],
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
    ) -> List[ConversionResult]:
        """
        Process a batch of I/O-intensive tasks using threading.

        Args:
            tasks: List of processing tasks
            processor_func: Function to process individual files

        Returns:
            List of conversion results
        """
        if not tasks:
            return []

        self._initialize_executors()

        # Adjust worker count if adaptive concurrency is enabled
        if self.enable_adaptive_concurrency and self.io_controller:
            current_stats = list(self.worker_stats.values())
            optimal_workers = self.io_controller.adjust_worker_count(current_stats)

            if optimal_workers != self.io_workers:
                self._resize_thread_executor(optimal_workers)

        results = []

        try:
            # Submit all tasks
            future_to_task = {}

            for task in tasks:
                future = self.thread_executor.submit(
                    self._process_single_task_io,
                    task.file_path,
                    task.options,
                    processor_func,
                    task.task_id,
                )
                future_to_task[future] = task
                task.started_time = time.time()
                self.active_tasks[task.task_id] = task

            # Collect results as they complete
            for future in as_completed(future_to_task):
                task = future_to_task[future]

                try:
                    result = future.result()
                    task.result = result
                    task.completed_time = time.time()
                    results.append(result)

                    # Update statistics
                    self._update_task_stats(task, success=True)

                except Exception as e:
                    task.error = str(e)
                    task.completed_time = time.time()

                    # Create error result
                    error_result = ConversionResult(
                        file_path=task.file_path, success=False, error_message=str(e)
                    )
                    task.result = error_result
                    results.append(error_result)

                    # Update statistics
                    self._update_task_stats(task, success=False)

                finally:
                    # Move task from active to completed
                    if task.task_id in self.active_tasks:
                        del self.active_tasks[task.task_id]
                    self.completed_tasks.append(task)

        except Exception as e:
            raise ConversionError(f"I/O batch processing failed: {str(e)}")

        return results

    def _process_single_task_cpu(
        self,
        file_path: str,
        options: ProcessingOptions,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
        task_id: str,
    ) -> ConversionResult:
        """Process a single task in a CPU worker process."""
        worker_id = f"cpu_worker_{os.getpid()}_{threading.current_thread().ident}"

        try:
            # Process the file
            result = processor_func(file_path, options)

            # Add worker info to result
            if hasattr(result, "__dict__"):
                result.worker_id = worker_id
                result.worker_type = "process"

            return result

        except Exception as e:
            raise ConversionError(f"CPU task processing failed: {str(e)}")

    def _process_single_task_io(
        self,
        file_path: str,
        options: ProcessingOptions,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
        task_id: str,
    ) -> ConversionResult:
        """Process a single task in an I/O worker thread."""
        worker_id = f"io_worker_{threading.current_thread().ident}"

        try:
            # Process the file
            result = processor_func(file_path, options)

            # Add worker info to result
            if hasattr(result, "__dict__"):
                result.worker_id = worker_id
                result.worker_type = "thread"

            return result

        except Exception as e:
            raise ConversionError(f"I/O task processing failed: {str(e)}")

    def _update_task_stats(self, task: ProcessingTask, success: bool):
        """Update task and worker statistics."""
        if not task.started_time or not task.completed_time:
            return

        processing_time = task.completed_time - task.started_time
        worker_id = task.worker_id or "unknown"

        with self.stats_lock:
            # Update worker stats
            if worker_id not in self.worker_stats:
                worker_type = "process" if "cpu_worker" in worker_id else "thread"
                self.worker_stats[worker_id] = WorkerStats(
                    worker_id=worker_id, worker_type=worker_type
                )

            self.worker_stats[worker_id].update_stats(processing_time, success)

        with self.metrics_lock:
            # Update global metrics
            self.performance_metrics["total_tasks"] += 1
            if success:
                self.performance_metrics["successful_tasks"] += 1
            else:
                self.performance_metrics["failed_tasks"] += 1

            self.performance_metrics["total_processing_time"] += processing_time
            self.performance_metrics["average_processing_time"] = (
                self.performance_metrics["total_processing_time"]
                / self.performance_metrics["total_tasks"]
            )

            # Update peak concurrent tasks
            current_active = len(self.active_tasks)
            if current_active > self.performance_metrics["peak_concurrent_tasks"]:
                self.performance_metrics["peak_concurrent_tasks"] = current_active

            # Calculate throughput
            if self.performance_metrics["total_processing_time"] > 0:
                self.performance_metrics["throughput_tasks_per_second"] = (
                    self.performance_metrics["total_tasks"]
                    / self.performance_metrics["total_processing_time"]
                )

    def _resize_process_executor(self, new_size: int):
        """Resize the process executor pool."""
        if new_size == self.cpu_workers:
            return

        # Shutdown current executor
        if self.process_executor:
            self.process_executor.shutdown(wait=False)

        # Create new executor with new size
        self.cpu_workers = new_size
        self.process_executor = ProcessPoolExecutor(
            max_workers=self.cpu_workers, mp_context=mp.get_context("spawn")
        )

    def _resize_thread_executor(self, new_size: int):
        """Resize the thread executor pool."""
        if new_size == self.io_workers:
            return

        # Shutdown current executor
        if self.thread_executor:
            self.thread_executor.shutdown(wait=False)

        # Create new executor with new size
        self.io_workers = new_size
        self.thread_executor = ThreadPoolExecutor(
            max_workers=self.io_workers, thread_name_prefix="ImageProcessor"
        )

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        with self.metrics_lock:
            metrics = self.performance_metrics.copy()

        with self.stats_lock:
            worker_stats = {
                wid: {
                    "worker_type": stats.worker_type,
                    "tasks_completed": stats.tasks_completed,
                    "average_processing_time": stats.average_processing_time,
                    "errors": stats.errors,
                    "last_active_time": stats.last_active_time,
                }
                for wid, stats in self.worker_stats.items()
            }

        stats = {
            "global_metrics": metrics,
            "worker_stats": worker_stats,
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "cpu_workers": self.cpu_workers,
            "io_workers": self.io_workers,
        }

        # Add adaptive concurrency stats if enabled
        if self.enable_adaptive_concurrency:
            if self.cpu_controller:
                stats["cpu_controller"] = self.cpu_controller.get_stats()
            if self.io_controller:
                stats["io_controller"] = self.io_controller.get_stats()

        return stats

    def benchmark_performance(
        self,
        test_tasks: List[ProcessingTask],
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
        test_configurations: List[Dict[str, int]],
    ) -> Dict[str, Any]:
        """
        Benchmark different worker configurations to find optimal settings.

        Args:
            test_tasks: List of tasks to use for benchmarking
            processor_func: Function to process files
            test_configurations: List of configurations to test
                Each config should have 'cpu_workers' and 'io_workers' keys

        Returns:
            Dictionary with benchmark results
        """
        benchmark_results = []

        for config in test_configurations:
            # Reset statistics
            self.performance_metrics = {
                "total_tasks": 0,
                "successful_tasks": 0,
                "failed_tasks": 0,
                "total_processing_time": 0.0,
                "average_processing_time": 0.0,
                "peak_concurrent_tasks": 0,
                "throughput_tasks_per_second": 0.0,
            }
            self.worker_stats.clear()
            self.active_tasks.clear()
            self.completed_tasks.clear()

            # Apply configuration
            self.cpu_workers = config["cpu_workers"]
            self.io_workers = config["io_workers"]

            # Shutdown existing executors
            if self.process_executor:
                self.process_executor.shutdown(wait=True)
                self.process_executor = None
            if self.thread_executor:
                self.thread_executor.shutdown(wait=True)
                self.thread_executor = None

            # Run benchmark
            start_time = time.time()

            try:
                # Determine task type based on file characteristics
                cpu_tasks = []
                io_tasks = []

                for task in test_tasks:
                    # Simple heuristic: larger files are more CPU-intensive
                    try:
                        file_size = os.path.getsize(task.file_path)
                        if file_size > 1024 * 1024:  # > 1MB
                            cpu_tasks.append(task)
                        else:
                            io_tasks.append(task)
                    except:
                        io_tasks.append(task)  # Default to I/O if can't determine size

                # Process tasks
                cpu_results = self.process_cpu_intensive_batch(
                    cpu_tasks, processor_func
                )
                io_results = self.process_io_intensive_batch(io_tasks, processor_func)

                end_time = time.time()
                total_time = end_time - start_time

                # Calculate results
                total_tasks = len(cpu_results) + len(io_results)
                successful_tasks = sum(1 for r in cpu_results + io_results if r.success)

                benchmark_results.append(
                    {
                        "configuration": config,
                        "total_time": total_time,
                        "total_tasks": total_tasks,
                        "successful_tasks": successful_tasks,
                        "throughput": total_tasks / total_time if total_time > 0 else 0,
                        "success_rate": (
                            successful_tasks / total_tasks if total_tasks > 0 else 0
                        ),
                        "performance_metrics": self.performance_metrics.copy(),
                    }
                )

            except Exception as e:
                benchmark_results.append(
                    {
                        "configuration": config,
                        "error": str(e),
                        "total_time": time.time() - start_time,
                    }
                )

        # Find best configuration
        valid_results = [r for r in benchmark_results if "error" not in r]
        if valid_results:
            best_config = max(valid_results, key=lambda x: x["throughput"])

            return {
                "benchmark_results": benchmark_results,
                "best_configuration": best_config,
                "recommendation": {
                    "cpu_workers": best_config["configuration"]["cpu_workers"],
                    "io_workers": best_config["configuration"]["io_workers"],
                    "expected_throughput": best_config["throughput"],
                },
            }
        else:
            return {
                "benchmark_results": benchmark_results,
                "error": "All benchmark configurations failed",
            }

    def shutdown(self):
        """Shutdown all executor pools."""
        if self.process_executor:
            self.process_executor.shutdown(wait=True)
            self.process_executor = None

        if self.thread_executor:
            self.thread_executor.shutdown(wait=True)
            self.thread_executor = None

    def __del__(self):
        """Cleanup when the processor is destroyed."""
        try:
            self.shutdown()
        except Exception:
            pass  # Ignore cleanup errors


# Global instance for easy access
_parallel_processor: Optional[ParallelProcessor] = None


def get_parallel_processor(**kwargs) -> ParallelProcessor:
    """Get the global parallel processor instance."""
    global _parallel_processor
    if _parallel_processor is None:
        _parallel_processor = ParallelProcessor(**kwargs)
    return _parallel_processor


def shutdown_parallel_processor():
    """Shutdown the global parallel processor."""
    global _parallel_processor
    if _parallel_processor:
        _parallel_processor.shutdown()
        _parallel_processor = None
