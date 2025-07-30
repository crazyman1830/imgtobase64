"""
Cache exception classes.

This module defines exceptions related to cache operations.
"""

from typing import Optional, Dict, Any
from .base import ImageConverterError, ErrorCode


class CacheError(ImageConverterError):
    """Base class for cache-related errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[ErrorCode] = None,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message, 
            error_code or ErrorCode.CACHE_ERROR, 
            context, 
            user_message
        )


class CacheWriteError(CacheError):
    """Exception raised when cache write operations fail."""
    
    def __init__(
        self, 
        cache_key: str, 
        operation: str = "write",
        original_error: Optional[Exception] = None
    ):
        message = f"Cache {operation} failed for key '{cache_key}'"
        
        if original_error:
            message += f": {str(original_error)}"
        
        user_message = "캐시 저장 중 오류가 발생했습니다."
        
        context = {
            'cache_key': cache_key,
            'operation': operation,
            'original_error': str(original_error) if original_error else None
        }
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CACHE_WRITE_ERROR,
            context=context,
            user_message=user_message
        )


class CacheReadError(CacheError):
    """Exception raised when cache read operations fail."""
    
    def __init__(
        self, 
        cache_key: str, 
        original_error: Optional[Exception] = None
    ):
        message = f"Cache read failed for key '{cache_key}'"
        
        if original_error:
            message += f": {str(original_error)}"
        
        user_message = "캐시 읽기 중 오류가 발생했습니다."
        
        context = {
            'cache_key': cache_key,
            'operation': 'read',
            'original_error': str(original_error) if original_error else None
        }
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CACHE_READ_ERROR,
            context=context,
            user_message=user_message
        )


class CacheCorruptionError(CacheError):
    """Exception raised when cache data is corrupted."""
    
    def __init__(
        self, 
        cache_key: str, 
        corruption_details: Optional[str] = None
    ):
        message = f"Cache data corruption detected for key '{cache_key}'"
        
        if corruption_details:
            message += f": {corruption_details}"
        
        user_message = "캐시 데이터가 손상되었습니다. 캐시를 재생성합니다."
        
        context = {
            'cache_key': cache_key,
            'corruption_details': corruption_details
        }
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CACHE_CORRUPTION,
            context=context,
            user_message=user_message
        )