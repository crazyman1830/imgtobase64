"""
Unit tests for the SecurityValidator class.
"""
import os
import tempfile
import logging
import pytest
from unittest.mock import patch, MagicMock

from src.core.security_validator import SecurityValidator
from src.models.models import SecurityThreatDetectedError
from src.models.processing_options import SecurityScanResult


class TestSecurityValidator:
    """Test cases for SecurityValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SecurityValidator(
            max_file_size=1024 * 1024,  # 1MB for testing
            enable_content_scan=True
        )
        
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_file(self, filename: str, content: bytes, size: int = None) -> str:
        """Create a test file with specified content."""
        file_path = os.path.join(self.temp_dir, filename)
        
        with open(file_path, 'wb') as f:
            if size:
                # Create file of specific size
                f.write(content * (size // len(content) + 1))
                f.truncate(size)
            else:
                f.write(content)
        
        return file_path
    
    def test_init_default_settings(self):
        """Test SecurityValidator initialization with default settings."""
        validator = SecurityValidator()
        
        assert validator.max_file_size == 10 * 1024 * 1024  # 10MB
        assert 'image/jpeg' in validator.allowed_mime_types
        assert 'image/png' in validator.allowed_mime_types
        assert validator.enable_content_scan is True
        assert validator.max_header_scan_size == 1024
    
    def test_init_custom_settings(self):
        """Test SecurityValidator initialization with custom settings."""
        custom_mime_types = {'image/jpeg', 'image/png'}
        validator = SecurityValidator(
            max_file_size=5 * 1024 * 1024,
            allowed_mime_types=custom_mime_types,
            enable_content_scan=False,
            max_header_scan_size=512
        )
        
        assert validator.max_file_size == 5 * 1024 * 1024
        assert validator.allowed_mime_types == custom_mime_types
        assert validator.enable_content_scan is False
        assert validator.max_header_scan_size == 512
    
    def test_validate_file_size_valid(self):
        """Test file size validation with valid file."""
        # Create a small test file
        test_file = self.create_test_file("small.txt", b"test content")
        
        result = self.validator.validate_file_size(test_file)
        assert result is True
    
    def test_validate_file_size_invalid(self):
        """Test file size validation with oversized file."""
        # Create a file larger than the limit
        large_content = b"x" * (2 * 1024 * 1024)  # 2MB
        test_file = self.create_test_file("large.txt", large_content)
        
        result = self.validator.validate_file_size(test_file)
        assert result is False
    
    def test_validate_file_size_nonexistent(self):
        """Test file size validation with non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.validator.validate_file_size("nonexistent.txt")
    
    def test_validate_mime_type_valid(self):
        """Test MIME type validation with valid image file."""
        # Create test file with JPEG extension
        test_file = self.create_test_file("test.jpg", b"test content")
        
        # Mock the mime detector directly
        mock_detector = MagicMock()
        mock_detector.from_file.return_value = 'image/jpeg'
        self.validator.mime_detector = mock_detector
        
        is_valid, detected_mime = self.validator.validate_mime_type(test_file)
        
        assert is_valid is True
        assert detected_mime == 'image/jpeg'
    
    def test_validate_mime_type_invalid(self):
        """Test MIME type validation with invalid file type."""
        # Create test file
        test_file = self.create_test_file("test.txt", b"test content")
        
        # Mock the mime detector directly
        mock_detector = MagicMock()
        mock_detector.from_file.return_value = 'text/plain'
        self.validator.mime_detector = mock_detector
        
        is_valid, detected_mime = self.validator.validate_mime_type(test_file)
        
        assert is_valid is False
        assert detected_mime == 'text/plain'
    
    def test_validate_mime_type_nonexistent(self):
        """Test MIME type validation with non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.validator.validate_mime_type("nonexistent.txt")
    
    def test_validate_file_header_jpeg(self):
        """Test file header validation with JPEG file."""
        # JPEG file signature
        jpeg_header = b'\xFF\xD8\xFF\xE0\x00\x10JFIF'
        test_file = self.create_test_file("test.jpg", jpeg_header)
        
        is_valid, detected_format = self.validator.validate_file_header(test_file)
        
        assert is_valid is True
        assert detected_format == 'image/jpeg'
    
    def test_validate_file_header_png(self):
        """Test file header validation with PNG file."""
        # PNG file signature
        png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
        test_file = self.create_test_file("test.png", png_header)
        
        is_valid, detected_format = self.validator.validate_file_header(test_file)
        
        assert is_valid is True
        assert detected_format == 'image/png'
    
    def test_validate_file_header_gif(self):
        """Test file header validation with GIF file."""
        # GIF87a file signature
        gif_header = b'GIF87a\x01\x00\x01\x00'
        test_file = self.create_test_file("test.gif", gif_header)
        
        is_valid, detected_format = self.validator.validate_file_header(test_file)
        
        assert is_valid is True
        assert detected_format == 'image/gif'
    
    def test_validate_file_header_webp(self):
        """Test file header validation with WebP file."""
        # WebP file signature
        webp_header = b'RIFF\x00\x00\x00\x00WEBP'
        test_file = self.create_test_file("test.webp", webp_header)
        
        is_valid, detected_format = self.validator.validate_file_header(test_file)
        
        assert is_valid is True
        assert detected_format == 'image/webp'
    
    def test_validate_file_header_invalid(self):
        """Test file header validation with invalid file."""
        # Invalid header
        invalid_header = b'INVALID_HEADER'
        test_file = self.create_test_file("test.txt", invalid_header)
        
        is_valid, detected_format = self.validator.validate_file_header(test_file)
        
        assert is_valid is False
        assert detected_format == 'unknown'
    
    def test_validate_file_header_nonexistent(self):
        """Test file header validation with non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.validator.validate_file_header("nonexistent.txt")
    
    def test_scan_file_content_safe(self):
        """Test content scanning with safe file."""
        safe_content = b'This is a safe image file content'
        test_file = self.create_test_file("safe.jpg", safe_content)
        
        is_safe, threats = self.validator._scan_file_content(test_file)
        assert is_safe is True
        assert len(threats) == 0
    
    def test_scan_file_content_suspicious(self):
        """Test content scanning with suspicious content."""
        suspicious_content = b'<script>alert("malicious")</script>'
        test_file = self.create_test_file("suspicious.jpg", suspicious_content)
        
        is_safe, threats = self.validator._scan_file_content(test_file)
        assert is_safe is False
        assert len(threats) > 0
        assert any('script' in threat.lower() for threat in threats)
    
    def test_scan_file_content_multiple_patterns(self):
        """Test content scanning with multiple suspicious patterns."""
        suspicious_content = b'javascript:void(0); <?php echo "test"; ?>'
        test_file = self.create_test_file("suspicious.jpg", suspicious_content)
        
        is_safe, threats = self.validator._scan_file_content(test_file)
        assert is_safe is False
        assert len(threats) >= 2  # Should detect both javascript and php patterns
    
    def test_scan_for_threats_safe_file(self):
        """Test comprehensive threat scanning with safe file."""
        # Create safe JPEG file
        jpeg_content = b'\xFF\xD8\xFF\xE0\x00\x10JFIF' + b'safe image content'
        test_file = self.create_test_file("safe.jpg", jpeg_content)
        
        # Mock the mime detector directly
        mock_detector = MagicMock()
        mock_detector.from_file.return_value = 'image/jpeg'
        self.validator.mime_detector = mock_detector
        
        result = self.validator.scan_for_threats(test_file)
        
        assert isinstance(result, SecurityScanResult)
        assert result.is_safe is True
        assert result.threat_level == "low"
        assert result.file_size_check is True
        assert result.mime_type_check is True
        assert result.header_check is True
        assert result.content_check is True
        assert len(result.warnings) == 0
    
    def test_scan_for_threats_unsafe_file(self):
        """Test comprehensive threat scanning with unsafe file."""
        # Create suspicious file with invalid header and content
        suspicious_content = b'INVALID_HEADER<script>alert("xss")</script>'
        test_file = self.create_test_file("malicious.jpg", suspicious_content)
        
        # Mock the mime detector directly
        mock_detector = MagicMock()
        mock_detector.from_file.return_value = 'text/plain'
        self.validator.mime_detector = mock_detector
        
        result = self.validator.scan_for_threats(test_file)
        
        assert isinstance(result, SecurityScanResult)
        assert result.is_safe is False
        assert result.threat_level == "high"
        assert result.mime_type_check is False
        assert result.header_check is False
        assert result.content_check is False
        assert len(result.warnings) > 0
    
    def test_validate_file_safe(self):
        """Test complete file validation with safe file."""
        # Create safe JPEG file
        jpeg_content = b'\xFF\xD8\xFF\xE0\x00\x10JFIF' + b'safe content'
        test_file = self.create_test_file("safe.jpg", jpeg_content)
        
        with patch.object(self.validator, 'scan_for_threats') as mock_scan:
            mock_scan.return_value = SecurityScanResult(
                is_safe=True,
                threat_level="low",
                warnings=[],
                scan_time=0.1
            )
            
            result = self.validator.validate_file(test_file)
            
            assert result.is_safe is True
            assert result.threat_level == "low"
    
    def test_validate_file_unsafe_no_raise(self):
        """Test complete file validation with unsafe file (no exception)."""
        test_file = self.create_test_file("unsafe.jpg", b'malicious content')
        
        with patch.object(self.validator, 'scan_for_threats') as mock_scan:
            mock_scan.return_value = SecurityScanResult(
                is_safe=False,
                threat_level="high",
                warnings=["Threat detected"],
                scan_time=0.1
            )
            
            result = self.validator.validate_file(test_file, raise_on_threat=False)
            
            assert result.is_safe is False
            assert result.threat_level == "high"
    
    def test_validate_file_unsafe_with_raise(self):
        """Test complete file validation with unsafe file (with exception)."""
        test_file = self.create_test_file("unsafe.jpg", b'malicious content')
        
        with patch.object(self.validator, 'scan_for_threats') as mock_scan:
            mock_scan.return_value = SecurityScanResult(
                is_safe=False,
                threat_level="high",
                warnings=["Threat detected"],
                scan_time=0.1
            )
            
            with pytest.raises(SecurityThreatDetectedError):
                self.validator.validate_file(test_file, raise_on_threat=True)
    
    def test_update_settings(self):
        """Test updating validator settings."""
        new_mime_types = {'image/jpeg'}
        
        self.validator.update_settings(
            max_file_size=2 * 1024 * 1024,
            allowed_mime_types=new_mime_types,
            enable_content_scan=False
        )
        
        assert self.validator.max_file_size == 2 * 1024 * 1024
        assert self.validator.allowed_mime_types == new_mime_types
        assert self.validator.enable_content_scan is False
    
    def test_get_settings(self):
        """Test getting current validator settings."""
        settings = self.validator.get_settings()
        
        assert 'max_file_size' in settings
        assert 'allowed_mime_types' in settings
        assert 'enable_content_scan' in settings
        assert 'max_header_scan_size' in settings
        
        assert settings['max_file_size'] == self.validator.max_file_size
        assert set(settings['allowed_mime_types']) == self.validator.allowed_mime_types
        assert settings['enable_content_scan'] == self.validator.enable_content_scan
    
    def test_image_signatures_coverage(self):
        """Test that all defined image signatures are properly detected."""
        test_cases = [
            (b'\xFF\xD8\xFF', 'image/jpeg'),
            (b'\x89PNG\r\n\x1a\n', 'image/png'),
            (b'GIF87a', 'image/gif'),
            (b'GIF89a', 'image/gif'),
            (b'BM', 'image/bmp'),
            (b'\x00\x00\x01\x00', 'image/x-icon'),
        ]
        
        for signature, expected_type in test_cases:
            test_file = self.create_test_file(f"test_{expected_type.replace('/', '_')}", signature + b'padding')
            is_valid, detected_format = self.validator.validate_file_header(test_file)
            
            assert is_valid is True
            assert detected_format == expected_type
    
    def test_suspicious_patterns_detection(self):
        """Test that all suspicious patterns are properly detected."""
        suspicious_patterns = [
            (b'<script>', 'script'),
            (b'javascript:', 'javascript'),
            (b'vbscript:', 'vbscript'),
            (b'onload=', 'onload'),
            (b'onerror=', 'onerror'),
            (b'<?php', 'php'),
            (b'<%', 'asp'),
            (b'eval(', 'eval'),
            (b'exec(', 'exec'),
            (b'system(', 'system'),
            (b'shell_exec(', 'shell_exec'),
        ]
        
        for pattern, safe_name in suspicious_patterns:
            test_content = b'safe content ' + pattern + b' more content'
            test_file = self.create_test_file(f"suspicious_{safe_name}.txt", test_content)
            
            is_safe, threats = self.validator._scan_file_content(test_file)
            assert is_safe is False, f"Pattern {pattern} should be detected as suspicious"
            assert len(threats) > 0, f"Pattern {pattern} should generate threat warnings"


