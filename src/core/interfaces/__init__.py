"""
Core interfaces for the image converter system.

This module defines the Protocol-based interfaces that establish contracts
for the core components of the image conversion system.
"""

from .image_converter import IImageConverter
from .file_handler import IFileHandler
from .cache_manager import ICacheManager

__all__ = [
    'IImageConverter',
    'IFileHandler', 
    'ICacheManager'
]