"""
Memory optimization utilities for the image base64 converter.

This module provides memory optimization features including:
- Streaming processing for large files
- Memory pool management for image processing
- Garbage collection optimization
- Memory usage monitoring
"""

import gc
import io
import os
import sys
import time
import weakref
from contextlib import contextmanager
from threading import Lock
from typing import Any, BinaryIO, Dict, Iterator, Optional, Union

import psutil
from PIL import Image
from PIL.ImageFile import ImageFile

from ..models.models import ConversionError


class MemoryPool:
    """
    Memory pool for reusing image processing buffers to reduce allocation overhead.

    This class manages a pool of BytesIO buffers that can be reused across
    image processing operations to minimize memory allocation and garbage collection.
    """

    def __init__(
        self,
        initial_size: int = 5,
        max_size: int = 20,
        buffer_size: int = 10 * 1024 * 1024,
    ):
        """
        Initialize the memory pool.

        Args:
            initial_size: Initial number of buffers to create
            max_size: Maximum number of buffers to keep in pool
            buffer_size: Size of each buffer in bytes (default: 10MB)
        """
        self.max_size = max_size
        self.buffer_size = buffer_size
        self._pool = []
        self._lock = Lock()
        self._stats = {"created": 0, "reused": 0, "returned": 0, "discarded": 0}

        # Pre-allocate initial buffers
        for _ in range(initial_size):
            self._pool.append(io.BytesIO())
            self._stats["created"] += 1

    def get_buffer(self) -> io.BytesIO:
        """
        Get a buffer from the pool or create a new one.

        Returns:
            BytesIO buffer ready for use
        """
        with self._lock:
            if self._pool:
                buffer = self._pool.pop()
                buffer.seek(0)
                buffer.truncate(0)
                self._stats["reused"] += 1
                return buffer
            else:
                # Create new buffer if pool is empty
                buffer = io.BytesIO()
                self._stats["created"] += 1
                return buffer

    def return_buffer(self, buffer: io.BytesIO) -> None:
        """
        Return a buffer to the pool for reuse.

        Args:
            buffer: BytesIO buffer to return
        """
        if buffer is None:
            return

        with self._lock:
            if len(self._pool) < self.max_size:
                # Clear the buffer and return to pool
                buffer.seek(0)
                buffer.truncate(0)
                self._pool.append(buffer)
                self._stats["returned"] += 1
            else:
                # Pool is full, discard the buffer
                self._stats["discarded"] += 1

    @contextmanager
    def get_managed_buffer(self):
        """
        Context manager for automatic buffer management.

        Yields:
            BytesIO buffer that will be automatically returned to pool
        """
        buffer = self.get_buffer()
        try:
            yield buffer
        finally:
            self.return_buffer(buffer)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        with self._lock:
            return {
                "pool_size": len(self._pool),
                "max_size": self.max_size,
                "buffer_size": self.buffer_size,
                "stats": self._stats.copy(),
            }

    def clear(self) -> None:
        """Clear all buffers from the pool."""
        with self._lock:
            self._pool.clear()
            self._stats["discarded"] += len(self._pool)


