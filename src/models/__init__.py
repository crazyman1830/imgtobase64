"""
Data models for the image base64 converter.
"""
from .models import (
    ConversionResult,
    ImageConverterError,
    UnsupportedFormatError,
    FileNotFoundError,
    PermissionError,
    CorruptedFileError,
    ConversionError,
    ProcessingQueueFullError,
    SecurityThreatDetectedError,
    CacheError,
    RateLimitExceededError
)
from .processing_options import (
    ProcessingOptions,
    ProgressInfo,
    SecurityScanResult
)

__all__ = [
    'ConversionResult',
    'ImageConverterError',
    'UnsupportedFormatError',
    'FileNotFoundError',
    'PermissionError',
    'CorruptedFileError',
    'ConversionError',
    'ProcessingQueueFullError',
    'SecurityThreatDetectedError',
    'CacheError',
    'RateLimitExceededError',
    'ProcessingOptions',
    'ProgressInfo',
    'SecurityScanResult'
]