"""
Multi-file processing handler for the image base64 converter.

This module provides functionality for handling multiple file processing
with queue management, progress tracking, and asynchronous processing.
Enhanced with memory optimization for large file processing.
"""

import asyncio
import gc
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from ..models.models import ConversionError, ConversionResult, ProcessingQueueFullError
from ..models.processing_options import ProcessingOptions, ProgressInfo
from .memory_optimizer import (
    get_gc_optimizer,
    get_memory_monitor,
    get_memory_pool,
    optimized_memory_context,
)
from .parallel_processor import (
    ParallelProcessor,
    ProcessingTask,
    get_parallel_processor,
)


@dataclass
class FileQueueItem:
    """
    Represents a single file in the processing queue.

    Attributes:
        file_path: Path to the file to be processed
        options: Processing options for this file
        priority: Processing priority (higher numbers = higher priority)
        added_time: Timestamp when item was added to queue
        started_time: Timestamp when processing started (None if not started)
        completed_time: Timestamp when processing completed (None if not completed)
        result: Processing result (None if not completed)
        error: Error message if processing failed (None if successful)
    """

    file_path: str
    options: ProcessingOptions
    priority: int = 0
    added_time: float = 0.0
    started_time: Optional[float] = None
    completed_time: Optional[float] = None
    result: Optional[ConversionResult] = None
    error: Optional[str] = None

    def __post_init__(self):
        """Set default added_time if not provided."""
        if self.added_time == 0.0:
            self.added_time = time.time()


@dataclass
class ProcessingQueue:
    """
    Represents a processing queue with metadata.

    Attributes:
        queue_id: Unique identifier for this queue
        items: List of FileQueueItem objects
        status: Current queue status
        created_time: When the queue was created
        started_time: When processing started (None if not started)
        completed_time: When processing completed (None if not completed)
        max_concurrent: Maximum number of concurrent processing tasks
        cancelled: Whether the queue processing has been cancelled
        progress_callback: Optional callback function for progress updates
    """

    queue_id: str
    items: List[FileQueueItem]
    status: str = "pending"  # pending, processing, completed, error, cancelled
    created_time: float = 0.0
    started_time: Optional[float] = None
    completed_time: Optional[float] = None
    max_concurrent: int = 3
    cancelled: bool = False
    progress_callback: Optional[Callable[[ProgressInfo], None]] = None

    def __post_init__(self):
        """Set default created_time if not provided."""
        if self.created_time == 0.0:
            self.created_time = time.time()