class StreamingImageProcessor:
    """
    Streaming image processor for handling large files without loading entire content into memory.

    This class provides methods for processing large images by streaming data
    in chunks rather than loading the entire file into memory at once.
    """

    def __init__(
        self, chunk_size: int = 8192, memory_pool: Optional[MemoryPool] = None
    ):
        """
        Initialize the streaming processor.

        Args:
            chunk_size: Size of chunks to read at a time (default: 8KB)
            memory_pool: Optional memory pool for buffer reuse
        """
        self.chunk_size = chunk_size
        self.memory_pool = memory_pool or MemoryPool()

        # Configure PIL for streaming
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        Image.MAX_IMAGE_PIXELS = None  # Remove PIL's default limit

    def stream_file_to_buffer(
        self, file_path: str, max_size: Optional[int] = None
    ) -> io.BytesIO:
        """
        Stream a file to a buffer in chunks to control memory usage.

        Args:
            file_path: Path to the file to stream
            max_size: Maximum file size to process (None for no limit)

        Returns:
            BytesIO buffer containing the file data

        Raises:
            ConversionError: If file is too large or streaming fails
        """
        if not os.path.exists(file_path):
            raise ConversionError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)

        if max_size and file_size > max_size:
            raise ConversionError(
                f"File too large: {file_size} bytes (max: {max_size} bytes)"
            )

        try:
            buffer = self.memory_pool.get_buffer()

            with open(file_path, "rb") as file:
                while True:
                    chunk = file.read(self.chunk_size)
                    if not chunk:
                        break
                    buffer.write(chunk)

            buffer.seek(0)
            return buffer

        except Exception as e:
            self.memory_pool.return_buffer(buffer)
            raise ConversionError(f"Failed to stream file: {str(e)}")

    def stream_image_from_buffer(self, buffer: io.BytesIO) -> Image.Image:
        """
        Load an image from a buffer with memory optimization.

        Args:
            buffer: BytesIO buffer containing image data

        Returns:
            PIL Image object

        Raises:
            ConversionError: If image loading fails
        """
        try:
            buffer.seek(0)

            # Use PIL's lazy loading to minimize memory usage
            image = Image.open(buffer)

            # Force load the image data to ensure it's accessible
            # even after the buffer is returned to the pool
            image.load()

            return image

        except Exception as e:
            raise ConversionError(f"Failed to load image from buffer: {str(e)}")

    def process_large_image_streaming(
        self, file_path: str, processor_func, max_memory_mb: int = 100
    ) -> Image.Image:
        """
        Process a large image using streaming to control memory usage.

        Args:
            file_path: Path to the image file
            processor_func: Function to process the image
            max_memory_mb: Maximum memory to use in MB

        Returns:
            Processed PIL Image object

        Raises:
            ConversionError: If processing fails
        """
        max_size = max_memory_mb * 1024 * 1024

        try:
            # Stream file to buffer
            with self.memory_pool.get_managed_buffer() as buffer:
                # Read file in chunks
                with open(file_path, "rb") as file:
                    total_read = 0
                    while True:
                        chunk = file.read(self.chunk_size)
                        if not chunk:
                            break

                        total_read += len(chunk)
                        if total_read > max_size:
                            raise ConversionError(
                                f"File exceeds memory limit: {total_read} bytes > {max_size} bytes"
                            )

                        buffer.write(chunk)

                # Load and process image
                buffer.seek(0)
                image = Image.open(buffer)
                image.load()

                # Process the image
                processed_image = processor_func(image)

                # Explicitly delete the original image to free memory
                del image
                gc.collect()

                return processed_image

        except Exception as e:
            raise ConversionError(f"Failed to process large image: {str(e)}")

    def get_image_info_streaming(self, file_path: str) -> Dict[str, Any]:
        """
        Get image information without loading the entire image into memory.

        Args:
            file_path: Path to the image file

        Returns:
            Dictionary with image information

        Raises:
            ConversionError: If info extraction fails
        """
        try:
            with self.memory_pool.get_managed_buffer() as buffer:
                # Read just enough data to get image headers
                with open(file_path, "rb") as file:
                    # Read first 64KB which should contain headers for most formats
                    header_data = file.read(65536)
                    buffer.write(header_data)

                buffer.seek(0)

                # Open image to read metadata without loading pixel data
                with Image.open(buffer) as image:
                    info = {
                        "size": image.size,
                        "width": image.width,
                        "height": image.height,
                        "format": image.format,
                        "mode": image.mode,
                        "file_size": os.path.getsize(file_path),
                    }

                    # Add format-specific info if available
                    if hasattr(image, "info") and image.info:
                        info["metadata"] = dict(image.info)

                    return info

        except Exception as e:
            raise ConversionError(f"Failed to get image info: {str(e)}")


