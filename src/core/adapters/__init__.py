"""
Legacy adapters for maintaining backward compatibility.

This module provides adapter classes that maintain the existing interfaces
while using the new refactored service layer underneath.
"""

from .file_handler_adapter import FileHandlerAdapter
from .image_converter_adapter import ImageConverterAdapter

__all__ = ["ImageConverterAdapter", "FileHandlerAdapter"]
