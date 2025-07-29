"""
Enhanced error handling system for the image converter.

This module provides comprehensive error handling, user-friendly error messages,
structured logging, and error recovery mechanisms.
"""
import logging
import traceback
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import json

from ..models.models import (
    ImageConverterError, ConversionError, UnsupportedFormatError,
    FileNotFoundError, PermissionError, CorruptedFileError,
    ProcessingQueueFullError, SecurityThreatDetectedError,
    CacheError, RateLimitExceededError
)


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
    
    def _setup_error_mappings(self) -> Dict[type, Dict[str, Any]]:
        """Set up error mappings for user-friendly messages."""
        return {
            FileNotFoundError: {
                'category': ErrorCategory.FILE_SYSTEM,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': 'The specified file could not be found. Please check the file path and try again.',
                'recovery_suggestions': [
                    'Verify the file path is correct',
                    'Check if the file exists in the specified location',
                    'Ensure you have permission to access the file'
                ]
            },
            PermissionError: {
                'category': ErrorCategory.FILE_SYSTEM,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': 'Permission denied. You do not have sufficient permissions to access this file.',
                'recovery_suggestions': [
                    'Check file permissions',
                    'Run the application with appropriate privileges',
                    'Contact your system administrator'
                ]
            },
            UnsupportedFormatError: {
                'category': ErrorCategory.VALIDATION,
                'severity': ErrorSeverity.LOW,
                'user_message': 'The file format is not supported. Please use a supported image format.',
                'recovery_suggestions': [
                    'Convert the file to a supported format (PNG, JPEG, WEBP, GIF, BMP)',
                    'Check the file extension matches the actual file format',
                    'Try with a different image file'
                ]
            },
            CorruptedFileError: {
                'category': ErrorCategory.PROCESSING,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': 'The image file appears to be corrupted or invalid.',
                'recovery_suggestions': [
                    'Try with a different image file',
                    'Re-download or re-create the image file',
                    'Check if the file was properly transferred'
                ]
            },
            SecurityThreatDetectedError: {
                'category': ErrorCategory.SECURITY,
                'severity': ErrorSeverity.HIGH,
                'user_message': 'A potential security threat was detected in the file. Processing has been blocked.',
                'recovery_suggestions': [
                    'Scan the file with antivirus software',
                    'Use a different, trusted image file',
                    'Contact support if you believe this is a false positive'
                ]
            },
            ProcessingQueueFullError: {
                'category': ErrorCategory.SYSTEM,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': 'The processing queue is currently full. Please try again later.',
                'recovery_suggestions': [
                    'Wait a few moments and try again',
                    'Process fewer files at once',
                    'Check system resources'
                ]
            },
            CacheError: {
                'category': ErrorCategory.CACHE,
                'severity': ErrorSeverity.LOW,
                'user_message': 'There was an issue with the cache system. Your request will be processed without caching.',
                'recovery_suggestions': [
                    'Clear the application cache',
                    'Check available disk space',
                    'Restart the application if the problem persists'
                ]
            },
            RateLimitExceededError: {
                'category': ErrorCategory.SYSTEM,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': 'Too many requests. Please wait before trying again.',
                'recovery_suggestions': [
                    'Wait a few minutes before retrying',
                    'Reduce the frequency of requests',
                    'Contact support if you need higher limits'
                ]
            },
            ConversionError: {
                'category': ErrorCategory.PROCESSING,
                'severity': ErrorSeverity.MEDIUM,
                'user_message': 'An error occurred during image processing.',
                'recovery_suggestions': [
                    'Try with a different image file',
                    'Check if the image file is valid',
                    'Reduce image size or complexity'
                ]
            }
        }
    
    def _setup_recovery_strategies(self):
        """Set up automatic recovery strategies for different error types."""
        self.recovery_strategies = {
            CacheError: self._recover_from_cache_error,
            ProcessingQueueFullError: self._recover_from_queue_full,
            RateLimitExceededError: self._recover_from_rate_limit
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
        
        # Create error context
        error_context = ErrorContext(
            error_id=error_id,
            timestamp=time.time(),
            severity=mapping.get('severity', ErrorSeverity.MEDIUM),
            category=mapping.get('category', ErrorCategory.SYSTEM),
            original_exception=exception,
            user_message=mapping.get('user_message', 'An unexpected error occurred.'),
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
    
    def _recover_from_rate_limit(self, error_context: ErrorContext) -> Dict[str, Any]:
        """Recovery strategy for rate limit errors."""
        self.logger.info(f"Attempting rate limit recovery for {error_context.error_id}")
        
        # Could implement exponential backoff
        return {
            'strategy': 'exponential_backoff',
            'success': False,
            'message': 'Rate limit exceeded, backoff required'
        }
    
    def get_user_friendly_message(self, exception: Exception) -> str:
        """Get a user-friendly error message for an exception."""
        error_type = type(exception)
        mapping = self.error_mappings.get(error_type, {})
        return mapping.get('user_message', 'An unexpected error occurred. Please try again.')
    
    def get_recovery_suggestions(self, exception: Exception) -> List[str]:
        """Get recovery suggestions for an exception."""
        error_type = type(exception)
        mapping = self.error_mappings.get(error_type, {})
        return mapping.get('recovery_suggestions', ['Contact support for assistance'])
    
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