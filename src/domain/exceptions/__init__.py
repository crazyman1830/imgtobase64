"""
Domain exceptions for the image converter system.

This module provides a comprehensive exception hierarchy with error codes
and user-friendly messages for better error handling and user experience.
"""

from .base import ImageConverterError, ErrorCode
from .validation import ValidationError, UnsupportedFormatError, FileSizeError
from .file_system import FileSystemError, FileNotFoundError, PermissionError
from .processing import ProcessingError, ConversionError, CorruptedFileError
from .security import SecurityError, SecurityThreatDetectedError
from .cache import CacheError
from .rate_limiting import RateLimitError, RateLimitExceededError
from .queue import QueueError, ProcessingQueueFullError

__all__ = [
    # Base exceptions
    'ImageConverterError',
    'ErrorCode',
    
    # Validation exceptions
    'ValidationError',
    'UnsupportedFormatError', 
    'FileSizeError',
    
    # File system exceptions
    'FileSystemError',
    'FileNotFoundError',
    'PermissionError',
    
    # Processing exceptions
    'ProcessingError',
    'ConversionError',
    'CorruptedFileError',
    
    # Security exceptions
    'SecurityError',
    'SecurityThreatDetectedError',
    
    # Cache exceptions
    'CacheError',
    
    # Rate limiting exceptions
    'RateLimitError',
    'RateLimitExceededError',
    
    # Queue exceptions
    'QueueError',
    'ProcessingQueueFullError'
]