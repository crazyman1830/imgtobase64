"""
Validation exception classes.

This module defines exceptions related to input validation and format checking.
"""

from typing import Optional, Dict, Any, List
from .base import ImageConverterError, ErrorCode


class ValidationError(ImageConverterError):
    """Base class for validation-related errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[ErrorCode] = None,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message, 
            error_code or ErrorCode.VALIDATION_ERROR, 
            context, 
            user_message
        )


class UnsupportedFormatError(ValidationError):
    """Exception raised when an unsupported image format is encountered."""
    
    def __init__(
        self, 
        file_path: str, 
        file_extension: str, 
        supported_formats: Optional[List[str]] = None
    ):
        supported_list = ', '.join(supported_formats) if supported_formats else "PNG, JPG, JPEG, GIF, BMP, WEBP"
        
        message = f"Unsupported file format '{file_extension}' for file '{file_path}'"
        user_message = f"'{file_extension}' 형식은 지원되지 않습니다. 지원되는 형식: {supported_list}"
        
        context = {
            'file_path': file_path,
            'file_extension': file_extension,
            'supported_formats': supported_formats or []
        }
        
        super().__init__(
            message=message,
            error_code=ErrorCode.UNSUPPORTED_FORMAT,
            context=context,
            user_message=user_message
        )


class FileSizeError(ValidationError):
    """Exception raised when file size exceeds allowed limits."""
    
    def __init__(
        self, 
        file_path: str, 
        file_size: int, 
        max_size: int,
        size_unit: str = "bytes"
    ):
        message = f"File size {file_size} {size_unit} exceeds maximum allowed size {max_size} {size_unit} for file '{file_path}'"
        
        # Convert to human-readable format for user message
        if size_unit == "bytes":
            file_size_mb = file_size / (1024 * 1024)
            max_size_mb = max_size / (1024 * 1024)
            user_message = f"파일 크기({file_size_mb:.1f}MB)가 허용된 최대 크기({max_size_mb:.1f}MB)를 초과했습니다."
        else:
            user_message = f"파일 크기({file_size} {size_unit})가 허용된 최대 크기({max_size} {size_unit})를 초과했습니다."
        
        context = {
            'file_path': file_path,
            'file_size': file_size,
            'max_size': max_size,
            'size_unit': size_unit
        }
        
        super().__init__(
            message=message,
            error_code=ErrorCode.FILE_SIZE_ERROR,
            context=context,
            user_message=user_message
        )


class InvalidInputError(ValidationError):
    """Exception raised when input parameters are invalid."""
    
    def __init__(
        self, 
        parameter_name: str, 
        parameter_value: Any, 
        expected_type: Optional[str] = None,
        validation_rule: Optional[str] = None
    ):
        message = f"Invalid input parameter '{parameter_name}' with value '{parameter_value}'"
        
        if expected_type:
            message += f", expected type: {expected_type}"
        
        if validation_rule:
            message += f", validation rule: {validation_rule}"
        
        user_message = f"입력 매개변수 '{parameter_name}'의 값이 올바르지 않습니다."
        
        context = {
            'parameter_name': parameter_name,
            'parameter_value': str(parameter_value),
            'expected_type': expected_type,
            'validation_rule': validation_rule
        }
        
        super().__init__(
            message=message,
            error_code=ErrorCode.INVALID_INPUT,
            context=context,
            user_message=user_message
        )