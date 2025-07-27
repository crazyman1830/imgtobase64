"""
Integration tests for the image base64 converter.

These tests verify the complete workflow from CLI input to final output,
testing the integration between all components of the system.
"""
import os
import sys
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.cli import CLI
from src.converter import ImageConverter
from src.file_handler import FileHandler
from src.models import ConversionResult


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete image base64 converter workflow."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_dir = tempfile.mkdtemp()
        self.converter = ImageConverter()
        self.file_handler = FileHandler()
        self.cli = CLI(self.converter, self.file_handler)
        
        # Create test image data (minimal valid image files)
        self.test_images = self._create_test_images()
    
    def tearDown(self):
        """Clean up test fixtures after each test method."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_test_images(self):
        """Create minimal test image files for different formats."""
        test_images = {}
        
        # Minimal PNG file (1x1 transparent pixel)
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,  # RGBA, CRC
            0x89, 0x00, 0x00, 0x00, 0x0B, 0x49, 0x44, 0x41,  # IDAT chunk
            0x54, 0x78, 0x9C, 0x62, 0x00, 0x02, 0x00, 0x00,  # Compressed data
            0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,  # CRC
            0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,  # IEND chunk
            0x42, 0x60, 0x82
        ])
        
        # Minimal GIF file (1x1 transparent pixel)
        gif_data = bytes([
            0x47, 0x49, 0x46, 0x38, 0x39, 0x61,  # GIF89a signature
            0x01, 0x00, 0x01, 0x00,              # 1x1 dimensions
            0x80, 0x00, 0x00,                    # Global color table
            0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF,  # Color table entries
            0x21, 0xF9, 0x04, 0x01, 0x00, 0x00,  # Graphic control extension
            0x00, 0x00, 0x2C, 0x00, 0x00, 0x00,  # Image descriptor
            0x00, 0x01, 0x00, 0x01, 0x00, 0x00,  # Image data
            0x02, 0x02, 0x04, 0x01, 0x00, 0x3B   # LZW data and trailer
        ])
        
        # Create test files
        png_path = os.path.join(self.test_dir, 'test.png')
        gif_path = os.path.join(self.test_dir, 'test.gif')
        jpg_path = os.path.join(self.test_dir, 'test.jpg')
        
        with open(png_path, 'wb') as f:
            f.write(png_data)
        
        with open(gif_path, 'wb') as f:
            f.write(gif_data)
        
        # For JPG, create a minimal JPEG file
        jpg_data = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,  # JPEG header
            0x49, 0x46, 0x00, 0x01, 0x01, 0x01, 0x00, 0x48,
            0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
            0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C,
            0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D,
            0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20,
            0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
            0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34,
            0x32, 0xFF, 0xC0, 0x00, 0x11, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0x02, 0x11,
            0x01, 0x03, 0x11, 0x01, 0xFF, 0xC4, 0x00, 0x14,
            0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x08, 0xFF, 0xC4, 0x00, 0x14, 0x10, 0x01,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0xFF, 0xDA, 0x00, 0x0C, 0x03, 0x01, 0x00, 0x02,
            0x11, 0x03, 0x11, 0x00, 0x3F, 0x00, 0xB2, 0xC0,
            0x07, 0xFF, 0xD9
        ])
        
        with open(jpg_path, 'wb') as f:
            f.write(jpg_data)
        
        test_images['png'] = png_path
        test_images['gif'] = gif_path
        test_images['jpg'] = jpg_path
        
        return test_images
    
    def test_single_file_conversion_workflow(self):
        """Test complete workflow for single file conversion."""
        # Test PNG file conversion
        png_path = self.test_images['png']
        
        # Test conversion through converter
        result = self.converter.convert_to_base64(png_path)
        
        self.assertTrue(result.success)
        self.assertEqual(result.file_path, png_path)
        self.assertEqual(result.mime_type, 'image/png')
        self.assertGreater(len(result.base64_data), 0)
        self.assertTrue(result.data_uri.startswith('data:image/png;base64,'))
        self.assertGreater(result.file_size, 0)
    
    def test_multiple_format_conversion_workflow(self):
        """Test conversion workflow for different image formats."""
        expected_mime_types = {
            'png': 'image/png',
            'gif': 'image/gif',
            'jpg': 'image/jpeg'
        }
        
        for format_name, file_path in self.test_images.items():
            with self.subTest(format=format_name):
                result = self.converter.convert_to_base64(file_path)
                
                self.assertTrue(result.success, f"Conversion failed for {format_name}")
                self.assertEqual(result.mime_type, expected_mime_types[format_name])
                self.assertGreater(len(result.base64_data), 0)
                self.assertTrue(result.data_uri.startswith(f'data:{expected_mime_types[format_name]};base64,'))
    
    def test_directory_scanning_workflow(self):
        """Test complete workflow for directory scanning and batch processing."""
        # Create subdirectory with additional images
        subdir = os.path.join(self.test_dir, 'subdir')
        os.makedirs(subdir)
        
        # Copy an image to subdirectory
        subdir_image = os.path.join(subdir, 'sub_test.png')
        shutil.copy2(self.test_images['png'], subdir_image)
        
        # Create a non-image file (should be ignored)
        text_file = os.path.join(self.test_dir, 'readme.txt')
        with open(text_file, 'w') as f:
            f.write('This is not an image')
        
        # Scan directory
        found_files = self.file_handler.find_image_files(self.test_dir)
        
        # Should find all image files including in subdirectory
        expected_files = set([
            self.test_images['png'],
            self.test_images['gif'], 
            self.test_images['jpg'],
            subdir_image
        ])
        
        self.assertEqual(set(found_files), expected_files)
        self.assertNotIn(text_file, found_files)
    
    def test_cli_single_file_processing(self):
        """Test CLI processing of single file with output capture."""
        png_path = self.test_images['png']
        
        # Capture stdout
        captured_output = StringIO()
        
        with patch('sys.stdout', captured_output):
            with patch('sys.argv', ['image-base64-converter', png_path]):
                try:
                    self.cli.run()
                except SystemExit as e:
                    # CLI should exit with code 0 on success
                    self.assertEqual(e.code, 0)
        
        output = captured_output.getvalue()
        self.assertTrue(output.startswith('data:image/png;base64,'))
    
    def test_cli_single_file_with_output_file(self):
        """Test CLI processing with file output."""
        png_path = self.test_images['png']
        output_path = os.path.join(self.test_dir, 'output.txt')
        
        with patch('sys.argv', ['image-base64-converter', png_path, '-o', output_path]):
            try:
                self.cli.run()
            except SystemExit as e:
                self.assertEqual(e.code, 0)
        
        # Verify output file was created and contains expected content
        self.assertTrue(os.path.exists(output_path))
        
        with open(output_path, 'r') as f:
            content = f.read()
        
        self.assertTrue(content.startswith('data:image/png;base64,'))
    
    def test_cli_directory_processing(self):
        """Test CLI batch processing of directory."""
        output_path = os.path.join(self.test_dir, 'batch_output.txt')
        
        with patch('sys.argv', ['image-base64-converter', self.test_dir, '-o', output_path]):
            try:
                self.cli.run()
            except SystemExit as e:
                self.assertEqual(e.code, 0)
        
        # Verify output file contains results for all images
        self.assertTrue(os.path.exists(output_path))
        
        with open(output_path, 'r') as f:
            content = f.read()
        
        # Should contain results for all test images
        self.assertIn('test.png', content)
        self.assertIn('test.gif', content)
        self.assertIn('test.jpg', content)
        self.assertIn('data:image/png;base64,', content)
        self.assertIn('data:image/gif;base64,', content)
        self.assertIn('data:image/jpeg;base64,', content)
    
    def test_error_handling_workflow(self):
        """Test error handling throughout the complete workflow."""
        # Test non-existent file
        non_existent = os.path.join(self.test_dir, 'does_not_exist.png')
        result = self.converter.convert_to_base64(non_existent)
        
        self.assertFalse(result.success)
        self.assertIn('File not found', result.error_message)
        
        # Test unsupported format
        unsupported_file = os.path.join(self.test_dir, 'test.txt')
        with open(unsupported_file, 'w') as f:
            f.write('This is not an image')
        
        result = self.converter.convert_to_base64(unsupported_file)
        self.assertFalse(result.success)
        self.assertIn('Unsupported file format', result.error_message)
    
    def test_cli_error_scenarios(self):
        """Test CLI error handling for various error scenarios."""
        # Test non-existent input file
        non_existent = os.path.join(self.test_dir, 'does_not_exist.png')
        
        with patch('sys.argv', ['image-base64-converter', non_existent]):
            with patch('sys.stderr', StringIO()) as captured_stderr:
                with self.assertRaises(SystemExit) as cm:
                    self.cli.run()
                
                self.assertEqual(cm.exception.code, 1)
                error_output = captured_stderr.getvalue()
                self.assertIn('does not exist', error_output)
        
        # Test unsupported file format
        text_file = os.path.join(self.test_dir, 'test.txt')
        with open(text_file, 'w') as f:
            f.write('Not an image')
        
        with patch('sys.argv', ['image-base64-converter', text_file]):
            with patch('sys.stderr', StringIO()) as captured_stderr:
                with self.assertRaises(SystemExit) as cm:
                    self.cli.run()
                
                self.assertEqual(cm.exception.code, 1)
                error_output = captured_stderr.getvalue()
                self.assertIn('Unsupported file format', error_output)
    
    def test_file_overwrite_protection(self):
        """Test file overwrite protection in the complete workflow."""
        png_path = self.test_images['png']
        output_path = os.path.join(self.test_dir, 'existing_output.txt')
        
        # Create existing output file
        with open(output_path, 'w') as f:
            f.write('Existing content')
        
        # Test without force flag (should fail)
        with patch('sys.argv', ['image-base64-converter', png_path, '-o', output_path]):
            with patch('sys.stdout', StringIO()) as captured_stdout:
                with self.assertRaises(SystemExit) as cm:
                    self.cli.run()
                
                self.assertEqual(cm.exception.code, 1)
                error_output = captured_stdout.getvalue()
                self.assertIn('already exists', error_output)
        
        # Test with force flag (should succeed)
        with patch('sys.argv', ['image-base64-converter', png_path, '-o', output_path, '-f']):
            try:
                self.cli.run()
            except SystemExit as e:
                self.assertEqual(e.code, 0)
        
        # Verify file was overwritten
        with open(output_path, 'r') as f:
            content = f.read()
        
        self.assertTrue(content.startswith('data:image/png;base64,'))
        self.assertNotEqual(content, 'Existing content')
    
    def test_verbose_output_workflow(self):
        """Test verbose output functionality in complete workflow."""
        png_path = self.test_images['png']
        
        with patch('sys.argv', ['image-base64-converter', png_path, '-v']):
            with patch('sys.stdout', StringIO()) as captured_stdout:
                try:
                    self.cli.run()
                except SystemExit as e:
                    self.assertEqual(e.code, 0)
        
        output = captured_stdout.getvalue()
        self.assertIn('Processing file:', output)
        self.assertIn('Conversion successful', output)
        self.assertIn('File size:', output)
        self.assertIn('MIME type:', output)
        self.assertIn('Base64 length:', output)
    
    def test_end_to_end_workflow_integration(self):
        """Test complete end-to-end workflow from CLI to final output."""
        # Create a more complex directory structure
        subdir1 = os.path.join(self.test_dir, 'images', 'png')
        subdir2 = os.path.join(self.test_dir, 'images', 'other')
        os.makedirs(subdir1)
        os.makedirs(subdir2)
        
        # Copy images to different subdirectories
        png_copy = os.path.join(subdir1, 'image1.png')
        gif_copy = os.path.join(subdir2, 'image2.gif')
        shutil.copy2(self.test_images['png'], png_copy)
        shutil.copy2(self.test_images['gif'], gif_copy)
        
        # Add some non-image files
        with open(os.path.join(subdir1, 'readme.txt'), 'w') as f:
            f.write('Documentation')
        with open(os.path.join(subdir2, 'config.json'), 'w') as f:
            f.write('{"setting": "value"}')
        
        # Process the entire directory structure
        output_path = os.path.join(self.test_dir, 'complete_output.txt')
        
        with patch('sys.argv', ['image-base64-converter', self.test_dir, '-o', output_path, '-v']):
            with patch('sys.stdout', StringIO()) as captured_stdout:
                try:
                    self.cli.run()
                except SystemExit as e:
                    self.assertEqual(e.code, 0)
        
        # Verify comprehensive output
        stdout_content = captured_stdout.getvalue()
        self.assertIn('Scanning directory:', stdout_content)
        self.assertIn('Found', stdout_content)
        self.assertIn('image file(s)', stdout_content)
        self.assertIn('Batch processing completed:', stdout_content)
        self.assertIn('Successful:', stdout_content)
        
        # Verify output file contains all expected results
        self.assertTrue(os.path.exists(output_path))
        
        with open(output_path, 'r') as f:
            file_content = f.read()
        
        # Should contain results for original images plus copies
        expected_files = ['test.png', 'test.gif', 'test.jpg', 'image1.png', 'image2.gif']
        for expected_file in expected_files:
            self.assertIn(expected_file, file_content)
        
        # Should not contain non-image files
        self.assertNotIn('readme.txt', file_content)
        self.assertNotIn('config.json', file_content)
        
        # Verify proper data URI format for each image type
        self.assertIn('data:image/png;base64,', file_content)
        self.assertIn('data:image/gif;base64,', file_content)
        self.assertIn('data:image/jpeg;base64,', file_content)


if __name__ == '__main__':
    unittest.main()