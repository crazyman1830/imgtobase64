"""
Data models for the image base64 converter.
"""
from dataclasses import dataclass


@dataclass
class ConversionResult:
    """
    Data class to hold the result of an image conversion operation.
    
    Attributes:
        file_path: Path to the original image file
        success: Whether the conversion was successful
        base64_data: The base64 encoded string (empty if conversion failed)
        data_uri: Complete data URI format string (empty if conversion failed)
        error_message: Error message if conversion failed (empty if successful)
        file_size: Size of the original file in bytes
        mime_type: MIME type of the image file
        image: PIL Image object (for base64 to image conversion)
        format: Image format (PNG, JPEG, etc.)
        size: Image dimensions as tuple (width, height)
    """
    file_path: str
    success: bool
    base64_data: str = ""
    data_uri: str = ""
    error_message: str = ""
    file_size: int = 0
    mime_type: str = ""
    image: object = None
    format: str = ""
    size: tuple = (0, 0)

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