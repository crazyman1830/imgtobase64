"""
Base exception classes for the image converter system.

This module defines the base exception class with error codes and
user-friendly message generation capabilities.
"""

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(Enum):
    """
    Enumeration of error codes for different types of errors.

    Error codes follow a hierarchical pattern:
    - 1xxx: Validation errors
    - 2xxx: File system errors
    - 3xxx: Processing errors
    - 4xxx: Security errors
    - 5xxx: Cache errors
    - 6xxx: Rate limiting errors
    - 7xxx: Queue errors
    - 9xxx: Unknown/Generic errors
    """

    # Validation errors (1xxx)
    VALIDATION_ERROR = "1000"
    UNSUPPORTED_FORMAT = "1001"
    FILE_SIZE_ERROR = "1002"
    INVALID_INPUT = "1003"

    # File system errors (2xxx)
    FILE_SYSTEM_ERROR = "2000"
    FILE_NOT_FOUND = "2001"
    PERMISSION_DENIED = "2002"
    DIRECTORY_NOT_FOUND = "2003"
    FILE_EXISTS = "2004"

    # Processing errors (3xxx)
    PROCESSING_ERROR = "3000"
    CONVERSION_ERROR = "3001"
    CORRUPTED_FILE = "3002"
    MEMORY_ERROR = "3003"
    TIMEOUT_ERROR = "3004"

    # Security errors (4xxx)
    SECURITY_ERROR = "4000"
    SECURITY_THREAT_DETECTED = "4001"
    MALICIOUS_CONTENT = "4002"
    SUSPICIOUS_ACTIVITY = "4003"

    # Cache errors (5xxx)
    CACHE_ERROR = "5000"
    CACHE_WRITE_ERROR = "5001"
    CACHE_READ_ERROR = "5002"
    CACHE_CORRUPTION = "5003"

    # Rate limiting errors (6xxx)
    RATE_LIMIT_ERROR = "6000"
    RATE_LIMIT_EXCEEDED = "6001"
    TOO_MANY_REQUESTS = "6002"

    # Queue errors (7xxx)
    QUEUE_ERROR = "7000"
    QUEUE_FULL = "7001"
    QUEUE_TIMEOUT = "7002"

    # Generic errors (9xxx)
    UNKNOWN_ERROR = "9000"
    INTERNAL_ERROR = "9001"


class ImageConverterError(Exception):
    """
    Base exception class for all image converter errors.

    This class provides error codes, user-friendly messages, and context
    information for better error handling and debugging.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[ErrorCode] = None,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
    ):
        """
        Initialize the base exception.

        Args:
            message: Technical error message for developers
            error_code: Specific error code for this error type
            context: Additional context information about the error
            user_message: User-friendly error message (auto-generated if not provided)
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or ErrorCode.UNKNOWN_ERROR
        self.context = context or {}
        self._user_message = user_message

    @property
    def user_message(self) -> str:
        """
        Get a user-friendly error message.

        Returns:
            User-friendly error message
        """
        if self._user_message:
            return self._user_message

        return self._generate_user_friendly_message()

    def _generate_user_friendly_message(self) -> str:
        """
        Generate a user-friendly error message based on the error code.

        Returns:
            User-friendly error message
        """
        error_messages = {
            ErrorCode.VALIDATION_ERROR: "입력 데이터가 유효하지 않습니다.",
            ErrorCode.UNSUPPORTED_FORMAT: "지원되지 않는 파일 형식입니다.",
            ErrorCode.FILE_SIZE_ERROR: "파일 크기가 허용된 범위를 초과했습니다.",
            ErrorCode.INVALID_INPUT: "입력 값이 올바르지 않습니다.",
            ErrorCode.FILE_SYSTEM_ERROR: "파일 시스템 오류가 발생했습니다.",
            ErrorCode.FILE_NOT_FOUND: "파일을 찾을 수 없습니다.",
            ErrorCode.PERMISSION_DENIED: "파일에 접근할 권한이 없습니다.",
            ErrorCode.DIRECTORY_NOT_FOUND: "디렉토리를 찾을 수 없습니다.",
            ErrorCode.FILE_EXISTS: "파일이 이미 존재합니다.",
            ErrorCode.PROCESSING_ERROR: "파일 처리 중 오류가 발생했습니다.",
            ErrorCode.CONVERSION_ERROR: "이미지 변환 중 오류가 발생했습니다.",
            ErrorCode.CORRUPTED_FILE: "파일이 손상되었거나 올바르지 않습니다.",
            ErrorCode.MEMORY_ERROR: "메모리 부족으로 처리할 수 없습니다.",
            ErrorCode.TIMEOUT_ERROR: "처리 시간이 초과되었습니다.",
            ErrorCode.SECURITY_ERROR: "보안 검사 중 오류가 발생했습니다.",
            ErrorCode.SECURITY_THREAT_DETECTED: "보안 위협이 감지되었습니다.",
            ErrorCode.MALICIOUS_CONTENT: "악성 콘텐츠가 감지되었습니다.",
            ErrorCode.SUSPICIOUS_ACTIVITY: "의심스러운 활동이 감지되었습니다.",
            ErrorCode.CACHE_ERROR: "캐시 시스템 오류가 발생했습니다.",
            ErrorCode.CACHE_WRITE_ERROR: "캐시 저장 중 오류가 발생했습니다.",
            ErrorCode.CACHE_READ_ERROR: "캐시 읽기 중 오류가 발생했습니다.",
            ErrorCode.CACHE_CORRUPTION: "캐시 데이터가 손상되었습니다.",
            ErrorCode.RATE_LIMIT_ERROR: "요청 제한 오류가 발생했습니다.",
            ErrorCode.RATE_LIMIT_EXCEEDED: "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
            ErrorCode.TOO_MANY_REQUESTS: "너무 많은 요청이 발생했습니다.",
            ErrorCode.QUEUE_ERROR: "처리 대기열 오류가 발생했습니다.",
            ErrorCode.QUEUE_FULL: "처리 대기열이 가득 찼습니다. 잠시 후 다시 시도해주세요.",
            ErrorCode.QUEUE_TIMEOUT: "처리 대기 시간이 초과되었습니다.",
            ErrorCode.UNKNOWN_ERROR: "알 수 없는 오류가 발생했습니다.",
            ErrorCode.INTERNAL_ERROR: "내부 시스템 오류가 발생했습니다.",
        }

        return error_messages.get(self.error_code, "오류가 발생했습니다.")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the exception to a dictionary representation.

        Returns:
            Dictionary containing error information
        """
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "user_message": self.user_message,
            "context": self.context,
        }

    def __str__(self) -> str:
        """String representation of the exception."""
        return f"[{self.error_code.value}] {self.message}"

    def __repr__(self) -> str:
        """Detailed string representation of the exception."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"error_code={self.error_code}, "
            f"context={self.context})"
        )
