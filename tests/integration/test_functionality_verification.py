"""
Comprehensive functionality verification tests for the refactored image converter.

This test suite verifies that all existing functionality continues to work
correctly after the refactoring, covering both CLI and web interfaces.

Requirements: 1.1, 1.2
"""
import sys
import os
import tempfile
import json
import subprocess
from pathlib import Path
from io import BytesIO
from PIL import Image
import pytest
import requests
from unittest.mock import patch, MagicMock

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.container import DIContainer
from src.cli import CLI
from src.web.refactored_app import create_app
from src.core.services.image_conversion_service import ImageConversionService
from src.domain.exceptions.base import ImageConverterError


class TestImageCreator:
    """Helper class for creating test images."""
    
    @staticmethod
    def create_test_image(format='PNG', size=(100, 100), color='red') -> str:
        """Create a test image file."""
        image = Image.new('RGB', size, color=color)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format.lower()}')
        image.save(temp_file.name, format)
        temp_file.close()
        return temp_file.name
    
    @staticmethod
    def create_test_directory_with_images() -> str:
        """Create a temporary directory with multiple test images."""
        temp_dir = tempfile.mkdtemp()
        
        # Create different format images
        formats = ['PNG', 'JPEG', 'GIF', 'BMP']
        created_files = []
        
        for i, fmt in enumerate(formats):
            colors = ['red', 'green', 'blue', 'yellow']
            image = Image.new('RGB', (50 + i*10, 50 + i*10), color=colors[i % len(colors)])
            file_path = os.path.join(temp_dir, f'test_image_{i}.{fmt.lower()}')
            
            if fmt == 'JPEG':
                image.save(file_path, fmt, quality=95)
            else:
                image.save(file_path, fmt)
            
            created_files.append(file_path)
        
        return temp_dir, created_files


