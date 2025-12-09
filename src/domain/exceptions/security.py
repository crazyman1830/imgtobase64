"""
Security exception classes.

This module defines exceptions related to security threats and validation.
"""

from typing import Any, Dict, List, Optional

from .base import ErrorCode, ImageConverterError


class SecurityError(ImageConverterError):
    """Base class for security-related errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[ErrorCode] = None,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
    ):
        super().__init__(
            message, error_code or ErrorCode.SECURITY_ERROR, context, user_message
        )


class SecurityThreatDetectedError(SecurityError):
    """Exception raised when a security threat is detected."""

    def __init__(
        self,
        file_path: str,
        threat_type: str,
        threat_details: Optional[str] = None,
        severity: str = "HIGH",
    ):
        message = f"Security threat detected in file '{file_path}': {threat_type}"

        if threat_details:
            message += f" - {threat_details}"

        user_message = "보안 위협이 감지되어 파일을 처리할 수 없습니다."

        context = {
            "file_path": file_path,
            "threat_type": threat_type,
            "threat_details": threat_details,
            "severity": severity,
        }

        super().__init__(
            message=message,
            error_code=ErrorCode.SECURITY_THREAT_DETECTED,
            context=context,
            user_message=user_message,
        )


class MaliciousContentError(SecurityError):
    """Exception raised when malicious content is detected."""

    def __init__(
        self,
        file_path: str,
        malware_signatures: Optional[List[str]] = None,
        scan_engine: Optional[str] = None,
    ):
        message = f"Malicious content detected in file: {file_path}"

        if malware_signatures:
            message += f" (signatures: {', '.join(malware_signatures)})"

        if scan_engine:
            message += f" (detected by: {scan_engine})"

        user_message = "악성 콘텐츠가 감지되어 파일을 처리할 수 없습니다."

        context = {
            "file_path": file_path,
            "malware_signatures": malware_signatures or [],
            "scan_engine": scan_engine,
        }

        super().__init__(
            message=message,
            error_code=ErrorCode.MALICIOUS_CONTENT,
            context=context,
            user_message=user_message,
        )


class SuspiciousActivityError(SecurityError):
    """Exception raised when suspicious activity is detected."""

    def __init__(
        self,
        activity_type: str,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[str] = None,
    ):
        message = f"Suspicious activity detected: {activity_type}"

        if source_ip:
            message += f" from IP: {source_ip}"

        if details:
            message += f" - {details}"

        user_message = "의심스러운 활동이 감지되었습니다. 잠시 후 다시 시도해주세요."

        context = {
            "activity_type": activity_type,
            "source_ip": source_ip,
            "user_agent": user_agent,
            "details": details,
        }

        super().__init__(
            message=message,
            error_code=ErrorCode.SUSPICIOUS_ACTIVITY,
            context=context,
            user_message=user_message,
        )
