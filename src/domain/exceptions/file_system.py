"""
File system exception classes.

This module defines exceptions related to file system operations.
"""

from typing import Optional, Dict, Any
from .base import ImageConverterError, ErrorCode


class FileSystemError(ImageConverterError):
    """Base class for file system-related errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[ErrorCode] = None,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message, 
            error_code or ErrorCode.FILE_SYSTEM_ERROR, 
            context, 
            user_message
        )


class FileNotFoundError(FileSystemError):
    """Exception raised when a file cannot be found."""
    
    def __init__(self, file_path: str):
        message = f"File not found: {file_path}"
        user_message = f"파일을 찾을 수 없습니다: {file_path}"
        
        context = {
            'file_path': file_path,
            'operation': 'file_access'
        }
        
        super().__init__(
            message=message,
            error_code=ErrorCode.FILE_NOT_FOUND,
            context=context,
            user_message=user_message
        )


class DirectoryNotFoundError(FileSystemError):
    """Exception raised when a directory cannot be found."""
    
    def __init__(self, directory_path: str):
        message = f"Directory not found: {directory_path}"
        user_message = f"디렉토리를 찾을 수 없습니다: {directory_path}"
        
        context = {
            'directory_path': directory_path,
            'operation': 'directory_access'
        }
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DIRECTORY_NOT_FOUND,
            context=context,
            user_message=user_message
        )


class PermissionError(FileSystemError):
    """Exception raised when there are insufficient permissions."""
    
    def __init__(self, file_path: str, operation: str = "access"):
        message = f"Permission denied: Cannot {operation} file {file_path}"
        user_message = f"파일에 접근할 권한이 없습니다: {file_path}"
        
        context = {
            'file_path': file_path,
            'operation': operation
        }
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PERMISSION_DENIED,
            context=context,
            user_message=user_message
        )


class FileExistsError(FileSystemError):
    """Exception raised when a file already exists and overwrite is not allowed."""
    
    def __init__(self, file_path: str):
        message = f"File already exists: {file_path}"
        user_message = f"파일이 이미 존재합니다: {file_path}"
        
        context = {
            'file_path': file_path,
            'operation': 'file_creation'
        }
        
        super().__init__(
            message=message,
            error_code=ErrorCode.FILE_EXISTS,
            context=context,
            user_message=user_message
        )