class MultiFileHandler:
    """
    Handles multiple file processing with queue management and progress tracking.

    This class provides functionality for:
    - Managing file processing queues
    - Asynchronous batch processing with concurrency control
    - Real-time progress tracking and updates
    - Processing cancellation
    - Queue status monitoring
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        max_queue_size: int = 100,
        enable_memory_optimization: bool = True,
    ):
        """
        Initialize the MultiFileHandler.

        Args:
            max_concurrent: Maximum number of files to process concurrently
            max_queue_size: Maximum number of items allowed in a single queue
            enable_memory_optimization: Whether to enable memory optimization features
        """
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.enable_memory_optimization = enable_memory_optimization

        # Dictionary to store active processing queues
        self._queues: Dict[str, ProcessingQueue] = {}

        # Thread pool for CPU-intensive operations
        self._thread_pool = ThreadPoolExecutor(max_workers=max_concurrent)

        # Lock for thread-safe operations
        self._lock = threading.RLock()

        # Event loop for async operations
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Active processing tasks
        self._active_tasks: Dict[str, asyncio.Task] = {}

        # Progress update callbacks
        self._progress_callbacks: Dict[str, List[Callable[[ProgressInfo], None]]] = {}

        # Memory optimization components
        if enable_memory_optimization:
            self.memory_pool = get_memory_pool()
            self.memory_monitor = get_memory_monitor()
            self.gc_optimizer = get_gc_optimizer()

            # Set up memory monitoring callbacks
            self.memory_monitor.add_callback(self._handle_memory_warning, "warning")
            self.memory_monitor.add_callback(self._handle_memory_critical, "critical")
        else:
            self.memory_pool = None
            self.memory_monitor = None
            self.gc_optimizer = None

        # Memory usage tracking
        self._memory_stats = {
            "peak_usage_mb": 0.0,
            "gc_collections": 0,
            "memory_warnings": 0,
            "memory_critical": 0,
        }

        # Parallel processing
        self.parallel_processor = (
            get_parallel_processor(
                cpu_workers=max(1, max_concurrent // 2),
                io_workers=max_concurrent,
                enable_adaptive_concurrency=enable_memory_optimization,
                max_memory_mb=500,
            )
            if enable_memory_optimization
            else None
        )

    def add_to_queue(
        self,
        files: List[str],
        options: Optional[ProcessingOptions] = None,
        priority: int = 0,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
    ) -> str:
        """
        Add files to a new processing queue.

        Args:
            files: List of file paths to process
            options: Processing options to apply to all files
            priority: Processing priority for all files
            progress_callback: Optional callback for progress updates

        Returns:
            Unique queue ID for tracking progress

        Raises:
            ProcessingQueueFullError: If queue size limit is exceeded
            ValueError: If files list is empty or invalid
        """
        if not files:
            raise ValueError("Files list cannot be empty")

        if len(files) > self.max_queue_size:
            raise ProcessingQueueFullError(
                f"Queue size limit exceeded. Maximum {self.max_queue_size} files allowed."
            )

        # Validate file paths
        for file_path in files:
            if not file_path or not isinstance(file_path, str):
                raise ValueError(f"Invalid file path: {file_path}")

            # Check if file exists (basic validation)
            path_obj = Path(file_path)
            if not path_obj.exists():
                raise ValueError(f"File not found: {file_path}")

        # Generate unique queue ID
        queue_id = str(uuid.uuid4())

        # Create default options if not provided
        if options is None:
            options = ProcessingOptions()

        # Create queue items
        queue_items = []
        for file_path in files:
            item = FileQueueItem(
                file_path=file_path, options=options, priority=priority
            )
            queue_items.append(item)

        # Create processing queue
        with self._lock:
            processing_queue = ProcessingQueue(
                queue_id=queue_id,
                items=queue_items,
                max_concurrent=self.max_concurrent,
                progress_callback=progress_callback,
            )

            self._queues[queue_id] = processing_queue

            # Register progress callback if provided
            if progress_callback:
                if queue_id not in self._progress_callbacks:
                    self._progress_callbacks[queue_id] = []
                self._progress_callbacks[queue_id].append(progress_callback)

        return queue_id

    def get_queue_info(self, queue_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a processing queue.

        Args:
            queue_id: Queue identifier

        Returns:
            Dictionary with queue information or None if not found
        """
        with self._lock:
            if queue_id not in self._queues:
                return None

            queue = self._queues[queue_id]

            # Count items by status
            pending_count = sum(1 for item in queue.items if item.started_time is None)
            processing_count = sum(
                1
                for item in queue.items
                if item.started_time is not None and item.completed_time is None
            )
            completed_count = sum(
                1 for item in queue.items if item.completed_time is not None
            )
            error_count = sum(1 for item in queue.items if item.error is not None)

            return {
                "queue_id": queue_id,
                "status": queue.status,
                "total_files": len(queue.items),
                "pending_files": pending_count,
                "processing_files": processing_count,
                "completed_files": completed_count,
                "error_files": error_count,
                "created_time": queue.created_time,
                "started_time": queue.started_time,
                "completed_time": queue.completed_time,
                "cancelled": queue.cancelled,
                "max_concurrent": queue.max_concurrent,
            }

    def get_progress(self, queue_id: str) -> Optional[ProgressInfo]:
        """
        Get current progress information for a processing queue.

        Args:
            queue_id: Queue identifier

        Returns:
            ProgressInfo object or None if queue not found
        """
        with self._lock:
            if queue_id not in self._queues:
                return None

            queue = self._queues[queue_id]

            # Calculate progress metrics
            total_files = len(queue.items)
            completed_files = sum(
                1 for item in queue.items if item.completed_time is not None
            )
            error_count = sum(1 for item in queue.items if item.error is not None)

            # Find currently processing file
            current_file = ""
            current_file_progress = 0.0
            for item in queue.items:
                if item.started_time is not None and item.completed_time is None:
                    current_file = Path(item.file_path).name
                    # For now, we don't have sub-file progress, so it's either 0 or 1
                    current_file_progress = 0.5  # Assume halfway through
                    break

            # Calculate estimated time remaining
            estimated_time_remaining = self._calculate_estimated_time(queue)

            # Determine status
            if queue.cancelled:
                status = "cancelled"
            elif queue.status == "error":
                status = "error"
            elif completed_files == total_files:
                status = "completed"
            elif queue.status == "processing":
                status = "processing"
            else:
                status = "pending"

            return ProgressInfo(
                queue_id=queue_id,
                total_files=total_files,
                completed_files=completed_files,
                current_file=current_file,
                estimated_time_remaining=estimated_time_remaining,
                status=status,
                error_count=error_count,
                start_time=queue.started_time or 0.0,
                current_file_progress=current_file_progress,
            )

    def _calculate_estimated_time(self, queue: ProcessingQueue) -> float:
        """
        Calculate estimated time remaining for queue processing.

        Args:
            queue: ProcessingQueue object

        Returns:
            Estimated time remaining in seconds
        """
        if not queue.started_time:
            return 0.0

        completed_items = [
            item for item in queue.items if item.completed_time is not None
        ]
        if not completed_items:
            return 0.0

        # Calculate average processing time per file
        total_processing_time = 0.0
        for item in completed_items:
            if item.started_time and item.completed_time:
                total_processing_time += item.completed_time - item.started_time

        if len(completed_items) == 0:
            return 0.0

        avg_processing_time = total_processing_time / len(completed_items)

        # Count remaining files
        remaining_files = sum(1 for item in queue.items if item.completed_time is None)

        # Estimate time considering concurrency
        if remaining_files == 0:
            return 0.0

        # Account for concurrent processing
        concurrent_factor = min(queue.max_concurrent, remaining_files)
        estimated_time = (remaining_files * avg_processing_time) / concurrent_factor

        return max(0.0, estimated_time)

    def cancel_processing(self, queue_id: str) -> bool:
        """
        Cancel processing for a specific queue.

        Args:
            queue_id: Queue identifier

        Returns:
            True if cancellation was successful, False if queue not found
        """
        with self._lock:
            if queue_id not in self._queues:
                return False

            queue = self._queues[queue_id]
            queue.cancelled = True
            queue.status = "cancelled"

            # Cancel the async task if it's running
            if queue_id in self._active_tasks:
                task = self._active_tasks[queue_id]
                if not task.done():
                    task.cancel()

            return True

    def remove_queue(self, queue_id: str) -> bool:
        """
        Remove a completed or cancelled queue from memory.

        Args:
            queue_id: Queue identifier

        Returns:
            True if queue was removed, False if not found or still processing
        """
        with self._lock:
            if queue_id not in self._queues:
                return False

            queue = self._queues[queue_id]

            # Only allow removal of completed, cancelled, or error queues
            if queue.status not in ["completed", "cancelled", "error"]:
                return False

            # Remove from active tasks if present
            if queue_id in self._active_tasks:
                del self._active_tasks[queue_id]

            # Remove progress callbacks
            if queue_id in self._progress_callbacks:
                del self._progress_callbacks[queue_id]

            # Remove the queue
            del self._queues[queue_id]

            return True

    def get_all_queues(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all processing queues.

        Returns:
            Dictionary mapping queue IDs to queue information
        """
        with self._lock:
            result = {}
            for queue_id in self._queues:
                queue_info = self.get_queue_info(queue_id)
                if queue_info:
                    result[queue_id] = queue_info
            return result

    def cleanup_completed_queues(self, max_age_hours: float = 24.0) -> int:
        """
        Clean up old completed queues to free memory.

        Args:
            max_age_hours: Maximum age in hours for completed queues

        Returns:
            Number of queues cleaned up
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        queues_to_remove = []

        with self._lock:
            for queue_id, queue in self._queues.items():
                if queue.status in ["completed", "cancelled", "error"]:
                    # Use completed_time if available, otherwise created_time
                    queue_time = queue.completed_time or queue.created_time
                    if current_time - queue_time > max_age_seconds:
                        queues_to_remove.append(queue_id)

        # Remove old queues
        cleanup_count = 0
        for queue_id in queues_to_remove:
            if self.remove_queue(queue_id):
                cleanup_count += 1

        return cleanup_count

    def _notify_progress(self, queue_id: str, progress_info: ProgressInfo) -> None:
        """
        Notify registered callbacks about progress updates.

        Args:
            queue_id: Queue identifier
            progress_info: Current progress information
        """
        if queue_id in self._progress_callbacks:
            for callback in self._progress_callbacks[queue_id]:
                try:
                    callback(progress_info)
                except Exception as e:
                    # Log error but don't stop processing
                    print(f"Error in progress callback: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics about the multi-file handler.

        Returns:
            Dictionary with handler statistics
        """
        with self._lock:
            total_queues = len(self._queues)
            active_queues = sum(
                1 for q in self._queues.values() if q.status == "processing"
            )
            completed_queues = sum(
                1 for q in self._queues.values() if q.status == "completed"
            )
            cancelled_queues = sum(
                1 for q in self._queues.values() if q.status == "cancelled"
            )
            error_queues = sum(1 for q in self._queues.values() if q.status == "error")

            total_files = sum(len(q.items) for q in self._queues.values())
            completed_files = sum(
                sum(1 for item in q.items if item.completed_time is not None)
                for q in self._queues.values()
            )

            return {
                "total_queues": total_queues,
                "active_queues": active_queues,
                "completed_queues": completed_queues,
                "cancelled_queues": cancelled_queues,
                "error_queues": error_queues,
                "total_files": total_files,
                "completed_files": completed_files,
                "max_concurrent": self.max_concurrent,
                "max_queue_size": self.max_queue_size,
                "thread_pool_size": self._thread_pool._max_workers,
            }

    async def process_queue(
        self,
        queue_id: str,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
    ) -> AsyncGenerator[ConversionResult, None]:
        """
        Process all files in a queue asynchronously with progress tracking.

        Args:
            queue_id: Queue identifier
            processor_func: Function to process individual files

        Yields:
            ConversionResult objects as files are processed

        Raises:
            ValueError: If queue not found
            ConversionError: If processing fails
        """
        with self._lock:
            if queue_id not in self._queues:
                raise ValueError(f"Queue not found: {queue_id}")

            queue = self._queues[queue_id]
            if queue.cancelled:
                return

            queue.status = "processing"
            queue.started_time = time.time()

        try:
            # Create semaphore to limit concurrent processing
            semaphore = asyncio.Semaphore(queue.max_concurrent)

            # Create tasks for all files
            tasks = []
            for item in queue.items:
                if queue.cancelled:
                    break

                task = asyncio.create_task(
                    self._process_single_file(queue_id, item, processor_func, semaphore)
                )
                tasks.append(task)

            # Store active task for cancellation
            self._active_tasks[queue_id] = asyncio.current_task()

            # Process files and yield results as they complete
            for completed_task in asyncio.as_completed(tasks):
                if queue.cancelled:
                    # Cancel remaining tasks
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    break

                try:
                    result = await completed_task
                    if result:
                        yield result

                        # Update progress and notify callbacks
                        progress_info = self.get_progress(queue_id)
                        if progress_info:
                            self._notify_progress(queue_id, progress_info)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    # Log error but continue processing other files
                    print(f"Error processing file: {e}")

            # Wait for any remaining tasks to complete or be cancelled
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        except asyncio.CancelledError:
            queue.cancelled = True
            queue.status = "cancelled"
        except Exception as e:
            queue.status = "error"
            raise ConversionError(f"Queue processing failed: {str(e)}")
        finally:
            # Update final status
            with self._lock:
                if not queue.cancelled and queue.status != "error":
                    queue.status = "completed"
                queue.completed_time = time.time()

                # Remove from active tasks
                if queue_id in self._active_tasks:
                    del self._active_tasks[queue_id]

                # Final progress notification
                progress_info = self.get_progress(queue_id)
                if progress_info:
                    self._notify_progress(queue_id, progress_info)

    async def _process_single_file(
        self,
        queue_id: str,
        item: FileQueueItem,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
        semaphore: asyncio.Semaphore,
    ) -> Optional[ConversionResult]:
        """
        Process a single file with concurrency control.

        Args:
            queue_id: Queue identifier
            item: FileQueueItem to process
            processor_func: Function to process the file
            semaphore: Semaphore for concurrency control

        Returns:
            ConversionResult or None if cancelled/failed
        """
        async with semaphore:
            # Check if processing was cancelled
            with self._lock:
                if queue_id not in self._queues or self._queues[queue_id].cancelled:
                    return None

            # Mark item as started
            item.started_time = time.time()

            try:
                # Run the processor function in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self._thread_pool, processor_func, item.file_path, item.options
                )

                # Mark item as completed
                item.completed_time = time.time()
                item.result = result

                return result

            except Exception as e:
                # Mark item as failed
                item.completed_time = time.time()
                item.error = str(e)

                # Create error result
                error_result = ConversionResult(
                    file_path=item.file_path, success=False, error_message=str(e)
                )
                item.result = error_result

                return error_result

    def start_processing(
        self,
        queue_id: str,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
    ) -> asyncio.Task:
        """
        Start processing a queue in the background.

        Args:
            queue_id: Queue identifier
            processor_func: Function to process individual files

        Returns:
            AsyncIO task for the processing operation

        Raises:
            ValueError: If queue not found
        """
        if queue_id not in self._queues:
            raise ValueError(f"Queue not found: {queue_id}")

        # Get or create event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Create and start the processing task
        async def process_and_collect():
            results = []
            async for result in self.process_queue(queue_id, processor_func):
                results.append(result)
            return results

        task = loop.create_task(process_and_collect())
        self._active_tasks[queue_id] = task

        return task

    def get_processing_results(self, queue_id: str) -> List[ConversionResult]:
        """
        Get all processing results for a completed queue.

        Args:
            queue_id: Queue identifier

        Returns:
            List of ConversionResult objects
        """
        with self._lock:
            if queue_id not in self._queues:
                return []

            queue = self._queues[queue_id]
            results = []

            for item in queue.items:
                if item.result:
                    results.append(item.result)

            return results

    def get_failed_files(self, queue_id: str) -> List[Dict[str, Any]]:
        """
        Get information about files that failed processing.

        Args:
            queue_id: Queue identifier

        Returns:
            List of dictionaries with failed file information
        """
        with self._lock:
            if queue_id not in self._queues:
                return []

            queue = self._queues[queue_id]
            failed_files = []

            for item in queue.items:
                if item.error:
                    failed_files.append(
                        {
                            "file_path": item.file_path,
                            "error": item.error,
                            "started_time": item.started_time,
                            "completed_time": item.completed_time,
                        }
                    )

            return failed_files

    def get_processing_summary(self, queue_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a comprehensive summary of queue processing.

        Args:
            queue_id: Queue identifier

        Returns:
            Dictionary with processing summary or None if queue not found
        """
        with self._lock:
            if queue_id not in self._queues:
                return None

            queue = self._queues[queue_id]

            total_files = len(queue.items)
            completed_files = sum(
                1 for item in queue.items if item.completed_time is not None
            )
            successful_files = sum(
                1
                for item in queue.items
                if item.completed_time is not None and item.error is None
            )
            failed_files = sum(1 for item in queue.items if item.error is not None)

            # Calculate processing times
            processing_times = []
            for item in queue.items:
                if item.started_time and item.completed_time:
                    processing_times.append(item.completed_time - item.started_time)

            avg_processing_time = (
                sum(processing_times) / len(processing_times) if processing_times else 0
            )
            total_processing_time = (
                queue.completed_time - queue.started_time
                if queue.started_time and queue.completed_time
                else 0
            )

            return {
                "queue_id": queue_id,
                "status": queue.status,
                "total_files": total_files,
                "completed_files": completed_files,
                "successful_files": successful_files,
                "failed_files": failed_files,
                "success_rate": (
                    (successful_files / completed_files * 100)
                    if completed_files > 0
                    else 0
                ),
                "average_processing_time": avg_processing_time,
                "total_processing_time": total_processing_time,
                "started_time": queue.started_time,
                "completed_time": queue.completed_time,
                "cancelled": queue.cancelled,
            }

    def _handle_memory_warning(
        self, threshold_type: str, usage: Dict[str, Any]
    ) -> None:
        """
        Handle memory warning by triggering garbage collection.

        Args:
            threshold_type: Type of threshold exceeded
            usage: Current memory usage information
        """
        self._memory_stats["memory_warnings"] += 1

        if self.gc_optimizer:
            # Trigger garbage collection to free memory
            gc_result = self.gc_optimizer.manual_collect()
            self._memory_stats["gc_collections"] += 1

            print(
                f"Memory warning: {usage['rss_mb']:.1f}MB used. "
                f"GC collected {gc_result['objects_collected']} objects."
            )

    def _handle_memory_critical(
        self, threshold_type: str, usage: Dict[str, Any]
    ) -> None:
        """
        Handle critical memory usage by aggressive cleanup.

        Args:
            threshold_type: Type of threshold exceeded
            usage: Current memory usage information
        """
        self._memory_stats["memory_critical"] += 1

        if self.gc_optimizer:
            # Aggressive garbage collection
            for generation in [0, 1, 2]:
                gc_result = self.gc_optimizer.manual_collect(generation)
                self._memory_stats["gc_collections"] += 1

            print(
                f"Critical memory usage: {usage['rss_mb']:.1f}MB used. "
                f"Performed aggressive garbage collection."
            )

        # Clear memory pool to free buffers
        if self.memory_pool:
            self.memory_pool.clear()

    async def process_queue_optimized(
        self,
        queue_id: str,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
        max_memory_mb: int = 500,
    ) -> AsyncGenerator[ConversionResult, None]:
        """
        Memory-optimized version of process_queue with enhanced memory management.

        Args:
            queue_id: Queue identifier
            processor_func: Function to process individual files
            max_memory_mb: Maximum memory usage threshold

        Yields:
            ConversionResult objects as files are processed

        Raises:
            ValueError: If queue not found
            ConversionError: If processing fails
        """
        if not self.enable_memory_optimization:
            # Fall back to regular processing
            async_gen = self.process_queue(queue_id, processor_func)
            async for result in async_gen:
                yield result
            return

        with self._lock:
            if queue_id not in self._queues:
                raise ValueError(f"Queue not found: {queue_id}")

            queue = self._queues[queue_id]
            if queue.cancelled:
                return

            queue.status = "processing"
            queue.started_time = time.time()

        try:
            with optimized_memory_context(max_memory_mb) as context:
                # Create semaphore to limit concurrent processing
                semaphore = asyncio.Semaphore(queue.max_concurrent)

                # Create tasks for all files
                tasks = []
                for item in queue.items:
                    if queue.cancelled:
                        break

                    task = asyncio.create_task(
                        self._process_single_file_optimized(
                            queue_id, item, processor_func, semaphore, context
                        )
                    )
                    tasks.append(task)

                # Store active task for cancellation
                self._active_tasks[queue_id] = asyncio.current_task()

                # Process files and yield results as they complete
                for completed_task in asyncio.as_completed(tasks):
                    if queue.cancelled:
                        # Cancel remaining tasks
                        for task in tasks:
                            if not task.done():
                                task.cancel()
                        break

                    try:
                        result = await completed_task
                        if result:
                            yield result

                            # Update memory stats
                            current_usage = context["memory_monitor"].get_memory_usage()
                            current_mb = current_usage.get("rss_mb", 0)
                            if current_mb > self._memory_stats["peak_usage_mb"]:
                                self._memory_stats["peak_usage_mb"] = current_mb

                            # Update progress and notify callbacks
                            progress_info = self.get_progress(queue_id)
                            if progress_info:
                                self._notify_progress(queue_id, progress_info)

                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        # Log error but continue processing other files
                        print(f"Error processing file: {e}")

                # Wait for any remaining tasks to complete or be cancelled
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

        except asyncio.CancelledError:
            queue.cancelled = True
            queue.status = "cancelled"
        except Exception as e:
            queue.status = "error"
            raise ConversionError(f"Queue processing failed: {str(e)}")
        finally:
            # Update final status
            with self._lock:
                if not queue.cancelled and queue.status != "error":
                    queue.status = "completed"
                queue.completed_time = time.time()

                # Remove from active tasks
                if queue_id in self._active_tasks:
                    del self._active_tasks[queue_id]

                # Final progress notification
                progress_info = self.get_progress(queue_id)
                if progress_info:
                    self._notify_progress(queue_id, progress_info)

    async def _process_single_file_optimized(
        self,
        queue_id: str,
        item: FileQueueItem,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
        semaphore: asyncio.Semaphore,
        memory_context: Dict[str, Any],
    ) -> Optional[ConversionResult]:
        """
        Process a single file with memory optimization and monitoring.

        Args:
            queue_id: Queue identifier
            item: FileQueueItem to process
            processor_func: Function to process the file
            semaphore: Semaphore for concurrency control
            memory_context: Memory optimization context

        Returns:
            ConversionResult or None if cancelled/failed
        """
        async with semaphore:
            # Check if processing was cancelled
            with self._lock:
                if queue_id not in self._queues or self._queues[queue_id].cancelled:
                    return None

            # Mark item as started
            item.started_time = time.time()

            try:
                # Monitor memory usage during processing
                with memory_context["memory_monitor"].monitor_operation(
                    f"process_file_{Path(item.file_path).name}"
                ) as monitoring:
                    # Run the processor function in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        self._thread_pool,
                        self._process_with_memory_optimization,
                        processor_func,
                        item.file_path,
                        item.options,
                        memory_context,
                    )

                    # Add memory monitoring info to result
                    if result and hasattr(result, "__dict__"):
                        result.memory_stats = {
                            "peak_memory_mb": monitoring.get("memory_delta_mb", 0),
                            "processing_time": monitoring.get("duration", 0),
                            "gc_optimized": True,
                        }

                # Mark item as completed
                item.completed_time = time.time()
                item.result = result

                return result

            except Exception as e:
                # Mark item as failed
                item.completed_time = time.time()
                item.error = str(e)

                # Create error result
                error_result = ConversionResult(
                    file_path=item.file_path, success=False, error_message=str(e)
                )
                item.result = error_result

                return error_result

    def _process_with_memory_optimization(
        self,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
        file_path: str,
        options: ProcessingOptions,
        memory_context: Dict[str, Any],
    ) -> ConversionResult:
        """
        Process a file with memory optimization techniques.

        Args:
            processor_func: Function to process the file
            file_path: Path to the file
            options: Processing options
            memory_context: Memory optimization context

        Returns:
            ConversionResult
        """
        try:
            # Check memory before processing
            memory_context["memory_monitor"].check_memory_thresholds()

            # Process the file
            result = processor_func(file_path, options)

            # Trigger garbage collection after processing
            if memory_context["gc_optimizer"]:
                memory_context["gc_optimizer"].manual_collect()

            return result

        except Exception as e:
            raise ConversionError(
                f"Failed to process file with memory optimization: {str(e)}"
            )

    def get_memory_statistics(self) -> Dict[str, Any]:
        """
        Get memory usage statistics for the handler.

        Returns:
            Dictionary with memory statistics
        """
        stats = self._memory_stats.copy()

        if self.memory_monitor:
            current_usage = self.memory_monitor.get_memory_usage()
            stats.update(
                {
                    "current_usage_mb": current_usage.get("rss_mb", 0),
                    "current_usage_percent": current_usage.get("percent", 0),
                    "system_available_mb": current_usage.get("system_available_mb", 0),
                }
            )

        if self.memory_pool:
            pool_stats = self.memory_pool.get_stats()
            stats["memory_pool"] = pool_stats

        if self.gc_optimizer:
            gc_stats = self.gc_optimizer.get_gc_stats()
            stats["garbage_collection"] = gc_stats

        return stats

    def optimize_memory_usage(self) -> Dict[str, Any]:
        """
        Manually optimize memory usage by cleaning up resources.

        Returns:
            Dictionary with optimization results
        """
        optimization_results = {
            "initial_memory_mb": 0,
            "final_memory_mb": 0,
            "memory_freed_mb": 0,
            "objects_collected": 0,
            "actions_taken": [],
        }

        if not self.enable_memory_optimization:
            optimization_results["actions_taken"].append("Memory optimization disabled")
            return optimization_results

        # Get initial memory usage
        if self.memory_monitor:
            initial_usage = self.memory_monitor.get_memory_usage()
            optimization_results["initial_memory_mb"] = initial_usage.get("rss_mb", 0)

        # Clean up completed queues
        cleaned_queues = self.cleanup_completed_queues(max_age_hours=1.0)
        if cleaned_queues > 0:
            optimization_results["actions_taken"].append(
                f"Cleaned {cleaned_queues} old queues"
            )

        # Clear memory pool
        if self.memory_pool:
            self.memory_pool.clear()
            optimization_results["actions_taken"].append("Cleared memory pool")

        # Trigger garbage collection
        if self.gc_optimizer:
            gc_result = self.gc_optimizer.manual_collect()
            optimization_results["objects_collected"] = gc_result["objects_collected"]
            optimization_results["actions_taken"].append(
                f'Collected {gc_result["objects_collected"]} objects'
            )

        # Get final memory usage
        if self.memory_monitor:
            final_usage = self.memory_monitor.get_memory_usage()
            optimization_results["final_memory_mb"] = final_usage.get("rss_mb", 0)
            optimization_results["memory_freed_mb"] = (
                optimization_results["initial_memory_mb"]
                - optimization_results["final_memory_mb"]
            )

        return optimization_results

    def process_queue_parallel(
        self,
        queue_id: str,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
        use_cpu_intensive: bool = False,
    ) -> List[ConversionResult]:
        """
        Process queue using parallel processing for maximum performance.

        Args:
            queue_id: Queue identifier
            processor_func: Function to process individual files
            use_cpu_intensive: Whether to use CPU-intensive processing

        Returns:
            List of conversion results

        Raises:
            ValueError: If queue not found or parallel processing not enabled
        """
        if not self.enable_memory_optimization or not self.parallel_processor:
            raise ValueError("Parallel processing not enabled")

        with self._lock:
            if queue_id not in self._queues:
                raise ValueError(f"Queue not found: {queue_id}")

            queue = self._queues[queue_id]
            if queue.cancelled:
                return []

            queue.status = "processing"
            queue.started_time = time.time()

        try:
            # Convert queue items to processing tasks
            tasks = []
            for item in queue.items:
                task = ProcessingTask(
                    task_id=f"{queue_id}_{item.file_path}",
                    file_path=item.file_path,
                    options=item.options,
                )
                tasks.append(task)

            # Process using parallel processor
            if use_cpu_intensive:
                results = self.parallel_processor.process_cpu_intensive_batch(
                    tasks, processor_func
                )
            else:
                results = self.parallel_processor.process_io_intensive_batch(
                    tasks, processor_func
                )

            # Update queue items with results
            for i, (item, result) in enumerate(zip(queue.items, results)):
                item.result = result
                item.completed_time = time.time()
                if not result.success:
                    item.error = result.error_message

            return results

        except Exception as e:
            queue.status = "error"
            raise ConversionError(f"Parallel queue processing failed: {str(e)}")
        finally:
            with self._lock:
                if not queue.cancelled and queue.status != "error":
                    queue.status = "completed"
                queue.completed_time = time.time()

    def get_parallel_processing_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get parallel processing performance statistics.

        Returns:
            Dictionary with parallel processing stats or None if not enabled
        """
        if not self.parallel_processor:
            return None

        return self.parallel_processor.get_performance_stats()

    def benchmark_parallel_performance(
        self,
        test_files: List[str],
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
    ) -> Optional[Dict[str, Any]]:
        """
        Benchmark parallel processing performance with different configurations.

        Args:
            test_files: List of test files to use for benchmarking
            processor_func: Function to process files

        Returns:
            Benchmark results or None if parallel processing not enabled
        """
        if not self.parallel_processor:
            return None

        # Create test tasks
        test_tasks = []
        for i, file_path in enumerate(test_files):
            task = ProcessingTask(
                task_id=f"benchmark_task_{i}",
                file_path=file_path,
                options=ProcessingOptions(),
            )
            test_tasks.append(task)

        # Define test configurations
        cpu_count = os.cpu_count() or 1
        test_configs = [
            {"cpu_workers": 1, "io_workers": 2},
            {"cpu_workers": max(1, cpu_count // 2), "io_workers": cpu_count},
            {"cpu_workers": cpu_count, "io_workers": cpu_count * 2},
            {"cpu_workers": cpu_count * 2, "io_workers": cpu_count * 4},
        ]

        return self.parallel_processor.benchmark_performance(
            test_tasks, processor_func, test_configs
        )

    def __del__(self):
        """Cleanup resources when the handler is destroyed."""
        try:
            if hasattr(self, "_thread_pool"):
                self._thread_pool.shutdown(wait=False)
        except Exception:
            pass  # Ignore cleanup errors
