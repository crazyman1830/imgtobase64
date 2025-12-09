"""
Web middleware for error handling and security.

This module provides middleware components that integrate with the refactored
service layer for consistent error handling and security measures.
"""

import time
from typing import Any, Dict, Optional

from flask import g, jsonify, request
from werkzeug.exceptions import HTTPException

from ..core.container import DIContainer
from ..core.error_handler import ErrorHandler
from ..core.structured_logger import StructuredLogger
from ..domain.exceptions.base import ImageConverterError
from ..domain.exceptions.security import SecurityError
from ..domain.exceptions.validation import ValidationError
from .error_formatter import ErrorResponseFormatter


class ErrorHandlingMiddleware:
    """
    Middleware for centralized error handling in web requests.

    This middleware integrates with the error handler service to provide
    consistent error responses across all endpoints with standardized
    HTTP status codes and user-friendly error messages.
    """

    def __init__(self, container: DIContainer):
        """
        Initialize error handling middleware.

        Args:
            container: Dependency injection container
        """
        self.container = container
        self.error_handler: ErrorHandler = container.get("error_handler")
        self.logger: StructuredLogger = container.get("logger")
        self.error_formatter = ErrorResponseFormatter()

        # Standard error response templates
        self.error_templates = {
            400: "잘못된 요청입니다.",
            401: "인증이 필요합니다.",
            403: "접근이 거부되었습니다.",
            404: "요청한 리소스를 찾을 수 없습니다.",
            405: "허용되지 않는 HTTP 메서드입니다.",
            413: "요청 크기가 너무 큽니다.",
            415: "지원되지 않는 미디어 타입입니다.",
            429: "요청 한도를 초과했습니다.",
            500: "서버에서 오류가 발생했습니다.",
            502: "게이트웨이 오류가 발생했습니다.",
            503: "서비스를 사용할 수 없습니다.",
        }

    def handle_error(self, error: Exception) -> tuple[Dict[str, Any], int]:
        """
        Handle exceptions and return appropriate HTTP responses.

        Args:
            error: Exception that occurred

        Returns:
            Tuple of (JSON response, HTTP status code)
        """
        # Prepare error context
        error_context = {
            "request_path": request.path,
            "request_method": request.method,
            "request_args": dict(request.args),
            "user_agent": request.headers.get("User-Agent", ""),
            "remote_addr": request.remote_addr,
            "timestamp": time.time(),
        }

        # Handle different types of errors
        if isinstance(error, HTTPException):
            return self._handle_http_exception(error, error_context)
        elif isinstance(error, ImageConverterError):
            return self._handle_application_error(error, error_context)
        else:
            return self._handle_unexpected_error(error, error_context)

    def _handle_http_exception(
        self, error: HTTPException, context: Dict[str, Any]
    ) -> tuple[Dict[str, Any], int]:
        """
        Handle HTTP exceptions (4xx, 5xx errors) with standardized responses.

        Args:
            error: HTTP exception
            context: Error context

        Returns:
            Tuple of (JSON response, HTTP status code)
        """
        # Log appropriate level based on status code
        if error.code >= 500:
            self.logger.error(
                f"Server error {error.code}: {error.description}",
                extra={**context, "error_type": "HTTPException"},
            )
        else:
            self.logger.warning(
                f"Client error {error.code}: {error.description}",
                extra={**context, "error_type": "HTTPException"},
            )

        # Use standardized error message or fallback to description
        user_message = (
            self.error_templates.get(error.code)
            or error.description
            or f"HTTP {error.code} 오류가 발생했습니다."
        )

        response_data = {
            "error": user_message,
            "error_code": f"HTTP_{error.code}",
            "status_code": error.code,
            "timestamp": context["timestamp"],
        }

        # Add additional context for certain errors
        if error.code == 413:  # Request Entity Too Large
            response_data["details"] = {
                "max_file_size_mb": getattr(
                    self.container.get_config(), "max_file_size_mb", 16
                ),
                "suggestion": "파일 크기를 줄이거나 여러 개의 작은 파일로 나누어 업로드해주세요.",
            }
        elif error.code == 415:  # Unsupported Media Type
            response_data["details"] = {
                "supported_types": [
                    "image/jpeg",
                    "image/png",
                    "image/gif",
                    "image/bmp",
                    "image/webp",
                ],
                "suggestion": "지원되는 이미지 형식의 파일을 업로드해주세요.",
            }
        elif error.code == 429:  # Too Many Requests
            response_data["details"] = {
                "retry_after": getattr(error, "retry_after", 60),
                "suggestion": "잠시 후 다시 시도해주세요.",
            }

        return response_data, error.code

    def _handle_application_error(
        self, error: ImageConverterError, context: Dict[str, Any]
    ) -> tuple[Dict[str, Any], int]:
        """
        Handle application-specific errors using the error formatter.

        Args:
            error: Application error
            context: Error context

        Returns:
            Tuple of (JSON response, HTTP status code)
        """
        # Log the error using the error handler service
        error_response = self.error_handler.handle_error(error, context)

        # Format the error response using the error formatter
        formatted_response, status_code = self.error_formatter.format_error_response(
            error, context
        )

        return formatted_response, status_code

    def _handle_unexpected_error(
        self, error: Exception, context: Dict[str, Any]
    ) -> tuple[Dict[str, Any], int]:
        """
        Handle unexpected errors using the error formatter.

        Args:
            error: Unexpected exception
            context: Error context

        Returns:
            Tuple of (JSON response, HTTP status code)
        """
        # Log the full error for debugging
        self.logger.error(
            f"Unexpected error: {str(error)}",
            extra={
                **context,
                "error_type": type(error).__name__,
                "error_traceback": True,
            },
            exc_info=True,
        )

        # Format the error response using the error formatter
        formatted_response, status_code = self.error_formatter.format_error_response(
            error, context
        )

        return formatted_response, status_code

    def _get_status_code_for_error(self, error: ImageConverterError) -> int:
        """
        Get appropriate HTTP status code for application error.

        Args:
            error: Application error

        Returns:
            HTTP status code
        """
        # Import here to avoid circular imports
        from ..domain.exceptions.cache import CacheError
        from ..domain.exceptions.file_system import FileNotFoundError
        from ..domain.exceptions.processing import ProcessingError
        from ..domain.exceptions.security import SecurityError
        from ..domain.exceptions.validation import ValidationError

        # Map error types to HTTP status codes
        error_status_map = {
            ValidationError: 400,
            SecurityError: 403,
            FileNotFoundError: 404,
            ProcessingError: 422,  # Unprocessable Entity
            CacheError: 503,  # Service Unavailable
        }

        # Get status code from mapping or default to 500
        return error_status_map.get(type(error), 500)


