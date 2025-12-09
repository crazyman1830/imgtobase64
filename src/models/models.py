"""
Data models for the image base64 converter.
"""

from dataclasses import dataclass
from typing import Optional

from .processing_options import ProcessingOptions, SecurityScanResult


@dataclass
class ConversionResult:
    """
    Result of an image conversion operation.

    Attributes:
        file_path: Path to the original image file
        success: Whether the conversion was successful
        base64_data: Base64 encoded string (empty if failed)
        data_uri: Complete data URI format string (empty if failed)
        error_message: Error message if failed (empty if successful)
        file_size: Size of the original file in bytes
        mime_type: MIME type of the image file
        image: PIL Image object (for base64 to image conversion)
        format: Image format (PNG, JPEG, etc.)
        size: Image dimensions as tuple (width, height)
        processing_options: Processing options used for conversion
        processing_time: Time taken for processing in seconds
        cache_hit: Whether result was retrieved from cache
        security_scan_result: Security scan result if performed
        thumbnail_data: Base64 encoded thumbnail for preview
    """

    file_path: str
    success: bool
    base64_data: str = ""
    data_uri: str = ""
    error_message: str = ""
    file_size: int = 0
    mime_type: str = ""
    image: Optional[object] = None
    format: str = ""
    size: tuple[int, int] = (0, 0)
    processing_options: Optional[ProcessingOptions] = None
    processing_time: float = 0.0
    cache_hit: bool = False
    security_scan_result: Optional[SecurityScanResult] = None
    thumbnail_data: str = ""


# Custom Exception Classes


class ImageConverterError(Exception):
    """Base exception class for image converter errors."""

    pass


class UnsupportedFormatError(ImageConverterError):
    """Exception raised when an unsupported image format is encountered."""

    pass


class FileNotFoundError(ImageConverterError):
    """Exception raised when a file cannot be found."""

    pass


class PermissionError(ImageConverterError):
    """Exception raised when there are insufficient permissions to read a file."""

    pass


class CorruptedFileError(ImageConverterError):
    """Exception raised when a file is corrupted or invalid."""

    pass


class ConversionError(ImageConverterError):
    """Exception raised during conversion operations."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ProcessingQueueFullError(ImageConverterError):
    """Exception raised when the processing queue is full."""

    pass


class SecurityThreatDetectedError(ImageConverterError):
    """Exception raised when a security threat is detected."""

    pass


class CacheError(ImageConverterError):
    """Exception raised for cache-related errors."""

    pass


class RateLimitExceededError(ImageConverterError):
    """Exception raised when rate limit is exceeded."""

    pass
