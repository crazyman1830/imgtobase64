"""
Image to base64 converter module.
"""

import base64
import os
import time
from pathlib import Path
from typing import Dict, Set

from ..domain.exceptions.base import ImageConverterError
from ..domain.exceptions.file_system import (
    FileNotFoundError,
)
from ..domain.exceptions.file_system import PermissionError as DomainPermissionError
from ..domain.exceptions.processing import CorruptedFileError
from ..domain.exceptions.validation import UnsupportedFormatError
from ..models.models import ConversionResult
from .error_handler import get_error_handler
from .structured_logger import get_structured_logger


class ImageConverter:
    """
    Handles conversion of image files to base64 format.

    Supports PNG, JPG, JPEG, GIF, BMP, and WEBP image formats.
    """

    def __init__(self):
        """Initialize the ImageConverter with supported formats and MIME type mappings."""
        # Supported image file extensions
        self.supported_formats: Set[str] = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
            ".webp",
        }

        # MIME type mapping for supported formats
        self.mime_type_mapping: Dict[str, str] = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }

        # Initialize error handler and logger
        self.error_handler = get_error_handler()
        self.logger = get_structured_logger("image_converter")

    def is_supported_format(self, file_path: str) -> bool:
        """
        Check if the given file has a supported image format.

        Args:
            file_path: Path to the image file

        Returns:
            True if the file format is supported, False otherwise
        """
        file_extension = Path(file_path).suffix.lower()
        return file_extension in self.supported_formats

    def get_mime_type(self, file_path: str) -> str:
        """
        Get the MIME type for the given image file.

        Args:
            file_path: Path to the image file

        Returns:
            MIME type string for the file

        Raises:
            UnsupportedFormatError: If the file format is not supported
        """
        file_extension = Path(file_path).suffix.lower()

        if file_extension not in self.supported_formats:
            raise UnsupportedFormatError(file_extension, list(self.supported_formats))

        return self.mime_type_mapping[file_extension]

    def convert_to_base64(self, file_path: str) -> ConversionResult:
        """
        Convert an image file to base64 format.

        Args:
            file_path: Path to the image file to convert

        Returns:
            ConversionResult object containing conversion details
        """
        start_time = time.time()
        with self.logger.operation_context(
            "convert_to_base64", file_path=file_path
        ) as operation_id:
            result = ConversionResult(file_path=file_path, success=False)

            try:
                # Check if file exists
                if not os.path.exists(file_path):
                    exception = FileNotFoundError(file_path=file_path)
                    error_context = self.error_handler.handle_error(
                        exception, operation="convert_to_base64", file_path=file_path
                    )
                    result.error_message = error_context.user_message
                    return result

                # Check if it's a file (not a directory)
                if not os.path.isfile(file_path):
                    exception = FileNotFoundError(f"Path is not a file: {file_path}")
                    error_context = self.error_handler.handle_error(
                        exception, operation="convert_to_base64", file_path=file_path
                    )
                    result.error_message = error_context.user_message
                    return result

                # Check if format is supported
                if not self.is_supported_format(file_path):
                    file_extension = Path(file_path).suffix.lower()
                    exception = UnsupportedFormatError(
                        file_extension, list(self.supported_formats)
                    )
                    error_context = self.error_handler.handle_error(
                        exception, operation="convert_to_base64", file_path=file_path
                    )
                    result.error_message = error_context.user_message
                    return result

                # Get MIME type
                try:
                    mime_type = self.get_mime_type(file_path)
                    result.mime_type = mime_type
                except UnsupportedFormatError as e:
                    error_context = self.error_handler.handle_error(
                        e, operation="convert_to_base64", file_path=file_path
                    )
                    result.error_message = error_context.user_message
                    return result

                # Read file and get size
                try:
                    with open(file_path, "rb") as image_file:
                        image_data = image_file.read()
                        result.file_size = len(image_data)

                        # Convert to base64
                        base64_encoded = base64.b64encode(image_data).decode("utf-8")
                        result.base64_data = base64_encoded

                        # Create data URI
                        result.data_uri = f"data:{mime_type};base64,{base64_encoded}"

                        result.success = True
                        result.processing_time = time.time() - start_time

                except PermissionError as e:
                    # Catch the built-in PermissionError and wrap it in our custom exception
                    custom_exception = DomainPermissionError(file_path=file_path)
                    error_context = self.error_handler.handle_error(
                        custom_exception,
                        operation="convert_to_base64",
                        file_path=file_path,
                    )
                    result.error_message = error_context.user_message
                except IOError as e:
                    error_context = self.error_handler.handle_error(
                        e, operation="convert_to_base64", file_path=file_path
                    )
                    result.error_message = error_context.user_message
                except Exception as e:
                    error_context = self.error_handler.handle_error(
                        e, operation="convert_to_base64", file_path=file_path
                    )
                    result.error_message = error_context.user_message
            except Exception as e:
                error_context = self.error_handler.handle_error(
                    e, operation="convert_to_base64", file_path=file_path
                )
                result.error_message = error_context.user_message

        return result

    def base64_to_image(self, base64_data: str, output_format: str = "PNG"):
        """
        Convert base64 data to image.

        Args:
            base64_data: Base64 encoded image data
            output_format: Output image format (PNG, JPEG, etc.)

        Returns:
            ConversionResult object with image data
        """
        from io import BytesIO

        from PIL import Image

        result = ConversionResult(file_path="base64_input", success=False)

        try:
            # Clean base64 data (remove data URI prefix if present)
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]

            # Decode base64
            image_data = base64.b64decode(base64_data)

            # Create PIL Image
            image = Image.open(BytesIO(image_data))

            # Store image info
            result.image = image
            result.format = output_format
            result.size = image.size
            result.file_size = len(image_data)
            result.success = True

            return result

        except Exception as e:
            result.error_message = f"Error converting base64 to image: {str(e)}"
            return result

    def validate_base64_image(self, base64_data: str) -> bool:
        """
        Validate if base64 data represents a valid image.

        Args:
            base64_data: Base64 encoded data to validate

        Returns:
            True if valid image data, False otherwise
        """
        try:
            from io import BytesIO

            from PIL import Image

            # Clean base64 data
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]

            # Try to decode and open as image
            image_data = base64.b64decode(base64_data)
            image = Image.open(BytesIO(image_data))

            # Try to verify the image
            image.verify()
            return True

        except Exception:
            return False
