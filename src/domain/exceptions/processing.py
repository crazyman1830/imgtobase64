"""
Processing exception classes.

This module defines exceptions related to image processing and conversion operations.
"""

from typing import Any, Dict, Optional

from .base import ErrorCode, ImageConverterError


class ProcessingError(ImageConverterError):
    """Base class for processing-related errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[ErrorCode] = None,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        processing_time: Optional[float] = None,
        file_path: Optional[str] = None,
        processing_stage: Optional[str] = None,
    ):
        # Add additional attributes to context
        if context is None:
            context = {}

        if processing_time is not None:
            context["processing_time"] = processing_time
            self.processing_time = processing_time

        if file_path is not None:
            context["file_path"] = file_path
            self.file_path = file_path

        if processing_stage is not None:
            context["processing_stage"] = processing_stage
            self.processing_stage = processing_stage

        super().__init__(
            message,
            error_code or ErrorCode.PROCESSING_ERROR,
            context,
            user_message or "파일 처리 중 오류가 발생했습니다.",
        )


class ConversionError(ProcessingError):
    """Exception raised during image conversion operations."""

    def __init__(
        self,
        file_path: str,
        operation: str = "conversion",
        original_error: Optional[Exception] = None,
    ):
        message = f"Conversion error during {operation} for file '{file_path}'"

        if original_error:
            message += f": {str(original_error)}"

        user_message = f"이미지 변환 중 오류가 발생했습니다: {file_path}"

        context = {
            "file_path": file_path,
            "operation": operation,
            "original_error": str(original_error) if original_error else None,
        }

        super().__init__(
            message=message,
            error_code=ErrorCode.CONVERSION_ERROR,
            context=context,
            user_message=user_message,
        )


class CorruptedFileError(ProcessingError):
    """Exception raised when a file is corrupted or invalid."""

    def __init__(self, file_path: str, details: Optional[str] = None):
        message = f"Corrupted or invalid file: {file_path}"

        if details:
            message += f" - {details}"

        user_message = f"파일이 손상되었거나 올바르지 않습니다: {file_path}"

        context = {"file_path": file_path, "corruption_details": details}

        super().__init__(
            message=message,
            error_code=ErrorCode.CORRUPTED_FILE,
            context=context,
            user_message=user_message,
        )


class MemoryError(ProcessingError):
    """Exception raised when there's insufficient memory for processing."""

    def __init__(
        self,
        file_path: str,
        required_memory: Optional[int] = None,
        available_memory: Optional[int] = None,
    ):
        message = f"Insufficient memory to process file: {file_path}"

        if required_memory and available_memory:
            message += (
                f" (required: {required_memory}MB, available: {available_memory}MB)"
            )

        user_message = "메모리 부족으로 파일을 처리할 수 없습니다. 파일 크기를 줄이거나 나중에 다시 시도해주세요."

        context = {
            "file_path": file_path,
            "required_memory_mb": required_memory,
            "available_memory_mb": available_memory,
        }

        super().__init__(
            message=message,
            error_code=ErrorCode.MEMORY_ERROR,
            context=context,
            user_message=user_message,
        )


class TimeoutError(ProcessingError):
    """Exception raised when processing times out."""

    def __init__(
        self, file_path: str, timeout_seconds: int, operation: str = "processing"
    ):
        message = f"Processing timeout ({timeout_seconds}s) exceeded for {operation} of file: {file_path}"
        user_message = f"처리 시간이 초과되었습니다. 파일이 너무 크거나 복잡할 수 있습니다: {file_path}"

        context = {
            "file_path": file_path,
            "timeout_seconds": timeout_seconds,
            "operation": operation,
        }

        super().__init__(
            message=message,
            error_code=ErrorCode.TIMEOUT_ERROR,
            context=context,
            user_message=user_message,
        )
