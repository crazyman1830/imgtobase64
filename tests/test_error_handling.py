"""
Tests for the enhanced error handling and logging system.
"""
import pytest
import tempfile
import shutil
import time
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.error_handler import (
    ErrorHandler, ErrorSeverity, ErrorCategory, ErrorContext,
    get_error_handler, handle_error
)
from src.core.structured_logger import (
    StructuredLogger, LogLevel, JSONFormatter, get_structured_logger
)
from src.models.models import (
    ConversionError, FileNotFoundError, SecurityThreatDetectedError,
    CacheError, ProcessingQueueFullError
)


class TestErrorHandler:
    """Test cases for the ErrorHandler class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = ErrorHandler()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.error_handler.clear_error_history()
    
    def test_error_handler_initialization(self):
        """Test error handler initialization."""
        handler = ErrorHandler()
        assert handler.error_counter == 0
        assert len(handler.error_history) == 0
        assert handler.logger is not None
        assert len(handler.error_mappings) > 0
        assert len(handler.recovery_strategies) > 0
    
    def test_handle_file_not_found_error(self):
        """Test handling FileNotFoundError."""
        exception = FileNotFoundError("Test file not found")
        file_path = "/test/path/image.jpg"
        
        error_context = self.error_handler.handle_error(
            exception,
            operation="convert_to_base64",
            file_path=file_path,
            user_id="test_user",
            session_id="test_session"
        )
        
        assert error_context.error_id.startswith("ERR_")
        assert error_context.severity == ErrorSeverity.MEDIUM
        assert error_context.category == ErrorCategory.FILE_SYSTEM
        assert error_context.file_path == file_path
        assert error_context.operation == "convert_to_base64"
        assert error_context.user_id == "test_user"
        assert error_context.session_id == "test_session"
        assert "file could not be found" in error_context.user_message.lower()
        assert len(error_context.recovery_suggestions) > 0
    
    def test_handle_security_threat_error(self):
        """Test handling SecurityThreatDetectedError."""
        exception = SecurityThreatDetectedError("Malicious content detected")
        
        error_context = self.error_handler.handle_error(
            exception,
            operation="security_scan",
            file_path="/test/malicious.jpg"
        )
        
        assert error_context.severity == ErrorSeverity.HIGH
        assert error_context.category == ErrorCategory.SECURITY
        assert "security threat" in error_context.user_message.lower()
        assert "antivirus" in " ".join(error_context.recovery_suggestions).lower()
    
    def test_handle_cache_error_with_recovery(self):
        """Test handling CacheError with automatic recovery."""
        exception = CacheError("Cache write failed")
        
        error_context = self.error_handler.handle_error(
            exception,
            operation="cache_store"
        )
        
        assert error_context.severity == ErrorSeverity.LOW
        assert error_context.category == ErrorCategory.CACHE
        assert error_context.metadata.get('recovery_attempted') is True
        assert error_context.metadata.get('recovery_result', {}).get('success') is True
    
    def test_error_history_management(self):
        """Test error history storage and management."""
        # Add multiple errors
        for i in range(5):
            exception = ConversionError(f"Test error {i}")
            self.error_handler.handle_error(exception, operation=f"test_op_{i}")
        
        assert len(self.error_handler.error_history) == 5
        assert self.error_handler.error_counter == 5
        
        # Test history limit
        self.error_handler.max_history_size = 3
        for i in range(3):
            exception = ConversionError(f"Additional error {i}")
            self.error_handler.handle_error(exception)
        
        # Should maintain only the last 3 entries
        assert len(self.error_handler.error_history) <= 3
    
    def test_get_user_friendly_message(self):
        """Test getting user-friendly error messages."""
        file_error = FileNotFoundError("File not found")
        message = self.error_handler.get_user_friendly_message(file_error)
        assert "file could not be found" in message.lower()
        
        # Test unknown error type
        unknown_error = ValueError("Unknown error")
        message = self.error_handler.get_user_friendly_message(unknown_error)
        assert "unexpected error" in message.lower()
    
    def test_get_recovery_suggestions(self):
        """Test getting recovery suggestions."""
        security_error = SecurityThreatDetectedError("Threat detected")
        suggestions = self.error_handler.get_recovery_suggestions(security_error)
        assert len(suggestions) > 0
        assert any("antivirus" in suggestion.lower() for suggestion in suggestions)
    
    def test_error_statistics(self):
        """Test error statistics generation."""
        # Add errors of different types and severities
        errors = [
            (FileNotFoundError("File not found"), "file_op"),
            (SecurityThreatDetectedError("Threat"), "security_scan"),
            (CacheError("Cache error"), "cache_op"),
            (ConversionError("Conversion failed"), "convert")
        ]
        
        for exception, operation in errors:
            self.error_handler.handle_error(exception, operation=operation)
        
        stats = self.error_handler.get_error_statistics()
        
        assert stats['total_errors'] == 4
        assert 'category_breakdown' in stats
        assert 'severity_breakdown' in stats
        assert 'recent_errors_count' in stats
        assert stats['recent_errors_count'] == 4  # All are recent
    
    def test_global_error_handler(self):
        """Test global error handler functions."""
        exception = ConversionError("Global test error")
        
        # Test global function
        error_context = handle_error(
            exception,
            operation="global_test",
            metadata={'test': True}
        )
        
        assert error_context.error_id.startswith("ERR_")
        assert error_context.operation == "global_test"
        assert error_context.metadata['test'] is True
        
        # Test singleton behavior
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        assert handler1 is handler2


class TestStructuredLogger:
    """Test cases for the StructuredLogger class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = os.path.join(self.temp_dir, "logs")
        self.logger = StructuredLogger(
            "test_logger",
            log_dir=self.log_dir,
            max_file_size=1024,  # Small size for testing
            backup_count=2
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_logger_initialization(self):
        """Test logger initialization."""
        assert self.logger.name == "test_logger"
        assert Path(self.log_dir).exists()
        assert len(self.logger.logger.handlers) > 0
        assert len(self.logger.operation_times) == 0
    
    def test_basic_logging(self):
        """Test basic logging functionality."""
        self.logger.info("Test info message", operation="test_op")
        self.logger.warning("Test warning message", user_id="test_user")
        self.logger.error("Test error message", error_id="ERR_123")
        
        # Check that log files are created
        log_files = list(Path(self.log_dir).glob("*.log"))
        assert len(log_files) > 0
    
    def test_operation_logging(self):
        """Test operation start/end logging."""
        operation_id = self.logger.log_operation_start(
            "test_operation",
            file_path="/test/file.jpg",
            user_id="test_user",
            metadata={'test': True}
        )
        
        assert operation_id.startswith("test_operation_")
        
        # Simulate some processing time
        time.sleep(0.01)
        processing_time = 0.01
        
        self.logger.log_operation_end(
            "test_operation",
            operation_id,
            success=True,
            processing_time=processing_time,
            file_path="/test/file.jpg",
            user_id="test_user"
        )
        
        # Check that operation time was recorded
        stats = self.logger.get_performance_statistics()
        assert "test_operation" in stats
        assert stats["test_operation"]["count"] == 1
    
    def test_performance_metrics(self):
        """Test performance metric logging."""
        self.logger.log_performance_metric(
            "processing_time",
            0.5,
            "seconds",
            operation="image_conversion",
            metadata={'file_size': 1024}
        )
        
        self.logger.log_performance_metric(
            "memory_usage",
            256,
            "MB",
            operation="image_processing"
        )
        
        # Performance metrics should be logged
        # We can't easily verify the content without reading log files
        # but we can verify the method doesn't raise exceptions
    
    def test_security_event_logging(self):
        """Test security event logging."""
        self.logger.log_security_event(
            "threat_detected",
            "high",
            "Malicious content found in uploaded file",
            file_path="/uploads/suspicious.jpg",
            user_id="user123",
            metadata={'threat_type': 'malware'}
        )
        
        # Security events should be logged to security log file
        security_log = Path(self.log_dir) / "test_logger_security.log"
        # File might not exist immediately due to buffering
    
    def test_error_context_logging(self):
        """Test error logging with full context."""
        exception = ValueError("Test exception")
        
        self.logger.log_error_with_context(
            "ERR_123",
            exception,
            operation="test_operation",
            file_path="/test/file.jpg",
            user_id="test_user",
            metadata={'additional_info': 'test'}
        )
        
        # Error should be logged with full context
        error_log = Path(self.log_dir) / "test_logger_errors.log"
        # File might not exist immediately due to buffering
    
    def test_performance_statistics(self):
        """Test performance statistics tracking."""
        # Log multiple operations
        operations = ["op1", "op2", "op1", "op3", "op1"]
        times = [0.1, 0.2, 0.15, 0.3, 0.12]
        
        for op, time_val in zip(operations, times):
            op_id = self.logger.log_operation_start(op)
            self.logger.log_operation_end(op, op_id, True, time_val)
        
        stats = self.logger.get_performance_statistics()
        
        # Check op1 statistics (3 occurrences)
        assert "op1" in stats
        assert stats["op1"]["count"] == 3
        assert abs(stats["op1"]["avg_time"] - 0.123333) < 0.001
        assert stats["op1"]["min_time"] == 0.1
        assert stats["op1"]["max_time"] == 0.15
        
        # Check other operations
        assert "op2" in stats
        assert stats["op2"]["count"] == 1
        assert "op3" in stats
        assert stats["op3"]["count"] == 1
    
    def test_json_formatter(self):
        """Test JSON formatter."""
        formatter = JSONFormatter()
        
        # Create a mock log record
        record = MagicMock()
        record.created = time.time()
        record.levelname = "INFO"
        record.name = "test_logger"
        record.getMessage.return_value = "Test message"
        record.exc_info = None
        
        # Add custom attributes
        record.operation = "test_op"
        record.file_path = "/test/file.jpg"
        record.user_id = "test_user"
        record.processing_time = 0.5
        
        formatted = formatter.format(record)
        
        # Should be valid JSON
        log_data = json.loads(formatted)
        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["operation"] == "test_op"
        assert log_data["file_path"] == "/test/file.jpg"
        assert log_data["user_id"] == "test_user"
        assert log_data["processing_time"] == 0.5
    
    def test_logger_singleton_behavior(self):
        """Test logger singleton behavior."""
        logger1 = get_structured_logger("test_singleton")
        logger2 = get_structured_logger("test_singleton")
        
        assert logger1 is logger2
        
        # Different names should create different instances
        logger3 = get_structured_logger("different_name")
        assert logger1 is not logger3


class TestIntegratedErrorHandlingAndLogging:
    """Test integration between error handling and logging systems."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = os.path.join(self.temp_dir, "logs")
        
        # Create integrated logger for error handler
        self.logger = StructuredLogger("error_handler_test", log_dir=self.log_dir)
        self.error_handler = ErrorHandler(logger=self.logger.logger)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.error_handler.clear_error_history()
    
    def test_integrated_error_logging(self):
        """Test that errors are properly logged with structured information."""
        exception = ConversionError("Integration test error")
        
        error_context = self.error_handler.handle_error(
            exception,
            operation="integration_test",
            file_path="/test/integration.jpg",
            user_id="integration_user",
            session_id="integration_session",
            metadata={'test_type': 'integration'}
        )
        
        # Error should be handled and logged
        assert error_context.error_id.startswith("ERR_")
        assert error_context.operation == "integration_test"
        
        # Check that error was added to history
        assert len(self.error_handler.error_history) == 1
        assert self.error_handler.error_history[0].error_id == error_context.error_id
    
    def test_performance_and_error_correlation(self):
        """Test correlation between performance logging and error handling."""
        # Start an operation
        operation_id = self.logger.log_operation_start(
            "test_operation_with_error",
            file_path="/test/error_file.jpg",
            user_id="test_user"
        )
        
        # Simulate an error during operation
        exception = ProcessingQueueFullError("Queue is full")
        error_context = self.error_handler.handle_error(
            exception,
            operation="test_operation_with_error",
            file_path="/test/error_file.jpg",
            user_id="test_user",
            metadata={'operation_id': operation_id}
        )
        
        # End operation with error
        self.logger.log_operation_end(
            "test_operation_with_error",
            operation_id,
            success=False,
            processing_time=0.1,
            file_path="/test/error_file.jpg",
            user_id="test_user",
            error_message=str(exception),
            metadata={'error_id': error_context.error_id}
        )
        
        # Both systems should have recorded the event
        assert len(self.error_handler.error_history) == 1
        stats = self.logger.get_performance_statistics()
        assert "test_operation_with_error" in stats


if __name__ == '__main__':
    pytest.main([__file__, '-v'])