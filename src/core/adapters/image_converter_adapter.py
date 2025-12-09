"""
Legacy ImageConverter adapter for backward compatibility.

This adapter maintains the original ImageConverter interface while using
the new refactored service layer underneath.
"""

import base64
from pathlib import Path
from typing import Dict, Set

from ...models.models import ConversionResult
from ...models.processing_options import ProcessingOptions
from ..config.app_config import AppConfig
from ..factories.service_factory import ServiceFactory
from ..services.image_conversion_service import ImageConversionService


class ImageConverterAdapter:
    """
    Adapter class that maintains the original ImageConverter interface.

    This class provides backward compatibility by wrapping the new
    ImageConversionService with the original ImageConverter API.
    """

    def __init__(self):
        """Initialize the adapter with the new service layer."""
        # Initialize with default configuration
        config = AppConfig.from_env()

        # Create the new service using the factory
        self._service = ServiceFactory.create_conversion_service(config)

        # Maintain the original interface properties
        self.supported_formats: Set[str] = self._service.get_supported_formats()

        # MIME type mapping for supported formats (for backward compatibility)
        self.mime_type_mapping: Dict[str, str] = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }

        # Legacy properties for compatibility
        self.error_handler = None  # Will be handled by the service
        self.logger = None  # Will be handled by the service

    def is_supported_format(self, file_path: str) -> bool:
        """
        Check if the given file has a supported image format.

        Args:
            file_path: Path to the image file

        Returns:
            True if the file format is supported, False otherwise
        """
        try:
            return self._service.validate_image_format(file_path)
        except Exception:
            # For backward compatibility, return False instead of raising
            return False

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
        try:
            return self._service.get_image_mime_type(file_path)
        except Exception as e:
            # Import here to avoid circular imports
            from ...models.models import UnsupportedFormatError

            # Convert to legacy exception type
            file_extension = Path(file_path).suffix.lower()
            supported_list = ", ".join(sorted(self.supported_formats))
            raise UnsupportedFormatError(
                f"Unsupported file format '{file_extension}'. "
                f"Supported formats: {supported_list}"
            )

    def convert_to_base64(self, file_path: str) -> ConversionResult:
        """
        Convert an image file to base64 format.

        This method maintains the original interface while using the new service layer.

        Args:
            file_path: Path to the image file to convert

        Returns:
            ConversionResult object containing conversion details
        """
        try:
            # Use default processing options for backward compatibility
            options = ProcessingOptions()

            # Call the new service
            result = self._service.convert_image(file_path, options)

            # The result should already be in the correct format
            return result

        except Exception as e:
            # Create a failed result for backward compatibility
            result = ConversionResult(file_path=file_path, success=False)
            result.error_message = str(e)
            return result

    def base64_to_image(self, base64_data: str, output_format: str = "PNG"):
        """
        Convert base64 data to image.

        This method maintains backward compatibility with the original interface.
        Note: This functionality is not implemented in the new service layer yet,
        so we maintain the original implementation for now.

        Args:
            base64_data: Base64 encoded image data
            output_format: Output image format (PNG, JPEG, etc.)

        Returns:
            ConversionResult object with image data
        """
        try:
            from io import BytesIO

            from PIL import Image
        except ImportError:
            result = ConversionResult(file_path="base64_input", success=False)
            result.error_message = (
                "PIL (Pillow) is required for base64 to image conversion"
            )
            return result

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

        This method maintains backward compatibility with the original interface.

        Args:
            base64_data: Base64 encoded data to validate

        Returns:
            True if valid image data, False otherwise
        """
        try:
            from io import BytesIO

            from PIL import Image
        except ImportError:
            return False

        try:
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

    # Additional methods for accessing new functionality while maintaining compatibility

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics from the underlying service.

        This is a new method that provides access to caching functionality
        while maintaining the adapter pattern.

        Returns:
            Dictionary containing cache statistics
        """
        return self._service.get_cache_stats()

    def clear_cache(self) -> None:
        """
        Clear the conversion cache.

        This is a new method that provides access to cache management
        while maintaining the adapter pattern.
        """
        self._service.clear_cache()

    def get_supported_formats(self) -> Set[str]:
        """
        Get the set of supported image file extensions.

        This method provides access to the supported formats from the service.

        Returns:
            Set of supported file extensions
        """
        return self._service.get_supported_formats()
