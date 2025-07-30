"""
Unified logging system for the image converter.

This module provides a consolidated logging system that integrates
all logging functionality into a single, consistent interface.
"""

from .unified_logger import (
    UnifiedLogger,
    LogLevel,
    LogContext,
    LogEntry,
    get_logger,
    get_main_logger,
    configure_logging,
    shutdown_logging
)

from .log_formatters import (
    JSONFormatter,
    StructuredFormatter,
    ConsoleFormatter
)

from .log_handlers import (
    RotatingFileHandler,
    SecurityLogHandler,
    PerformanceLogHandler
)

__all__ = [
    # Core logging classes
    'UnifiedLogger',
    'LogLevel',
    'LogContext', 
    'LogEntry',
    
    # Factory functions
    'get_logger',
    'get_main_logger',
    'configure_logging',
    'shutdown_logging',
    
    # Formatters
    'JSONFormatter',
    'StructuredFormatter',
    'ConsoleFormatter',
    
    # Handlers
    'RotatingFileHandler',
    'SecurityLogHandler',
    'PerformanceLogHandler'
]