class TestRateLimiter:
    """Test cases for RateLimiter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from src.core.rate_limiter import RateLimiter, RateLimitConfig
        
        # Create rate limiter with low limits for testing
        config = RateLimitConfig(
            requests_per_minute=5,
            requests_per_hour=20,
            requests_per_day=100,
            burst_limit=3,
            burst_window=10
        )
        self.rate_limiter = RateLimiter(config)
        self.test_ip = "192.168.1.100"
    
    def test_rate_limiter_init(self):
        """Test rate limiter initialization."""
        from src.core.rate_limiter import RateLimiter, RateLimitConfig
        
        config = RateLimitConfig(requests_per_minute=10)
        limiter = RateLimiter(config)
        
        assert limiter.config.requests_per_minute == 10
        assert limiter.config.requests_per_hour == 1000  # default
    
    def test_check_rate_limit_within_limits(self):
        """Test rate limit check when within limits."""
        status = self.rate_limiter.check_rate_limit(self.test_ip, raise_on_limit=False)
        
        assert status.ip_address == self.test_ip
        assert status.is_limited is False
        assert status.remaining_requests > 0
    
    def test_record_request_success(self):
        """Test successful request recording."""
        status = self.rate_limiter.record_request(self.test_ip)
        
        assert status.requests_in_minute == 1
        assert status.requests_in_hour == 1
        assert status.requests_in_day == 1
        assert status.requests_in_burst == 1
        assert status.is_limited is False
    
    def test_burst_limit_exceeded(self):
        """Test burst limit enforcement."""
        from src.models.models import RateLimitExceededError
        
        # Make requests up to burst limit
        for i in range(3):
            self.rate_limiter.record_request(self.test_ip)
        
        # Next request should exceed burst limit
        with pytest.raises(RateLimitExceededError):
            self.rate_limiter.record_request(self.test_ip)
    
    def test_minute_limit_exceeded(self):
        """Test minute limit enforcement by directly manipulating request history."""
        from src.models.models import RateLimitExceededError
        import time
        
        # Directly add requests to minute history to simulate minute limit being reached
        current_time = time.time()
        for i in range(5):  # Fill up to minute limit
            self.rate_limiter._minute_requests[self.test_ip].append(current_time - i)
            self.rate_limiter._hour_requests[self.test_ip].append(current_time - i)
            self.rate_limiter._day_requests[self.test_ip].append(current_time - i)
        
        # Next request should exceed minute limit
        with pytest.raises(RateLimitExceededError):
            self.rate_limiter.record_request(self.test_ip)
    
    def test_get_status(self):
        """Test getting rate limit status."""
        # Record some requests
        self.rate_limiter.record_request(self.test_ip)
        self.rate_limiter.record_request(self.test_ip)
        
        status = self.rate_limiter.get_status(self.test_ip)
        
        assert status.requests_in_minute == 2
        assert status.requests_in_hour == 2
        assert status.requests_in_day == 2
        assert status.requests_in_burst == 2
    
    def test_reset_ip(self):
        """Test resetting rate limit for specific IP."""
        # Record some requests
        self.rate_limiter.record_request(self.test_ip)
        self.rate_limiter.record_request(self.test_ip)
        
        # Reset the IP
        self.rate_limiter.reset_ip(self.test_ip)
        
        # Check that counters are reset
        status = self.rate_limiter.get_status(self.test_ip)
        assert status.requests_in_minute == 0
        assert status.requests_in_hour == 0
        assert status.requests_in_day == 0
        assert status.requests_in_burst == 0
    
    def test_get_stats(self):
        """Test getting rate limiter statistics."""
        # Record requests from multiple IPs
        self.rate_limiter.record_request("192.168.1.1")
        self.rate_limiter.record_request("192.168.1.2")
        self.rate_limiter.record_request("192.168.1.1")
        
        stats = self.rate_limiter.get_stats()
        
        assert stats['tracked_ips'] == 2
        assert stats['requests_last_minute'] == 3
        assert stats['requests_last_hour'] == 3
        assert stats['requests_last_day'] == 3
        assert 'config' in stats
    
    def test_update_config(self):
        """Test updating rate limiter configuration."""
        from src.core.rate_limiter import RateLimitConfig
        
        new_config = RateLimitConfig(requests_per_minute=100)
        self.rate_limiter.update_config(new_config)
        
        assert self.rate_limiter.config.requests_per_minute == 100
    
    def test_multiple_ips_independent(self):
        """Test that different IPs have independent rate limits."""
        ip1 = "192.168.1.1"
        ip2 = "192.168.1.2"
        
        # Make requests from both IPs
        self.rate_limiter.record_request(ip1)
        self.rate_limiter.record_request(ip1)
        self.rate_limiter.record_request(ip2)
        
        status1 = self.rate_limiter.get_status(ip1)
        status2 = self.rate_limiter.get_status(ip2)
        
        assert status1.requests_in_minute == 2
        assert status2.requests_in_minute == 1


class TestSecurityLogger:
    """Test cases for SecurityLogger class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        import tempfile
        from src.core.security_logger import SecurityLogger
        
        # Create temporary log file
        self.temp_log = tempfile.NamedTemporaryFile(delete=False, suffix='.log')
        self.temp_log.close()
        
        self.security_logger = SecurityLogger(
            log_file=self.temp_log.name,
            log_level=logging.DEBUG
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import os
        if os.path.exists(self.temp_log.name):
            os.unlink(self.temp_log.name)
    
    def test_log_security_scan(self):
        """Test logging security scan results."""
        from src.models.processing_options import SecurityScanResult
        
        scan_result = SecurityScanResult(
            is_safe=False,
            threat_level="high",
            warnings=["Test warning"],
            scan_time=0.1
        )
        
        self.security_logger.log_security_scan(
            file_path="/test/file.jpg",
            scan_result=scan_result,
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0"
        )
        
        # Check that log file was written
        with open(self.temp_log.name, 'r') as f:
            log_content = f.read()
            assert 'security_scan' in log_content
            assert 'high' in log_content
            assert '192.168.1.1' in log_content
    
    def test_log_rate_limit_violation(self):
        """Test logging rate limit violations."""
        self.security_logger.log_rate_limit_violation(
            ip_address="192.168.1.1",
            violation_type="minute",
            current_count=10,
            limit=5,
            user_agent="TestAgent/1.0"
        )
        
        # Check that log file was written
        with open(self.temp_log.name, 'r') as f:
            log_content = f.read()
            assert 'rate_limit_violation' in log_content
            assert 'minute' in log_content
            assert '192.168.1.1' in log_content
    
    def test_log_suspicious_activity(self):
        """Test logging suspicious activity."""
        self.security_logger.log_suspicious_activity(
            activity_type="malicious_upload",
            description="Suspicious file upload detected",
            ip_address="192.168.1.1",
            additional_data={"file_type": "executable"}
        )
        
        # Check that log file was written
        with open(self.temp_log.name, 'r') as f:
            log_content = f.read()
            assert 'suspicious_activity' in log_content
            assert 'malicious_upload' in log_content
            assert 'executable' in log_content
    
    def test_log_system_event(self):
        """Test logging system events."""
        self.security_logger.log_system_event(
            event_type="startup",
            description="Security system initialized",
            severity="info"
        )
        
        # Check that log file was written
        with open(self.temp_log.name, 'r') as f:
            log_content = f.read()
            assert 'system_event' in log_content
            assert 'startup' in log_content
            assert 'initialized' in log_content