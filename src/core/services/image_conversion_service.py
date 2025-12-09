"""
Image conversion service implementation.

This module provides the ImageConversionService class that implements
the business logic for image conversion operations with dependency injection.
"""

import time
from typing import Optional

from ...domain.exceptions.base import ImageConverterError
from ...domain.exceptions.file_system import FileNotFoundError
from ...domain.exceptions.processing import ProcessingError
from ...domain.exceptions.validation import ValidationError
from ...models.models import ConversionResult
from ...models.processing_options import ProcessingOptions
from ..interfaces.cache_manager import ICacheManager
from ..interfaces.file_handler import IFileHandler
from ..interfaces.image_converter import IImageConverter


class ImageConversionService:
    """
    Service class that orchestrates image conversion operations.

    This service integrates caching, validation, error handling, and the actual
    conversion process through dependency injection of specialized components.
    """

    def __init__(
        self,
        converter: IImageConverter,
        file_handler: IFileHandler,
        cache_manager: ICacheManager,
    ):
        """
        Initialize the image conversion service with dependencies.

        Args:
            converter: Image converter implementation
            file_handler: File handler implementation
            cache_manager: Cache manager implementation
        """
        self._converter = converter
        self._file_handler = file_handler
        self._cache_manager = cache_manager

    def convert_image(
        self, file_path: str, options: Optional[ProcessingOptions] = None
    ) -> ConversionResult:
        """
        Convert an image file to base64 format with integrated caching and validation.

        This method provides the main business logic for image conversion:
        1. Validates the input file
        2. Checks cache for existing result
        3. Performs conversion if not cached
        4. Stores result in cache
        5. Returns the conversion result

        Args:
            file_path: Path to the image file to convert
            options: Optional processing options for the conversion

        Returns:
            ConversionResult object containing conversion details and result

        Raises:
            ValidationError: If input validation fails
            FileNotFoundError: If the file doesn't exist
            ProcessingError: If conversion fails
        """
        start_time = time.time()

        try:
            # Step 1: Validate input
            self._validate_input(file_path, options)

            # Step 2: Generate cache key
            cache_key = self._cache_manager.get_cache_key(file_path, options)

            # Step 3: Check cache first
            cached_result = self._cache_manager.get_cached_result(cache_key)
            if cached_result is not None:
                cached_result.cache_hit = True
                return cached_result

            # Step 4: Perform conversion
            result = self._perform_conversion(file_path, options)

            # Step 5: Store in cache if successful
            if result.success:
                self._cache_manager.store_result(cache_key, result)

            # Step 6: Set processing time
            result.processing_time = time.time() - start_time
            result.cache_hit = False

            return result

        except ImageConverterError:
            # Re-raise known errors
            raise
        except Exception as e:
            # Wrap unexpected errors
            processing_time = time.time() - start_time
            raise ProcessingError(
                f"Unexpected error during image conversion: {str(e)}",
                processing_time=processing_time,
            )

    def validate_image_format(self, file_path: str) -> bool:
        """
        Validate if the given file has a supported image format.

        Args:
            file_path: Path to the image file to validate

        Returns:
            True if the file format is supported, False otherwise

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        try:
            # Check if file exists first
            if not self._file_handler.file_exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # Use converter to validate format
            return self._converter.validate_format(file_path)

        except FileNotFoundError:
            raise
        except Exception as e:
            raise ValidationError(f"Error validating image format: {str(e)}")

    def get_supported_formats(self) -> set[str]:
        """
        Get the set of supported image file extensions.

        Returns:
            Set of supported file extensions
        """
        return self._converter.get_supported_formats()

    def get_image_mime_type(self, file_path: str) -> str:
        """
        Get the MIME type for the given image file.

        Args:
            file_path: Path to the image file

        Returns:
            MIME type string for the file

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValidationError: If the file format is not supported
        """
        try:
            # Check if file exists first
            if not self._file_handler.file_exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # Get MIME type from converter
            return self._converter.get_mime_type(file_path)

        except FileNotFoundError:
            raise
        except Exception as e:
            raise ValidationError(f"Error getting MIME type: {str(e)}")

    def _validate_input(
        self, file_path: str, options: Optional[ProcessingOptions]
    ) -> None:
        """
        Validate input parameters for conversion.

        Args:
            file_path: Path to the image file
            options: Processing options (can be None)

        Raises:
            ValidationError: If validation fails
            FileNotFoundError: If the file doesn't exist
        """
        # Validate file path
        if not file_path or not isinstance(file_path, str):
            raise ValidationError("File path must be a non-empty string")

        # Check if file exists and is accessible
        if not self._file_handler.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Validate file format
        if not self._converter.validate_format(file_path):
            supported_formats = ", ".join(
                sorted(self._converter.get_supported_formats())
            )
            raise ValidationError(
                f"Unsupported file format. Supported formats: {supported_formats}"
            )

        # Validate processing options if provided
        if options is not None:
            self._validate_processing_options(options)

    def _validate_processing_options(self, options: ProcessingOptions) -> None:
        """
        Validate processing options.

        Args:
            options: Processing options to validate

        Raises:
            ValidationError: If options are invalid
        """
        if not isinstance(options, ProcessingOptions):
            raise ValidationError(
                "Processing options must be a ProcessingOptions instance"
            )

        # Additional validation can be added here
        # The ProcessingOptions class already has __post_init__ validation

    def _perform_conversion(
        self, file_path: str, options: Optional[ProcessingOptions]
    ) -> ConversionResult:
        """
        Perform the actual image conversion.

        Args:
            file_path: Path to the image file
            options: Processing options

        Returns:
            ConversionResult object

        Raises:
            ProcessingError: If conversion fails
        """
        try:
            # Delegate to the converter implementation
            result = self._converter.convert_to_base64(file_path, options)

            # Set processing options in result
            result.processing_options = options

            return result

        except Exception as e:
            raise ProcessingError(f"Image conversion failed: {str(e)}")

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary containing cache statistics
        """
        return self._cache_manager.get_cache_stats()

    def clear_cache(self) -> None:
        """
        Clear the conversion cache.
        """
        self._cache_manager.clear_cache()
