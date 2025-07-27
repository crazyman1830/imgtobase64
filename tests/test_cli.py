"""
Unit tests for the CLI module.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import argparse
import sys
import io
from pathlib import Path

from src.cli import CLI
from src.models import ConversionResult, ImageConverterError, FileNotFoundError


class TestCLI(unittest.TestCase):
    """Test cases for the CLI class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_converter = Mock()
        self.mock_file_handler = Mock()
        self.cli = CLI(converter=self.mock_converter, file_handler=self.mock_file_handler)
    
    def test_init_with_dependencies(self):
        """Test CLI initialization with provided dependencies."""
        cli = CLI(converter=self.mock_converter, file_handler=self.mock_file_handler)
        self.assertEqual(cli.converter, self.mock_converter)
        self.assertEqual(cli.file_handler, self.mock_file_handler)
    
    def test_init_with_default_dependencies(self):
        """Test CLI initialization with default dependencies."""
        cli = CLI()
        self.assertIsNotNone(cli.converter)
        self.assertIsNotNone(cli.file_handler)
    
    @patch('sys.argv', ['prog', 'test.png'])
    def test_parse_arguments_single_file(self):
        """Test parsing arguments for single file processing."""
        args = self.cli.parse_arguments()
        self.assertEqual(args.input_path, 'test.png')
        self.assertIsNone(args.output_path)
        self.assertFalse(args.force)
        self.assertFalse(args.verbose)
    
    @patch('sys.argv', ['prog', 'test.png', '-o', 'output.txt', '-f', '-v'])
    def test_parse_arguments_with_all_options(self):
        """Test parsing arguments with all options."""
        args = self.cli.parse_arguments()
        self.assertEqual(args.input_path, 'test.png')
        self.assertEqual(args.output_path, 'output.txt')
        self.assertTrue(args.force)
        self.assertTrue(args.verbose)
    
    @patch('sys.argv', ['prog', '/path/to/images/', '--output', 'batch.txt'])
    def test_parse_arguments_directory_processing(self):
        """Test parsing arguments for directory processing."""
        args = self.cli.parse_arguments()
        self.assertEqual(args.input_path, '/path/to/images/')
        self.assertEqual(args.output_path, 'batch.txt')
    
    @patch('sys.argv', ['prog', '--help'])
    def test_parse_arguments_help(self):
        """Test that help argument exits the program."""
        with self.assertRaises(SystemExit):
            self.cli.parse_arguments()
    
    @patch('sys.argv', ['prog', '--version'])
    def test_parse_arguments_version(self):
        """Test that version argument exits the program."""
        with self.assertRaises(SystemExit):
            self.cli.parse_arguments()


