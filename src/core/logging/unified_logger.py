"""
Unified logging system that consolidates all logging functionality.

This module provides a single, consistent logging interface that integrates
structured logging, security logging, performance logging, and error logging.
"""

import logging
import logging.handlers
import json
import time
import threading
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime

from ..utils.path_utils import PathUtils
from ..utils.type_utils import TypeUtils
from ..config.unified_config_manager import get_config


class LogLevel(Enum):
    """Unified log levels for the application."""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    SECURITY = 60
    PERFORMANCE = 25


@dataclass
class LogContext:
    """Context information for structured logging."""
    operation: Optional[str] = None
    operation_id: Optional[str] = None
    file_path: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    error_id: Optional[str] = None
    processing_time: Optional[float] = None
    memory_usage: Optional[int] = None
    thread_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize computed fields."""
        if self.thread_id is None:
            self.thread_id = str(threading.current_thread().ident)
        
        if self.correlation_id is None and self.operation_id:
            self.correlation_id = self.operation_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = value
        return result
    
    def merge(self, other: 'LogContext') -> 'LogContext':
        """Merge with another context, with other taking precedence."""
        merged = LogContext()
        
        for field_name in self.__dataclass_fields__:
            self_value = getattr(self, field_name)
            other_value = getattr(other, field_name)
            
            if field_name == 'metadata':
                # Special handling for metadata merging
                merged_metadata = {}
                if self_value:
                    merged_metadata.update(self_value)
                if other_value:
                    merged_metadata.update(other_value)
                setattr(merged, field_name, merged_metadata if merged_metadata else None)
            else:
                # Other fields: other takes precedence
                setattr(merged, field_name, other_value if other_value is not None else self_value)
        
        return merged


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
            'timestamp': self.timestamp,
            'iso_timestamp': datetime.fromtimestamp(self.timestamp).isoformat(),
            'level': self.level,
            'logger': self.logger_name,
            'message': self.message
        }
        
        if self.context:
            result.update(self.context.to_dict())
        
        if self.exception_info:
            result['exception'] = self.exception_info
        
        return result


class UnifiedLogger:
    """
    Unified logger that consolidates all logging functionality.
    
    This logger provides:
    - Structured logging with JSON format
    - Context management and correlation
    - Performance tracking
    - Security event logging
    - Multiple output handlers
    - Thread-safe operation
    """
    
    def __init__(
        self,
        name: str,
        config_manager=None
    ):
        """
        Initialize the unified logger.
        
        Args:
            name: Logger name
            config_manager: Configuration manager instance
        """
        self.name = name
        self._config_manager = config_manager
        
        # Initialize Python logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(LogLevel.TRACE.value)
        
        # Add custom log levels
        self._add_custom_levels()
        
        # Set up handlers based on configuration
        self._setup_handlers()
        
        # Context management
        self._context_stack: List[LogContext] = []
        self._context_lock = threading.Lock()
        
        # Performance tracking
        self._operation_times: Dict[str, List[float]] = {}
        self._operation_lock = threading.Lock()
        
        # Event listeners
        self._event_listeners: List[Callable] = []
        self._listener_lock = threading.Lock()
    
    def _add_custom_levels(self):
        """Add custom log levels to the logging module."""
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
    
    def _setup_handlers(self):
        """Set up logging handlers based on configuration."""
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Get configuration
        log_level = get_config('logging.level', 'INFO')
        log_dir = get_config('logging.directory', 'logs')
        enable_file_logging = get_config('logging.enable_file_logging', True)
        max_file_size_mb = get_config('logging.max_file_size_mb', 10)
        backup_count = get_config('logging.backup_count', 5)
        
        # Ensure log directory exists
        log_dir_path = PathUtils.ensure_directory_exists(log_dir)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        from .log_formatters import ConsoleFormatter
        console_handler.setFormatter(ConsoleFormatter())
        self.logger.addHandler(console_handler)
        
        if enable_file_logging:
            # Main log file handler
            main_log_file = log_dir_path / f"{self.name}.log"
            main_handler = logging.handlers.RotatingFileHandler(
                main_log_file,
                maxBytes=max_file_size_mb * 1024 * 1024,
                backupCount=backup_count
            )
            main_handler.setLevel(LogLevel.TRACE.value)
            
            from .log_formatters import JSONFormatter
            main_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(main_handler)
            
            # Error log file handler
            error_log_file = log_dir_path / f"{self.name}_errors.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=max_file_size_mb * 1024 * 1024,
                backupCount=backup_count
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(error_handler)
            
            # Security log file handler
            security_log_file = log_dir_path / f"{self.name}_security.log"
            from .log_handlers import SecurityLogHandler
            security_handler = SecurityLogHandler(
                security_log_file,
                maxBytes=max_file_size_mb * 1024 * 1024,
                backupCount=backup_count
            )
            security_handler.setLevel(LogLevel.SECURITY.value)
            self.logger.addHandler(security_handler)
            
            # Performance log file handler
            performance_log_file = log_dir_path / f"{self.name}_performance.log"
            from .log_handlers import PerformanceLogHandler
            performance_handler = PerformanceLogHandler(
                performance_log_file,
                maxBytes=max_file_size_mb * 1024 * 1024,
                backupCount=backup_count
            )
            performance_handler.setLevel(LogLevel.PERFORMANCE.value)
            self.logger.addHandler(performance_handler)
    
    @contextmanager
    def operation_context(
        self,
        operation: str,
        **context_kwargs
    ):
        """
        Context manager for logging operations with automatic timing and correlation.
        
        Args:
            operation: Operation name
            **context_kwargs: Additional context parameters
        """
        operation_id = f"{operation}_{int(time.time() * 1000000)}"
        start_time = time.time()
        
        # Create context
        context = LogContext(
            operation=operation,
            operation_id=operation_id,
            correlation_id=operation_id,
            **context_kwargs
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
            
            self.info(f"Completed operation: {operation}", context=context)
            
        except Exception as e:
            # Failure
            processing_time = time.time() - start_time
            context.processing_time = processing_time
            context.metadata = context.metadata or {}
            context.metadata['error'] = str(e)
            context.metadata['error_type'] = type(e).__name__
            
            self.error(f"Failed operation: {operation}", context=context, exc_info=True)
            raise
        finally:
            # Pop context from stack
            with self._context_lock:
                if self._context_stack and self._context_stack[-1].operation_id == operation_id:
                    self._context_stack.pop()
    
    def _track_operation_time(self, operation: str, processing_time: float):
        """Track operation time for performance statistics."""
        with self._operation_lock:
            if operation not in self._operation_times:
                self._operation_times[operation] = []
            
            self._operation_times[operation].append(processing_time)
            
            # Keep only last 1000 times for each operation
            if len(self._operation_times[operation]) > 1000:
                self._operation_times[operation] = self._operation_times[operation][-1000:]
    
    def _get_current_context(self) -> Optional[LogContext]:
        """Get the current context from the stack."""
        with self._context_lock:
            return self._context_stack[-1] if self._context_stack else None
    
    def _merge_contexts(self, provided_context: Optional[LogContext]) -> Optional[LogContext]:
        """Merge provided context with current context."""
        current_context = self._get_current_context()
        
        if not current_context and not provided_context:
            return None
        
        if not current_context:
            return provided_context
        
        if not provided_context:
            return current_context
        
        return current_context.merge(provided_context)
    
    def _log_with_context(
        self,
        level: int,
        message: str,
        context: Optional[LogContext] = None,
        exc_info: bool = False,
        **kwargs
    ):
        """Internal method to log with context merging."""
        # Merge contexts
        final_context = self._merge_contexts(context)
        
        # Create log entry
        log_entry = LogEntry(
            timestamp=time.time(),
            level=logging.getLevelName(level),
            logger_name=self.name,
            message=message,
            context=final_context,
            exception_info=None
        )
        
        # Prepare extra data for Python logger
        extra = {}
        if final_context:
            extra.update(final_context.to_dict())
        extra.update(kwargs)
        
        # Log the message
        self.logger.log(level, message, extra=extra, exc_info=exc_info)
        
        # Notify event listeners
        self._notify_event_listeners(log_entry)
    
    def _notify_event_listeners(self, log_entry: LogEntry):
        """Notify all event listeners of a log entry."""
        with self._listener_lock:
            for listener in self._event_listeners:
                try:
                    listener(log_entry)
                except Exception as e:
                    # Don't let listener errors break logging
                    print(f"Warning: Log event listener failed: {e}")
    
    def add_event_listener(self, listener: Callable[[LogEntry], None]):
        """Add an event listener for log entries."""
        with self._listener_lock:
            self._event_listeners.append(listener)
    
    def remove_event_listener(self, listener: Callable[[LogEntry], None]):
        """Remove an event listener."""
        with self._listener_lock:
            if listener in self._event_listeners:
                self._event_listeners.remove(listener)
    
    # Logging methods
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
    
    def error(self, message: str, context: Optional[LogContext] = None, exc_info: bool = False, **kwargs):
        """Log error message."""
        self._log_with_context(logging.ERROR, message, context, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, context: Optional[LogContext] = None, exc_info: bool = False, **kwargs):
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, context, exc_info=exc_info, **kwargs)
    
    def security(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Log security event."""
        self._log_with_context(LogLevel.SECURITY.value, message, context, **kwargs)
    
    def performance(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Log performance metric."""
        self._log_with_context(LogLevel.PERFORMANCE.value, message, context, **kwargs)
    
    # Convenience methods for common logging patterns
    def log_operation_start(self, operation: str, **context_kwargs) -> str:
        """Log the start of an operation and return operation ID."""
        operation_id = f"{operation}_{int(time.time() * 1000000)}"
        context = LogContext(
            operation=operation,
            operation_id=operation_id,
            **context_kwargs
        )
        self.info(f"Starting operation: {operation}", context=context)
        return operation_id
    
    def log_operation_end(
        self,
        operation: str,
        operation_id: str,
        success: bool = True,
        processing_time: Optional[float] = None,
        error_message: Optional[str] = None,
        **context_kwargs
    ):
        """Log the end of an operation."""
        context = LogContext(
            operation=operation,
            operation_id=operation_id,
            processing_time=processing_time,
            **context_kwargs
        )
        
        if processing_time:
            self._track_operation_time(operation, processing_time)
        
        if success:
            self.info(f"Completed operation: {operation}", context=context)
        else:
            if error_message:
                context.metadata = context.metadata or {}
                context.metadata['error_message'] = error_message
            self.error(f"Failed operation: {operation}", context=context)
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        **context_kwargs
    ):
        """Log a security event."""
        context = LogContext(**context_kwargs)
        context.metadata = context.metadata or {}
        context.metadata.update({
            'event_type': event_type,
            'severity': severity,
            'description': description
        })
        
        self.security(f"Security event: {event_type} - {description}", context=context)
    
    def log_performance_metric(
        self,
        metric_name: str,
        value: Union[float, int],
        unit: str,
        **context_kwargs
    ):
        """Log a performance metric."""
        context = LogContext(**context_kwargs)
        context.metadata = context.metadata or {}
        context.metadata.update({
            'metric_name': metric_name,
            'metric_value': value,
            'metric_unit': unit
        })
        
        self.performance(f"Performance metric: {metric_name} = {value} {unit}", context=context)
    
    def get_performance_statistics(self) -> Dict[str, Any]:
        """Get performance statistics for all operations."""
        stats = {}
        
        with self._operation_lock:
            for operation, times in self._operation_times.items():
                if times:
                    stats[operation] = {
                        'count': len(times),
                        'avg_time': sum(times) / len(times),
                        'min_time': min(times),
                        'max_time': max(times),
                        'total_time': sum(times),
                        'recent_avg': sum(times[-10:]) / min(len(times), 10)
                    }
        
        return stats
    
    def clear_performance_statistics(self):
        """Clear performance statistics."""
        with self._operation_lock:
            self._operation_times.clear()
    
    def reconfigure(self):
        """Reconfigure the logger based on current configuration."""
        self._setup_handlers()


# Global logger instances
_loggers: Dict[str, UnifiedLogger] = {}
_logger_lock = threading.Lock()


def get_logger(name: str) -> UnifiedLogger:
    """Get or create a unified logger instance."""
    with _logger_lock:
        if name not in _loggers:
            _loggers[name] = UnifiedLogger(name)
        return _loggers[name]


def get_main_logger() -> UnifiedLogger:
    """Get the main application logger."""
    return get_logger('image_converter')


def configure_logging():
    """Configure all existing loggers based on current configuration."""
    with _logger_lock:
        for logger in _loggers.values():
            logger.reconfigure()


def shutdown_logging():
    """Shutdown all loggers and handlers."""
    with _logger_lock:
        for logger in _loggers.values():
            for handler in logger.logger.handlers:
                handler.close()
            logger.logger.handlers.clear()
        _loggers.clear()


# Convenience functions for common logging patterns
def create_log_context(**kwargs) -> LogContext:
    """Create a LogContext with the provided parameters."""
    return LogContext(**kwargs)