"""
Multi-file processing handler for the image base64 converter.
Legacy compatibility shim for the refactored processing package.
"""

from .processing.handler import MultiFileHandler
from .processing.manager import FileQueueItem, ProcessingQueue
from ..models.models import ConversionError, ConversionResult, ProcessingQueueFullError
from ..models.processing_options import ProcessingOptions, ProgressInfo

__all__ = [
    "MultiFileHandler",
    "FileQueueItem",
    "ProcessingQueue",
    "ConversionError",
    "ConversionResult",
    "ProcessingQueueFullError",
    "ProcessingOptions",
    "ProgressInfo",
]
