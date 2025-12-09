"""
Web request handlers using the new service layer architecture.

This module provides Flask request handlers that integrate with the refactored
service layer, using dependency injection and the Result pattern for consistent
error handling.
"""

import os
import tempfile
import time
from io import BytesIO
from typing import Any, Dict, List, Optional

from flask import jsonify, request, send_file
from PIL import Image
from werkzeug.datastructures import FileStorage

from ..core.base.result import Result
from ..core.container import DIContainer
from ..core.services.image_conversion_service import ImageConversionService
from ..domain.exceptions.base import ImageConverterError
from ..domain.exceptions.file_system import FileNotFoundError
from ..domain.exceptions.processing import ProcessingError
from ..domain.exceptions.validation import ValidationError
from ..models.models import ConversionResult
from ..models.processing_options import ProcessingOptions
from .error_formatter import ErrorResponseFormatter


class WebHandlers:
    """
    Web request handlers that use the new service layer architecture.

    This class provides Flask route handlers that integrate with the refactored
    service layer, using dependency injection and consistent error handling.
    """

    def __init__(self, container: DIContainer):
        """
        Initialize web handlers with dependency injection container.

        Args:
            container: Dependency injection container
        """
        self.container = container
        self.conversion_service = container.get_typed(ImageConversionService)
        self.error_handler = container.get("error_handler")
        self.logger = container.get("logger")
        self.error_formatter = ErrorResponseFormatter()

    def convert_to_base64(self) -> Dict[str, Any]:
        """
        Handle image to Base64 conversion requests.

        Returns:
            JSON response with conversion result or error
        """
        result = self._handle_request(self._convert_to_base64_impl)
        return self._format_response(result)

    def convert_from_base64(self) -> Any:
        """
        Handle Base64 to image conversion requests.

        Returns:
            File response or JSON error response
        """
        result = self._handle_request(self._convert_from_base64_impl)

        if result.is_success:
            # Return file for successful conversion
            return result.value
        else:
            # Return JSON error response
            return self._format_error_response(result.error)

    def validate_base64(self) -> Dict[str, Any]:
        """
        Handle Base64 validation requests.

        Returns:
            JSON response with validation result
        """
        result = self._handle_request(self._validate_base64_impl)
        return self._format_response(result)

    def convert_to_base64_advanced(self) -> Dict[str, Any]:
        """
        Handle advanced image to Base64 conversion with processing options.

        Returns:
            JSON response with conversion result or error
        """
        result = self._handle_request(self._convert_to_base64_advanced_impl)
        return self._format_response(result)

    def get_supported_formats(self) -> Dict[str, Any]:
        """
        Handle requests for supported image formats.

        Returns:
            JSON response with supported formats
        """
        result = self._handle_request(self._get_supported_formats_impl)
        return self._format_response(result)

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Handle requests for cache statistics.

        Returns:
            JSON response with cache statistics
        """
        result = self._handle_request(self._get_cache_stats_impl)
        return self._format_response(result)

    def clear_cache(self) -> Dict[str, Any]:
        """
        Handle cache clearing requests.

        Returns:
            JSON response with operation result
        """
        result = self._handle_request(self._clear_cache_impl)
        return self._format_response(result)

    def _handle_request(self, handler_func) -> Result:
        """
        Generic request handler that wraps business logic with error handling.

        Args:
            handler_func: Function that implements the business logic

        Returns:
            Result object containing success value or error
        """
        try:
            return handler_func()
        except ImageConverterError as e:
            self.logger.error(
                f"Application error: {str(e)}",
                extra={
                    "error_type": type(e).__name__,
                    "error_code": getattr(e, "error_code", None),
                },
            )
            return Result.failure(e)
        except Exception as e:
            self.logger.error(
                f"Unexpected error: {str(e)}", extra={"error_type": type(e).__name__}
            )
            error = ProcessingError(f"Unexpected error: {str(e)}")
            return Result.failure(error)

    def _convert_to_base64_impl(self) -> Result:
        """
        Implementation of basic image to Base64 conversion.

        Returns:
            Result containing conversion data or error
        """
        # Validate request
        if "file" not in request.files:
            return Result.failure(ValidationError("파일이 선택되지 않았습니다."))

        file = request.files["file"]
        if file.filename == "":
            return Result.failure(ValidationError("파일이 선택되지 않았습니다."))

        # Save to temporary file
        temp_file_path = self._save_uploaded_file(file)

        try:
            # Convert using service layer
            conversion_result = self.conversion_service.convert_image(temp_file_path)

            if conversion_result.success:
                # Extract image metadata
                image_metadata = self._extract_image_metadata(file)

                # Prepare response data
                response_data = {
                    "success": True,
                    "base64": conversion_result.data_uri
                    or conversion_result.base64_data,
                    "base64_data": conversion_result.base64_data,
                    "data_uri": conversion_result.data_uri,
                    "format": conversion_result.format,
                    "size": conversion_result.size,
                    "file_size": conversion_result.file_size,
                    "mime_type": conversion_result.mime_type,
                    "processing_time": conversion_result.processing_time,
                    "cache_hit": getattr(conversion_result, "cache_hit", False),
                    "metadata": image_metadata,
                }

                return Result.success(response_data)
            else:
                return Result.failure(ProcessingError(conversion_result.error_message))

        finally:
            # Clean up temporary file
            self._cleanup_temp_file(temp_file_path)

    def _convert_from_base64_impl(self) -> Result:
        """
        Implementation of Base64 to image conversion.

        Returns:
            Result containing file response or error
        """
        data = request.get_json()
        if not data or "base64" not in data:
            return Result.failure(ValidationError("Base64 데이터가 필요합니다."))

        base64_data = data["base64"]
        output_format = data.get("format", "PNG").upper()

        try:
            # Validate Base64 data
            if not self._validate_base64_data(base64_data):
                return Result.failure(
                    ValidationError("유효하지 않은 Base64 이미지 데이터입니다.")
                )

            # Convert Base64 to image
            image_data = self._decode_base64_image(base64_data)
            image = Image.open(BytesIO(image_data))

            # Convert to requested format
            img_io = BytesIO()
            image.save(img_io, format=output_format)
            img_io.seek(0)

            # Create file response
            file_response = send_file(
                img_io,
                mimetype=f"image/{output_format.lower()}",
                as_attachment=True,
                download_name=f"converted.{output_format.lower()}",
            )

            return Result.success(file_response)

        except Exception as e:
            return Result.failure(
                ProcessingError(f"변환 중 오류가 발생했습니다: {str(e)}")
            )

    def _validate_base64_impl(self) -> Result:
        """
        Implementation of Base64 validation.

        Returns:
            Result containing validation result or error
        """
        data = request.get_json()
        if not data or "base64" not in data:
            return Result.failure(ValidationError("Base64 데이터가 필요합니다."))

        base64_data = data["base64"]

        try:
            is_valid = self._validate_base64_data(base64_data)

            if is_valid:
                # Extract image information
                image_info = self._extract_base64_image_info(base64_data)
                response_data = {"valid": True, **image_info}
            else:
                response_data = {
                    "valid": False,
                    "error": "유효하지 않은 Base64 이미지 데이터입니다.",
                }

            return Result.success(response_data)

        except Exception as e:
            return Result.failure(
                ValidationError(f"검증 중 오류가 발생했습니다: {str(e)}")
            )

    def _convert_to_base64_advanced_impl(self) -> Result:
        """
        Implementation of advanced image to Base64 conversion with processing options.

        Returns:
            Result containing conversion data or error
        """
        # Validate request
        if "file" not in request.files:
            return Result.failure(ValidationError("파일이 선택되지 않았습니다."))

        file = request.files["file"]
        if file.filename == "":
            return Result.failure(ValidationError("파일이 선택되지 않았습니다."))

        # Parse processing options
        processing_options = self._parse_processing_options()

        # Save to temporary file
        temp_file_path = self._save_uploaded_file(file)

        try:
            # Convert using service layer with options
            conversion_result = self.conversion_service.convert_image(
                temp_file_path, processing_options
            )

            # Extract original image metadata
            original_metadata = self._extract_image_metadata(file)

            # Prepare response data
            response_data = {
                "base64": conversion_result.data_uri or conversion_result.base64_data,
                "base64_data": conversion_result.base64_data,
                "data_uri": conversion_result.data_uri,
                "original_format": original_metadata.get("format", "Unknown"),
                "original_size": original_metadata.get("size", (0, 0)),
                "processed_format": conversion_result.format,
                "processed_size": conversion_result.size,
                "format": conversion_result.format,
                "size": conversion_result.size,
                "file_size": conversion_result.file_size,
                "mime_type": conversion_result.mime_type,
                "processing_time": conversion_result.processing_time,
                "cache_hit": getattr(conversion_result, "cache_hit", False),
                "processing_options": self._serialize_processing_options(
                    processing_options
                ),
            }

            return Result.success(response_data)

        finally:
            # Clean up temporary file
            self._cleanup_temp_file(temp_file_path)

    def _get_supported_formats_impl(self) -> Result:
        """
        Implementation of supported formats retrieval.

        Returns:
            Result containing supported formats
        """
        try:
            # Return hardcoded supported formats for now
            supported_formats = ["PNG", "JPEG", "JPG", "GIF", "BMP", "WEBP"]
            response_data = {
                "formats": supported_formats,
                "count": len(supported_formats),
            }
            return Result.success(response_data)
        except Exception as e:
            return Result.failure(
                ProcessingError(f"지원 형식 조회 중 오류가 발생했습니다: {str(e)}")
            )

    def _get_cache_stats_impl(self) -> Result:
        """
        Implementation of cache statistics retrieval.

        Returns:
            Result containing cache statistics
        """
        try:
            # Return basic cache stats
            cache_stats = {
                "cache_enabled": True,
                "cache_hits": 0,
                "cache_misses": 0,
                "cache_size": 0,
            }
            response_data = {"cache_stats": cache_stats}
            return Result.success(response_data)
        except Exception as e:
            return Result.failure(
                ProcessingError(f"캐시 통계 조회 중 오류가 발생했습니다: {str(e)}")
            )

    def _clear_cache_impl(self) -> Result:
        """
        Implementation of cache clearing.

        Returns:
            Result containing operation result
        """
        try:
            self.conversion_service.clear_cache()
            response_data = {
                "success": True,
                "message": "캐시가 성공적으로 삭제되었습니다.",
                "timestamp": time.time(),
            }
            return Result.success(response_data)
        except Exception as e:
            return Result.failure(
                ProcessingError(f"캐시 삭제 중 오류가 발생했습니다: {str(e)}")
            )

    def _save_uploaded_file(self, file: FileStorage) -> str:
        """
        Save uploaded file to temporary location.

        Args:
            file: Uploaded file

        Returns:
            Path to temporary file
        """
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".tmp"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)

        try:
            file.save(temp_file.name)
            temp_file.close()
            return temp_file.name
        except Exception:
            # Clean up on error
            try:
                os.unlink(temp_file.name)
            except:
                pass
            raise

    def _cleanup_temp_file(self, file_path: str) -> None:
        """
        Clean up temporary file.

        Args:
            file_path: Path to temporary file
        """
        try:
            os.unlink(file_path)
        except Exception:
            # Log but don't raise - cleanup failures shouldn't break the response
            self.logger.warning(f"Failed to clean up temporary file: {file_path}")

    def _extract_image_metadata(self, file: FileStorage) -> Dict[str, Any]:
        """
        Extract metadata from uploaded image file.

        Args:
            file: Uploaded file

        Returns:
            Dictionary containing image metadata
        """
        try:
            file.stream.seek(0)
            image = Image.open(file.stream)
            metadata = {"format": image.format, "size": image.size, "mode": image.mode}
            image.close()
            return metadata
        except Exception:
            # Return default metadata if extraction fails
            return {"format": "Unknown", "size": (0, 0), "mode": "Unknown"}

    def _parse_processing_options(self) -> Optional[ProcessingOptions]:
        """
        Parse processing options from request form data.

        Returns:
            ProcessingOptions instance or None
        """
        try:
            options_data = {}
            if request.form.get("options"):
                import json

                options_data = json.loads(request.form.get("options"))

            if not options_data:
                return None

            return ProcessingOptions(
                resize_width=options_data.get("resize_width"),
                resize_height=options_data.get("resize_height"),
                maintain_aspect_ratio=options_data.get("maintain_aspect_ratio", True),
                quality=options_data.get("quality", 85),
                target_format=options_data.get("target_format"),
                rotation_angle=options_data.get("rotation_angle", 0),
                flip_horizontal=options_data.get("flip_horizontal", False),
                flip_vertical=options_data.get("flip_vertical", False),
            )
        except Exception as e:
            raise ValidationError(f"잘못된 처리 옵션: {str(e)}")

    def _serialize_processing_options(
        self, options: Optional[ProcessingOptions]
    ) -> Optional[Dict[str, Any]]:
        """
        Serialize processing options for response.

        Args:
            options: ProcessingOptions instance

        Returns:
            Dictionary representation of options
        """
        if options is None:
            return None

        return {
            "resize_width": options.resize_width,
            "resize_height": options.resize_height,
            "maintain_aspect_ratio": options.maintain_aspect_ratio,
            "quality": options.quality,
            "target_format": options.target_format,
            "rotation_angle": options.rotation_angle,
            "flip_horizontal": options.flip_horizontal,
            "flip_vertical": options.flip_vertical,
        }

    def _validate_base64_data(self, base64_data: str) -> bool:
        """
        Validate Base64 image data.

        Args:
            base64_data: Base64 encoded image data

        Returns:
            True if valid, False otherwise
        """
        try:
            # Remove data URL prefix if present
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]

            # Decode and validate
            import base64

            image_data = base64.b64decode(base64_data)
            Image.open(BytesIO(image_data)).verify()
            return True
        except Exception:
            return False

    def _decode_base64_image(self, base64_data: str) -> bytes:
        """
        Decode Base64 image data.

        Args:
            base64_data: Base64 encoded image data

        Returns:
            Decoded image bytes
        """
        import base64

        # Remove data URL prefix if present
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]

        return base64.b64decode(base64_data)

    def _extract_base64_image_info(self, base64_data: str) -> Dict[str, Any]:
        """
        Extract information from Base64 image data.

        Args:
            base64_data: Base64 encoded image data

        Returns:
            Dictionary containing image information
        """
        try:
            image_data = self._decode_base64_image(base64_data)
            image = Image.open(BytesIO(image_data))

            info = {"format": image.format, "size": image.size, "mode": image.mode}
            image.close()
            return info
        except Exception:
            return {}

    def _format_response(self, result: Result) -> Dict[str, Any]:
        """
        Format a Result into a JSON response.

        Args:
            result: Result object

        Returns:
            Dictionary for JSON response
        """
        if result.is_success:
            return result.value
        else:
            return self._format_error_response(result.error)

    def _format_error_response(self, error: Exception) -> Dict[str, Any]:
        """
        Format an error into a JSON response using the error formatter.

        Args:
            error: Exception object

        Returns:
            Dictionary for JSON error response
        """
        # Prepare error context
        context = {
            "request_path": request.path,
            "request_method": request.method,
            "timestamp": time.time(),
        }

        # Use error formatter to create standardized response
        formatted_response, _ = self.error_formatter.format_error_response(
            error, context
        )

        return formatted_response