class SecurityMiddleware:
    """
    Middleware for security measures in web requests.

    This middleware provides security headers, request validation,
    and other security measures.
    """

    def __init__(self, container: DIContainer):
        """
        Initialize security middleware.

        Args:
            container: Dependency injection container
        """
        self.container = container
        self.logger: StructuredLogger = container.get("logger")
        self.config = container.get_config()

    def before_request(self) -> Optional[tuple[Dict[str, Any], int]]:
        """
        Process request before handling.

        Returns:
            Optional error response if request should be rejected
        """
        try:
            # Store request start time
            g.request_start_time = time.time()

            # Validate request size
            if self._is_request_too_large():
                return self._create_error_response(
                    "Request too large", "REQUEST_TOO_LARGE", 413
                )

            # Validate content type for POST requests
            if request.method == "POST" and not self._is_valid_content_type():
                return self._create_error_response(
                    "Invalid content type", "INVALID_CONTENT_TYPE", 415
                )

            # Rate limiting (if configured)
            if (
                hasattr(self.config, "enable_rate_limiting")
                and self.config.enable_rate_limiting
            ):
                if self._is_rate_limited():
                    return self._create_error_response(
                        "Rate limit exceeded", "RATE_LIMIT_EXCEEDED", 429
                    )

            # Log request
            self.logger.info(
                f"Request: {request.method} {request.path}",
                extra={
                    "request_method": request.method,
                    "request_path": request.path,
                    "remote_addr": request.remote_addr,
                    "user_agent": request.headers.get("User-Agent", ""),
                    "content_length": request.content_length or 0,
                },
            )

            return None

        except Exception as e:
            self.logger.error(f"Security middleware error: {str(e)}")
            return self._create_error_response(
                "Security check failed", "SECURITY_ERROR", 500
            )

    def after_request(self, response):
        """
        Process response after handling.

        Args:
            response: Flask response object

        Returns:
            Modified response object
        """
        try:
            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            # Add CORS headers if needed
            if hasattr(self.config, "enable_cors") and self.config.enable_cors:
                response.headers["Access-Control-Allow-Origin"] = "*"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = (
                    "Content-Type, Authorization"
                )

            # Log response
            processing_time = time.time() - getattr(
                g, "request_start_time", time.time()
            )

            self.logger.info(
                f"Response: {response.status_code} ({processing_time:.3f}s)",
                extra={
                    "response_status": response.status_code,
                    "processing_time": processing_time,
                    "response_size": response.content_length or 0,
                },
            )

            return response

        except Exception as e:
            self.logger.error(f"After request middleware error: {str(e)}")
            return response

    def _is_request_too_large(self) -> bool:
        """
        Check if request is too large.

        Returns:
            True if request is too large
        """
        max_size = getattr(self.config, "max_file_size_mb", 16) * 1024 * 1024
        return request.content_length and request.content_length > max_size

    def _is_valid_content_type(self) -> bool:
        """
        Check if content type is valid for POST requests.

        Returns:
            True if content type is valid
        """
        if request.path.startswith("/api/"):
            # API endpoints should have appropriate content types
            valid_types = [
                "application/json",
                "multipart/form-data",
                "application/x-www-form-urlencoded",
            ]

            content_type = request.content_type
            if content_type:
                return any(content_type.startswith(vt) for vt in valid_types)
            return False

        return True

    def _is_rate_limited(self) -> bool:
        """
        Check if request should be rate limited.

        Returns:
            True if request should be rate limited
        """
        # Simple rate limiting implementation
        # In production, use Redis or similar for distributed rate limiting

        # For now, just return False (no rate limiting)
        # This can be implemented based on specific requirements
        return False

    def _create_error_response(
        self, message: str, error_code: str, status_code: int
    ) -> tuple[Dict[str, Any], int]:
        """
        Create standardized error response.

        Args:
            message: Error message
            error_code: Error code
            status_code: HTTP status code

        Returns:
            Tuple of (JSON response, HTTP status code)
        """
        return {
            "error": message,
            "error_code": error_code,
            "timestamp": time.time(),
        }, status_code


