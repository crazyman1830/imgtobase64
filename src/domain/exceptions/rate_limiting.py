"""
Rate limiting exception classes.

This module defines exceptions related to rate limiting and request throttling.
"""

from typing import Optional, Dict, Any
from .base import ImageConverterError, ErrorCode


class RateLimitError(ImageConverterError):
    """Base class for rate limiting-related errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[ErrorCode] = None,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message, 
            error_code or ErrorCode.RATE_LIMIT_ERROR, 
            context, 
            user_message
        )


class RateLimitExceededError(RateLimitError):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(
        self, 
        client_id: str,
        limit: int,
        window_seconds: int,
        retry_after_seconds: Optional[int] = None
    ):
        message = f"Rate limit exceeded for client '{client_id}': {limit} requests per {window_seconds} seconds"
        
        if retry_after_seconds:
            user_message = f"요청 한도를 초과했습니다. {retry_after_seconds}초 후에 다시 시도해주세요."
        else:
            user_message = "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요."
        
        context = {
            'client_id': client_id,
            'limit': limit,
            'window_seconds': window_seconds,
            'retry_after_seconds': retry_after_seconds
        }
        
        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            context=context,
            user_message=user_message
        )


class TooManyRequestsError(RateLimitError):
    """Exception raised when too many requests are made in a short period."""
    
    def __init__(
        self, 
        client_id: str,
        request_count: int,
        time_window: str = "minute"
    ):
        message = f"Too many requests from client '{client_id}': {request_count} requests in the last {time_window}"
        user_message = f"너무 많은 요청이 발생했습니다. 잠시 후 다시 시도해주세요."
        
        context = {
            'client_id': client_id,
            'request_count': request_count,
            'time_window': time_window
        }
        
        super().__init__(
            message=message,
            error_code=ErrorCode.TOO_MANY_REQUESTS,
            context=context,
            user_message=user_message
        )