"""
Error response formatting utilities for web interface.

This module provides utilities for formatting error responses in a consistent
and user-friendly manner across all web endpoints.
"""

import time
from typing import Any, Dict, List, Optional

from flask import request

from ..domain.exceptions.base import ImageConverterError
from ..domain.exceptions.cache import CacheError
from ..domain.exceptions.file_system import FileNotFoundError
from ..domain.exceptions.processing import ProcessingError
from ..domain.exceptions.security import SecurityError
from ..domain.exceptions.validation import ValidationError


class ErrorResponseFormatter:
    """
    Formatter for creating standardized error responses.

    This class provides methods to format various types of errors into
    consistent JSON responses with appropriate HTTP status codes and
    user-friendly messages.
    """

    def __init__(self):
        """Initialize the error response formatter."""
        # User-friendly error messages for different error types
        self.error_messages = {
            ValidationError: "입력 데이터가 올바르지 않습니다.",
            SecurityError: "보안 검사에 실패했습니다.",
            FileNotFoundError: "파일을 찾을 수 없습니다.",
            ProcessingError: "이미지 처리 중 오류가 발생했습니다.",
            CacheError: "캐시 서비스에 일시적인 문제가 발생했습니다.",
        }

        # HTTP status codes for different error types
        self.status_codes = {
            ValidationError: 400,
            SecurityError: 403,
            FileNotFoundError: 404,
            ProcessingError: 422,
            CacheError: 503,
        }

        # Suggestions for different error types
        self.error_suggestions = {
            ValidationError: [
                "입력 데이터의 형식과 값을 확인해주세요.",
                "필수 필드가 모두 포함되어 있는지 확인해주세요.",
            ],
            SecurityError: [
                "파일이 안전한지 확인해주세요.",
                "지원되는 파일 형식인지 확인해주세요.",
            ],
            FileNotFoundError: [
                "파일 경로가 올바른지 확인해주세요.",
                "파일이 존재하는지 확인해주세요.",
            ],
            ProcessingError: [
                "이미지 파일이 손상되지 않았는지 확인해주세요.",
                "다른 이미지 파일로 다시 시도해주세요.",
            ],
            CacheError: [
                "잠시 후 다시 시도해주세요.",
                "문제가 지속되면 관리자에게 문의해주세요.",
            ],
        }

    def format_error_response(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> tuple[Dict[str, Any], int]:
        """
        Format an error into a standardized JSON response.

        Args:
            error: Exception that occurred
            context: Optional context information

        Returns:
            Tuple of (JSON response dict, HTTP status code)
        """
        context = context or {}
        timestamp = time.time()

        if isinstance(error, ImageConverterError):
            return self._format_application_error(error, context, timestamp)
        else:
            return self._format_generic_error(error, context, timestamp)

    def _format_application_error(
        self, error: ImageConverterError, context: Dict[str, Any], timestamp: float
    ) -> tuple[Dict[str, Any], int]:
        """
        Format application-specific errors.

        Args:
            error: Application error
            context: Error context
            timestamp: Error timestamp

        Returns:
            Tuple of (JSON response dict, HTTP status code)
        """
        error_type = type(error)

        # Get user-friendly message
        user_message = getattr(error, "user_message", None)
        if not user_message:
            user_message = self.error_messages.get(error_type, str(error))

        # Get error code
        error_code = getattr(error, "error_code", None)
        if not error_code:
            error_code = error_type.__name__.upper()
        else:
            # Convert enum to string value if it's an ErrorCode enum
            if hasattr(error_code, "value"):
                error_code = error_code.value

        # Get HTTP status code
        status_code = self.status_codes.get(error_type, 500)

        # Build response
        response = {
            "error": user_message,
            "error_code": error_code,
            "error_type": error_type.__name__,
            "timestamp": timestamp,
        }

        # Add suggestions if available
        suggestions = self.error_suggestions.get(error_type)
        if suggestions:
            response["suggestions"] = suggestions

        # Add technical details for debugging (only in development)
        if self._should_include_debug_info():
            response["debug"] = {
                "original_message": str(error),
                "error_class": f"{error_type.__module__}.{error_type.__name__}",
                "context": context,
            }

        # Add specific error details based on error type
        if isinstance(error, ValidationError):
            response.update(self._get_validation_error_details(error))
        elif isinstance(error, ProcessingError):
            response.update(self._get_processing_error_details(error))
        elif isinstance(error, SecurityError):
            response.update(self._get_security_error_details(error))
        elif isinstance(error, FileNotFoundError):
            response.update(self._get_file_error_details(error))
        elif isinstance(error, CacheError):
            response.update(self._get_cache_error_details(error))

        return response, status_code

    def _format_generic_error(
        self, error: Exception, context: Dict[str, Any], timestamp: float
    ) -> tuple[Dict[str, Any], int]:
        """
        Format generic/unexpected errors.

        Args:
            error: Generic exception
            context: Error context
            timestamp: Error timestamp

        Returns:
            Tuple of (JSON response dict, HTTP status code)
        """
        response = {
            "error": "서버에서 예상치 못한 오류가 발생했습니다.",
            "error_code": "INTERNAL_SERVER_ERROR",
            "error_type": "UnexpectedError",
            "timestamp": timestamp,
            "suggestions": [
                "잠시 후 다시 시도해주세요.",
                "문제가 지속되면 관리자에게 문의해주세요.",
            ],
        }

        # Add debug info in development
        if self._should_include_debug_info():
            response["debug"] = {
                "original_message": str(error),
                "error_class": f"{type(error).__module__}.{type(error).__name__}",
                "context": context,
            }

        return response, 500

    def _get_validation_error_details(self, error: ValidationError) -> Dict[str, Any]:
        """
        Get specific details for validation errors.

        Args:
            error: Validation error

        Returns:
            Dictionary with validation error details
        """
        details = {}

        # Add field-specific validation errors if available
        if hasattr(error, "field_errors"):
            details["field_errors"] = error.field_errors

        # Add validation rules if available
        if hasattr(error, "validation_rules"):
            details["validation_rules"] = error.validation_rules

        return {"details": details} if details else {}

    def _get_processing_error_details(self, error: ProcessingError) -> Dict[str, Any]:
        """
        Get specific details for processing errors.

        Args:
            error: Processing error

        Returns:
            Dictionary with processing error details
        """
        details = {}

        # Add processing time if available
        if hasattr(error, "processing_time"):
            details["processing_time"] = error.processing_time

        # Add file information if available
        if hasattr(error, "file_path"):
            details["file_path"] = error.file_path

        # Add processing stage if available
        if hasattr(error, "processing_stage"):
            details["processing_stage"] = error.processing_stage

        return {"details": details} if details else {}

    def _get_security_error_details(self, error: SecurityError) -> Dict[str, Any]:
        """
        Get specific details for security errors.

        Args:
            error: Security error

        Returns:
            Dictionary with security error details
        """
        details = {}

        # Add security check type if available
        if hasattr(error, "check_type"):
            details["security_check"] = error.check_type

        # Add allowed values if available
        if hasattr(error, "allowed_values"):
            details["allowed_values"] = error.allowed_values

        return {"details": details} if details else {}

    def _get_file_error_details(self, error: FileNotFoundError) -> Dict[str, Any]:
        """
        Get specific details for file errors.

        Args:
            error: File error

        Returns:
            Dictionary with file error details
        """
        details = {}

        # Add file path if available (sanitized)
        if hasattr(error, "file_path"):
            # Only include filename, not full path for security
            import os

            details["filename"] = os.path.basename(error.file_path)

        return {"details": details} if details else {}

    def _get_cache_error_details(self, error: CacheError) -> Dict[str, Any]:
        """
        Get specific details for cache errors.

        Args:
            error: Cache error

        Returns:
            Dictionary with cache error details
        """
        details = {}

        # Add cache backend information if available
        if hasattr(error, "cache_backend"):
            details["cache_backend"] = error.cache_backend

        # Add retry information
        details["retry_recommended"] = True
        details["retry_delay_seconds"] = 5

        return {"details": details} if details else {}

    def _should_include_debug_info(self) -> bool:
        """
        Determine if debug information should be included in error responses.

        Returns:
            True if debug info should be included
        """
        # Include debug info in development or if explicitly requested
        try:
            from flask import current_app

            return current_app.debug or request.args.get("debug") == "1"
        except:
            return False

    def format_validation_error_list(
        self, errors: List[str], field: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format a list of validation errors.

        Args:
            errors: List of validation error messages
            field: Optional field name that failed validation

        Returns:
            Formatted error response
        """
        response = {
            "error": "입력 데이터 검증에 실패했습니다.",
            "error_code": "VALIDATION_FAILED",
            "error_type": "ValidationError",
            "timestamp": time.time(),
            "validation_errors": errors,
        }

        if field:
            response["field"] = field

        response["suggestions"] = [
            "입력 데이터를 확인하고 다시 시도해주세요.",
            "필수 필드가 모두 포함되어 있는지 확인해주세요.",
        ]

        return response

    def format_success_response(
        self, data: Any, message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format a success response.

        Args:
            data: Response data
            message: Optional success message

        Returns:
            Formatted success response
        """
        response = {"success": True, "data": data, "timestamp": time.time()}

        if message:
            response["message"] = message

        return response