class RequestLoggingMiddleware:
    """
    Middleware for detailed request/response logging.

    This middleware provides comprehensive logging of HTTP requests
    and responses for monitoring and debugging purposes.
    """

    def __init__(self, container: DIContainer):
        """
        Initialize request logging middleware.

        Args:
            container: Dependency injection container
        """
        self.container = container
        self.logger: StructuredLogger = container.get("logger")
        self.config = container.get_config()

    def log_request(self) -> None:
        """Log incoming request details."""
        if not self._should_log_request():
            return

        request_data = {
            "method": request.method,
            "path": request.path,
            "query_string": request.query_string.decode("utf-8"),
            "remote_addr": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", ""),
            "content_type": request.content_type,
            "content_length": request.content_length or 0,
            "headers": dict(request.headers) if self._should_log_headers() else {},
        }

        self.logger.info("HTTP Request", extra=request_data)

    def log_response(self, response) -> None:
        """
        Log response details.

        Args:
            response: Flask response object
        """
        if not self._should_log_response():
            return

        processing_time = time.time() - getattr(g, "request_start_time", time.time())

        response_data = {
            "status_code": response.status_code,
            "content_type": response.content_type,
            "content_length": response.content_length or 0,
            "processing_time": processing_time,
            "headers": dict(response.headers) if self._should_log_headers() else {},
        }

        self.logger.info("HTTP Response", extra=response_data)

    def _should_log_request(self) -> bool:
        """
        Determine if request should be logged.

        Returns:
            True if request should be logged
        """
        # Skip logging for static files and health checks
        skip_paths = ["/static/", "/favicon.ico", "/api/health"]
        return not any(request.path.startswith(path) for path in skip_paths)

    def _should_log_response(self) -> bool:
        """
        Determine if response should be logged.

        Returns:
            True if response should be logged
        """
        return self._should_log_request()

    def _should_log_headers(self) -> bool:
        """
        Determine if headers should be logged.

        Returns:
            True if headers should be logged
        """
        # Only log headers in debug mode or if explicitly configured
        return (hasattr(self.config, "debug") and self.config.debug) or (
            hasattr(self.config, "log_headers") and self.config.log_headers
        )
