"""
Unit tests for the FileHandler class.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open

from src.file_handler import FileHandler
from src.models import FileNotFoundError, PermissionError, ImageConverterError


class TestFileHandler(unittest.TestCase):
    """Test cases for FileHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.file_handler = FileHandler()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_file_exists_with_valid_file(self):
        """Test file_exists with a valid, readable file."""
        # Create a temporary file
        temp_file = os.path.join(self.temp_dir, "test.txt")
        with open(temp_file, 'w') as f:
            f.write("test content")
        
        result = self.file_handler.file_exists(temp_file)
        self.assertTrue(result)
    
    def test_file_exists_with_nonexistent_file(self):
        """Test file_exists with a non-existent file."""
        nonexistent_file = os.path.join(self.temp_dir, "nonexistent.txt")
        
        with self.assertRaises(FileNotFoundError) as context:
            self.file_handler.file_exists(nonexistent_file)
        
        self.assertIn("File not found", str(context.exception))
    
    def test_file_exists_with_directory(self):
        """Test file_exists with a directory path."""
        with self.assertRaises(FileNotFoundError) as context:
            self.file_handler.file_exists(self.temp_dir)
        
        self.assertIn("Path is not a file", str(context.exception))
    
    @patch('os.access')
    def test_file_exists_with_permission_denied(self, mock_access):
        """Test file_exists with permission denied."""
        # Create a temporary file
        temp_file = os.path.join(self.temp_dir, "test.txt")
        with open(temp_file, 'w') as f:
            f.write("test content")
        
        # Mock os.access to return False for read permission
        mock_access.return_value = False
        
        with self.assertRaises(PermissionError) as context:
            self.file_handler.file_exists(temp_file)
        
        self.assertIn("Permission denied", str(context.exception))
    
    def test_find_image_files_with_valid_directory(self):
        """Test find_image_files with a directory containing image files."""
        # Create test image files
        image_files = ["test1.png", "test2.jpg", "test3.gif", "test4.bmp"]
        non_image_files = ["test.txt", "test.doc"]
        
        for filename in image_files + non_image_files:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test content")
        
        result = self.file_handler.find_image_files(self.temp_dir)
        
        # Should only return image files, sorted
        expected_files = [os.path.join(self.temp_dir, f) for f in sorted(image_files)]
        self.assertEqual(result, expected_files)
    
    def test_find_image_files_with_subdirectories(self):
        """Test find_image_files with subdirectories."""
        # Create subdirectory
        sub_dir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(sub_dir)
        
        # Create image files in main directory and subdirectory
        main_file = os.path.join(self.temp_dir, "main.png")
        sub_file = os.path.join(sub_dir, "sub.jpg")
        
        for file_path in [main_file, sub_file]:
            with open(file_path, 'w') as f:
                f.write("test content")
        
        result = self.file_handler.find_image_files(self.temp_dir)
        
        # Should find files in both directories, sorted
        expected_files = sorted([main_file, sub_file])
        self.assertEqual(result, expected_files)
    
    def test_find_image_files_with_nonexistent_directory(self):
        """Test find_image_files with non-existent directory."""
        nonexistent_dir = os.path.join(self.temp_dir, "nonexistent")
        
        with self.assertRaises(FileNotFoundError) as context:
            self.file_handler.find_image_files(nonexistent_dir)
        
        self.assertIn("Directory not found", str(context.exception))
    
    def test_find_image_files_with_file_path(self):
        """Test find_image_files with a file path instead of directory."""
        temp_file = os.path.join(self.temp_dir, "test.txt")
        with open(temp_file, 'w') as f:
            f.write("test content")
        
        with self.assertRaises(FileNotFoundError) as context:
            self.file_handler.find_image_files(temp_file)
        
        self.assertIn("Path is not a directory", str(context.exception))
    
    @patch('os.access')
    def test_find_image_files_with_permission_denied(self, mock_access):
        """Test find_image_files with permission denied on directory."""
        # Mock os.access to return False for read permission on directory
        def access_side_effect(path, mode):
            if path == self.temp_dir and mode == os.R_OK:
                return False
            return True
        
        mock_access.side_effect = access_side_effect
        
        with self.assertRaises(PermissionError) as context:
            self.file_handler.find_image_files(self.temp_dir)
        
        self.assertIn("Permission denied", str(context.exception))
    
    def test_save_to_file_success(self):
        """Test save_to_file with successful save."""
        output_file = os.path.join(self.temp_dir, "output.txt")
        content = "test base64 content"
        
        with patch('builtins.print') as mock_print:
            result = self.file_handler.save_to_file(content, output_file)
        
        self.assertTrue(result)
        
        # Verify file was created with correct content
        with open(output_file, 'r') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, content)
        
        # Verify success message was printed
        mock_print.assert_called_once_with(f"File saved successfully: {output_file}")
    
    def test_save_to_file_with_existing_file_no_overwrite(self):
        """Test save_to_file with existing file and overwrite=False."""
        output_file = os.path.join(self.temp_dir, "existing.txt")
        
        # Create existing file
        with open(output_file, 'w') as f:
            f.write("existing content")
        
        with self.assertRaises(FileExistsError) as context:
            self.file_handler.save_to_file("new content", output_file, overwrite=False)
        
        self.assertIn("File already exists", str(context.exception))
    
    def test_save_to_file_with_existing_file_with_overwrite(self):
        """Test save_to_file with existing file and overwrite=True."""
        output_file = os.path.join(self.temp_dir, "existing.txt")
        new_content = "new content"
        
        # Create existing file
        with open(output_file, 'w') as f:
            f.write("existing content")
        
        with patch('builtins.print') as mock_print:
            result = self.file_handler.save_to_file(new_content, output_file, overwrite=True)
        
        self.assertTrue(result)
        
        # Verify file was overwritten with new content
        with open(output_file, 'r') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, new_content)
    
    def test_save_to_file_creates_directory(self):
        """Test save_to_file creates parent directories if they don't exist."""
        nested_dir = os.path.join(self.temp_dir, "nested", "dir")
        output_file = os.path.join(nested_dir, "output.txt")
        content = "test content"
        
        with patch('builtins.print') as mock_print:
            result = self.file_handler.save_to_file(content, output_file)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(nested_dir))
        
        # Verify file was created with correct content
        with open(output_file, 'r') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, content)
    
    @patch('os.makedirs')
    def test_save_to_file_directory_creation_fails(self, mock_makedirs):
        """Test save_to_file when directory creation fails."""
        mock_makedirs.side_effect = OSError("Permission denied")
        
        nested_dir = os.path.join(self.temp_dir, "nested", "dir")
        output_file = os.path.join(nested_dir, "output.txt")
        
        with self.assertRaises(PermissionError) as context:
            self.file_handler.save_to_file("content", output_file)
        
        self.assertIn("Cannot create directory", str(context.exception))
    
    @patch('builtins.open', side_effect=IOError("Write failed"))
    def test_save_to_file_write_fails(self, mock_open_func):
        """Test save_to_file when file write fails."""
        output_file = os.path.join(self.temp_dir, "output.txt")
        
        with self.assertRaises(PermissionError) as context:
            self.file_handler.save_to_file("content", output_file)
        
        self.assertIn("Error writing file", str(context.exception))


if __name__ == '__main__':
    unittest.main()