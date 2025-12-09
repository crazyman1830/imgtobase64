"""
Streaming file handler service implementation.

This module provides the StreamingFileHandler class that implements
memory-efficient file operations using streaming and chunked processing
for large files.
"""

import hashlib
import os
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional

from ...domain.exceptions.file_system import FileNotFoundError, FileSystemError
from ..base.result import Result
from .file_handler_service import FileHandlerService


class StreamingFileHandler(FileHandlerService):
    """
    Enhanced file handler service with streaming capabilities.

    This service extends the base FileHandlerService with memory-efficient
    streaming operations for large files, including chunked reading,
    streaming processing, and memory-optimized operations.
    """

    # Default chunk size: 64KB - good balance between memory usage and I/O efficiency
    DEFAULT_CHUNK_SIZE = 64 * 1024

    # Maximum chunk size: 1MB - prevents excessive memory usage
    MAX_CHUNK_SIZE = 1024 * 1024

    def __init__(self, default_chunk_size: int = DEFAULT_CHUNK_SIZE):
        """
        Initialize the streaming file handler service.

        Args:
            default_chunk_size: Default size for file chunks in bytes
        """
        super().__init__()
        self.default_chunk_size = min(default_chunk_size, self.MAX_CHUNK_SIZE)

    def read_file_chunks(
        self, file_path: str, chunk_size: Optional[int] = None
    ) -> Iterator[bytes]:
        """
        Read a file in chunks to minimize memory usage.

        Args:
            file_path: Path to the file to read
            chunk_size: Size of each chunk in bytes (uses default if None)

        Yields:
            Chunks of file content as bytes

        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If the file cannot be read
            FileSystemError: For other file system errors
        """
        result = self.read_file_chunks_safe(file_path, chunk_size)
        if result.is_success:
            yield from result.value
        else:
            # Convert Result error to exception for interface compatibility
            error = result.error
            if isinstance(error, (FileNotFoundError, PermissionError)):
                raise error
            else:
                raise FileSystemError(f"Error reading file chunks: {error}")

    def read_file_chunks_safe(
        self, file_path: str, chunk_size: Optional[int] = None
    ) -> Result[Iterator[bytes], Exception]:
        """
        Safely read a file in chunks using Result pattern.

        Args:
            file_path: Path to the file to read
            chunk_size: Size of each chunk in bytes (uses default if None)

        Returns:
            Result containing iterator of file chunks or error
        """
        try:
            # Validate input
            if not file_path or not isinstance(file_path, str):
                return Result.failure(
                    ValueError("File path must be a non-empty string")
                )

            if chunk_size is not None:
                if not isinstance(chunk_size, int) or chunk_size <= 0:
                    return Result.failure(
                        ValueError("Chunk size must be a positive integer")
                    )
                chunk_size = min(chunk_size, self.MAX_CHUNK_SIZE)
            else:
                chunk_size = self.default_chunk_size

            # Check if file exists and is readable
            file_check = self.file_exists_safe(file_path)
            if not file_check.is_success:
                return Result.failure(file_check.error)

            if not file_check.value:
                return Result.failure(FileNotFoundError(f"File not found: {file_path}"))

            # Create generator function for chunks
            def chunk_generator():
                try:
                    with open(file_path, "rb") as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            yield chunk
                except Exception as e:
                    raise FileSystemError(
                        f"Error reading chunk from {file_path}: {str(e)}"
                    )

            return Result.success(chunk_generator())

        except Exception as e:
            return Result.failure(
                FileSystemError(
                    f"Unexpected error setting up chunk reading for {file_path}: {str(e)}"
                )
            )

    def process_file_streaming(
        self,
        file_path: str,
        processor: Callable[[bytes], bytes],
        chunk_size: Optional[int] = None,
    ) -> Iterator[bytes]:
        """
        Process a file in streaming fashion with a processor function.

        Args:
            file_path: Path to the file to process
            processor: Function that processes each chunk
            chunk_size: Size of each chunk in bytes

        Yields:
            Processed chunks as bytes

        Raises:
            FileNotFoundError: If the file doesn't exist
            FileSystemError: For processing errors
        """
        result = self.process_file_streaming_safe(file_path, processor, chunk_size)
        if result.is_success:
            yield from result.value
        else:
            error = result.error
            if isinstance(error, FileNotFoundError):
                raise error
            else:
                raise FileSystemError(f"Error in streaming processing: {error}")

    def process_file_streaming_safe(
        self,
        file_path: str,
        processor: Callable[[bytes], bytes],
        chunk_size: Optional[int] = None,
    ) -> Result[Iterator[bytes], Exception]:
        """
        Safely process a file in streaming fashion using Result pattern.

        Args:
            file_path: Path to the file to process
            processor: Function that processes each chunk
            chunk_size: Size of each chunk in bytes

        Returns:
            Result containing iterator of processed chunks or error
        """
        try:
            # Validate processor function
            if not callable(processor):
                return Result.failure(
                    ValueError("Processor must be a callable function")
                )

            # Get chunk iterator
            chunks_result = self.read_file_chunks_safe(file_path, chunk_size)
            if not chunks_result.is_success:
                return Result.failure(chunks_result.error)

            # Create processing generator
            def processing_generator():
                try:
                    for chunk in chunks_result.value:
                        processed_chunk = processor(chunk)
                        if processed_chunk:  # Only yield non-empty chunks
                            yield processed_chunk
                except Exception as e:
                    raise FileSystemError(f"Error processing chunk: {str(e)}")

            return Result.success(processing_generator())

        except Exception as e:
            return Result.failure(
                FileSystemError(f"Unexpected error in streaming processing: {str(e)}")
            )

    def calculate_file_hash_streaming(
        self, file_path: str, algorithm: str = "sha256"
    ) -> str:
        """
        Calculate file hash using streaming to handle large files efficiently.

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use ('md5', 'sha1', 'sha256', etc.)

        Returns:
            Hexadecimal hash string

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the algorithm is not supported
            FileSystemError: For other errors
        """
        result = self.calculate_file_hash_streaming_safe(file_path, algorithm)
        if result.is_success:
            return result.value
        else:
            error = result.error
            if isinstance(error, (FileNotFoundError, ValueError)):
                raise error
            else:
                raise FileSystemError(f"Error calculating hash: {error}")

    def calculate_file_hash_streaming_safe(
        self, file_path: str, algorithm: str = "sha256"
    ) -> Result[str, Exception]:
        """
        Safely calculate file hash using streaming with Result pattern.

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use

        Returns:
            Result containing hash string or error
        """
        try:
            # Validate algorithm
            try:
                hasher = hashlib.new(algorithm)
            except ValueError:
                return Result.failure(
                    ValueError(f"Unsupported hash algorithm: {algorithm}")
                )

            # Get chunk iterator
            chunks_result = self.read_file_chunks_safe(file_path)
            if not chunks_result.is_success:
                return Result.failure(chunks_result.error)

            # Process chunks to calculate hash
            for chunk in chunks_result.value:
                hasher.update(chunk)

            return Result.success(hasher.hexdigest())

        except Exception as e:
            return Result.failure(
                FileSystemError(
                    f"Unexpected error calculating hash for {file_path}: {str(e)}"
                )
            )

    def copy_file_streaming(
        self, source_path: str, dest_path: str, chunk_size: Optional[int] = None
    ) -> bool:
        """
        Copy a file using streaming to handle large files efficiently.

        Args:
            source_path: Path to the source file
            dest_path: Path to the destination file
            chunk_size: Size of each chunk in bytes

        Returns:
            True if copy was successful

        Raises:
            FileNotFoundError: If the source file doesn't exist
            PermissionError: If there are permission issues
            FileSystemError: For other errors
        """
        result = self.copy_file_streaming_safe(source_path, dest_path, chunk_size)
        if result.is_success:
            return result.value
        else:
            error = result.error
            if isinstance(error, (FileNotFoundError, PermissionError)):
                raise error
            else:
                raise FileSystemError(f"Error copying file: {error}")

    def copy_file_streaming_safe(
        self, source_path: str, dest_path: str, chunk_size: Optional[int] = None
    ) -> Result[bool, Exception]:
        """
        Safely copy a file using streaming with Result pattern.

        Args:
            source_path: Path to the source file
            dest_path: Path to the destination file
            chunk_size: Size of each chunk in bytes

        Returns:
            Result containing success status or error
        """
        try:
            # Validate inputs
            if not source_path or not isinstance(source_path, str):
                return Result.failure(
                    ValueError("Source path must be a non-empty string")
                )

            if not dest_path or not isinstance(dest_path, str):
                return Result.failure(
                    ValueError("Destination path must be a non-empty string")
                )

            # Create destination directory if needed
            dest_dir = os.path.dirname(dest_path)
            if dest_dir and not os.path.exists(dest_dir):
                try:
                    os.makedirs(dest_dir, exist_ok=True)
                except OSError as e:
                    return Result.failure(
                        PermissionError(f"Cannot create directory {dest_dir}: {str(e)}")
                    )

            # Get chunk iterator for source file
            chunks_result = self.read_file_chunks_safe(source_path, chunk_size)
            if not chunks_result.is_success:
                return Result.failure(chunks_result.error)

            # Copy file chunk by chunk
            try:
                with open(dest_path, "wb") as dest_file:
                    for chunk in chunks_result.value:
                        dest_file.write(chunk)

                return Result.success(True)

            except OSError as e:
                return Result.failure(
                    PermissionError(
                        f"Error writing to destination {dest_path}: {str(e)}"
                    )
                )

        except Exception as e:
            return Result.failure(
                FileSystemError(f"Unexpected error copying file: {str(e)}")
            )

    @contextmanager
    def open_file_streaming(
        self, file_path: str, mode: str = "rb", chunk_size: Optional[int] = None
    ):
        """
        Context manager for streaming file operations.

        Args:
            file_path: Path to the file
            mode: File open mode
            chunk_size: Chunk size for operations

        Yields:
            File-like object with streaming capabilities

        Raises:
            FileNotFoundError: If the file doesn't exist (for read modes)
            PermissionError: If there are permission issues
        """
        # Validate inputs
        if not file_path or not isinstance(file_path, str):
            raise ValueError("File path must be a non-empty string")

        if chunk_size is not None:
            if not isinstance(chunk_size, int) or chunk_size <= 0:
                raise ValueError("Chunk size must be a positive integer")
            chunk_size = min(chunk_size, self.MAX_CHUNK_SIZE)
        else:
            chunk_size = self.default_chunk_size

        # For read modes, check if file exists
        if "r" in mode:
            if not self.file_exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

        # For write modes, create directory if needed
        if "w" in mode or "a" in mode:
            file_dir = os.path.dirname(file_path)
            if file_dir and not os.path.exists(file_dir):
                try:
                    os.makedirs(file_dir, exist_ok=True)
                except OSError as e:
                    raise PermissionError(
                        f"Cannot create directory {file_dir}: {str(e)}"
                    )

        try:
            with open(file_path, mode) as file_obj:
                # Add chunk_size attribute to file object for convenience
                file_obj.chunk_size = chunk_size
                yield file_obj
        except OSError as e:
            if "r" in mode:
                raise FileNotFoundError(f"Cannot open file for reading: {file_path}")
            else:
                raise PermissionError(f"Cannot open file for writing: {file_path}")

    def get_memory_usage_estimate(
        self, file_path: str, chunk_size: Optional[int] = None
    ) -> int:
        """
        Estimate memory usage for streaming operations on a file.

        Args:
            file_path: Path to the file
            chunk_size: Chunk size to use for estimation

        Returns:
            Estimated memory usage in bytes

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        if chunk_size is None:
            chunk_size = self.default_chunk_size

        # For streaming operations, memory usage is primarily the chunk size
        # plus some overhead for buffers and objects
        overhead = 1024  # Estimated overhead in bytes
        return chunk_size + overhead

    def is_large_file(self, file_path: str, threshold_mb: int = 100) -> bool:
        """
        Check if a file is considered large and should use streaming.

        Args:
            file_path: Path to the file
            threshold_mb: Size threshold in megabytes

        Returns:
            True if file is larger than threshold

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        file_size = self.get_file_size(file_path)
        threshold_bytes = threshold_mb * 1024 * 1024
        return file_size > threshold_bytes
