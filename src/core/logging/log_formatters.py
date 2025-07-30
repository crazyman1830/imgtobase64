"""
Log formatters for the unified logging system.

This module provides various log formatters for different output formats
including JSON, structured text, and console-friendly formats.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..utils.type_utils import TypeUtils


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_extra: bool = True):
        """
        Initialize JSON formatter.
        
        Args:
            include_extra: Whether to include extra fields from log record
        """
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log data
        log_data = {
            'timestamp': record.created,
            'iso_timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if enabled
        if self.include_extra:
            # Get all extra fields from the record
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info'
                }:
                    extra_fields[key] = value
            
            if extra_fields:
                log_data.update(extra_fields)
        
        # Convert to JSON with safe serialization
        return json.dumps(
            TypeUtils.make_json_serializable(log_data),
            ensure_ascii=False,
            separators=(',', ':')
        )


class StructuredFormatter(logging.Formatter):
    """Structured text formatter for human-readable logs."""
    
    def __init__(self, include_context: bool = True):
        """
        Initialize structured formatter.
        
        Args:
            include_context: Whether to include context information
        """
        super().__init__()
        self.include_context = include_context
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured text."""
        # Base format
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        base_msg = f"[{timestamp}] {record.levelname:8} {record.name}: {record.getMessage()}"
        
        # Add location information
        location = f" ({record.filename}:{record.lineno})"
        base_msg += location
        
        # Add context information if available and enabled
        if self.include_context:
            context_parts = []
            
            # Operation context
            if hasattr(record, 'operation'):
                context_parts.append(f"op={record.operation}")
            
            if hasattr(record, 'operation_id'):
                context_parts.append(f"op_id={record.operation_id}")
            
            # File context
            if hasattr(record, 'file_path'):
                context_parts.append(f"file={record.file_path}")
            
            # User context
            if hasattr(record, 'user_id'):
                context_parts.append(f"user={record.user_id}")
            
            if hasattr(record, 'ip_address'):
                context_parts.append(f"ip={record.ip_address}")
            
            # Performance context
            if hasattr(record, 'processing_time'):
                context_parts.append(f"time={record.processing_time:.3f}s")
            
            if hasattr(record, 'memory_usage'):
                context_parts.append(f"mem={record.memory_usage}")
            
            if context_parts:
                base_msg += f" [{', '.join(context_parts)}]"
        
        # Add exception information if present
        if record.exc_info:
            base_msg += "\\n" + self.formatException(record.exc_info)
        
        return base_msg


class ConsoleFormatter(logging.Formatter):
    """Console formatter optimized for terminal output."""
    
    # ANSI color codes
    COLORS = {
        'TRACE': '\\033[90m',      # Dark gray
        'DEBUG': '\\033[36m',      # Cyan
        'INFO': '\\033[32m',       # Green
        'WARNING': '\\033[33m',    # Yellow
        'ERROR': '\\033[31m',      # Red
        'CRITICAL': '\\033[35m',   # Magenta
        'SECURITY': '\\033[91m',   # Bright red
        'PERFORMANCE': '\\033[94m', # Bright blue
        'RESET': '\\033[0m'        # Reset
    }
    
    def __init__(self, use_colors: bool = True, compact: bool = False):
        """
        Initialize console formatter.
        
        Args:
            use_colors: Whether to use ANSI colors
            compact: Whether to use compact format
        """
        super().__init__()
        self.use_colors = use_colors
        self.compact = compact
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console output."""
        # Choose format based on compact setting
        if self.compact:
            timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
            base_msg = f"{timestamp} {record.levelname[0]} {record.getMessage()}"
        else:
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
            logger_name = record.name.split('.')[-1]  # Use only the last part
            base_msg = f"{timestamp} {record.levelname:8} {logger_name}: {record.getMessage()}"
        
        # Add colors if enabled
        if self.use_colors:
            color = self.COLORS.get(record.levelname, '')
            reset = self.COLORS['RESET']
            base_msg = f"{color}{base_msg}{reset}"
        
        # Add important context information
        context_parts = []
        
        if hasattr(record, 'operation') and record.operation:
            context_parts.append(f"[{record.operation}]")
        
        if hasattr(record, 'file_path') and record.file_path:
            # Show only filename, not full path
            from pathlib import Path
            filename = Path(record.file_path).name
            context_parts.append(f"({filename})")
        
        if hasattr(record, 'processing_time') and record.processing_time:
            context_parts.append(f"({record.processing_time:.3f}s)")
        
        if context_parts:
            base_msg += f" {' '.join(context_parts)}"
        
        # Add exception information if present (but keep it concise)
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            # For console, show only the exception type and message
            lines = exc_text.split('\\n')
            if lines:
                base_msg += f"\\n  Exception: {lines[-1]}"
        
        return base_msg


class SecurityFormatter(logging.Formatter):
    """Specialized formatter for security events."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format security log record."""
        # Create security-specific log structure
        security_data = {
            'timestamp': record.created,
            'iso_timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'event_type': 'security',
            'message': record.getMessage()
        }
        
        # Add security-specific fields
        security_fields = [
            'ip_address', 'user_agent', 'user_id', 'session_id',
            'event_type', 'severity', 'description', 'file_path'
        ]
        
        for field in security_fields:
            if hasattr(record, field):
                security_data[field] = getattr(record, field)
        
        # Add metadata if present
        if hasattr(record, 'metadata') and record.metadata:
            security_data['metadata'] = record.metadata
        
        return json.dumps(
            TypeUtils.make_json_serializable(security_data),
            ensure_ascii=False,
            separators=(',', ':')
        )


class PerformanceFormatter(logging.Formatter):
    """Specialized formatter for performance metrics."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format performance log record."""
        # Create performance-specific log structure
        perf_data = {
            'timestamp': record.created,
            'iso_timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'event_type': 'performance',
            'message': record.getMessage()
        }
        
        # Add performance-specific fields
        perf_fields = [
            'operation', 'operation_id', 'processing_time', 'memory_usage',
            'metric_name', 'metric_value', 'metric_unit', 'file_path'
        ]
        
        for field in perf_fields:
            if hasattr(record, field):
                perf_data[field] = getattr(record, field)
        
        # Add metadata if present
        if hasattr(record, 'metadata') and record.metadata:
            perf_data['metadata'] = record.metadata
        
        return json.dumps(
            TypeUtils.make_json_serializable(perf_data),
            ensure_ascii=False,
            separators=(',', ':')
        )