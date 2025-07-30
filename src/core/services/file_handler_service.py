"""
File handler service implementation.

This module provides the FileHandlerService class that implements
file system operations with improved error handling using the Result pattern.
"""
import os
import fnmatch
from pathlib import Path
from typing import List

from ..interfaces.file_handler import IFileHandler
from ..base.result import Result
from ...domain.exceptions.base import ImageConverterError
from ...domain.exceptions.file_system import FileNotFoundError, PermissionError, FileSystemError


class FileHandlerService(IFileHandler):
    """
    Service class that handles file system operations with Result pattern.
    
    This service provides file operations with improved error handling,
    using the Result pattern to avoid exceptions for expected error conditions.
    """
    
    def __init__(self):
        """Initialize the file handler service."""
        # Supported image file extensions
        self.supported_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'
        }
    
    def read_file(self, file_path: str) -> bytes:
        """
        Read the contents of a file.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            File contents as bytes
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If the file cannot be read
        """
        try:
            result = self.read_file_safe(file_path)
            if result.is_success:
                return result.value
            else:
                # Convert Result error to exception for interface compatibility
                error = result.error
                if isinstance(error, FileNotFoundError):
                    raise error
                elif isinstance(error, PermissionError):
                    raise error
                else:
                    raise FileSystemError(f"Error reading file: {error}")
        except Exception as e:
            if isinstance(e, (FileNotFoundError, PermissionError, FileSystemError)):
                raise
            else:
                raise FileSystemError(f"Unexpected error reading file {file_path}: {str(e)}")
    
    def read_file_safe(self, file_path: str) -> Result[bytes, Exception]:
        """
        Safely read the contents of a file using Result pattern.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            Result containing file contents or error
        """
        try:
            # Validate input
            if not file_path or not isinstance(file_path, str):
                return Result.failure(ValueError("File path must be a non-empty string"))
            
            # Check if file exists
            if not os.path.exists(file_path):
                return Result.failure(FileNotFoundError(f"File not found: {file_path}"))
            
            # Check if it's a file (not a directory)
            if not os.path.isfile(file_path):
                return Result.failure(FileNotFoundError(f"Path is not a file: {file_path}"))
            
            # Check if file is readable
            if not os.access(file_path, os.R_OK):
                return Result.failure(PermissionError(f"Permission denied: Cannot read file {file_path}"))
            
            # Read file contents
            with open(file_path, 'rb') as f:
                content = f.read()
            
            return Result.success(content)
            
        except OSError as e:
            return Result.failure(FileSystemError(f"OS error reading file {file_path}: {str(e)}"))
        except Exception as e:
            return Result.failure(FileSystemError(f"Unexpected error reading file {file_path}: {str(e)}"))
    
    def save_file(self, content: str, output_path: str, overwrite: bool = False) -> bool:
        """
        Save content to a file.
        
        Args:
            content: Content to write to the file
            output_path: Path where the file should be saved
            overwrite: If True, overwrite existing files without confirmation
            
        Returns:
            True if file was saved successfully, False otherwise
            
        Raises:
            PermissionError: If there are insufficient permissions to write the file
            FileExistsError: If file exists and overwrite is False
        """
        try:
            result = self.save_file_safe(content, output_path, overwrite)
            if result.is_success:
                return result.value
            else:
                # Convert Result error to exception for interface compatibility
                error = result.error
                if isinstance(error, (PermissionError, FileExistsError)):
                    raise error
                else:
                    raise FileSystemError(f"Error saving file: {error}")
        except Exception as e:
            if isinstance(e, (PermissionError, FileExistsError, FileSystemError)):
                raise
            else:
                raise FileSystemError(f"Unexpected error saving file {output_path}: {str(e)}")
    
    def save_file_safe(self, content: str, output_path: str, overwrite: bool = False) -> Result[bool, Exception]:
        """
        Safely save content to a file using Result pattern.
        
        Args:
            content: Content to write to the file
            output_path: Path where the file should be saved
            overwrite: If True, overwrite existing files without confirmation
            
        Returns:
            Result containing success status or error
        """
        try:
            # Validate input
            if not isinstance(content, str):
                return Result.failure(ValueError("Content must be a string"))
            
            if not output_path or not isinstance(output_path, str):
                return Result.failure(ValueError("Output path must be a non-empty string"))
            
            # Check if file already exists
            if os.path.exists(output_path) and not overwrite:
                return Result.failure(FileExistsError(f"File already exists: {output_path}"))
            
            # Create directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except OSError as e:
                    return Result.failure(PermissionError(f"Cannot create directory {output_dir}: {str(e)}"))
            
            # Check if we can write to the directory
            if output_dir and not os.access(output_dir, os.W_OK):
                return Result.failure(PermissionError(f"Permission denied: Cannot write to directory {output_dir}"))
            
            # Write content to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return Result.success(True)
            
        except OSError as e:
            return Result.failure(PermissionError(f"Error writing file {output_path}: {str(e)}"))
        except Exception as e:
            return Result.failure(FileSystemError(f"Unexpected error saving file {output_path}: {str(e)}"))
    
    def find_files(self, directory: str, pattern: str = "*") -> List[str]:
        """
        Find files in the specified directory matching the given pattern.
        
        Args:
            directory: Path to the directory to scan
            pattern: File pattern to match (default: "*" for all files)
            
        Returns:
            List of paths to files found in the directory
            
        Raises:
            FileNotFoundError: If the directory doesn't exist
            PermissionError: If the directory is not accessible
        """
        try:
            result = self.find_files_safe(directory, pattern)
            if result.is_success:
                return result.value
            else:
                # Convert Result error to exception for interface compatibility
                error = result.error
                if isinstance(error, (FileNotFoundError, PermissionError)):
                    raise error
                else:
                    raise FileSystemError(f"Error finding files: {error}")
        except Exception as e:
            if isinstance(e, (FileNotFoundError, PermissionError, FileSystemError)):
                raise
            else:
                raise FileSystemError(f"Unexpected error finding files in {directory}: {str(e)}")
    
    def find_files_safe(self, directory: str, pattern: str = "*") -> Result[List[str], Exception]:
        """
        Safely find files in the specified directory using Result pattern.
        
        Args:
            directory: Path to the directory to scan
            pattern: File pattern to match (default: "*" for all files)
            
        Returns:
            Result containing list of file paths or error
        """
        try:
            # Validate input
            if not directory or not isinstance(directory, str):
                return Result.failure(ValueError("Directory path must be a non-empty string"))
            
            if not pattern or not isinstance(pattern, str):
                return Result.failure(ValueError("Pattern must be a non-empty string"))
            
            # Check if directory exists
            if not os.path.exists(directory):
                return Result.failure(FileNotFoundError(f"Directory not found: {directory}"))
            
            # Check if it's a directory
            if not os.path.isdir(directory):
                return Result.failure(FileNotFoundError(f"Path is not a directory: {directory}"))
            
            # Check if directory is readable
            if not os.access(directory, os.R_OK):
                return Result.failure(PermissionError(f"Permission denied: Cannot read directory {directory}"))
            
            found_files = []
            
            # Walk through directory and subdirectories
            for root, dirs, files in os.walk(directory):
                for file in files:
                    # Apply pattern matching
                    if fnmatch.fnmatch(file, pattern):
                        file_path = os.path.join(root, file)
                        
                        # Verify the file is actually accessible
                        try:
                            if os.access(file_path, os.R_OK):
                                found_files.append(file_path)
                        except (OSError, IOError):
                            # Skip files that can't be accessed
                            continue
            
            # Sort the results for consistent ordering
            return Result.success(sorted(found_files))
            
        except OSError as e:
            return Result.failure(PermissionError(f"Error scanning directory {directory}: {str(e)}"))
        except Exception as e:
            return Result.failure(FileSystemError(f"Unexpected error scanning directory {directory}: {str(e)}"))
    
    def find_image_files(self, directory_path: str) -> List[str]:
        """
        Find all image files in the specified directory and its subdirectories.
        
        Args:
            directory_path: Path to the directory to scan
            
        Returns:
            List of paths to image files found in the directory
            
        Raises:
            FileNotFoundError: If the directory doesn't exist
            PermissionError: If the directory is not accessible
        """
        try:
            result = self.find_image_files_safe(directory_path)
            if result.is_success:
                return result.value
            else:
                # Convert Result error to exception for interface compatibility
                error = result.error
                if isinstance(error, (FileNotFoundError, PermissionError)):
                    raise error
                else:
                    raise FileSystemError(f"Error finding image files: {error}")
        except Exception as e:
            if isinstance(e, (FileNotFoundError, PermissionError, FileSystemError)):
                raise
            else:
                raise FileSystemError(f"Unexpected error finding image files in {directory_path}: {str(e)}")
    
    def find_image_files_safe(self, directory_path: str) -> Result[List[str], Exception]:
        """
        Safely find all image files in the specified directory using Result pattern.
        
        Args:
            directory_path: Path to the directory to scan
            
        Returns:
            Result containing list of image file paths or error
        """
        try:
            # Validate input
            if not directory_path or not isinstance(directory_path, str):
                return Result.failure(ValueError("Directory path must be a non-empty string"))
            
            # Check if directory exists
            if not os.path.exists(directory_path):
                return Result.failure(FileNotFoundError(f"Directory not found: {directory_path}"))
            
            # Check if it's a directory
            if not os.path.isdir(directory_path):
                return Result.failure(FileNotFoundError(f"Path is not a directory: {directory_path}"))
            
            # Check if directory is readable
            if not os.access(directory_path, os.R_OK):
                return Result.failure(PermissionError(f"Permission denied: Cannot read directory {directory_path}"))
            
            image_files = []
            
            # Recursively walk through directory and subdirectories
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_extension = Path(file_path).suffix.lower()
                    
                    # Check if file has supported image extension
                    if file_extension in self.supported_extensions:
                        # Verify the file is actually accessible
                        try:
                            if os.access(file_path, os.R_OK):
                                image_files.append(file_path)
                        except (OSError, IOError):
                            # Skip files that can't be accessed
                            continue
            
            # Sort the results for consistent ordering
            return Result.success(sorted(image_files))
            
        except OSError as e:
            return Result.failure(PermissionError(f"Error scanning directory {directory_path}: {str(e)}"))
        except Exception as e:
            return Result.failure(FileSystemError(f"Unexpected error scanning directory {directory_path}: {str(e)}"))
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists and is accessible.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file exists and is readable, False otherwise
        """
        try:
            result = self.file_exists_safe(file_path)
            return result.unwrap_or(False)
        except Exception:
            return False
    
    def file_exists_safe(self, file_path: str) -> Result[bool, Exception]:
        """
        Safely check if a file exists using Result pattern.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            Result containing existence status or error
        """
        try:
            # Validate input
            if not file_path or not isinstance(file_path, str):
                return Result.failure(ValueError("File path must be a non-empty string"))
            
            # Check existence and accessibility
            if not os.path.exists(file_path):
                return Result.success(False)
            
            if not os.path.isfile(file_path):
                return Result.success(False)
            
            if not os.access(file_path, os.R_OK):
                return Result.success(False)
            
            return Result.success(True)
            
        except Exception as e:
            return Result.failure(FileSystemError(f"Error checking file existence {file_path}: {str(e)}"))
    
    def get_file_size(self, file_path: str) -> int:
        """
        Get the size of a file in bytes.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File size in bytes
            
        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        try:
            result = self.get_file_size_safe(file_path)
            if result.is_success:
                return result.value
            else:
                # Convert Result error to exception for interface compatibility
                error = result.error
                if isinstance(error, FileNotFoundError):
                    raise error
                else:
                    raise FileSystemError(f"Error getting file size: {error}")
        except Exception as e:
            if isinstance(e, (FileNotFoundError, FileSystemError)):
                raise
            else:
                raise FileSystemError(f"Unexpected error getting file size for {file_path}: {str(e)}")
    
    def get_file_size_safe(self, file_path: str) -> Result[int, Exception]:
        """
        Safely get the size of a file using Result pattern.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Result containing file size or error
        """
        try:
            # Validate input
            if not file_path or not isinstance(file_path, str):
                return Result.failure(ValueError("File path must be a non-empty string"))
            
            # Check if file exists
            if not os.path.exists(file_path):
                return Result.failure(FileNotFoundError(f"File not found: {file_path}"))
            
            # Check if it's a file
            if not os.path.isfile(file_path):
                return Result.failure(FileNotFoundError(f"Path is not a file: {file_path}"))
            
            # Get file size
            size = os.path.getsize(file_path)
            return Result.success(size)
            
        except OSError as e:
            return Result.failure(FileSystemError(f"OS error getting file size for {file_path}: {str(e)}"))
        except Exception as e:
            return Result.failure(FileSystemError(f"Unexpected error getting file size for {file_path}: {str(e)}"))