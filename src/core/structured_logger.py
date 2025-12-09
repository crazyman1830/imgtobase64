"""
Improved structured logging system for the image converter.

This module provides simplified yet comprehensive structured logging with JSON formatting,
log rotation, performance metrics, and seamless integration with the error handling system.
"""

import json
import logging
import logging.handlers
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class LogLevel(Enum):
    """Custom log levels for the application."""

    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    SECURITY = 60  # Custom level for security events
    PERFORMANCE = 25  # Custom level for performance metrics


@dataclass
class LogContext:
    """Context information for structured logging."""

    operation: Optional[str] = None
    operation_id: Optional[str] = None
    file_path: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    error_id: Optional[str] = None
    processing_time: Optional[float] = None
    memory_usage: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class LogEntry:
    """Structured log entry."""

    timestamp: float
    level: str
    logger_name: str
    message: str
    context: Optional[LogContext] = None
    exception_info: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "timestamp": self.timestamp,
            "level": self.level,
            "logger": self.logger_name,
            "message": self.message,
        }

        if self.context:
            result.update(self.context.to_dict())

        if self.exception_info:
            result["exception"] = self.exception_info

        return result


class JSONFormatter(logging.Formatter):
    """Improved JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Extract context from record
        context = LogContext(
            operation=getattr(record, "operation", None),
            operation_id=getattr(record, "operation_id", None),
            file_path=getattr(record, "file_path", None),
            user_id=getattr(record, "user_id", None),
            session_id=getattr(record, "session_id", None),
            error_id=getattr(record, "error_id", None),
            processing_time=getattr(record, "processing_time", None),
            memory_usage=getattr(record, "memory_usage", None),
            metadata=getattr(record, "metadata", None),
        )

        # Create log entry
        log_entry = LogEntry(
            timestamp=record.created,
            level=record.levelname,
            logger_name=record.name,
            message=record.getMessage(),
            context=context if any(context.to_dict().values()) else None,
            exception_info=(
                self.formatException(record.exc_info) if record.exc_info else None
            ),
        )

        return json.dumps(log_entry.to_dict(), default=str, ensure_ascii=False)


class StructuredLogger:
    """
    Improved structured logger with simplified interface and better context management.
    """

    def __init__(
        self,
        name: str,
        log_dir: str = "logs",
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console_level: str = "INFO",
        file_level: str = "DEBUG",
    ):
        """Initialize the structured logger."""
        self.name = name
        self.log_dir = Path(log_dir)
        self.max_file_size = max_file_size
        self.backup_count = backup_count

        # Create log directory
        self.log_dir.mkdir(exist_ok=True)

        # Set up logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Add custom log levels
        self._add_custom_levels()

        # Set up handlers
        self._setup_handlers(console_level, file_level)

        # Performance tracking
        self.operation_times: Dict[str, List[float]] = {}
        self.operation_lock = threading.Lock()

        # Context stack for nested operations
        self._context_stack: List[LogContext] = []
        self._context_lock = threading.Lock()

    def _add_custom_levels(self):
        """Add custom log levels."""
        # Add SECURITY level
        logging.addLevelName(LogLevel.SECURITY.value, "SECURITY")

        def security(self, message, *args, **kwargs):
            if self.isEnabledFor(LogLevel.SECURITY.value):
                self._log(LogLevel.SECURITY.value, message, args, **kwargs)

        logging.Logger.security = security

        # Add PERFORMANCE level
        logging.addLevelName(LogLevel.PERFORMANCE.value, "PERFORMANCE")

        def performance(self, message, *args, **kwargs):
            if self.isEnabledFor(LogLevel.PERFORMANCE.value):
                self._log(LogLevel.PERFORMANCE.value, message, args, **kwargs)

        logging.Logger.performance = performance

        # Add TRACE level
        logging.addLevelName(LogLevel.TRACE.value, "TRACE")

        def trace(self, message, *args, **kwargs):
            if self.isEnabledFor(LogLevel.TRACE.value):
                self._log(LogLevel.TRACE.value, message, args, **kwargs)

        logging.Logger.trace = trace

    def _setup_handlers(self, console_level: str, file_level: str):
        """Set up logging handlers."""
        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler with simple format
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, console_level.upper()))
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler with JSON format
        log_file = self.log_dir / f"{self.name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=self.max_file_size, backupCount=self.backup_count
        )
        file_handler.setLevel(getattr(logging, file_level.upper()))
        file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(file_handler)

        # Error file handler for errors and above
        error_log_file = self.log_dir / f"{self.name}_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file, maxBytes=self.max_file_size, backupCount=self.backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(error_handler)

        # Security log handler
        security_log_file = self.log_dir / f"{self.name}_security.log"
        security_handler = logging.handlers.RotatingFileHandler(
            security_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
        )
        security_handler.setLevel(LogLevel.SECURITY.value)
        security_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(security_handler)

        # Performance log handler
        performance_log_file = self.log_dir / f"{self.name}_performance.log"
        performance_handler = logging.handlers.RotatingFileHandler(
            performance_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
        )
        performance_handler.setLevel(LogLevel.PERFORMANCE.value)
        performance_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(performance_handler)

    @contextmanager
    def operation_context(
        self,
        operation: str,
        file_path: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for logging operations with automatic timing."""
        operation_id = f"{operation}_{int(time.time() * 1000)}"
        start_time = time.time()

        # Create context
        context = LogContext(
            operation=operation,
            operation_id=operation_id,
            file_path=file_path,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata,
        )

        # Push context to stack
        with self._context_lock:
            self._context_stack.append(context)

        try:
            self.info(f"Starting operation: {operation}", context=context)
            yield operation_id

            # Success
            processing_time = time.time() - start_time
            context.processing_time = processing_time
            self._track_operation_time(operation, processing_time)
            self.info(f"Completed operation: {operation} (success)", context=context)

        except Exception as e:
            # Failure
            processing_time = time.time() - start_time
            context.processing_time = processing_time
            context.metadata = context.metadata or {}
            context.metadata["error"] = str(e)
            self.error(f"Failed operation: {operation}", context=context, exc_info=True)
            raise
        finally:
            # Pop context from stack
            with self._context_lock:
                if (
                    self._context_stack
                    and self._context_stack[-1].operation_id == operation_id
                ):
                    self._context_stack.pop()

    def _track_operation_time(self, operation: str, processing_time: float):
        """Track operation time for statistics."""
        with self.operation_lock:
            if operation not in self.operation_times:
                self.operation_times[operation] = []
            self.operation_times[operation].append(processing_time)

            # Keep only last 100 times for each operation
            if len(self.operation_times[operation]) > 100:
                self.operation_times[operation] = self.operation_times[operation][-100:]

    def _get_current_context(self) -> Optional[LogContext]:
        """Get the current context from the stack."""
        with self._context_lock:
            return self._context_stack[-1] if self._context_stack else None

    def _merge_contexts(
        self, provided_context: Optional[LogContext]
    ) -> Optional[LogContext]:
        """Merge provided context with current context."""
        current_context = self._get_current_context()

        if not current_context and not provided_context:
            return None

        if not current_context:
            return provided_context

        if not provided_context:
            return current_context

        # Merge contexts, with provided context taking precedence
        merged = LogContext()
        for field in [
            "operation",
            "operation_id",
            "file_path",
            "user_id",
            "session_id",
            "error_id",
            "processing_time",
            "memory_usage",
        ]:
            current_value = getattr(current_context, field)
            provided_value = getattr(provided_context, field)
            setattr(
                merged,
                field,
                provided_value if provided_value is not None else current_value,
            )

        # Merge metadata
        merged.metadata = {}
        if current_context.metadata:
            merged.metadata.update(current_context.metadata)
        if provided_context.metadata:
            merged.metadata.update(provided_context.metadata)

        return merged if any(merged.to_dict().values()) else None

    def log_operation_result(
        self,
        operation: str,
        success: bool,
        processing_time: Optional[float] = None,
        error_message: Optional[str] = None,
        context: Optional[LogContext] = None,
    ):
        """Log the result of an operation."""
        if processing_time:
            self._track_operation_time(operation, processing_time)

        result_context = context or LogContext()
        result_context.operation = result_context.operation or operation
        result_context.processing_time = (
            result_context.processing_time or processing_time
        )

        if error_message:
            result_context.metadata = result_context.metadata or {}
            result_context.metadata["error_message"] = error_message

        message = (
            f"Operation {operation} {'completed successfully' if success else 'failed'}"
        )

        if success:
            self.info(message, context=result_context)
        else:
            self.error(message, context=result_context)

    def log_performance_metric(
        self,
        metric_name: str,
        value: Union[float, int],
        unit: str,
        context: Optional[LogContext] = None,
    ):
        """Log a performance metric."""
        metric_context = context or LogContext()
        metric_context.metadata = metric_context.metadata or {}
        metric_context.metadata.update(
            {"metric_name": metric_name, "metric_value": value, "metric_unit": unit}
        )

        self.performance(
            f"Performance metric: {metric_name} = {value} {unit}",
            context=metric_context,
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        context: Optional[LogContext] = None,
    ):
        """Log a security event."""
        security_context = context or LogContext()
        security_context.metadata = security_context.metadata or {}
        security_context.metadata.update(
            {"event_type": event_type, "severity": severity, "description": description}
        )

        self.security(
            f"Security event: {event_type} - {description}", context=security_context
        )

    def log_error_with_context(
        self, error_id: str, exception: Exception, context: Optional[LogContext] = None
    ):
        """Log an error with full context."""
        error_context = context or LogContext()
        error_context.error_id = error_id
        error_context.metadata = error_context.metadata or {}
        error_context.metadata["exception_type"] = type(exception).__name__

        self.error(
            f"Error {error_id}: {str(exception)}", context=error_context, exc_info=True
        )

    def get_performance_statistics(self) -> Dict[str, Any]:
        """Get performance statistics for all operations."""
        stats = {}

        with self.operation_lock:
            for operation, times in self.operation_times.items():
                if times:
                    stats[operation] = {
                        "count": len(times),
                        "avg_time": sum(times) / len(times),
                        "min_time": min(times),
                        "max_time": max(times),
                        "total_time": sum(times),
                    }

        return stats

    def clear_performance_statistics(self):
        """Clear performance statistics."""
        with self.operation_lock:
            self.operation_times.clear()

    def _log_with_context(
        self,
        level: int,
        message: str,
        context: Optional[LogContext] = None,
        exc_info: bool = False,
        **kwargs,
    ):
        """Internal method to log with context merging."""
        # Merge contexts
        final_context = self._merge_contexts(context)

        # Prepare extra data
        extra = {}
        if final_context:
            extra.update(final_context.to_dict())

        # Add any additional kwargs
        extra.update(kwargs)

        self.logger.log(level, message, extra=extra, exc_info=exc_info)

    def trace(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Log trace message."""
        self._log_with_context(LogLevel.TRACE.value, message, context, **kwargs)

    def debug(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, context, **kwargs)

    def info(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Log info message."""
        self._log_with_context(logging.INFO, message, context, **kwargs)

    def warning(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, context, **kwargs)

    def error(
        self,
        message: str,
        context: Optional[LogContext] = None,
        exc_info: bool = False,
        **kwargs,
    ):
        """Log error message."""
        self._log_with_context(
            logging.ERROR, message, context, exc_info=exc_info, **kwargs
        )

    def critical(
        self,
        message: str,
        context: Optional[LogContext] = None,
        exc_info: bool = False,
        **kwargs,
    ):
        """Log critical message."""
        self._log_with_context(
            logging.CRITICAL, message, context, exc_info=exc_info, **kwargs
        )

    def security(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Log security event."""
        self._log_with_context(LogLevel.SECURITY.value, message, context, **kwargs)

    def performance(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Log performance metric."""
        self._log_with_context(LogLevel.PERFORMANCE.value, message, context, **kwargs)


# Global logger instances
_loggers: Dict[str, StructuredLogger] = {}
_logger_lock = threading.Lock()


def get_structured_logger(name: str, **kwargs) -> StructuredLogger:
    """Get or create a structured logger instance."""
    with _logger_lock:
        if name not in _loggers:
            _loggers[name] = StructuredLogger(name, **kwargs)
        return _loggers[name]


def get_main_logger() -> StructuredLogger:
    """Get the main application logger."""
    return get_structured_logger("image_converter")


def get_performance_logger() -> StructuredLogger:
    """Get the performance logger."""
    return get_structured_logger("image_converter_performance")


def get_security_logger() -> StructuredLogger:
    """Get the security logger."""
    return get_structured_logger("image_converter_security")


def create_log_context(
    operation: Optional[str] = None,
    operation_id: Optional[str] = None,
    file_path: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    error_id: Optional[str] = None,
    processing_time: Optional[float] = None,
    memory_usage: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> LogContext:
    """Convenience function to create a LogContext."""
    return LogContext(
        operation=operation,
        operation_id=operation_id,
        file_path=file_path,
        user_id=user_id,
        session_id=session_id,
        error_id=error_id,
        processing_time=processing_time,
        memory_usage=memory_usage,
        metadata=metadata,
    )
