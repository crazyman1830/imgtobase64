"""
Enhanced error handling system for the image converter.

This module provides comprehensive error handling, user-friendly error messages,
structured logging, and error recovery mechanisms integrated with the Result pattern.
"""
import logging
import traceback
import time
from typing import Dict, Any, Optional, List, Callable, Type
from dataclasses import dataclass
from enum import Enum
import json

from ..domain.exceptions.base import ImageConverterError, ErrorCode
from ..domain.exceptions.validation import ValidationError, UnsupportedFormatError, FileSizeError
from ..domain.exceptions.file_system import FileSystemError, FileNotFoundError, PermissionError
from ..domain.exceptions.processing import ProcessingError, ConversionError, CorruptedFileError
from ..domain.exceptions.security import SecurityError, SecurityThreatDetectedError
from ..domain.exceptions.cache import CacheError, CacheWriteError, CacheReadError
from ..domain.exceptions.queue import QueueError, ProcessingQueueFullError
from ..core.base.result import Result


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better classification."""
    FILE_SYSTEM = "file_system"
    PROCESSING = "processing"
    SECURITY = "security"
    NETWORK = "network"
    CACHE = "cache"
    VALIDATION = "validation"
    SYSTEM = "system"
    USER_INPUT = "user_input"


@dataclass
class ErrorContext:
    """Context information for errors."""
    error_id: str
    timestamp: float
    severity: ErrorSeverity
    category: ErrorCategory
    original_exception: Exception
    user_message: str
    technical_message: str
    file_path: Optional[str] = None
    operation: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    stack_trace: Optional[str] = None
    recovery_suggestions: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.recovery_suggestions is None:
            self.recovery_suggestions = []
        if self.metadata is None:
            self.metadata = {}


class ErrorHandler:
    """
    Comprehensive error handler with user-friendly messages and recovery mechanisms.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the error handler."""
        self.logger = logger or self._setup_logger()
        self.error_counter = 0
        self.error_history: List[ErrorContext] = []
        self.max_history_size = 1000
        
        # Error mapping for user-friendly messages
        self.error_mappings = self._setup_error_mappings()
        
        # Recovery strategies
        self.recovery_strategies: Dict[type, Callable] = {}
        self._setup_recovery_strategies()
    
    def _setup_logger(self) -> logging.Logger:
        """Set up structured logging."""
        logger = logging.getLogger('image_converter.error_handler')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # File handler for errors
            file_handler = logging.FileHandler('logs/error_handler.log')
            file_handler.setLevel(logging.WARNING)
            
            # JSON formatter for structured logging
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        
        return logger
    
    def _setup_error_mappings(self) -> Dict[Type[Exception], Dict[str, Any]]:
        """Set up error mappings for user-friendly messages."""
        return {
            # File System Errors
            FileNotFoundError: {
                'category': ErrorCategory.FILE_SYSTEM,
                'severity': ErrorSeverity.MEDIUM,
                'recovery_suggestions': [
                    'Verify the file path is correct',
                    'Check if the file exists in the specified location',
                    'Ensure you have permission to access the file'
                ]
            },
            PermissionError: {
                'category': ErrorCategory.FILE_SYSTEM,
                'severity': ErrorSeverity.MEDIUM,
                'recovery_suggestions': [
                    'Check file permissions',
                    'Run the application with appropriate privileges',
                    'Contact your system administrator'
                ]
            },
            FileSystemError: {
                'category': ErrorCategory.FILE_SYSTEM,
                'severity': ErrorSeverity.MEDIUM,
                'recovery_suggestions': [
                    'Check file system permissions',
                    'Verify disk space availability',
                    'Try again with a different file location'
                ]
            },
            
            # Validation Errors
            UnsupportedFormatError: {
                'category': ErrorCategory.VALIDATION,
                'severity': ErrorSeverity.LOW,
                'recovery_suggestions': [
                    'Convert the file to a supported format (PNG, JPEG, WEBP, GIF, BMP)',
                    'Check the file extension matches the actual file format',
                    'Try with a different image file'
                ]
            },
            FileSizeError: {
                'category': ErrorCategory.VALIDATION,
                'severity': ErrorSeverity.LOW,
                'recovery_suggestions': [
                    'Reduce the file size',
                    'Compress the image before processing',
                    'Check the maximum allowed file size'
                ]
            },
            ValidationError: {
                'category': ErrorCategory.VALIDATION,
                'severity': ErrorSeverity.LOW,
                'recovery_suggestions': [
                    'Check input parameters',
                    'Verify file format and content',
                    'Review the validation requirements'
                ]
            },
            
            # Processing Errors
            CorruptedFileError: {
                'category': ErrorCategory.PROCESSING,
                'severity': ErrorSeverity.MEDIUM,
                'recovery_suggestions': [
                    'Try with a different image file',
                    'Re-download or re-create the image file',
                    'Check if the file was properly transferred'
                ]
            },
            ConversionError: {
                'category': ErrorCategory.PROCESSING,
                'severity': ErrorSeverity.MEDIUM,
                'recovery_suggestions': [
                    'Try with a different image file',
                    'Check if the image file is valid',
                    'Reduce image size or complexity'
                ]
            },
            ProcessingError: {
                'category': ErrorCategory.PROCESSING,
                'severity': ErrorSeverity.MEDIUM,
                'recovery_suggestions': [
                    'Retry the operation',
                    'Check system resources',
                    'Try with a simpler image'
                ]
            },
            
            # Security Errors
            SecurityThreatDetectedError: {
                'category': ErrorCategory.SECURITY,
                'severity': ErrorSeverity.HIGH,
                'recovery_suggestions': [
                    'Scan the file with antivirus software',
                    'Use a different, trusted image file',
                    'Contact support if you believe this is a false positive'
                ]
            },
            SecurityError: {
                'category': ErrorCategory.SECURITY,
                'severity': ErrorSeverity.HIGH,
                'recovery_suggestions': [
                    'Review security settings',
                    'Use trusted files only',
                    'Contact security team if needed'
                ]
            },
            
            # Cache Errors
            CacheWriteError: {
                'category': ErrorCategory.CACHE,
                'severity': ErrorSeverity.LOW,
                'recovery_suggestions': [
                    'Clear the application cache',
                    'Check available disk space',
                    'Restart the application if the problem persists'
                ]
            },
            CacheReadError: {
                'category': ErrorCategory.CACHE,
                'severity': ErrorSeverity.LOW,
                'recovery_suggestions': [
                    'Clear the application cache',
                    'Check cache file permissions',
                    'Restart the application if the problem persists'
                ]
            },
            CacheError: {
                'category': ErrorCategory.CACHE,
                'severity': ErrorSeverity.LOW,
                'recovery_suggestions': [
                    'Clear the application cache',
                    'Check available disk space',
                    'Restart the application if the problem persists'
                ]
            },
            
            # Queue Errors
            ProcessingQueueFullError: {
                'category': ErrorCategory.SYSTEM,
                'severity': ErrorSeverity.MEDIUM,
                'recovery_suggestions': [
                    'Wait a few moments and try again',
                    'Process fewer files at once',
                    'Check system resources'
                ]
            },
            QueueError: {
                'category': ErrorCategory.SYSTEM,
                'severity': ErrorSeverity.MEDIUM,
                'recovery_suggestions': [
                    'Retry the operation',
                    'Check system status',
                    'Contact support if the problem persists'
                ]
            }
        }
    
    def _setup_recovery_strategies(self):
        """Set up automatic recovery strategies for different error types."""
        self.recovery_strategies = {
            CacheError: self._recover_from_cache_error,
            CacheWriteError: self._recover_from_cache_error,
            CacheReadError: self._recover_from_cache_error,
            ProcessingQueueFullError: self._recover_from_queue_full,
            QueueError: self._recover_from_queue_error
        }
    
    def handle_error(
        self,
        exception: Exception,
        operation: Optional[str] = None,
        file_path: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """
        Handle an error with comprehensive logging and user-friendly messaging.
        
        Args:
            exception: The exception that occurred
            operation: The operation being performed when the error occurred
            file_path: The file path involved (if applicable)
            user_id: User identifier (if applicable)
            session_id: Session identifier (if applicable)
            metadata: Additional metadata about the error
            
        Returns:
            ErrorContext object with error details and recovery suggestions
        """
        self.error_counter += 1
        error_id = f"ERR_{int(time.time())}_{self.error_counter}"
        
        # Get error mapping
        error_type = type(exception)
        mapping = self.error_mappings.get(error_type, {})
        
        # Extract user message from domain exception if available
        user_message = mapping.get('user_message')
        if isinstance(exception, ImageConverterError):
            user_message = exception.user_message
        elif user_message is None:
            user_message = 'An unexpected error occurred.'
        
        # Create error context
        error_context = ErrorContext(
            error_id=error_id,
            timestamp=time.time(),
            severity=mapping.get('severity', ErrorSeverity.MEDIUM),
            category=mapping.get('category', ErrorCategory.SYSTEM),
            original_exception=exception,
            user_message=user_message,
            technical_message=str(exception),
            file_path=file_path,
            operation=operation,
            user_id=user_id,
            session_id=session_id,
            stack_trace=traceback.format_exc(),
            recovery_suggestions=mapping.get('recovery_suggestions', []),
            metadata=metadata or {}
        )
        
        # Log the error
        self._log_error(error_context)
        
        # Store in history
        self._store_error_history(error_context)
        
        # Attempt recovery if strategy exists
        if error_type in self.recovery_strategies:
            try:
                recovery_result = self.recovery_strategies[error_type](error_context)
                error_context.metadata['recovery_attempted'] = True
                error_context.metadata['recovery_result'] = recovery_result
            except Exception as recovery_error:
                self.logger.warning(f"Recovery strategy failed for {error_id}: {recovery_error}")
                error_context.metadata['recovery_failed'] = str(recovery_error)
        
        return error_context
    
    def _log_error(self, error_context: ErrorContext):
        """Log error with structured information."""
        log_data = {
            'error_id': error_context.error_id,
            'timestamp': error_context.timestamp,
            'severity': error_context.severity.value,
            'category': error_context.category.value,
            'operation': error_context.operation,
            'file_path': error_context.file_path,
            'user_id': error_context.user_id,
            'session_id': error_context.session_id,
            'technical_message': error_context.technical_message,
            'metadata': error_context.metadata
        }
        
        # Log based on severity
        if error_context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"Critical error {error_context.error_id}: {json.dumps(log_data)}")
        elif error_context.severity == ErrorSeverity.HIGH:
            self.logger.error(f"High severity error {error_context.error_id}: {json.dumps(log_data)}")
        elif error_context.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Medium severity error {error_context.error_id}: {json.dumps(log_data)}")
        else:
            self.logger.info(f"Low severity error {error_context.error_id}: {json.dumps(log_data)}")
        
        # Log stack trace for high severity errors
        if error_context.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.error(f"Stack trace for {error_context.error_id}:\n{error_context.stack_trace}")
    
    def _store_error_history(self, error_context: ErrorContext):
        """Store error in history for analysis."""
        self.error_history.append(error_context)
        
        # Maintain history size limit
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    def _recover_from_cache_error(self, error_context: ErrorContext) -> Dict[str, Any]:
        """Recovery strategy for cache errors."""
        self.logger.info(f"Attempting cache error recovery for {error_context.error_id}")
        
        # For cache errors, we can continue without caching
        return {
            'strategy': 'bypass_cache',
            'success': True,
            'message': 'Continuing without cache'
        }
    
    def _recover_from_queue_full(self, error_context: ErrorContext) -> Dict[str, Any]:
        """Recovery strategy for queue full errors."""
        self.logger.info(f"Attempting queue full recovery for {error_context.error_id}")
        
        # Could implement retry logic or queue prioritization
        return {
            'strategy': 'retry_later',
            'success': False,
            'message': 'Queue is full, retry recommended'
        }
    
    def _recover_from_queue_error(self, error_context: ErrorContext) -> Dict[str, Any]:
        """Recovery strategy for general queue errors."""
        self.logger.info(f"Attempting queue error recovery for {error_context.error_id}")
        
        # Could implement retry logic or alternative processing
        return {
            'strategy': 'retry_with_delay',
            'success': False,
            'message': 'Queue error occurred, retry recommended'
        }
    
    def get_user_friendly_message(self, exception: Exception) -> str:
        """Get a user-friendly error message for an exception."""
        if isinstance(exception, ImageConverterError):
            return exception.user_message
        
        error_type = type(exception)
        mapping = self.error_mappings.get(error_type, {})
        return mapping.get('user_message', 'An unexpected error occurred. Please try again.')
    
    def get_recovery_suggestions(self, exception: Exception) -> List[str]:
        """Get recovery suggestions for an exception."""
        error_type = type(exception)
        mapping = self.error_mappings.get(error_type, {})
        return mapping.get('recovery_suggestions', ['Contact support for assistance'])
    
    def handle_with_result(
        self,
        operation: Callable[[], Any],
        operation_name: Optional[str] = None,
        file_path: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Result[Any, ErrorContext]:
        """
        Execute an operation and return a Result with error handling.
        
        Args:
            operation: The operation to execute
            operation_name: Name of the operation for logging
            file_path: File path involved (if applicable)
            user_id: User identifier (if applicable)
            session_id: Session identifier (if applicable)
            metadata: Additional metadata
            
        Returns:
            Result containing either the operation result or error context
        """
        try:
            result = operation()
            return Result.success(result)
        except Exception as e:
            error_context = self.handle_error(
                e, operation_name, file_path, user_id, session_id, metadata
            )
            return Result.failure(error_context)
    
    def wrap_result_error(self, result: Result, operation: Optional[str] = None) -> Result:
        """
        Wrap a Result's error with proper error handling.
        
        Args:
            result: The Result to wrap
            operation: Operation name for context
            
        Returns:
            Result with wrapped error context
        """
        if result.is_success:
            return result
        
        # If the error is already an ErrorContext, return as is
        if isinstance(result.error, ErrorContext):
            return result
        
        # If the error is an Exception, handle it
        if isinstance(result.error, Exception):
            error_context = self.handle_error(result.error, operation)
            return Result.failure(error_context)
        
        # For other error types, create a generic error context
        generic_error = ImageConverterError(
            message=str(result.error),
            error_code=ErrorCode.UNKNOWN_ERROR
        )
        error_context = self.handle_error(generic_error, operation)
        return Result.failure(error_context)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        if not self.error_history:
            return {'total_errors': 0}
        
        # Count by category
        category_counts = {}
        severity_counts = {}
        recent_errors = []
        
        current_time = time.time()
        one_hour_ago = current_time - 3600
        
        for error in self.error_history:
            # Category counts
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Severity counts
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Recent errors (last hour)
            if error.timestamp > one_hour_ago:
                recent_errors.append({
                    'error_id': error.error_id,
                    'timestamp': error.timestamp,
                    'category': category,
                    'severity': severity,
                    'operation': error.operation
                })
        
        return {
            'total_errors': len(self.error_history),
            'category_breakdown': category_counts,
            'severity_breakdown': severity_counts,
            'recent_errors_count': len(recent_errors),
            'recent_errors': recent_errors[-10:],  # Last 10 recent errors
            'error_rate_per_hour': len(recent_errors)
        }
    
    def clear_error_history(self):
        """Clear error history (useful for testing or maintenance)."""
        self.error_history.clear()
        self.error_counter = 0
        self.logger.info("Error history cleared")


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def handle_error(
    exception: Exception,
    operation: Optional[str] = None,
    file_path: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> ErrorContext:
    """Convenience function to handle errors using the global error handler."""
    return get_error_handler().handle_error(
        exception, operation, file_path, user_id, session_id, metadata
    )


def handle_with_result(
    operation: Callable[[], Any],
    operation_name: Optional[str] = None,
    file_path: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Result[Any, ErrorContext]:
    """Convenience function to execute operations with Result pattern error handling."""
    return get_error_handler().handle_with_result(
        operation, operation_name, file_path, user_id, session_id, metadata
    )