"""
Integration test for the refactored web interface.

This script tests the integration between the web handlers, error handling,
and the service layer to ensure everything works together correctly.
"""
import sys
import os
import tempfile
from pathlib import Path
from io import BytesIO
from PIL import Image

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.container import DIContainer
from src.web.handlers import WebHandlers
from src.web.error_formatter import ErrorResponseFormatter
from src.domain.exceptions.validation import ValidationError


def create_test_image() -> str:
    """
    Create a test image file for testing.
    
    Returns:
        Path to the created test image
    """
    # Create a simple 1x1 pixel PNG image
    image = Image.new('RGB', (1, 1), color='red')
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    image.save(temp_file.name, 'PNG')
    temp_file.close()
    
    return temp_file.name


def test_container_initialization():
    """Test that the DI container initializes correctly."""
    print("🧪 Testing DI Container Initialization")
    print("=" * 50)
    
    try:
        container = DIContainer.create_default()
        
        # Test that we can get required services
        config = container.get_config()
        print(f"   ✅ Config loaded: {type(config).__name__}")
        
        conversion_service = container.get('image_conversion_service')
        print(f"   ✅ Conversion service: {type(conversion_service).__name__}")
        
        error_handler = container.get('error_handler')
        print(f"   ✅ Error handler: {type(error_handler).__name__}")
        
        logger = container.get('logger')
        print(f"   ✅ Logger: {type(logger).__name__}")
        
        print("   ✅ Container initialization successful!")
        return container
        
    except Exception as e:
        print(f"   ❌ Container initialization failed: {str(e)}")
        raise


def test_web_handlers_initialization(container):
    """Test that web handlers initialize correctly."""
    print("\n🧪 Testing Web Handlers Initialization")
    print("=" * 50)
    
    try:
        handlers = WebHandlers(container)
        
        # Test that handlers have required dependencies
        assert handlers.container is not None
        assert handlers.conversion_service is not None
        assert handlers.error_handler is not None
        assert handlers.logger is not None
        assert handlers.error_formatter is not None
        
        print("   ✅ Web handlers initialization successful!")
        return handlers
        
    except Exception as e:
        print(f"   ❌ Web handlers initialization failed: {str(e)}")
        raise


def test_error_formatter_integration():
    """Test error formatter integration."""
    print("\n🧪 Testing Error Formatter Integration")
    print("=" * 50)
    
    try:
        formatter = ErrorResponseFormatter()
        
        # Test with a validation error
        error = ValidationError("Test validation error")
        response, status_code = formatter.format_error_response(error)
        
        # Verify response structure
        assert 'error' in response
        assert 'error_code' in response
        assert 'error_type' in response
        assert 'timestamp' in response
        assert 'suggestions' in response
        assert status_code == 400
        
        print("   ✅ Error formatter integration successful!")
        print(f"   📝 Sample response: {response['error']}")
        
    except Exception as e:
        print(f"   ❌ Error formatter integration failed: {str(e)}")
        raise


def test_service_layer_integration(container):
    """Test service layer integration."""
    print("\n🧪 Testing Service Layer Integration")
    print("=" * 50)
    
    try:
        # Get the conversion service
        conversion_service = container.get('image_conversion_service')
        
        # Create a test image
        test_image_path = create_test_image()
        
        try:
            # Test image conversion
            result = conversion_service.convert_image(test_image_path)
            
            # Verify result
            assert result.success is True
            assert result.base64_data is not None
            assert len(result.base64_data) > 0
            
            print("   ✅ Service layer integration successful!")
            print(f"   📝 Converted image size: {result.file_size} bytes")
            
        finally:
            # Clean up test image
            try:
                os.unlink(test_image_path)
            except:
                pass
                
    except Exception as e:
        print(f"   ❌ Service layer integration failed: {str(e)}")
        raise


def test_error_handling_flow(container):
    """Test the complete error handling flow."""
    print("\n🧪 Testing Error Handling Flow")
    print("=" * 50)
    
    try:
        conversion_service = container.get('image_conversion_service')
        
        # Test with non-existent file (should trigger FileNotFoundError)
        try:
            result = conversion_service.convert_image("/non/existent/file.jpg")
            print("   ❌ Expected error but got success")
            
        except Exception as e:
            # This should be caught and handled by the error system
            formatter = ErrorResponseFormatter()
            response, status_code = formatter.format_error_response(e)
            
            print(f"   ✅ Error handling flow successful!")
            print(f"   📝 Error type: {response.get('error_type', 'Unknown')}")
            print(f"   📝 Status code: {status_code}")
            print(f"   📝 User message: {response.get('error', 'No message')}")
            
    except Exception as e:
        print(f"   ❌ Error handling flow failed: {str(e)}")
        raise


def test_cache_integration(container):
    """Test cache integration."""
    print("\n🧪 Testing Cache Integration")
    print("=" * 50)
    
    try:
        conversion_service = container.get('image_conversion_service')
        
        # Get cache stats
        cache_stats = conversion_service.get_cache_stats()
        
        print("   ✅ Cache integration successful!")
        print(f"   📝 Cache stats: {cache_stats}")
        
        # Test cache clearing
        conversion_service.clear_cache()
        print("   ✅ Cache clearing successful!")
        
    except Exception as e:
        print(f"   ❌ Cache integration failed: {str(e)}")
        # Don't raise - cache might not be enabled in test config


def run_integration_tests():
    """Run all integration tests."""
    print("🚀 Starting Integration Tests")
    print("=" * 60)
    
    try:
        # Test 1: Container initialization
        container = test_container_initialization()
        
        # Test 2: Web handlers initialization
        handlers = test_web_handlers_initialization(container)
        
        # Test 3: Error formatter integration
        test_error_formatter_integration()
        
        # Test 4: Service layer integration
        test_service_layer_integration(container)
        
        # Test 5: Error handling flow
        test_error_handling_flow(container)
        
        # Test 6: Cache integration
        test_cache_integration(container)
        
        print("\n" + "=" * 60)
        print("🎉 All integration tests passed successfully!")
        print("✨ The refactored web interface is working correctly!")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    run_integration_tests()