"""
Structured logging system for the image converter.

This module provides comprehensive structured logging with JSON formatting,
log rotation, performance metrics, and integration with the error handling system.
"""
import logging
import logging.handlers
import json
import time
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading


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
class LogEntry:
    """Structured log entry."""
    timestamp: float
    level: str
    logger_name: str
    message: str
    operation: Optional[str] = None
    file_path: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    processing_time: Optional[float] = None
    memory_usage: Optional[int] = None
    error_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Extract custom fields from record
        log_entry = LogEntry(
            timestamp=record.created,
            level=record.levelname,
            logger_name=record.name,
            message=record.getMessage(),
            operation=getattr(record, 'operation', None),
            file_path=getattr(record, 'file_path', None),
            user_id=getattr(record, 'user_id', None),
            session_id=getattr(record, 'session_id', None),
            processing_time=getattr(record, 'processing_time', None),
            memory_usage=getattr(record, 'memory_usage', None),
            error_id=getattr(record, 'error_id', None),
            metadata=getattr(record, 'metadata', None)
        )
        
        # Add exception info if present
        if record.exc_info:
            log_entry.metadata = log_entry.metadata or {}
            log_entry.metadata['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry.to_dict(), default=str)


class StructuredLogger:
    """
    Enhanced structured logger with performance tracking and custom log levels.
    """
    
    def __init__(
        self,
        name: str,
        log_dir: str = "logs",
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console_level: str = "INFO",
        file_level: str = "DEBUG"
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
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler with JSON format
        log_file = self.log_dir / f"{self.name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        file_handler.setLevel(getattr(logging, file_level.upper()))
        file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(file_handler)
        
        # Error file handler for errors and above
        error_log_file = self.log_dir / f"{self.name}_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(error_handler)
        
        # Security log handler
        security_log_file = self.log_dir / f"{self.name}_security.log"
        security_handler = logging.handlers.RotatingFileHandler(
            security_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        security_handler.setLevel(LogLevel.SECURITY.value)
        security_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(security_handler)
        
        # Performance log handler
        performance_log_file = self.log_dir / f"{self.name}_performance.log"
        performance_handler = logging.handlers.RotatingFileHandler(
            performance_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        performance_handler.setLevel(LogLevel.PERFORMANCE.value)
        performance_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(performance_handler)
    
    def log_operation_start(
        self,
        operation: str,
        file_path: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log the start of an operation and return operation ID."""
        operation_id = f"{operation}_{int(time.time() * 1000)}"
        
        self.logger.info(
            f"Starting operation: {operation}",
            extra={
                'operation': operation,
                'operation_id': operation_id,
                'file_path': file_path,
                'user_id': user_id,
                'session_id': session_id,
                'metadata': metadata
            }
        )
        
        return operation_id
    
    def log_operation_end(
        self,
        operation: str,
        operation_id: str,
        success: bool,
        processing_time: float,
        file_path: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log the end of an operation."""
        # Track operation time for statistics
        with self.operation_lock:
            if operation not in self.operation_times:
                self.operation_times[operation] = []
            self.operation_times[operation].append(processing_time)
            
            # Keep only last 100 times for each operation
            if len(self.operation_times[operation]) > 100:
                self.operation_times[operation] = self.operation_times[operation][-100:]
        
        level = logging.INFO if success else logging.ERROR
        message = f"Completed operation: {operation} ({'success' if success else 'failed'})"
        
        extra_data = {
            'operation': operation,
            'operation_id': operation_id,
            'success': success,
            'processing_time': processing_time,
            'file_path': file_path,
            'user_id': user_id,
            'session_id': session_id,
            'metadata': metadata
        }
        
        if error_message:
            extra_data['error_message'] = error_message
        
        self.logger.log(level, message, extra=extra_data)
    
    def log_performance_metric(
        self,
        metric_name: str,
        value: float,
        unit: str,
        operation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a performance metric."""
        self.logger.performance(
            f"Performance metric: {metric_name} = {value} {unit}",
            extra={
                'metric_name': metric_name,
                'metric_value': value,
                'metric_unit': unit,
                'operation': operation,
                'metadata': metadata
            }
        )
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        file_path: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a security event."""
        self.logger.security(
            f"Security event: {event_type} - {description}",
            extra={
                'event_type': event_type,
                'severity': severity,
                'description': description,
                'file_path': file_path,
                'user_id': user_id,
                'session_id': session_id,
                'metadata': metadata
            }
        )
    
    def log_error_with_context(
        self,
        error_id: str,
        exception: Exception,
        operation: Optional[str] = None,
        file_path: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log an error with full context."""
        self.logger.error(
            f"Error {error_id}: {str(exception)}",
            extra={
                'error_id': error_id,
                'exception_type': type(exception).__name__,
                'operation': operation,
                'file_path': file_path,
                'user_id': user_id,
                'session_id': session_id,
                'metadata': metadata
            },
            exc_info=True
        )
    
    def get_performance_statistics(self) -> Dict[str, Any]:
        """Get performance statistics for all operations."""
        stats = {}
        
        with self.operation_lock:
            for operation, times in self.operation_times.items():
                if times:
                    stats[operation] = {
                        'count': len(times),
                        'avg_time': sum(times) / len(times),
                        'min_time': min(times),
                        'max_time': max(times),
                        'total_time': sum(times)
                    }
        
        return stats
    
    def clear_performance_statistics(self):
        """Clear performance statistics."""
        with self.operation_lock:
            self.operation_times.clear()
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(message, extra=kwargs)
    
    def trace(self, message: str, **kwargs):
        """Log trace message."""
        self.logger.trace(message, extra=kwargs)


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
    return get_structured_logger('image_converter')


def get_performance_logger() -> StructuredLogger:
    """Get the performance logger."""
    return get_structured_logger('image_converter_performance')


def get_security_logger() -> StructuredLogger:
    """Get the security logger."""
    return get_structured_logger('image_converter_security')