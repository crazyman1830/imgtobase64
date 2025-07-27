"""
Unit tests for the ImageConverter class.
"""
import base64
import os
import tempfile
import unittest
from pathlib import Path

from src.converter import ImageConverter
from src.models import UnsupportedFormatError


class TestImageConverter(unittest.TestCase):
    """Test cases for ImageConverter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.converter = ImageConverter()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_image_file(self, filename: str, content: bytes = None) -> str:
        """Create a test image file with given content."""
        if content is None:
            # Create a minimal PNG file (1x1 pixel transparent PNG)
            content = bytes([
                0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
                0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
                0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
                0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,  # IHDR data
                0x89, 0x00, 0x00, 0x00, 0x0B, 0x49, 0x44, 0x41,  # IDAT chunk
                0x54, 0x78, 0x9C, 0x62, 0x00, 0x02, 0x00, 0x00,  # IDAT data
                0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,  # IDAT data
                0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,  # IEND chunk
                0x42, 0x60, 0x82
            ])
        
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(content)
        return file_path
    
    def test_init(self):
        """Test ImageConverter initialization."""
        converter = ImageConverter()
        
        # Check supported formats
        expected_formats = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        self.assertEqual(converter.supported_formats, expected_formats)
        
        # Check MIME type mapping
        expected_mapping = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }
        self.assertEqual(converter.mime_type_mapping, expected_mapping)
    
    def test_is_supported_format_valid_formats(self):
        """Test is_supported_format with valid image formats."""
        test_cases = [
            'image.png',
            'image.jpg',
            'image.jpeg',
            'image.gif',
            'image.bmp',
            'image.webp',
            'IMAGE.PNG',  # Test case insensitive
            '/path/to/image.jpg',
            'image.JPG'
        ]
        
        for file_path in test_cases:
            with self.subTest(file_path=file_path):
                self.assertTrue(self.converter.is_supported_format(file_path))
    
    def test_is_supported_format_invalid_formats(self):
        """Test is_supported_format with invalid image formats."""
        test_cases = [
            'document.txt',
            'image.tiff',
            'image.svg',
            'image.pdf',
            'image',  # No extension
            'image.',  # Empty extension
        ]
        
        for file_path in test_cases:
            with self.subTest(file_path=file_path):
                self.assertFalse(self.converter.is_supported_format(file_path))
    
    def test_get_mime_type_valid_formats(self):
        """Test get_mime_type with valid image formats."""
        test_cases = [
            ('image.png', 'image/png'),
            ('image.jpg', 'image/jpeg'),
            ('image.jpeg', 'image/jpeg'),
            ('image.gif', 'image/gif'),
            ('image.bmp', 'image/bmp'),
            ('image.webp', 'image/webp'),
            ('IMAGE.PNG', 'image/png'),  # Test case insensitive
        ]
        
        for file_path, expected_mime in test_cases:
            with self.subTest(file_path=file_path):
                mime_type = self.converter.get_mime_type(file_path)
                self.assertEqual(mime_type, expected_mime)
    
    def test_get_mime_type_invalid_format(self):
        """Test get_mime_type with invalid image format."""
        with self.assertRaises(UnsupportedFormatError) as context:
            self.converter.get_mime_type('document.txt')
        
        error_message = str(context.exception)
        self.assertIn("Unsupported file format '.txt'", error_message)
        self.assertIn("Supported formats:", error_message)
    
    def test_convert_to_base64_success(self):
        """Test successful base64 conversion."""
        # Create a test PNG file
        test_content = b'test image content'
        file_path = self.create_test_image_file('test.png', test_content)
        
        result = self.converter.convert_to_base64(file_path)
        
        self.assertTrue(result.success)
        self.assertEqual(result.file_path, file_path)
        self.assertEqual(result.file_size, len(test_content))
        self.assertEqual(result.mime_type, 'image/png')
        self.assertEqual(result.error_message, '')
        
        # Verify base64 encoding
        expected_base64 = base64.b64encode(test_content).decode('utf-8')
        self.assertEqual(result.base64_data, expected_base64)
        
        # Verify data URI format
        expected_data_uri = f"data:image/png;base64,{expected_base64}"
        self.assertEqual(result.data_uri, expected_data_uri)
    
    def test_convert_to_base64_file_not_found(self):
        """Test conversion with non-existent file."""
        non_existent_file = os.path.join(self.temp_dir, 'nonexistent.png')
        
        result = self.converter.convert_to_base64(non_existent_file)
        
        self.assertFalse(result.success)
        self.assertEqual(result.file_path, non_existent_file)
        self.assertIn("File not found", result.error_message)
        self.assertEqual(result.base64_data, '')
        self.assertEqual(result.data_uri, '')
    
    def test_convert_to_base64_unsupported_format(self):
        """Test conversion with unsupported file format."""
        # Create a text file
        file_path = os.path.join(self.temp_dir, 'test.txt')
        with open(file_path, 'w') as f:
            f.write('test content')
        
        result = self.converter.convert_to_base64(file_path)
        
        self.assertFalse(result.success)
        self.assertEqual(result.file_path, file_path)
        self.assertIn("Unsupported file format '.txt'", result.error_message)
        self.assertIn("Supported formats:", result.error_message)
        self.assertEqual(result.base64_data, '')
        self.assertEqual(result.data_uri, '')
    
    def test_convert_to_base64_directory_path(self):
        """Test conversion with directory path instead of file."""
        result = self.converter.convert_to_base64(self.temp_dir)
        
        self.assertFalse(result.success)
        self.assertEqual(result.file_path, self.temp_dir)
        self.assertIn("Path is not a file", result.error_message)
    
    def test_convert_to_base64_different_formats(self):
        """Test conversion with different supported image formats."""
        test_formats = [
            ('test.png', 'image/png'),
            ('test.jpg', 'image/jpeg'),
            ('test.jpeg', 'image/jpeg'),
            ('test.gif', 'image/gif'),
            ('test.bmp', 'image/bmp'),
            ('test.webp', 'image/webp'),
        ]
        
        test_content = b'test image content'
        
        for filename, expected_mime in test_formats:
            with self.subTest(filename=filename):
                file_path = self.create_test_image_file(filename, test_content)
                result = self.converter.convert_to_base64(file_path)
                
                self.assertTrue(result.success, f"Failed for {filename}: {result.error_message}")
                self.assertEqual(result.mime_type, expected_mime)
                self.assertEqual(result.file_size, len(test_content))
                
                # Verify data URI format
                expected_base64 = base64.b64encode(test_content).decode('utf-8')
                expected_data_uri = f"data:{expected_mime};base64,{expected_base64}"
                self.assertEqual(result.data_uri, expected_data_uri)


if __name__ == '__main__':
    unittest.main()