class MemoryMonitor:
    """
    Memory usage monitor for tracking and optimizing memory consumption.

    This class provides utilities for monitoring memory usage during
    image processing operations and triggering optimization when needed.
    """

    def __init__(
        self, warning_threshold_mb: int = 500, critical_threshold_mb: int = 1000
    ):
        """
        Initialize the memory monitor.

        Args:
            warning_threshold_mb: Memory usage threshold for warnings (MB)
            critical_threshold_mb: Memory usage threshold for critical actions (MB)
        """
        self.warning_threshold = warning_threshold_mb * 1024 * 1024
        self.critical_threshold = critical_threshold_mb * 1024 * 1024
        self.process = psutil.Process()
        self._callbacks = []

    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get current memory usage information.

        Returns:
            Dictionary with memory usage details
        """
        try:
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()

            # Get system memory info
            system_memory = psutil.virtual_memory()

            return {
                "rss": memory_info.rss,  # Resident Set Size
                "vms": memory_info.vms,  # Virtual Memory Size
                "percent": memory_percent,
                "rss_mb": memory_info.rss / (1024 * 1024),
                "vms_mb": memory_info.vms / (1024 * 1024),
                "system_total_mb": system_memory.total / (1024 * 1024),
                "system_available_mb": system_memory.available / (1024 * 1024),
                "system_percent": system_memory.percent,
            }
        except Exception as e:
            return {"error": str(e)}

    def check_memory_thresholds(self) -> Dict[str, Any]:
        """
        Check if memory usage exceeds configured thresholds.

        Returns:
            Dictionary with threshold check results
        """
        usage = self.get_memory_usage()

        if "error" in usage:
            return usage

        rss = usage["rss"]
        result = {
            "usage": usage,
            "warning": rss > self.warning_threshold,
            "critical": rss > self.critical_threshold,
            "warning_threshold_mb": self.warning_threshold / (1024 * 1024),
            "critical_threshold_mb": self.critical_threshold / (1024 * 1024),
        }

        # Trigger callbacks if thresholds are exceeded
        if result["critical"]:
            self._trigger_callbacks("critical", usage)
        elif result["warning"]:
            self._trigger_callbacks("warning", usage)

        return result

    def add_callback(self, callback, threshold_type: str = "warning"):
        """
        Add a callback to be triggered when memory thresholds are exceeded.

        Args:
            callback: Function to call when threshold is exceeded
            threshold_type: 'warning' or 'critical'
        """
        self._callbacks.append((callback, threshold_type))

    def _trigger_callbacks(self, threshold_type: str, usage: Dict[str, Any]):
        """
        Trigger registered callbacks for the specified threshold type.

        Args:
            threshold_type: Type of threshold exceeded
            usage: Current memory usage information
        """
        for callback, callback_threshold in self._callbacks:
            if callback_threshold == threshold_type:
                try:
                    callback(threshold_type, usage)
                except Exception as e:
                    print(f"Error in memory callback: {e}")

    @contextmanager
    def monitor_operation(self, operation_name: str = "operation"):
        """
        Context manager for monitoring memory usage during an operation.

        Args:
            operation_name: Name of the operation being monitored

        Yields:
            Dictionary with monitoring results
        """
        start_usage = self.get_memory_usage()
        start_time = time.time()

        monitoring_data = {
            "operation_name": operation_name,
            "start_usage": start_usage,
            "start_time": start_time,
        }

        try:
            yield monitoring_data
        finally:
            end_usage = self.get_memory_usage()
            end_time = time.time()

            monitoring_data.update(
                {
                    "end_usage": end_usage,
                    "end_time": end_time,
                    "duration": end_time - start_time,
                    "memory_delta_mb": (
                        end_usage.get("rss", 0) - start_usage.get("rss", 0)
                    )
                    / (1024 * 1024),
                }
            )


class GarbageCollectionOptimizer:
    """
    Garbage collection optimizer for improving memory management during image processing.

    This class provides utilities for optimizing Python's garbage collection
    to reduce memory fragmentation and improve performance.
    """

    def __init__(self):
        """Initialize the garbage collection optimizer."""
        self.original_thresholds = gc.get_threshold()
        self.stats = {
            "manual_collections": 0,
            "objects_collected": 0,
            "time_spent": 0.0,
        }

    def optimize_for_image_processing(self):
        """
        Optimize garbage collection settings for image processing workloads.

        This adjusts GC thresholds to reduce the frequency of automatic
        garbage collection during intensive image processing operations.
        """
        # Increase thresholds to reduce automatic GC frequency
        # This is beneficial for image processing where we have many temporary objects
        gc.set_threshold(1000, 15, 15)  # Default is usually (700, 10, 10)

        # Disable automatic GC during critical operations
        # We'll manually trigger it at appropriate times
        gc.disable()

    def restore_default_settings(self):
        """Restore original garbage collection settings."""
        gc.set_threshold(*self.original_thresholds)
        gc.enable()

    def manual_collect(self, generation: Optional[int] = None) -> Dict[str, Any]:
        """
        Manually trigger garbage collection with timing and statistics.

        Args:
            generation: GC generation to collect (None for all)

        Returns:
            Dictionary with collection statistics
        """
        start_time = time.time()

        if generation is None:
            collected = gc.collect()
        else:
            collected = gc.collect(generation)

        end_time = time.time()
        duration = end_time - start_time

        self.stats["manual_collections"] += 1
        self.stats["objects_collected"] += collected
        self.stats["time_spent"] += duration

        return {
            "objects_collected": collected,
            "duration": duration,
            "generation": generation,
            "total_stats": self.stats.copy(),
        }

    @contextmanager
    def optimized_context(self):
        """
        Context manager for optimized garbage collection during image processing.

        This temporarily optimizes GC settings and restores them afterwards.
        """
        self.optimize_for_image_processing()
        try:
            yield self
        finally:
            # Perform final cleanup
            self.manual_collect()
            self.restore_default_settings()

    def get_gc_stats(self) -> Dict[str, Any]:
        """
        Get current garbage collection statistics.

        Returns:
            Dictionary with GC statistics
        """
        return {
            "thresholds": gc.get_threshold(),
            "counts": gc.get_count(),
            "stats": gc.get_stats(),
            "optimizer_stats": self.stats.copy(),
            "enabled": gc.isenabled(),
        }


# Global instances for easy access
_memory_pool = MemoryPool()
_memory_monitor = MemoryMonitor()
_gc_optimizer = GarbageCollectionOptimizer()


def get_memory_pool() -> MemoryPool:
    """Get the global memory pool instance."""
    return _memory_pool


def get_memory_monitor() -> MemoryMonitor:
    """Get the global memory monitor instance."""
    return _memory_monitor


def get_gc_optimizer() -> GarbageCollectionOptimizer:
    """Get the global garbage collection optimizer instance."""
    return _gc_optimizer


@contextmanager
def optimized_memory_context(max_memory_mb: int = 500):
    """
    Context manager for optimized memory usage during image processing.

    Args:
        max_memory_mb: Maximum memory usage threshold in MB

    This combines memory monitoring, garbage collection optimization,
    and automatic cleanup for optimal memory usage.
    """
    monitor = get_memory_monitor()
    gc_optimizer = get_gc_optimizer()

    # Set up memory monitoring
    monitor.warning_threshold = max_memory_mb * 1024 * 1024 * 0.8  # 80% of max
    monitor.critical_threshold = max_memory_mb * 1024 * 1024  # 100% of max

    # Add automatic GC callback for critical memory usage
    def memory_callback(threshold_type, usage):
        if threshold_type == "critical":
            gc_optimizer.manual_collect()

    monitor.add_callback(memory_callback, "critical")

    with gc_optimizer.optimized_context():
        with monitor.monitor_operation("optimized_memory_context") as monitoring_data:
            try:
                yield {
                    "memory_pool": get_memory_pool(),
                    "memory_monitor": monitor,
                    "gc_optimizer": gc_optimizer,
                    "monitoring_data": monitoring_data,
                }
            finally:
                # Final cleanup
                gc_optimizer.manual_collect()
                get_memory_pool().clear()
