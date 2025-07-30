"""
Test script for verifying the improved error handling in the web interface.

This script tests various error scenarios to ensure that the error handling
middleware and formatters work correctly.
"""
import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.web.error_formatter import ErrorResponseFormatter
from src.domain.exceptions.validation import ValidationError
from src.domain.exceptions.security import SecurityError
from src.domain.exceptions.file_system import FileNotFoundError
from src.domain.exceptions.processing import ProcessingError
from src.domain.exceptions.cache import CacheError


def test_error_formatter():
    """Test the error response formatter with various error types."""
    formatter = ErrorResponseFormatter()
    
    print("🧪 Testing Error Response Formatter")
    print("=" * 50)
    
    # Test validation error
    print("\n1. Testing ValidationError:")
    validation_error = ValidationError("Invalid file format")
    response, status_code = formatter.format_error_response(validation_error)
    print(f"   Status Code: {status_code}")
    print(f"   Response: {response}")
    
    # Test security error
    print("\n2. Testing SecurityError:")
    security_error = SecurityError("File contains malicious content")
    response, status_code = formatter.format_error_response(security_error)
    print(f"   Status Code: {status_code}")
    print(f"   Response: {response}")
    
    # Test file not found error
    print("\n3. Testing FileNotFoundError:")
    file_error = FileNotFoundError("test.jpg")
    response, status_code = formatter.format_error_response(file_error)
    print(f"   Status Code: {status_code}")
    print(f"   Response: {response}")
    
    # Test processing error
    print("\n4. Testing ProcessingError:")
    processing_error = ProcessingError("Image conversion failed")
    response, status_code = formatter.format_error_response(processing_error)
    print(f"   Status Code: {status_code}")
    print(f"   Response: {response}")
    
    # Test cache error
    print("\n5. Testing CacheError:")
    cache_error = CacheError("Cache backend unavailable")
    response, status_code = formatter.format_error_response(cache_error)
    print(f"   Status Code: {status_code}")
    print(f"   Response: {response}")
    
    # Test generic error
    print("\n6. Testing Generic Exception:")
    generic_error = Exception("Unexpected error occurred")
    response, status_code = formatter.format_error_response(generic_error)
    print(f"   Status Code: {status_code}")
    print(f"   Response: {response}")
    
    print("\n✅ Error formatter tests completed!")


def test_validation_error_list():
    """Test formatting of validation error lists."""
    formatter = ErrorResponseFormatter()
    
    print("\n🧪 Testing Validation Error List Formatting")
    print("=" * 50)
    
    errors = [
        "File size exceeds maximum limit",
        "Unsupported file format",
        "Missing required field: filename"
    ]
    
    response = formatter.format_validation_error_list(errors, "file")
    print(f"Response: {response}")
    
    print("\n✅ Validation error list test completed!")


def test_success_response():
    """Test formatting of success responses."""
    formatter = ErrorResponseFormatter()
    
    print("\n🧪 Testing Success Response Formatting")
    print("=" * 50)
    
    data = {
        'base64': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==',
        'format': 'PNG',
        'size': (1, 1),
        'file_size': 95
    }
    
    response = formatter.format_success_response(data, "Image converted successfully")
    print(f"Response: {response}")
    
    print("\n✅ Success response test completed!")


def test_error_context():
    """Test error formatting with context information."""
    formatter = ErrorResponseFormatter()
    
    print("\n🧪 Testing Error Formatting with Context")
    print("=" * 50)
    
    context = {
        'request_path': '/api/convert/to-base64',
        'request_method': 'POST',
        'user_agent': 'Mozilla/5.0 (Test Browser)',
        'remote_addr': '127.0.0.1'
    }
    
    error = ProcessingError("Image processing failed during resize operation")
    error.processing_stage = "resize"
    error.file_path = "/tmp/test_image.jpg"
    error.processing_time = 2.5
    
    response, status_code = formatter.format_error_response(error, context)
    print(f"Status Code: {status_code}")
    print(f"Response: {response}")
    
    print("\n✅ Error context test completed!")


if __name__ == '__main__':
    """Run all error handling tests."""
    print("🚀 Starting Error Handling Tests")
    print("=" * 60)
    
    try:
        test_error_formatter()
        test_validation_error_list()
        test_success_response()
        test_error_context()
        
        print("\n" + "=" * 60)
        print("🎉 All error handling tests passed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)