class TestCLISingleFileProcessing(unittest.TestCase):
    """Test cases for single file processing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_converter = Mock()
        self.mock_file_handler = Mock()
        self.cli = CLI(converter=self.mock_converter, file_handler=self.mock_file_handler)
    
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_process_single_file_success_stdout(self, mock_stdout):
        """Test successful single file processing with stdout output."""
        # Setup mock result
        result = ConversionResult(
            file_path="test.png",
            success=True,
            base64_data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
            data_uri="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
            file_size=100,
            mime_type="image/png"
        )
        self.mock_converter.convert_to_base64.return_value = result
        
        # Execute
        self.cli.process_single_file("test.png")
        
        # Verify
        self.mock_converter.convert_to_base64.assert_called_once_with("test.png")
        output = mock_stdout.getvalue()
        self.assertIn("data:image/png;base64,", output)
    
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_process_single_file_success_verbose(self, mock_stdout):
        """Test successful single file processing with verbose output."""
        # Setup mock result
        result = ConversionResult(
            file_path="test.png",
            success=True,
            base64_data="test_base64_data",
            data_uri="data:image/png;base64,test_base64_data",
            file_size=1024,
            mime_type="image/png"
        )
        self.mock_converter.convert_to_base64.return_value = result
        
        # Execute
        self.cli.process_single_file("test.png", verbose=True)
        
        # Verify
        output = mock_stdout.getvalue()
        self.assertIn("Processing file: test.png", output)
        self.assertIn("✓ Conversion successful", output)
        self.assertIn("File size: 1,024 bytes", output)
        self.assertIn("MIME type: image/png", output)
    
    def test_process_single_file_success_save_to_file(self):
        """Test successful single file processing with file output."""
        # Setup mock result
        result = ConversionResult(
            file_path="test.png",
            success=True,
            data_uri="data:image/png;base64,test_data"
        )
        self.mock_converter.convert_to_base64.return_value = result
        
        # Execute
        self.cli.process_single_file("test.png", output_path="output.txt")
        
        # Verify
        self.mock_file_handler.save_to_file.assert_called_once_with(
            "data:image/png;base64,test_data",
            "output.txt",
            overwrite=False
        )
    
    def test_process_single_file_success_force_overwrite(self):
        """Test single file processing with force overwrite."""
        # Setup mock result
        result = ConversionResult(
            file_path="test.png",
            success=True,
            data_uri="data:image/png;base64,test_data"
        )
        self.mock_converter.convert_to_base64.return_value = result
        
        # Execute
        self.cli.process_single_file("test.png", output_path="output.txt", force_overwrite=True)
        
        # Verify
        self.mock_file_handler.save_to_file.assert_called_once_with(
            "data:image/png;base64,test_data",
            "output.txt",
            overwrite=True
        )
    
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_process_single_file_conversion_failure(self, mock_stderr):
        """Test single file processing with conversion failure."""
        # Setup mock result
        result = ConversionResult(
            file_path="test.png",
            success=False,
            error_message="Unsupported format"
        )
        self.mock_converter.convert_to_base64.return_value = result
        
        # Execute and verify SystemExit
        with self.assertRaises(SystemExit) as cm:
            self.cli.process_single_file("test.png")
        
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error: Unsupported format", mock_stderr.getvalue())
    
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_process_single_file_save_file_exists_error(self, mock_stdout):
        """Test single file processing with file exists error."""
        # Setup mock result
        result = ConversionResult(
            file_path="test.png",
            success=True,
            data_uri="data:image/png;base64,test_data"
        )
        self.mock_converter.convert_to_base64.return_value = result
        self.mock_file_handler.save_to_file.side_effect = FileExistsError("File already exists")
        
        # Execute and verify SystemExit
        with self.assertRaises(SystemExit) as cm:
            self.cli.process_single_file("test.png", output_path="output.txt")
        
        self.assertEqual(cm.exception.code, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Error: Output file already exists", output)
        self.assertIn("Use -f/--force to overwrite", output)


class TestCLIBatchProcessing(unittest.TestCase):
    """Test cases for batch processing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_converter = Mock()
        self.mock_file_handler = Mock()
        self.cli = CLI(converter=self.mock_converter, file_handler=self.mock_file_handler)
    
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_process_directory_success(self, mock_stdout):
        """Test successful directory processing."""
        # Setup mock file list
        self.mock_file_handler.find_image_files.return_value = ["image1.png", "image2.jpg"]
        
        # Setup mock conversion results
        result1 = ConversionResult(
            file_path="image1.png",
            success=True,
            data_uri="data:image/png;base64,data1",
            file_size=100,
            mime_type="image/png",
            base64_data="data1"
        )
        result2 = ConversionResult(
            file_path="image2.jpg",
            success=True,
            data_uri="data:image/jpeg;base64,data2",
            file_size=200,
            mime_type="image/jpeg",
            base64_data="data2"
        )
        self.mock_converter.convert_to_base64.side_effect = [result1, result2]
        
        # Execute
        self.cli.process_directory("/test/dir")
        
        # Verify
        self.mock_file_handler.find_image_files.assert_called_once_with("/test/dir")
        self.assertEqual(self.mock_converter.convert_to_base64.call_count, 2)
        
        output = mock_stdout.getvalue()
        self.assertIn("Batch processing completed:", output)
        self.assertIn("Successful: 2", output)
        self.assertIn("Failed: 0", output)
        self.assertIn("File: image1.png", output)
        self.assertIn("File: image2.jpg", output)
    
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_process_directory_no_files(self, mock_stdout):
        """Test directory processing with no image files found."""
        # Setup mock empty file list
        self.mock_file_handler.find_image_files.return_value = []
        
        # Execute
        self.cli.process_directory("/test/dir")
        
        # Verify
        output = mock_stdout.getvalue()
        self.assertIn("No image files found in directory", output)
    
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_process_directory_mixed_results(self, mock_stderr, mock_stdout):
        """Test directory processing with mixed success/failure results."""
        # Setup mock file list
        self.mock_file_handler.find_image_files.return_value = ["good.png", "bad.png"]
        
        # Setup mock conversion results
        result1 = ConversionResult(
            file_path="good.png",
            success=True,
            data_uri="data:image/png;base64,data1",
            file_size=100,
            mime_type="image/png",
            base64_data="data1"
        )
        result2 = ConversionResult(
            file_path="bad.png",
            success=False,
            error_message="Corrupted file"
        )
        self.mock_converter.convert_to_base64.side_effect = [result1, result2]
        
        # Execute and verify SystemExit due to failures
        with self.assertRaises(SystemExit) as cm:
            self.cli.process_directory("/test/dir")
        
        self.assertEqual(cm.exception.code, 1)
        
        # Verify output
        stdout_output = mock_stdout.getvalue()
        stderr_output = mock_stderr.getvalue()
        
        self.assertIn("Successful: 1", stdout_output)
        self.assertIn("Failed: 1", stdout_output)
        self.assertIn("Error processing bad.png: Corrupted file", stderr_output)
    
    def test_process_directory_save_to_file(self):
        """Test directory processing with file output."""
        # Setup mock file list and results
        self.mock_file_handler.find_image_files.return_value = ["test.png"]
        result = ConversionResult(
            file_path="test.png",
            success=True,
            data_uri="data:image/png;base64,data1",
            file_size=100,
            mime_type="image/png",
            base64_data="data1"
        )
        self.mock_converter.convert_to_base64.return_value = result
        
        # Execute
        self.cli.process_directory("/test/dir", output_path="batch.txt")
        
        # Verify save_to_file was called
        self.mock_file_handler.save_to_file.assert_called_once()
        args = self.mock_file_handler.save_to_file.call_args
        self.assertEqual(args[0][1], "batch.txt")  # output_path
        self.assertEqual(args[1]['overwrite'], False)  # overwrite parameter


