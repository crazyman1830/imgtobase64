"""
Domain exceptions for the image converter system.

This module provides a comprehensive exception hierarchy with error codes
and user-friendly messages for better error handling and user experience.
"""

from .base import ErrorCode, ImageConverterError
from .cache import CacheError
from .file_system import FileNotFoundError, FileSystemError, PermissionError
from .processing import ConversionError, CorruptedFileError, ProcessingError
from .queue import ProcessingQueueFullError, QueueError
from .rate_limiting import RateLimitError, RateLimitExceededError
from .security import SecurityError, SecurityThreatDetectedError
from .validation import FileSizeError, UnsupportedFormatError, ValidationError

__all__ = [
    # Base exceptions
    "ImageConverterError",
    "ErrorCode",
    # Validation exceptions
    "ValidationError",
    "UnsupportedFormatError",
    "FileSizeError",
    # File system exceptions
    "FileSystemError",
    "FileNotFoundError",
    "PermissionError",
    # Processing exceptions
    "ProcessingError",
    "ConversionError",
    "CorruptedFileError",
    # Security exceptions
    "SecurityError",
    "SecurityThreatDetectedError",
    # Cache exceptions
    "CacheError",
    # Rate limiting exceptions
    "RateLimitError",
    "RateLimitExceededError",
    # Queue exceptions
    "QueueError",
    "ProcessingQueueFullError",
]
