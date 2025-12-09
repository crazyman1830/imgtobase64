"""
Specialized log handlers for the unified logging system.

This module provides custom log handlers for different types of log events
including security events, performance metrics, and error handling.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Any, Dict, Optional

from .log_formatters import JSONFormatter, PerformanceFormatter, SecurityFormatter


class RotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Enhanced rotating file handler with better error handling."""

    def __init__(
        self,
        filename: str,
        mode: str = "a",
        maxBytes: int = 0,
        backupCount: int = 0,
        encoding: Optional[str] = "utf-8",
        delay: bool = False,
    ):
        """
        Initialize rotating file handler.

        Args:
            filename: Log file path
            mode: File open mode
            maxBytes: Maximum file size before rotation
            backupCount: Number of backup files to keep
            encoding: File encoding
            delay: Whether to delay file opening
        """
        # Ensure directory exists
        log_path = Path(filename)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)

    def emit(self, record: logging.LogRecord):
        """Emit a log record with enhanced error handling."""
        try:
            super().emit(record)
        except Exception as e:
            # If logging fails, try to write to stderr
            try:
                import sys

                sys.stderr.write(f"Logging error: {e}\\n")
                sys.stderr.write(f"Failed to log: {record.getMessage()}\\n")
            except:
                # If even stderr fails, there's not much we can do
                pass


class SecurityLogHandler(RotatingFileHandler):
    """Specialized handler for security events."""

    def __init__(
        self,
        filename: str,
        maxBytes: int = 10 * 1024 * 1024,  # 10MB
        backupCount: int = 10,
        encoding: str = "utf-8",
    ):
        """
        Initialize security log handler.

        Args:
            filename: Security log file path
            maxBytes: Maximum file size before rotation
            backupCount: Number of backup files to keep
            encoding: File encoding
        """
        super().__init__(filename, "a", maxBytes, backupCount, encoding)
        self.setFormatter(SecurityFormatter())

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter to only allow security-related log records."""
        # Allow records with SECURITY level or security-related metadata
        if record.levelno == 60:  # SECURITY level
            return True

        # Also allow records that have security-related attributes
        security_indicators = [
            "ip_address",
            "user_agent",
            "security_event",
            "threat_level",
            "scan_result",
            "rate_limit",
            "suspicious_activity",
        ]

        return any(hasattr(record, indicator) for indicator in security_indicators)


class PerformanceLogHandler(RotatingFileHandler):
    """Specialized handler for performance metrics."""

    def __init__(
        self,
        filename: str,
        maxBytes: int = 10 * 1024 * 1024,  # 10MB
        backupCount: int = 5,
        encoding: str = "utf-8",
    ):
        """
        Initialize performance log handler.

        Args:
            filename: Performance log file path
            maxBytes: Maximum file size before rotation
            backupCount: Number of backup files to keep
            encoding: File encoding
        """
        super().__init__(filename, "a", maxBytes, backupCount, encoding)
        self.setFormatter(PerformanceFormatter())

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter to only allow performance-related log records."""
        # Allow records with PERFORMANCE level or performance-related metadata
        if record.levelno == 25:  # PERFORMANCE level
            return True

        # Also allow records that have performance-related attributes
        performance_indicators = [
            "processing_time",
            "memory_usage",
            "metric_name",
            "metric_value",
            "operation_time",
            "performance_metric",
        ]

        return any(hasattr(record, indicator) for indicator in performance_indicators)


class ErrorLogHandler(RotatingFileHandler):
    """Specialized handler for error and exception logging."""

    def __init__(
        self,
        filename: str,
        maxBytes: int = 10 * 1024 * 1024,  # 10MB
        backupCount: int = 10,
        encoding: str = "utf-8",
    ):
        """
        Initialize error log handler.

        Args:
            filename: Error log file path
            maxBytes: Maximum file size before rotation
            backupCount: Number of backup files to keep
            encoding: File encoding
        """
        super().__init__(filename, "a", maxBytes, backupCount, encoding)
        self.setFormatter(JSONFormatter(include_extra=True))

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter to only allow error-level and above log records."""
        return record.levelno >= logging.ERROR


class DebugLogHandler(RotatingFileHandler):
    """Specialized handler for debug information."""

    def __init__(
        self,
        filename: str,
        maxBytes: int = 50 * 1024 * 1024,  # 50MB (debug logs can be large)
        backupCount: int = 3,
        encoding: str = "utf-8",
    ):
        """
        Initialize debug log handler.

        Args:
            filename: Debug log file path
            maxBytes: Maximum file size before rotation
            backupCount: Number of backup files to keep
            encoding: File encoding
        """
        super().__init__(filename, "a", maxBytes, backupCount, encoding)
        self.setFormatter(JSONFormatter(include_extra=True))

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter to only allow debug and trace level records."""
        return record.levelno <= logging.DEBUG