class TestCLIMainRun(unittest.TestCase):
    """Test cases for the main run functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_converter = Mock()
        self.mock_file_handler = Mock()
        self.cli = CLI(converter=self.mock_converter, file_handler=self.mock_file_handler)
    
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('sys.argv', ['prog', 'test.png'])
    def test_run_single_file(self, mock_isfile, mock_exists):
        """Test run method with single file input."""
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        # Mock the process_single_file method
        with patch.object(self.cli, 'process_single_file') as mock_process:
            self.cli.run()
            mock_process.assert_called_once_with(
                file_path='test.png',
                output_path=None,
                force_overwrite=False,
                verbose=False
            )
    
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('os.path.isdir')
    @patch('sys.argv', ['prog', '/test/dir', '-v'])
    def test_run_directory(self, mock_isdir, mock_isfile, mock_exists):
        """Test run method with directory input."""
        mock_exists.return_value = True
        mock_isfile.return_value = False
        mock_isdir.return_value = True
        
        # Mock the process_directory method
        with patch.object(self.cli, 'process_directory') as mock_process:
            self.cli.run()
            mock_process.assert_called_once_with(
                directory_path='/test/dir',
                output_path=None,
                force_overwrite=False,
                verbose=True
            )
    
    @patch('os.path.exists')
    @patch('sys.argv', ['prog', 'nonexistent.png'])
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_run_nonexistent_input(self, mock_stderr, mock_exists):
        """Test run method with nonexistent input path."""
        mock_exists.return_value = False
        
        with self.assertRaises(SystemExit) as cm:
            self.cli.run()
        
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error: Input path does not exist", mock_stderr.getvalue())
    
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('os.path.isdir')
    @patch('sys.argv', ['prog', '/dev/null'])
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_run_invalid_input_type(self, mock_stderr, mock_isdir, mock_isfile, mock_exists):
        """Test run method with input that is neither file nor directory."""
        mock_exists.return_value = True
        mock_isfile.return_value = False
        mock_isdir.return_value = False
        
        with self.assertRaises(SystemExit) as cm:
            self.cli.run()
        
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error: Input path is neither a file nor a directory", mock_stderr.getvalue())


if __name__ == '__main__':
    unittest.main()