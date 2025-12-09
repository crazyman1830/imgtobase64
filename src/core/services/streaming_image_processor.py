"""
Streaming image processor with memory optimization.

This module provides memory-efficient image processing capabilities
using streaming and object pooling for large files.
"""

import base64
import gc
from io import BytesIO
from typing import Any, Callable, Iterator, Optional

from ...domain.exceptions.file_system import FileNotFoundError
from ...domain.exceptions.processing import ImageProcessingError, ProcessingError
from ..base.result import Result
from ..utils.memory_pool import get_bytearray_pool, get_string_builder_pool
from .streaming_file_handler import StreamingFileHandler


class StreamingImageProcessor:
    """
    Memory-efficient image processor using streaming and object pooling.

    This processor handles large image files by processing them in chunks
    and using memory pools to reduce garbage collection pressure.
    """

    def __init__(self, file_handler: Optional[StreamingFileHandler] = None):
        """
        Initialize the streaming image processor.

        Args:
            file_handler: Optional file handler (creates default if None)
        """
        self.file_handler = file_handler or StreamingFileHandler()

        # Memory optimization settings
        self.chunk_size = 64 * 1024  # 64KB chunks
        self.gc_threshold = 100  # Force GC after processing this many chunks
        self._processed_chunks = 0

    def convert_to_base64_streaming(self, file_path: str) -> str:
        """
        Convert an image file to base64 using streaming to handle large files.

        Args:
            file_path: Path to the image file

        Returns:
            Base64 encoded string

        Raises:
            FileNotFoundError: If the file doesn't exist
            ProcessingError: If conversion fails
        """
        result = self.convert_to_base64_streaming_safe(file_path)
        if result.is_success:
            return result.value
        else:
            error = result.error
            if isinstance(error, FileNotFoundError):
                raise error
            else:
                raise ProcessingError(f"Error converting to base64: {error}")

    def convert_to_base64_streaming_safe(
        self, file_path: str
    ) -> Result[str, Exception]:
        """
        Safely convert an image file to base64 using streaming with Result pattern.

        Args:
            file_path: Path to the image file

        Returns:
            Result containing base64 string or error
        """
        try:
            # Validate input
            if not file_path or not isinstance(file_path, str):
                return Result.failure(
                    ValueError("File path must be a non-empty string")
                )

            # Check if file exists
            if not self.file_handler.file_exists(file_path):
                return Result.failure(FileNotFoundError(f"File not found: {file_path}"))

            # Check if it's a large file that should use streaming
            if self.file_handler.is_large_file(file_path, threshold_mb=50):
                return self._convert_large_file_to_base64(file_path)
            else:
                return self._convert_small_file_to_base64(file_path)

        except Exception as e:
            return Result.failure(
                ProcessingError(f"Unexpected error in base64 conversion: {str(e)}")
            )

    def _convert_small_file_to_base64(self, file_path: str) -> Result[str, Exception]:
        """
        Convert a small file to base64 using standard method.

        Args:
            file_path: Path to the file

        Returns:
            Result containing base64 string or error
        """
        try:
            # Read file normally for small files
            file_content = self.file_handler.read_file(file_path)
            base64_content = base64.b64encode(file_content).decode("utf-8")
            return Result.success(base64_content)

        except Exception as e:
            return Result.failure(
                ProcessingError(f"Error converting small file to base64: {str(e)}")
            )

    def _convert_large_file_to_base64(self, file_path: str) -> Result[str, Exception]:
        """
        Convert a large file to base64 using streaming and memory pooling.

        Args:
            file_path: Path to the file

        Returns:
            Result containing base64 string or error
        """
        try:
            # Get string builder from pool for efficient string concatenation
            string_pool = get_string_builder_pool()

            with string_pool.get_object() as base64_parts:
                # Process file in chunks
                chunks_result = self.file_handler.read_file_chunks_safe(
                    file_path, self.chunk_size
                )
                if not chunks_result.is_success:
                    return Result.failure(chunks_result.error)

                self._processed_chunks = 0

                # Convert each chunk to base64
                for chunk in chunks_result.value:
                    if not chunk:  # Skip empty chunks
                        continue

                    # Convert chunk to base64
                    chunk_b64 = base64.b64encode(chunk).decode("utf-8")
                    base64_parts.append(chunk_b64)

                    self._processed_chunks += 1

                    # Periodic garbage collection for memory management
                    if self._processed_chunks % self.gc_threshold == 0:
                        gc.collect()

                # Join all base64 parts
                result_b64 = "".join(base64_parts)

                # Final garbage collection
                gc.collect()

                return Result.success(result_b64)

        except Exception as e:
            return Result.failure(
                ProcessingError(f"Error converting large file to base64: {str(e)}")
            )

    def process_image_streaming(
        self,
        file_path: str,
        processor: Callable[[bytes], bytes],
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Process an image file using streaming with a custom processor function.

        Args:
            file_path: Path to the input image file
            processor: Function to process each chunk
            output_path: Optional path to save processed image

        Returns:
            Path to output file if output_path provided, None otherwise

        Raises:
            FileNotFoundError: If the input file doesn't exist
            ProcessingError: If processing fails
        """
        result = self.process_image_streaming_safe(file_path, processor, output_path)
        if result.is_success:
            return result.value
        else:
            error = result.error
            if isinstance(error, FileNotFoundError):
                raise error
            else:
                raise ProcessingError(f"Error in streaming image processing: {error}")

    def process_image_streaming_safe(
        self,
        file_path: str,
        processor: Callable[[bytes], bytes],
        output_path: Optional[str] = None,
    ) -> Result[Optional[str], Exception]:
        """
        Safely process an image file using streaming with Result pattern.

        Args:
            file_path: Path to the input image file
            processor: Function to process each chunk
            output_path: Optional path to save processed image

        Returns:
            Result containing output path or None
        """
        try:
            # Validate inputs
            if not file_path or not isinstance(file_path, str):
                return Result.failure(
                    ValueError("File path must be a non-empty string")
                )

            if not callable(processor):
                return Result.failure(
                    ValueError("Processor must be a callable function")
                )

            # Check if input file exists
            if not self.file_handler.file_exists(file_path):
                return Result.failure(
                    FileNotFoundError(f"Input file not found: {file_path}")
                )

            # Process file using streaming
            processed_chunks_result = self.file_handler.process_file_streaming_safe(
                file_path, processor, self.chunk_size
            )

            if not processed_chunks_result.is_success:
                return Result.failure(processed_chunks_result.error)

            # If output path is provided, save processed data
            if output_path:
                return self._save_processed_chunks(
                    processed_chunks_result.value, output_path
                )
            else:
                # Just consume the iterator to process the file
                for _ in processed_chunks_result.value:
                    pass
                return Result.success(None)

        except Exception as e:
            return Result.failure(
                ProcessingError(f"Unexpected error in streaming processing: {str(e)}")
            )

    def _save_processed_chunks(
        self, chunks: Iterator[bytes], output_path: str
    ) -> Result[str, Exception]:
        """
        Save processed chunks to an output file.

        Args:
            chunks: Iterator of processed chunks
            output_path: Path to save the output

        Returns:
            Result containing output path or error
        """
        try:
            # Get buffer from pool for efficient writing
            buffer_pool = get_bytearray_pool(self.chunk_size)

            with buffer_pool.get_object() as write_buffer:
                with self.file_handler.open_file_streaming(
                    output_path, "wb"
                ) as output_file:
                    self._processed_chunks = 0

                    for chunk in chunks:
                        if chunk:
                            output_file.write(chunk)

                            self._processed_chunks += 1

                            # Periodic garbage collection
                            if self._processed_chunks % self.gc_threshold == 0:
                                gc.collect()

                    # Final garbage collection
                    gc.collect()

            return Result.success(output_path)

        except Exception as e:
            return Result.failure(
                ProcessingError(f"Error saving processed chunks: {str(e)}")
            )

    def calculate_image_hash_streaming(
        self, file_path: str, algorithm: str = "sha256"
    ) -> str:
        """
        Calculate hash of an image file using streaming.

        Args:
            file_path: Path to the image file
            algorithm: Hash algorithm to use

        Returns:
            Hexadecimal hash string

        Raises:
            FileNotFoundError: If the file doesn't exist
            ProcessingError: If hash calculation fails
        """
        try:
            return self.file_handler.calculate_file_hash_streaming(file_path, algorithm)
        except FileNotFoundError:
            raise
        except Exception as e:
            raise ProcessingError(f"Error calculating image hash: {str(e)}")

    def copy_image_streaming(self, source_path: str, dest_path: str) -> bool:
        """
        Copy an image file using streaming for memory efficiency.

        Args:
            source_path: Path to the source image
            dest_path: Path to the destination

        Returns:
            True if copy was successful

        Raises:
            FileNotFoundError: If the source file doesn't exist
            ProcessingError: If copy fails
        """
        try:
            return self.file_handler.copy_file_streaming(
                source_path, dest_path, self.chunk_size
            )
        except FileNotFoundError:
            raise
        except Exception as e:
            raise ProcessingError(f"Error copying image: {str(e)}")

    def get_memory_usage_estimate(self, file_path: str) -> int:
        """
        Estimate memory usage for processing a file.

        Args:
            file_path: Path to the file

        Returns:
            Estimated memory usage in bytes
        """
        try:
            base_usage = self.file_handler.get_memory_usage_estimate(
                file_path, self.chunk_size
            )

            # Add overhead for base64 encoding (approximately 4/3 of original size)
            encoding_overhead = int(self.chunk_size * 1.34)

            # Add overhead for string building
            string_overhead = 1024

            return base_usage + encoding_overhead + string_overhead

        except Exception:
            # Return conservative estimate if calculation fails
            return self.chunk_size * 3

    def optimize_chunk_size_for_file(self, file_path: str) -> int:
        """
        Determine optimal chunk size for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            Optimal chunk size in bytes
        """
        try:
            file_size = self.file_handler.get_file_size(file_path)

            # For very small files, use smaller chunks
            if file_size < 1024 * 1024:  # < 1MB
                return min(16 * 1024, file_size)  # 16KB or file size

            # For medium files, use standard chunk size
            elif file_size < 100 * 1024 * 1024:  # < 100MB
                return 64 * 1024  # 64KB

            # For large files, use larger chunks for efficiency
            else:
                return 256 * 1024  # 256KB

        except Exception:
            # Return default if optimization fails
            return self.chunk_size

    def set_chunk_size(self, chunk_size: int) -> None:
        """
        Set the chunk size for streaming operations.

        Args:
            chunk_size: New chunk size in bytes
        """
        if chunk_size > 0:
            self.chunk_size = min(chunk_size, StreamingFileHandler.MAX_CHUNK_SIZE)

    def force_garbage_collection(self) -> None:
        """Force garbage collection to free memory."""
        gc.collect()
        self._processed_chunks = 0
