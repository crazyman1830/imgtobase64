"""
Legacy FileHandler adapter for backward compatibility.

This adapter maintains the original FileHandler interface while using
the new refactored service layer underneath.
"""
import os
from pathlib import Path
from typing import List

from ..services.file_handler_service import FileHandlerService
from ...domain.exceptions.file_system import FileNotFoundError, PermissionError
from ...models.models import ImageConverterError


class FileHandlerAdapter:
    """
    Adapter class that maintains the original FileHandler interface.
    
    This class provides backward compatibility by wrapping the new
    FileHandlerService with the original FileHandler API.
    """
    
    def __init__(self):
        """Initialize the adapter with the new service layer."""
        # Create the new service
        self._service = FileHandlerService()
        
        # Maintain the original interface properties
        self.supported_extensions = self._service.supported_extensions
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists and is accessible.
        
        This method maintains the original interface behavior, including
        raising exceptions for error conditions.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file exists and is readable, False otherwise
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If the file exists but is not readable
        """
        try:
            # Use the safe version and convert to exceptions for compatibility
            result = self._service.file_exists_safe(file_path)
            
            if result.is_success:
                if result.value:
                    return True
                else:
                    # Check specific reasons for failure to maintain original behavior
                    if not os.path.exists(file_path):
                        raise FileNotFoundError(f"File not found: {file_path}")
                    elif not os.path.isfile(file_path):
                        raise FileNotFoundError(f"Path is not a file: {file_path}")
                    elif not os.access(file_path, os.R_OK):
                        raise PermissionError(f"Permission denied: Cannot read file {file_path}")
                    else:
                        return False
            else:
                # Convert service errors to legacy exceptions
                error = result.error
                if isinstance(error, ValueError):
                    raise FileNotFoundError(str(error))
                else:
                    raise error
                    
        except (FileNotFoundError, PermissionError):
            # Re-raise expected exceptions
            raise
        except Exception as e:
            # Convert unexpected errors to legacy format
            raise ImageConverterError(f"Error checking file existence: {str(e)}")
    
    def find_image_files(self, directory_path: str) -> List[str]:
        """
        Find all image files in the specified directory and its subdirectories.
        
        This method maintains the original interface behavior, including
        raising exceptions for error conditions.
        
        Args:
            directory_path: Path to the directory to scan
            
        Returns:
            List of paths to image files found in the directory
            
        Raises:
            FileNotFoundError: If the directory doesn't exist
            PermissionError: If the directory is not accessible
        """
        try:
            # Use the safe version and convert to exceptions for compatibility
            result = self._service.find_image_files_safe(directory_path)
            
            if result.is_success:
                return result.value
            else:
                # Convert service errors to legacy exceptions
                error = result.error
                if isinstance(error, (FileNotFoundError, PermissionError)):
                    raise error
                elif isinstance(error, ValueError):
                    raise FileNotFoundError(str(error))
                else:
                    raise PermissionError(f"Error scanning directory {directory_path}: {str(error)}")
                    
        except (FileNotFoundError, PermissionError):
            # Re-raise expected exceptions
            raise
        except Exception as e:
            # Convert unexpected errors to legacy format
            raise PermissionError(f"Error scanning directory {directory_path}: {str(e)}")
    
    def save_to_file(self, content: str, output_path: str, overwrite: bool = False) -> bool:
        """
        Save content to a file with optional overwrite confirmation.
        
        This method maintains the original interface behavior, including
        raising exceptions for error conditions.
        
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
            # Use the new service method
            success = self._service.save_file(content, output_path, overwrite)
            
            if success:
                # Maintain original behavior of printing success message
                print(f"File saved successfully: {output_path}")
            
            return success
            
        except (PermissionError, FileExistsError):
            # Re-raise expected exceptions
            raise
        except Exception as e:
            # Convert unexpected errors to legacy format
            raise ImageConverterError(f"Unexpected error saving file {output_path}: {str(e)}")
    
    # Additional methods that provide access to new functionality
    
    def read_file(self, file_path: str) -> bytes:
        """
        Read the contents of a file.
        
        This method provides access to the new file reading functionality
        while maintaining compatibility.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            File contents as bytes
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If the file cannot be read
        """
        return self._service.read_file(file_path)
    
    def find_files(self, directory: str, pattern: str = "*") -> List[str]:
        """
        Find files in the specified directory matching the given pattern.
        
        This method provides access to the new pattern-based file finding
        functionality while maintaining compatibility.
        
        Args:
            directory: Path to the directory to scan
            pattern: File pattern to match (default: "*" for all files)
            
        Returns:
            List of paths to files found in the directory
            
        Raises:
            FileNotFoundError: If the directory doesn't exist
            PermissionError: If the directory is not accessible
        """
        return self._service.find_files(directory, pattern)
    
    def get_file_size(self, file_path: str) -> int:
        """
        Get the size of a file in bytes.
        
        This method provides access to the new file size functionality
        while maintaining compatibility.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File size in bytes
            
        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        return self._service.get_file_size(file_path)
    
    # Safe versions that return Result objects for new code
    
    def read_file_safe(self, file_path: str):
        """
        Safely read the contents of a file using Result pattern.
        
        This method provides access to the Result-based API for new code
        that wants to avoid exceptions.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            Result containing file contents or error
        """
        return self._service.read_file_safe(file_path)
    
    def save_file_safe(self, content: str, output_path: str, overwrite: bool = False):
        """
        Safely save content to a file using Result pattern.
        
        This method provides access to the Result-based API for new code
        that wants to avoid exceptions.
        
        Args:
            content: Content to write to the file
            output_path: Path where the file should be saved
            overwrite: If True, overwrite existing files without confirmation
            
        Returns:
            Result containing success status or error
        """
        return self._service.save_file_safe(content, output_path, overwrite)
    
    def find_files_safe(self, directory: str, pattern: str = "*"):
        """
        Safely find files in the specified directory using Result pattern.
        
        This method provides access to the Result-based API for new code
        that wants to avoid exceptions.
        
        Args:
            directory: Path to the directory to scan
            pattern: File pattern to match (default: "*" for all files)
            
        Returns:
            Result containing list of file paths or error
        """
        return self._service.find_files_safe(directory, pattern)
    
    def find_image_files_safe(self, directory_path: str):
        """
        Safely find all image files in the specified directory using Result pattern.
        
        This method provides access to the Result-based API for new code
        that wants to avoid exceptions.
        
        Args:
            directory_path: Path to the directory to scan
            
        Returns:
            Result containing list of image file paths or error
        """
        return self._service.find_image_files_safe(directory_path)
    
    def file_exists_safe(self, file_path: str):
        """
        Safely check if a file exists using Result pattern.
        
        This method provides access to the Result-based API for new code
        that wants to avoid exceptions.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            Result containing existence status or error
        """
        return self._service.file_exists_safe(file_path)
    
    def get_file_size_safe(self, file_path: str):
        """
        Safely get the size of a file using Result pattern.
        
        This method provides access to the Result-based API for new code
        that wants to avoid exceptions.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Result containing file size or error
        """
        return self._service.get_file_size_safe(file_path)