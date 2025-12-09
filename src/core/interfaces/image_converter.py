"""
Image converter interface definition.

This module defines the IImageConverter protocol that establishes the contract
for image conversion operations.
"""

from typing import Optional, Protocol

from ...models.models import ConversionResult
from ...models.processing_options import ProcessingOptions


class IImageConverter(Protocol):
    """
    Protocol defining the interface for image conversion operations.

    This interface establishes the contract for converting images to base64 format
    and performing related validation operations.
    """

    def convert_to_base64(
        self, file_path: str, options: Optional[ProcessingOptions] = None
    ) -> ConversionResult:
        """
        Convert an image file to base64 format.

        Args:
            file_path: Path to the image file to convert
            options: Optional processing options for the conversion

        Returns:
            ConversionResult object containing conversion details and result
        """
        ...

    def validate_format(self, file_path: str) -> bool:
        """
        Validate if the given file has a supported image format.

        Args:
            file_path: Path to the image file to validate

        Returns:
            True if the file format is supported, False otherwise
        """
        ...

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
        ...

    def get_supported_formats(self) -> set[str]:
        """
        Get the set of supported image file extensions.

        Returns:
            Set of supported file extensions (e.g., {'.png', '.jpg', '.jpeg'})
        """
        ...