class TestDependencyInjectionContainer:
    """Test the dependency injection container functionality."""
    
    def test_container_creation_default(self):
        """Test creating container with default configuration."""
        container = DIContainer.create_default()
        
        # Verify all required services are available
        assert container.get('image_conversion_service') is not None
        assert container.get('file_handler') is not None
        assert container.get('cache_manager') is not None
        assert container.get('error_handler') is not None
        assert container.get('logger') is not None
        
        # Verify configuration is loaded
        config = container.get_config()
        assert config is not None
        assert hasattr(config, 'max_file_size_mb')
    
    def test_container_creation_from_config(self):
        """Test creating container from configuration file."""
        # Create temporary config file
        config_data = {
            "max_file_size_mb": 20,
            "cache_backend": "memory",
            "log_level": "DEBUG"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            container = DIContainer.create_from_config_file(config_file)
            config = container.get_config()
            
            assert config.max_file_size_mb == 20
            assert config.log_level == "DEBUG"
            
        finally:
            os.unlink(config_file)
    
    def test_service_dependencies(self):
        """Test that services have proper dependencies injected."""
        container = DIContainer.create_default()
        
        conversion_service = container.get('image_conversion_service')
        assert isinstance(conversion_service, ImageConversionService)
        
        # Verify service has required dependencies
        assert hasattr(conversion_service, '_file_handler')
        assert hasattr(conversion_service, '_cache_manager')
        assert hasattr(conversion_service, '_logger')


class TestCLIFunctionality:
    """Test CLI functionality with the refactored architecture."""
    
    def setup_method(self):
        """Set up test environment."""
        self.container = DIContainer.create_default()
        self.cli = CLI(self.container)
        self.test_images = []
        self.test_dirs = []
    
    def teardown_method(self):
        """Clean up test files."""
        for image_path in self.test_images:
            try:
                os.unlink(image_path)
            except:
                pass
        
        for dir_path in self.test_dirs:
            try:
                import shutil
                shutil.rmtree(dir_path)
            except:
                pass
    
    def test_single_file_conversion(self):
        """Test converting a single image file via CLI."""
        # Create test image
        test_image = TestImageCreator.create_test_image()
        self.test_images.append(test_image)
        
        # Create output file
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        output_file.close()
        self.test_images.append(output_file.name)
        
        # Test conversion
        self.cli.process_single_file(
            file_path=test_image,
            output_path=output_file.name,
            force_overwrite=True,
            verbose=True
        )
        
        # Verify output file was created and contains base64 data
        assert os.path.exists(output_file.name)
        with open(output_file.name, 'r') as f:
            content = f.read()
            assert 'data:image/' in content
            assert 'base64,' in content
    
    def test_directory_batch_conversion(self):
        """Test batch conversion of directory via CLI."""
        # Create test directory with images
        test_dir, created_files = TestImageCreator.create_test_directory_with_images()
        self.test_dirs.append(test_dir)
        
        # Create output file
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        output_file.close()
        self.test_images.append(output_file.name)
        
        # Test batch conversion
        self.cli.process_directory(
            directory_path=test_dir,
            output_path=output_file.name,
            force_overwrite=True,
            verbose=True
        )
        
        # Verify output file contains multiple conversions
        assert os.path.exists(output_file.name)
        with open(output_file.name, 'r') as f:
            content = f.read()
            # Should contain multiple file sections
            assert content.count('File:') >= 2
            assert content.count('data:image/') >= 2
    
    def test_cli_error_handling(self):
        """Test CLI error handling for invalid inputs."""
        # Test with non-existent file
        with pytest.raises(SystemExit):
            with patch('sys.stderr'):
                self.cli.process_single_file('/non/existent/file.jpg')
    
    def test_cli_argument_parsing(self):
        """Test CLI argument parsing."""
        # Mock sys.argv for testing
        test_args = ['program', 'test.jpg', '-o', 'output.txt', '-v', '-f']
        
        with patch('sys.argv', test_args):
            args = self.cli.parse_arguments()
            
            assert args.input_path == 'test.jpg'
            assert args.output_path == 'output.txt'
            assert args.verbose is True
            assert args.force is True


class TestWebInterfaceFunctionality:
    """Test web interface functionality with the refactored architecture."""
    
    def setup_method(self):
        """Set up test environment."""
        self.app, self.socketio, self.container = create_app()
        self.client = self.app.test_client()
        self.test_images = []
    
    def teardown_method(self):
        """Clean up test files."""
        for image_path in self.test_images:
            try:
                os.unlink(image_path)
            except:
                pass
    
    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get('/api/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'image-converter'
        assert 'timestamp' in data
    
    def test_convert_to_base64_endpoint(self):
        """Test image to base64 conversion endpoint."""
        # Create test image
        test_image = TestImageCreator.create_test_image()
        self.test_images.append(test_image)
        
        # Test conversion via web API
        with open(test_image, 'rb') as f:
            response = self.client.post('/api/convert/to-base64', data={
                'file': (f, 'test.png')
            })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'base64_data' in data
        assert data['base64_data'].startswith('data:image/')
    
    def test_validate_base64_endpoint(self):
        """Test base64 validation endpoint."""
        # Valid base64 data
        valid_base64 = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
        
        response = self.client.post('/api/validate-base64', 
                                  json={'base64_data': valid_base64})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True
        assert 'format' in data
    
    def test_get_supported_formats_endpoint(self):
        """Test supported formats endpoint."""
        response = self.client.get('/api/formats')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'formats' in data
        assert isinstance(data['formats'], list)
        assert 'PNG' in data['formats']
        assert 'JPEG' in data['formats']
    
    def test_cache_stats_endpoint(self):
        """Test cache statistics endpoint."""
        response = self.client.get('/api/cache/stats')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'cache_stats' in data
    
    def test_cache_clear_endpoint(self):
        """Test cache clearing endpoint."""
        response = self.client.post('/api/cache/clear')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
    
    def test_web_error_handling(self):
        """Test web interface error handling."""
        # Test with invalid file upload
        response = self.client.post('/api/convert/to-base64', data={
            'file': (BytesIO(b'invalid image data'), 'test.txt')
        })
        
        assert response.status_code >= 400
        data = response.get_json()
        assert 'error' in data
        assert 'error_code' in data


class TestServiceLayerIntegration:
    """Test service layer integration and functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.container = DIContainer.create_default()
        self.conversion_service = self.container.get('image_conversion_service')
        self.test_images = []
    
    def teardown_method(self):
        """Clean up test files."""
        for image_path in self.test_images:
            try:
                os.unlink(image_path)
            except:
                pass
    
    def test_image_conversion_service(self):
        """Test image conversion service functionality."""
        # Create test image
        test_image = TestImageCreator.create_test_image()
        self.test_images.append(test_image)
        
        # Test conversion
        result = self.conversion_service.convert_image(test_image)
        
        assert result.success is True
        assert result.base64_data is not None
        assert len(result.base64_data) > 0
        assert result.mime_type == 'image/png'
        assert result.file_size > 0
    
    def test_file_handler_service(self):
        """Test file handler service functionality."""
        file_handler = self.container.get('file_handler')
        
        # Create test file
        test_content = "test content"
        test_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
        test_file.write(test_content)
        test_file.close()
        self.test_images.append(test_file.name)
        
        # Test reading
        read_result = file_handler.read_file(test_file.name)
        assert read_result.success is True
        assert test_content.encode() in read_result.data
        
        # Test saving
        output_file = tempfile.NamedTemporaryFile(delete=False)
        output_file.close()
        self.test_images.append(output_file.name)
        
        save_result = file_handler.save_file("new content", output_file.name)
        assert save_result.success is True
    
    def test_cache_manager_service(self):
        """Test cache manager service functionality."""
        cache_manager = self.container.get('cache_manager')
        
        # Test cache operations
        test_key = "test_key"
        test_value = {"data": "test_data"}
        
        # Set value
        set_result = cache_manager.set(test_key, test_value)
        assert set_result is True
        
        # Get value
        get_result = cache_manager.get(test_key)
        assert get_result == test_value
        
        # Clear cache
        cache_manager.clear()
        get_result_after_clear = cache_manager.get(test_key)
        assert get_result_after_clear is None
    
    def test_error_handler_service(self):
        """Test error handler service functionality."""
        error_handler = self.container.get('error_handler')
        
        # Test error handling
        test_error = ImageConverterError("Test error")
        error_context = error_handler.handle_error(test_error, {"operation": "test"})
        
        assert error_context is not None
        assert hasattr(error_context, 'user_message')
        assert len(error_context.user_message) > 0


class TestBackwardCompatibility:
    """Test backward compatibility with legacy interfaces."""
    
    def setup_method(self):
        """Set up test environment."""
        self.container = DIContainer.create_default()
        self.test_images = []
    
    def teardown_method(self):
        """Clean up test files."""
        for image_path in self.test_images:
            try:
                os.unlink(image_path)
            except:
                pass
    
    def test_legacy_adapter_compatibility(self):
        """Test that legacy adapters maintain compatibility."""
        from src.core.adapters.legacy_image_converter_adapter import LegacyImageConverterAdapter
        
        # Create legacy adapter
        legacy_adapter = LegacyImageConverterAdapter(self.container)
        
        # Create test image
        test_image = TestImageCreator.create_test_image()
        self.test_images.append(test_image)
        
        # Test legacy interface
        result = legacy_adapter.convert_to_base64(test_image)
        
        # Verify result format matches legacy expectations
        assert isinstance(result, str)
        assert result.startswith('data:image/')
    
    def test_configuration_compatibility(self):
        """Test that configuration system maintains compatibility."""
        # Test that old configuration keys still work
        config = self.container.get_config()
        
        # These should be available for backward compatibility
        assert hasattr(config, 'max_file_size_mb')
        assert hasattr(config, 'cache_enabled')
        assert hasattr(config, 'log_level')


def run_functionality_verification_tests():
    """Run all functionality verification tests."""
    print("🚀 Starting Functionality Verification Tests")
    print("=" * 60)
    
    # Run pytest with verbose output
    pytest_args = [
        __file__,
        '-v',
        '--tb=short',
        '--color=yes'
    ]
    
    result = pytest.main(pytest_args)
    
    if result == 0:
        print("\n" + "=" * 60)
        print("🎉 All functionality verification tests passed!")
        print("✅ Refactored code maintains all existing functionality")
    else:
        print("\n" + "=" * 60)
        print("❌ Some functionality verification tests failed!")
        print("🔍 Please review the test output above for details")
    
    return result == 0


if __name__ == '__main__':
    success = run_functionality_verification_tests()
    sys.exit(0 if success else 1)