class AsyncLogHandler(logging.Handler):
    """Asynchronous log handler for high-performance logging."""

    def __init__(self, target_handler: logging.Handler, queue_size: int = 1000):
        """
        Initialize async log handler.

        Args:
            target_handler: The actual handler to write logs
            queue_size: Maximum queue size for pending log records
        """
        super().__init__()
        self.target_handler = target_handler
        self.queue_size = queue_size

        # Set up queue and worker thread
        import queue
        import threading

        self.log_queue = queue.Queue(maxsize=queue_size)
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.shutdown_event = threading.Event()
        self.worker_thread.start()

    def emit(self, record: logging.LogRecord):
        """Emit a log record asynchronously."""
        try:
            # Try to put the record in the queue without blocking
            self.log_queue.put_nowait(record)
        except:
            # If queue is full, drop the record (or handle as needed)
            pass

    def _worker(self):
        """Worker thread that processes log records."""
        while not self.shutdown_event.is_set():
            try:
                # Get record from queue with timeout
                record = self.log_queue.get(timeout=1.0)

                # Process the record with the target handler
                self.target_handler.emit(record)

                # Mark task as done
                self.log_queue.task_done()

            except:
                # Timeout or other error, continue
                continue

    def close(self):
        """Close the handler and shutdown the worker thread."""
        # Signal shutdown
        self.shutdown_event.set()

        # Wait for worker thread to finish
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)

        # Close target handler
        self.target_handler.close()

        super().close()


class FilteredHandler(logging.Handler):
    """Handler that applies custom filtering logic."""

    def __init__(
        self,
        target_handler: logging.Handler,
        filter_func: Optional[callable] = None,
        include_patterns: Optional[list] = None,
        exclude_patterns: Optional[list] = None,
    ):
        """
        Initialize filtered handler.

        Args:
            target_handler: The actual handler to write logs
            filter_func: Custom filter function
            include_patterns: Patterns to include (regex)
            exclude_patterns: Patterns to exclude (regex)
        """
        super().__init__()
        self.target_handler = target_handler
        self.filter_func = filter_func
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []

        # Compile regex patterns
        import re

        self.include_regex = [re.compile(pattern) for pattern in self.include_patterns]
        self.exclude_regex = [re.compile(pattern) for pattern in self.exclude_patterns]

    def emit(self, record: logging.LogRecord):
        """Emit a log record after applying filters."""
        # Apply custom filter function
        if self.filter_func and not self.filter_func(record):
            return

        # Apply include patterns
        if self.include_regex:
            message = record.getMessage()
            if not any(pattern.search(message) for pattern in self.include_regex):
                return

        # Apply exclude patterns
        if self.exclude_regex:
            message = record.getMessage()
            if any(pattern.search(message) for pattern in self.exclude_regex):
                return

        # If all filters pass, emit the record
        self.target_handler.emit(record)

    def close(self):
        """Close the handler."""
        self.target_handler.close()
        super().close()


class MetricsHandler(logging.Handler):
    """Handler that collects metrics from log records."""

    def __init__(self):
        """Initialize metrics handler."""
        super().__init__()
        self.metrics: Dict[str, Any] = {
            "total_logs": 0,
            "logs_by_level": {},
            "logs_by_logger": {},
            "error_count": 0,
            "warning_count": 0,
            "security_events": 0,
            "performance_metrics": 0,
        }
        self.lock = logging._lock  # Use logging module's lock

    def emit(self, record: logging.LogRecord):
        """Process log record and update metrics."""
        with self.lock:
            # Update total count
            self.metrics["total_logs"] += 1

            # Update by level
            level = record.levelname
            self.metrics["logs_by_level"][level] = (
                self.metrics["logs_by_level"].get(level, 0) + 1
            )

            # Update by logger
            logger = record.name
            self.metrics["logs_by_logger"][logger] = (
                self.metrics["logs_by_logger"].get(logger, 0) + 1
            )

            # Update specific counters
            if record.levelno >= logging.ERROR:
                self.metrics["error_count"] += 1
            elif record.levelno >= logging.WARNING:
                self.metrics["warning_count"] += 1

            if record.levelno == 60:  # SECURITY level
                self.metrics["security_events"] += 1

            if record.levelno == 25:  # PERFORMANCE level
                self.metrics["performance_metrics"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        with self.lock:
            return self.metrics.copy()

    def reset_metrics(self):
        """Reset all metrics."""
        with self.lock:
            self.metrics = {
                "total_logs": 0,
                "logs_by_level": {},
                "logs_by_logger": {},
                "error_count": 0,
                "warning_count": 0,
                "security_events": 0,
                "performance_metrics": 0,
            }
