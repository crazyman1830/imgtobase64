"""
Data models for the image base64 converter.
"""

from .models import (
    CacheError,
    ConversionError,
    ConversionResult,
    CorruptedFileError,
    FileNotFoundError,
    ImageConverterError,
    PermissionError,
    ProcessingQueueFullError,
    RateLimitExceededError,
    SecurityThreatDetectedError,
    UnsupportedFormatError,
)
from .processing_options import ProcessingOptions, ProgressInfo, SecurityScanResult

__all__ = [
    "ConversionResult",
    "ImageConverterError",
    "UnsupportedFormatError",
    "FileNotFoundError",
    "PermissionError",
    "CorruptedFileError",
    "ConversionError",
    "ProcessingQueueFullError",
    "SecurityThreatDetectedError",
    "CacheError",
    "RateLimitExceededError",
    "ProcessingOptions",
    "ProgressInfo",
    "SecurityScanResult",
]
