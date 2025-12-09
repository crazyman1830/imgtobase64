"""
Unified logging system for the image converter.

This module provides a consolidated logging system that integrates
all logging functionality into a single, consistent interface.
"""

from .log_formatters import ConsoleFormatter, JSONFormatter, StructuredFormatter
from .log_handlers import PerformanceLogHandler, RotatingFileHandler, SecurityLogHandler
from .unified_logger import (
    LogContext,
    LogEntry,
    LogLevel,
    UnifiedLogger,
    configure_logging,
    get_logger,
    get_main_logger,
    shutdown_logging,
)

__all__ = [
    # Core logging classes
    "UnifiedLogger",
    "LogLevel",
    "LogContext",
    "LogEntry",
    # Factory functions
    "get_logger",
    "get_main_logger",
    "configure_logging",
    "shutdown_logging",
    # Formatters
    "JSONFormatter",
    "StructuredFormatter",
    "ConsoleFormatter",
    # Handlers
    "RotatingFileHandler",
    "SecurityLogHandler",
    "PerformanceLogHandler",
]
