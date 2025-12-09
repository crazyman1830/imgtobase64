"""
Queue exception classes.

This module defines exceptions related to processing queues and task management.
"""

from typing import Any, Dict, Optional

from .base import ErrorCode, ImageConverterError


class QueueError(ImageConverterError):
    """Base class for queue-related errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[ErrorCode] = None,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
    ):
        super().__init__(
            message, error_code or ErrorCode.QUEUE_ERROR, context, user_message
        )


class ProcessingQueueFullError(QueueError):
    """Exception raised when the processing queue is full."""

    def __init__(
        self,
        queue_name: str = "processing",
        current_size: Optional[int] = None,
        max_size: Optional[int] = None,
    ):
        message = f"Processing queue '{queue_name}' is full"

        if current_size is not None and max_size is not None:
            message += f" ({current_size}/{max_size})"

        user_message = "처리 대기열이 가득 찼습니다. 잠시 후 다시 시도해주세요."

        context = {
            "queue_name": queue_name,
            "current_size": current_size,
            "max_size": max_size,
        }

        super().__init__(
            message=message,
            error_code=ErrorCode.QUEUE_FULL,
            context=context,
            user_message=user_message,
        )


class QueueTimeoutError(QueueError):
    """Exception raised when queue operations timeout."""

    def __init__(
        self, operation: str, timeout_seconds: int, queue_name: str = "processing"
    ):
        message = (
            f"Queue {operation} timeout ({timeout_seconds}s) for queue '{queue_name}'"
        )
        user_message = f"처리 대기 시간이 초과되었습니다. 다시 시도해주세요."

        context = {
            "operation": operation,
            "timeout_seconds": timeout_seconds,
            "queue_name": queue_name,
        }

        super().__init__(
            message=message,
            error_code=ErrorCode.QUEUE_TIMEOUT,
            context=context,
            user_message=user_message,
        )
