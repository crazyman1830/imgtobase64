"""
Security logging module for the image base64 converter.

This module provides structured logging for security events including
threat detection, rate limiting violations, and security scan results.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..models.processing_options import SecurityScanResult


class SecurityLogger:
    """
    Specialized logger for security events.

    Provides structured logging with JSON format for security-related events
    including threat detection, rate limiting, and security scan results.
    """

    def __init__(
        self,
        log_file: str = "security.log",
        log_level: int = logging.INFO,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
    ):
        """
        Initialize the security logger.

        Args:
            log_file: Path to the log file
            log_level: Logging level
            max_file_size: Maximum log file size before rotation
            backup_count: Number of backup files to keep
        """
        self.log_file = log_file

        # Create logger
        self.logger = logging.getLogger(f"security_{id(self)}")
        self.logger.setLevel(log_level)

        # Prevent duplicate handlers
        if not self.logger.handlers:
            # Create file handler with rotation
            from logging.handlers import RotatingFileHandler

            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file, maxBytes=max_file_size, backupCount=backup_count
            )
            file_handler.setLevel(log_level)

            # Create console handler for important events
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)

            # Create JSON formatter
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def _create_base_event(self, event_type: str, **kwargs) -> Dict[str, Any]:
        """
        Create a base security event structure.

        Args:
            event_type: Type of security event
            **kwargs: Additional event data

        Returns:
            dict: Base event structure
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "version": "1.0",
            **kwargs,
        }

    def log_security_scan(
        self,
        file_path: str,
        scan_result: SecurityScanResult,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Log security scan results.

        Args:
            file_path: Path to the scanned file
            scan_result: Security scan results
            ip_address: IP address of the requester
            user_agent: User agent string
        """
        event = self._create_base_event(
            "security_scan",
            file_path=file_path,
            scan_result={
                "is_safe": scan_result.is_safe,
                "threat_level": scan_result.threat_level,
                "warnings": scan_result.warnings,
                "scan_time": scan_result.scan_time,
                "file_size_check": scan_result.file_size_check,
                "mime_type_check": scan_result.mime_type_check,
                "header_check": scan_result.header_check,
                "content_check": scan_result.content_check,
                "scan_details": scan_result.scan_details,
            },
            client_info={"ip_address": ip_address, "user_agent": user_agent},
        )

        # Log at appropriate level based on threat level
        if scan_result.threat_level == "high" or not scan_result.is_safe:
            self.logger.error(f"Security threat detected: {json.dumps(event)}")
        elif scan_result.threat_level == "medium":
            self.logger.warning(f"Security warning: {json.dumps(event)}")
        else:
            self.logger.info(f"Security scan completed: {json.dumps(event)}")

    def log_rate_limit_violation(
        self,
        ip_address: str,
        violation_type: str,
        current_count: int,
        limit: int,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Log rate limit violations.

        Args:
            ip_address: IP address that exceeded the limit
            violation_type: Type of rate limit violated (minute, hour, day, burst)
            current_count: Current request count
            limit: Rate limit threshold
            user_agent: User agent string
        """
        event = self._create_base_event(
            "rate_limit_violation",
            ip_address=ip_address,
            violation_type=violation_type,
            current_count=current_count,
            limit=limit,
            client_info={"user_agent": user_agent},
        )

        self.logger.warning(f"Rate limit violation: {json.dumps(event)}")

    def log_file_upload(
        self,
        file_path: str,
        file_size: int,
        mime_type: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log file upload events.

        Args:
            file_path: Path to the uploaded file
            file_size: Size of the uploaded file
            mime_type: MIME type of the file
            ip_address: IP address of the uploader
            user_agent: User agent string
            success: Whether the upload was successful
            error_message: Error message if upload failed
        """
        event = self._create_base_event(
            "file_upload",
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            success=success,
            error_message=error_message,
            client_info={"ip_address": ip_address, "user_agent": user_agent},
        )

        if success:
            self.logger.info(f"File upload: {json.dumps(event)}")
        else:
            self.logger.error(f"File upload failed: {json.dumps(event)}")

    def log_suspicious_activity(
        self,
        activity_type: str,
        description: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log suspicious activity.

        Args:
            activity_type: Type of suspicious activity
            description: Description of the activity
            ip_address: IP address involved
            user_agent: User agent string
            additional_data: Additional data about the activity
        """
        event = self._create_base_event(
            "suspicious_activity",
            activity_type=activity_type,
            description=description,
            client_info={"ip_address": ip_address, "user_agent": user_agent},
            additional_data=additional_data or {},
        )

        self.logger.warning(f"Suspicious activity: {json.dumps(event)}")

    def log_authentication_event(
        self,
        event_type: str,  # login, logout, failed_login, etc.
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        failure_reason: Optional[str] = None,
    ) -> None:
        """
        Log authentication events.

        Args:
            event_type: Type of authentication event
            username: Username involved (if applicable)
            ip_address: IP address of the user
            user_agent: User agent string
            success: Whether the authentication was successful
            failure_reason: Reason for authentication failure
        """
        event = self._create_base_event(
            "authentication",
            auth_event_type=event_type,
            username=username,
            success=success,
            failure_reason=failure_reason,
            client_info={"ip_address": ip_address, "user_agent": user_agent},
        )

        if success:
            self.logger.info(f"Authentication event: {json.dumps(event)}")
        else:
            self.logger.warning(f"Authentication failure: {json.dumps(event)}")

    def log_system_event(
        self,
        event_type: str,
        description: str,
        severity: str = "info",  # info, warning, error, critical
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log system-level security events.

        Args:
            event_type: Type of system event
            description: Description of the event
            severity: Severity level
            additional_data: Additional event data
        """
        event = self._create_base_event(
            "system_event",
            system_event_type=event_type,
            description=description,
            severity=severity,
            additional_data=additional_data or {},
        )

        # Log at appropriate level
        if severity == "critical":
            self.logger.critical(f"Critical system event: {json.dumps(event)}")
        elif severity == "error":
            self.logger.error(f"System error: {json.dumps(event)}")
        elif severity == "warning":
            self.logger.warning(f"System warning: {json.dumps(event)}")
        else:
            self.logger.info(f"System event: {json.dumps(event)}")

    def get_recent_events(
        self, event_type: Optional[str] = None, hours: int = 24, max_events: int = 1000
    ) -> list[Dict[str, Any]]:
        """
        Get recent security events from the log file.

        Args:
            event_type: Filter by event type (optional)
            hours: Number of hours to look back
            max_events: Maximum number of events to return

        Returns:
            list: Recent security events
        """
        events = []
        cutoff_time = time.time() - (hours * 3600)

        try:
            with open(self.log_file, "r") as f:
                lines = f.readlines()

                # Process lines in reverse order (most recent first)
                for line in reversed(lines[-max_events:]):
                    try:
                        # Parse log line to extract JSON
                        if " - " in line:
                            parts = line.split(" - ", 3)
                            if len(parts) >= 4:
                                json_part = parts[3].strip()
                                event = json.loads(json_part)

                                # Check timestamp
                                event_time = datetime.fromisoformat(
                                    event["timestamp"].replace("Z", "+00:00")
                                ).timestamp()

                                if event_time >= cutoff_time:
                                    # Filter by event type if specified
                                    if (
                                        event_type is None
                                        or event.get("event_type") == event_type
                                    ):
                                        events.append(event)

                                        if len(events) >= max_events:
                                            break
                    except (json.JSONDecodeError, KeyError, ValueError):
                        # Skip malformed log entries
                        continue

        except FileNotFoundError:
            # Log file doesn't exist yet
            pass
        except Exception as e:
            self.logger.error(f"Error reading log file: {e}")

        return events


# Global security logger instance
_global_security_logger: Optional[SecurityLogger] = None


def get_security_logger() -> SecurityLogger:
    """
    Get the global security logger instance.

    Returns:
        SecurityLogger: Global security logger instance
    """
    global _global_security_logger
    if _global_security_logger is None:
        _global_security_logger = SecurityLogger()
    return _global_security_logger


def configure_security_logger(
    log_file: str = "security.log",
    log_level: int = logging.INFO,
    max_file_size: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """
    Configure the global security logger.

    Args:
        log_file: Path to the log file
        log_level: Logging level
        max_file_size: Maximum log file size before rotation
        backup_count: Number of backup files to keep
    """
    global _global_security_logger
    _global_security_logger = SecurityLogger(
        log_file=log_file,
        log_level=log_level,
        max_file_size=max_file_size,
        backup_count=backup_count,
    )
