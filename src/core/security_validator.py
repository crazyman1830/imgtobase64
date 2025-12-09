"""
Security validation module for the image base64 converter.

This module provides security validation functionality including file size limits,
MIME type validation, file header verification, and basic threat detection.
"""

import hashlib
import mimetypes
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Set

# Try to import magic, but handle gracefully if not available
try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None

from ..models.models import SecurityThreatDetectedError
from ..models.processing_options import SecurityScanResult
from .security_logger import get_security_logger


class SecurityValidator:
    """
    Security validator for image files.

    Provides comprehensive security validation including file size limits,
    MIME type validation, file header verification, and basic threat detection.
    """

    # Common image file signatures (magic numbers)
    IMAGE_SIGNATURES = {
        b"\xff\xd8\xff": "image/jpeg",
        b"\x89PNG\r\n\x1a\n": "image/png",
        b"GIF87a": "image/gif",
        b"GIF89a": "image/gif",
        b"RIFF": "image/webp",  # WebP files start with RIFF
        b"BM": "image/bmp",
        b"\x00\x00\x01\x00": "image/x-icon",  # ICO format
    }

    # Allowed MIME types for image files
    DEFAULT_ALLOWED_MIME_TYPES = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
        "image/tiff",
        "image/x-icon",
    }

    # Suspicious patterns that might indicate malicious content
    SUSPICIOUS_PATTERNS = [
        b"<script",
        b"javascript:",
        b"vbscript:",
        b"onload=",
        b"onerror=",
        b"<?php",
        b"<%",
        b"eval(",
        b"exec(",
        b"system(",
        b"shell_exec(",
    ]

    # Advanced malicious patterns for deeper scanning
    ADVANCED_THREAT_PATTERNS = [
        # Embedded executables
        b"MZ",  # DOS/Windows executable header
        b"\x7fELF",  # Linux executable header
        b"\xca\xfe\xba\xbe",  # Java class file
        b"PK\x03\x04",  # ZIP file (could contain executables)
        # Suspicious URLs and protocols
        b"http://",
        b"https://",
        b"ftp://",
        b"file://",
        # Potential code injection
        b"document.write",
        b"innerHTML",
        b"outerHTML",
        b"document.cookie",
        b"window.location",
        # Database injection patterns
        b"union select",
        b"drop table",
        b"insert into",
        b"delete from",
        # Command injection patterns
        b"cmd.exe",
        b"/bin/sh",
        b"/bin/bash",
        b"powershell",
    ]

    # File size thresholds for different threat levels
    SIZE_THRESHOLDS = {
        "suspicious": 50 * 1024 * 1024,  # 50MB
        "very_large": 100 * 1024 * 1024,  # 100MB
    }

    def __init__(
        self,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB default
        allowed_mime_types: Optional[Set[str]] = None,
        enable_content_scan: bool = True,
        max_header_scan_size: int = 1024,  # First 1KB for header check
    ):
        """
        Initialize the security validator.

        Args:
            max_file_size: Maximum allowed file size in bytes
            allowed_mime_types: Set of allowed MIME types (uses default if None)
            enable_content_scan: Whether to perform content scanning for threats
            max_header_scan_size: Maximum bytes to scan for file header validation
        """
        self.max_file_size = max_file_size
        self.allowed_mime_types = (
            allowed_mime_types or self.DEFAULT_ALLOWED_MIME_TYPES.copy()
        )
        self.enable_content_scan = enable_content_scan
        self.max_header_scan_size = max_header_scan_size

        # Initialize python-magic for MIME type detection
        if MAGIC_AVAILABLE:
            try:
                self.mime_detector = magic.Magic(mime=True)
            except Exception:
                # Fallback to mimetypes module if python-magic fails to initialize
                self.mime_detector = None
        else:
            # python-magic not available, use mimetypes module
            self.mime_detector = None

        # Initialize security logger
        self.security_logger = get_security_logger()

    def validate_file_size(self, file_path: str) -> bool:
        """
        Validate that the file size is within allowed limits.

        Args:
            file_path: Path to the file to validate

        Returns:
            bool: True if file size is valid, False otherwise

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        try:
            file_size = os.path.getsize(file_path)
            return file_size <= self.max_file_size
        except OSError:
            raise FileNotFoundError(f"File not found: {file_path}")

    def validate_mime_type(self, file_path: str) -> tuple[bool, str]:
        """
        Validate the MIME type of the file.

        Checks both the file extension and the actual file content to detect
        MIME type mismatches that could indicate malicious files.

        Args:
            file_path: Path to the file to validate

        Returns:
            tuple: (is_valid, detected_mime_type)

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get MIME type from file extension
        extension_mime, _ = mimetypes.guess_type(file_path)

        # Get MIME type from file content
        if self.mime_detector:
            try:
                content_mime = self.mime_detector.from_file(file_path)
            except Exception:
                # Fallback to extension-based detection
                content_mime = extension_mime
        else:
            content_mime = extension_mime

        # Check if detected MIME type is allowed
        is_valid = content_mime in self.allowed_mime_types if content_mime else False

        return is_valid, content_mime or "unknown"

    def validate_file_header(self, file_path: str) -> tuple[bool, str]:
        """
        Validate the file header (magic numbers) to ensure file integrity.

        Args:
            file_path: Path to the file to validate

        Returns:
            tuple: (is_valid, detected_format)

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, "rb") as f:
                header = f.read(self.max_header_scan_size)

            # Check against known image signatures
            for signature, format_type in self.IMAGE_SIGNATURES.items():
                if header.startswith(signature):
                    return True, format_type

                # Special case for WebP files
                if (
                    signature == b"RIFF"
                    and header.startswith(b"RIFF")
                    and b"WEBP" in header[:12]
                ):
                    return True, "image/webp"

            return False, "unknown"

        except IOError as e:
            raise FileNotFoundError(f"Cannot read file header: {file_path} - {str(e)}")

    def scan_for_threats(self, file_path: str) -> SecurityScanResult:
        """
        Perform a comprehensive security scan of the file.

        Args:
            file_path: Path to the file to scan

        Returns:
            SecurityScanResult: Detailed scan results

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        start_time = time.time()
        scan_result = SecurityScanResult(
            is_safe=True,
            threat_level="low",
            warnings=[],
            scan_time=0.0,
            file_size_check=True,
            mime_type_check=True,
            header_check=True,
            content_check=True,
            scan_details={},
        )

        try:
            # 1. File size validation
            try:
                file_size_valid = self.validate_file_size(file_path)
                scan_result.file_size_check = file_size_valid
                scan_result.scan_details["file_size"] = os.path.getsize(file_path)

                if not file_size_valid:
                    scan_result.is_safe = False
                    scan_result.threat_level = "medium"
                    scan_result.add_warning(
                        f"File size exceeds limit of {self.max_file_size} bytes"
                    )
            except Exception as e:
                scan_result.file_size_check = False
                scan_result.add_warning(f"File size check failed: {str(e)}")

            # 2. MIME type validation
            try:
                mime_valid, detected_mime = self.validate_mime_type(file_path)
                scan_result.mime_type_check = mime_valid
                scan_result.scan_details["detected_mime_type"] = detected_mime

                if not mime_valid:
                    scan_result.is_safe = False
                    scan_result.threat_level = "high"
                    scan_result.add_warning(
                        f"Invalid or disallowed MIME type: {detected_mime}"
                    )
            except Exception as e:
                scan_result.mime_type_check = False
                scan_result.add_warning(f"MIME type check failed: {str(e)}")

            # 3. File header validation
            try:
                header_valid, detected_format = self.validate_file_header(file_path)
                scan_result.header_check = header_valid
                scan_result.scan_details["detected_format"] = detected_format

                if not header_valid:
                    scan_result.is_safe = False
                    scan_result.threat_level = "high"
                    scan_result.add_warning(
                        f"Invalid file header or unknown format: {detected_format}"
                    )
            except Exception as e:
                scan_result.header_check = False
                scan_result.add_warning(f"File header check failed: {str(e)}")

            # 4. Content scanning for suspicious patterns
            if self.enable_content_scan:
                try:
                    content_safe, content_threats = self._scan_file_content(file_path)
                    scan_result.content_check = content_safe
                    scan_result.scan_details["content_threats"] = content_threats

                    if not content_safe:
                        scan_result.is_safe = False
                        scan_result.threat_level = "high"
                        for threat in content_threats:
                            scan_result.add_warning(f"Content threat: {threat}")
                except Exception as e:
                    scan_result.content_check = False
                    scan_result.add_warning(f"Content scan failed: {str(e)}")

            # 5. Advanced security checks
            try:
                advanced_safe, advanced_warnings = (
                    self._perform_advanced_security_checks(file_path)
                )
                scan_result.scan_details["advanced_checks"] = {
                    "safe": advanced_safe,
                    "warnings": advanced_warnings,
                }

                if not advanced_safe:
                    scan_result.is_safe = False
                    if scan_result.threat_level == "low":
                        scan_result.threat_level = "medium"

                    for warning in advanced_warnings:
                        scan_result.add_warning(f"Advanced check: {warning}")

            except Exception as e:
                scan_result.add_warning(f"Advanced security checks failed: {str(e)}")

            # Calculate final threat level
            if not scan_result.is_safe:
                failed_checks = sum(
                    [
                        not scan_result.file_size_check,
                        not scan_result.mime_type_check,
                        not scan_result.header_check,
                        not scan_result.content_check,
                    ]
                )

                if failed_checks >= 3:
                    scan_result.threat_level = "high"
                elif failed_checks >= 2:
                    scan_result.threat_level = "medium"
                else:
                    scan_result.threat_level = "low"

        except Exception as e:
            scan_result.is_safe = False
            scan_result.threat_level = "high"
            scan_result.add_warning(f"Security scan failed: {str(e)}")

        finally:
            scan_result.scan_time = time.time() - start_time

        return scan_result

    def _scan_file_content(
        self, file_path: str, chunk_size: int = 8192
    ) -> tuple[bool, list[str]]:
        """
        Scan file content for suspicious patterns.

        Args:
            file_path: Path to the file to scan
            chunk_size: Size of chunks to read for scanning

        Returns:
            tuple: (is_safe, detected_threats)
        """
        detected_threats = []

        try:
            file_size = os.path.getsize(file_path)

            # Check file size thresholds
            if file_size > self.SIZE_THRESHOLDS["very_large"]:
                detected_threats.append(f"File extremely large: {file_size} bytes")
            elif file_size > self.SIZE_THRESHOLDS["suspicious"]:
                detected_threats.append(f"File suspiciously large: {file_size} bytes")

            with open(file_path, "rb") as f:
                bytes_read = 0
                max_scan_size = min(file_size, 10 * 1024 * 1024)  # Limit scan to 10MB

                # Read file in chunks to handle large files efficiently
                while bytes_read < max_scan_size:
                    remaining = max_scan_size - bytes_read
                    chunk_size_actual = min(chunk_size, remaining)
                    chunk = f.read(chunk_size_actual)

                    if not chunk:
                        break

                    bytes_read += len(chunk)

                    # Convert to lowercase for case-insensitive matching
                    chunk_lower = chunk.lower()

                    # Check for basic suspicious patterns
                    for pattern in self.SUSPICIOUS_PATTERNS:
                        if pattern in chunk_lower:
                            detected_threats.append(
                                f"Suspicious pattern detected: {pattern.decode('utf-8', errors='ignore')}"
                            )

                    # Check for advanced threat patterns
                    for pattern in self.ADVANCED_THREAT_PATTERNS:
                        if pattern in chunk_lower:
                            detected_threats.append(
                                f"Advanced threat pattern detected: {pattern.decode('utf-8', errors='ignore')}"
                            )

            return len(detected_threats) == 0, detected_threats

        except IOError as e:
            # If we can't read the file, consider it suspicious
            detected_threats.append(f"File read error: {str(e)}")
            return False, detected_threats

    def _perform_advanced_security_checks(
        self, file_path: str
    ) -> tuple[bool, list[str]]:
        """
        Perform advanced security checks beyond basic validation.

        Args:
            file_path: Path to the file to check

        Returns:
            tuple: (is_safe, warnings)
        """
        warnings = []
        is_safe = True

        try:
            # Check file permissions (if accessible)
            file_stat = os.stat(file_path)

            # Check for unusual file permissions
            if hasattr(file_stat, "st_mode"):
                # On Unix-like systems, check for executable bits
                if file_stat.st_mode & 0o111:  # Any execute permission
                    warnings.append("File has executable permissions")
                    is_safe = False

            # Check file creation/modification time
            current_time = time.time()
            file_mtime = file_stat.st_mtime

            # Flag files modified very recently (within last minute)
            if current_time - file_mtime < 60:
                warnings.append("File was modified very recently")

            # Check for hidden file attributes (Windows)
            if os.name == "nt":
                import stat

                if file_stat.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN:
                    warnings.append("File has hidden attribute")

            # Check file extension vs content mismatch
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
                # For image files, check if they actually contain image data
                try:
                    with open(file_path, "rb") as f:
                        header = f.read(32)

                    # Check if file starts with known image signatures
                    has_image_signature = any(
                        header.startswith(sig) for sig in self.IMAGE_SIGNATURES.keys()
                    )

                    if not has_image_signature:
                        warnings.append(
                            f"File extension {file_ext} doesn't match content"
                        )
                        is_safe = False

                except IOError:
                    warnings.append("Cannot verify file content matches extension")

        except (OSError, AttributeError) as e:
            warnings.append(f"Advanced security check failed: {str(e)}")

        return is_safe, warnings

    def validate_file(
        self,
        file_path: str,
        raise_on_threat: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> SecurityScanResult:
        """
        Perform complete file validation.

        Args:
            file_path: Path to the file to validate
            raise_on_threat: Whether to raise exception if threat is detected
            ip_address: IP address of the requester (for logging)
            user_agent: User agent string (for logging)

        Returns:
            SecurityScanResult: Complete validation results

        Raises:
            SecurityThreatDetectedError: If threat detected and raise_on_threat is True
        """
        scan_result = self.scan_for_threats(file_path)

        # Log the security scan result
        self.security_logger.log_security_scan(
            file_path=file_path,
            scan_result=scan_result,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if not scan_result.is_safe and raise_on_threat:
            threat_summary = scan_result.get_summary()
            warnings_text = "; ".join(scan_result.warnings)

            # Log the threat detection
            self.security_logger.log_suspicious_activity(
                activity_type="threat_detected",
                description=f"Security threat detected in file: {threat_summary}",
                ip_address=ip_address,
                user_agent=user_agent,
                additional_data={
                    "file_path": file_path,
                    "threat_level": scan_result.threat_level,
                    "warnings": scan_result.warnings,
                },
            )

            raise SecurityThreatDetectedError(
                f"Security threat detected in file {file_path}: {threat_summary}. "
                f"Warnings: {warnings_text}"
            )

        return scan_result

    def update_settings(
        self,
        max_file_size: Optional[int] = None,
        allowed_mime_types: Optional[Set[str]] = None,
        enable_content_scan: Optional[bool] = None,
    ) -> None:
        """
        Update validator settings.

        Args:
            max_file_size: New maximum file size limit
            allowed_mime_types: New set of allowed MIME types
            enable_content_scan: Whether to enable content scanning
        """
        if max_file_size is not None:
            self.max_file_size = max_file_size

        if allowed_mime_types is not None:
            self.allowed_mime_types = allowed_mime_types

        if enable_content_scan is not None:
            self.enable_content_scan = enable_content_scan

    def get_settings(self) -> Dict[str, Any]:
        """
        Get current validator settings.

        Returns:
            dict: Current settings
        """
        return {
            "max_file_size": self.max_file_size,
            "allowed_mime_types": list(self.allowed_mime_types),
            "enable_content_scan": self.enable_content_scan,
            "max_header_scan_size": self.max_header_scan_size,
        }
