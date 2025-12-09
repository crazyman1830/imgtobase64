"""
Memory-optimized image conversion service.

This module provides a memory-optimized version of the image conversion service
that integrates streaming processing, memory pooling, and garbage collection optimization.
"""

import time
import weakref
from typing import Any, Dict, Optional

from ...domain.exceptions.base import ImageConverterError
from ...domain.exceptions.file_system import FileNotFoundError
from ...domain.exceptions.processing import ProcessingError
from ...domain.exceptions.validation import ValidationError
from ...models.models import ConversionResult
from ...models.processing_options import ProcessingOptions
from ..interfaces.cache_manager import ICacheManager
from ..interfaces.file_handler import IFileHandler
from ..interfaces.image_converter import IImageConverter
from ..utils.memory_optimizer import MemoryOptimizer, get_global_memory_optimizer
from ..utils.memory_pool import get_bytearray_pool, get_string_builder_pool
from .image_conversion_service import ImageConversionService
from .streaming_image_processor import StreamingImageProcessor


class MemoryOptimizedConversionService(ImageConversionService):
    """
    Memory-optimized image conversion service.

    This service extends the base ImageConversionService with memory optimization
    features including streaming processing, object pooling, and intelligent
    garbage collection management.
    """

    def __init__(
        self,
        converter: IImageConverter,
        file_handler: IFileHandler,
        cache_manager: ICacheManager,
        memory_optimizer: Optional[MemoryOptimizer] = None,
        large_file_threshold_mb: int = 50,
    ):
        """
        Initialize the memory-optimized conversion service.

        Args:
            converter: Image converter implementation
            file_handler: File handler implementation
            cache_manager: Cache manager implementation
            memory_optimizer: Optional memory optimizer (uses global if None)
            large_file_threshold_mb: Threshold for using streaming processing
        """
        super().__init__(converter, file_handler, cache_manager)

        self._memory_optimizer = memory_optimizer or get_global_memory_optimizer()
        self._streaming_processor = StreamingImageProcessor(file_handler)
        self._large_file_threshold_mb = large_file_threshold_mb

        # Memory optimization settings
        self._optimization_strategy = "balanced"
        self._auto_gc_enabled = True
        self._memory_tracking_enabled = True

        # Statistics tracking
        self._conversion_stats = {
            "total_conversions": 0,
            "streaming_conversions": 0,
            "memory_optimized_conversions": 0,
            "peak_memory_usage": 0,
            "total_memory_saved": 0,
        }

        # Weak references for cleanup tracking
        self._tracked_objects = weakref.WeakSet()

    def convert_image(
        self, file_path: str, options: Optional[ProcessingOptions] = None
    ) -> ConversionResult:
        """
        Convert an image file with memory optimization.

        This method automatically chooses between standard and streaming conversion
        based on file size and applies appropriate memory optimization strategies.

        Args:
            file_path: Path to the image file to convert
            options: Optional processing options for the conversion

        Returns:
            ConversionResult object containing conversion details and result

        Raises:
            ValidationError: If input validation fails
            FileNotFoundError: If the file doesn't exist
            ProcessingError: If conversion fails
        """
        start_time = time.time()

        # Start memory monitoring
        if self._memory_tracking_enabled:
            self._memory_optimizer.monitor.set_baseline()

        try:
            # Validate input first
            self._validate_input(file_path, options)

            # Determine if we should use streaming based on file size
            should_use_streaming = self._should_use_streaming(file_path)

            # Choose conversion strategy
            if should_use_streaming:
                result = self._convert_with_streaming(file_path, options, start_time)
                self._conversion_stats["streaming_conversions"] += 1
            else:
                result = self._convert_with_optimization(file_path, options, start_time)
                self._conversion_stats["memory_optimized_conversions"] += 1

            # Update statistics
            self._conversion_stats["total_conversions"] += 1
            self._update_memory_stats()

            return result

        except ImageConverterError:
            raise
        except Exception as e:
            processing_time = time.time() - start_time
            raise ProcessingError(
                f"Unexpected error during optimized image conversion: {str(e)}",
                processing_time=processing_time,
            )
        finally:
            # Cleanup if auto GC is enabled
            if self._auto_gc_enabled:
                self._perform_cleanup()

    def _should_use_streaming(self, file_path: str) -> bool:
        """
        Determine if streaming should be used for the given file.

        Args:
            file_path: Path to the file

        Returns:
            True if streaming should be used
        """
        try:
            file_size_bytes = self._file_handler.get_file_size(file_path)
            file_size_mb = file_size_bytes / (1024 * 1024)
            return file_size_mb > self._large_file_threshold_mb
        except Exception:
            # If we can't determine file size, use standard conversion
            return False

    def _convert_with_streaming(
        self, file_path: str, options: Optional[ProcessingOptions], start_time: float
    ) -> ConversionResult:
        """
        Convert image using streaming for large files.

        Args:
            file_path: Path to the image file
            options: Processing options
            start_time: Conversion start time

        Returns:
            ConversionResult object
        """
        # Use memory optimization context for large files
        with self._memory_optimizer.optimized_context("large_objects"):
            # Generate cache key
            cache_key = self._cache_manager.get_cache_key(file_path, options)

            # Check cache first
            cached_result = self._cache_manager.get_cached_result(cache_key)
            if cached_result is not None:
                cached_result.cache_hit = True
                cached_result.processing_time = time.time() - start_time
                return cached_result

            # Perform streaming conversion
            try:
                base64_content = self._streaming_processor.convert_to_base64_streaming(
                    file_path
                )

                # Create result
                result = ConversionResult(
                    success=True,
                    base64_content=base64_content,
                    file_path=file_path,
                    processing_time=time.time() - start_time,
                    cache_hit=False,
                    processing_options=options,
                    file_size=self._file_handler.get_file_size(file_path),
                    mime_type=self._converter.get_mime_type(file_path),
                )

                # Cache the result
                self._cache_manager.store_result(cache_key, result)

                return result

            except Exception as e:
                raise ProcessingError(f"Streaming conversion failed: {str(e)}")

    def _convert_with_optimization(
        self, file_path: str, options: Optional[ProcessingOptions], start_time: float
    ) -> ConversionResult:
        """
        Convert image using standard method with memory optimization.

        Args:
            file_path: Path to the image file
            options: Processing options
            start_time: Conversion start time

        Returns:
            ConversionResult object
        """
        # Use balanced optimization for smaller files
        with self._memory_optimizer.optimized_context(self._optimization_strategy):
            # Use object pools for temporary objects
            string_pool = get_string_builder_pool()

            with string_pool.get_object() as temp_strings:
                # Track temporary objects
                if self._memory_tracking_enabled:
                    self._memory_optimizer.monitor.track_object(
                        temp_strings, "temp_string_list"
                    )

                # Perform standard conversion with memory tracking
                return super().convert_image(file_path, options)

    def _update_memory_stats(self) -> None:
        """Update memory usage statistics."""
        if not self._memory_tracking_enabled:
            return

        try:
            current_stats = self._memory_optimizer.monitor.get_current_memory_stats()
            peak_memory = self._memory_optimizer.monitor.get_peak_memory()

            if peak_memory > self._conversion_stats["peak_memory_usage"]:
                self._conversion_stats["peak_memory_usage"] = peak_memory

            # Update peak memory tracking
            self._memory_optimizer.monitor.update_peak_memory()

        except Exception:
            # Ignore errors in statistics tracking
            pass

    def _perform_cleanup(self) -> None:
        """Perform memory cleanup operations."""
        try:
            # Clean up tracked objects
            dead_count = len([obj for obj in self._tracked_objects if obj is None])

            # Force garbage collection if needed
            if dead_count > 10 or self._conversion_stats["total_conversions"] % 50 == 0:
                cleanup_stats = self._memory_optimizer.force_cleanup()

                # Update statistics
                if "objects_collected" in cleanup_stats.get("gc_statistics", {}):
                    collected = cleanup_stats["gc_statistics"]["objects_collected"]
                    self._conversion_stats["total_memory_saved"] += (
                        collected * 100
                    )  # Rough estimate

        except Exception:
            # Ignore cleanup errors
            pass

    def set_optimization_strategy(self, strategy: str) -> None:
        """
        Set the memory optimization strategy.

        Args:
            strategy: Strategy name ('balanced', 'large_objects', 'small_objects')
        """
        if strategy in ["balanced", "large_objects", "small_objects"]:
            self._optimization_strategy = strategy

    def set_large_file_threshold(self, threshold_mb: int) -> None:
        """
        Set the threshold for using streaming processing.

        Args:
            threshold_mb: Threshold in megabytes
        """
        if threshold_mb > 0:
            self._large_file_threshold_mb = threshold_mb

    def enable_auto_gc(self, enabled: bool = True) -> None:
        """
        Enable or disable automatic garbage collection.

        Args:
            enabled: Whether to enable auto GC
        """
        self._auto_gc_enabled = enabled

    def enable_memory_tracking(self, enabled: bool = True) -> None:
        """
        Enable or disable memory usage tracking.

        Args:
            enabled: Whether to enable memory tracking
        """
        self._memory_tracking_enabled = enabled

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive memory and conversion statistics.

        Returns:
            Dictionary with memory and conversion statistics
        """
        memory_report = self._memory_optimizer.get_optimization_report()

        return {
            "conversion_stats": self._conversion_stats.copy(),
            "memory_report": memory_report,
            "optimization_settings": {
                "strategy": self._optimization_strategy,
                "large_file_threshold_mb": self._large_file_threshold_mb,
                "auto_gc_enabled": self._auto_gc_enabled,
                "memory_tracking_enabled": self._memory_tracking_enabled,
            },
            "cache_stats": self.get_cache_stats(),
        }

    def force_memory_cleanup(self) -> Dict[str, Any]:
        """
        Force comprehensive memory cleanup and return statistics.

        Returns:
            Dictionary with cleanup statistics
        """
        # Force streaming processor cleanup
        self._streaming_processor.force_garbage_collection()

        # Force optimizer cleanup
        cleanup_stats = self._memory_optimizer.force_cleanup()

        # Clear weak references
        self._tracked_objects.clear()

        return cleanup_stats

    def optimize_for_batch_processing(self) -> None:
        """
        Optimize settings for batch processing of multiple files.
        """
        self.set_optimization_strategy("large_objects")
        self.enable_auto_gc(True)
        self.enable_memory_tracking(True)

        # Start global optimization
        self._memory_optimizer.start_optimization("large_objects")

    def restore_default_optimization(self) -> None:
        """
        Restore default optimization settings.
        """
        self.set_optimization_strategy("balanced")
        self.enable_auto_gc(True)
        self.enable_memory_tracking(True)

        # Stop global optimization
        self._memory_optimizer.stop_optimization()

    def get_memory_usage_estimate(self, file_path: str) -> int:
        """
        Estimate memory usage for converting a specific file.

        Args:
            file_path: Path to the file

        Returns:
            Estimated memory usage in bytes
        """
        try:
            if self._should_use_streaming(file_path):
                return self._streaming_processor.get_memory_usage_estimate(file_path)
            else:
                # For standard conversion, estimate based on file size
                file_size = self._file_handler.get_file_size(file_path)
                # Base64 encoding increases size by ~33%, plus overhead
                return int(file_size * 1.5)
        except Exception:
            # Return conservative estimate
            return 10 * 1024 * 1024  # 10MB
