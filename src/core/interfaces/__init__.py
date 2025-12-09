"""
Core interfaces for the image converter system.

This module defines the Protocol-based interfaces that establish contracts
for the core components of the image conversion system.
"""

from .cache_manager import ICacheManager
from .file_handler import IFileHandler
from .image_converter import IImageConverter

__all__ = ["IImageConverter", "IFileHandler", "ICacheManager"]
