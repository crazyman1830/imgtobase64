"""
File handling utilities for the image base64 converter.
"""
import os
from pathlib import Path
from typing import List

from models import (
    ImageConverterError,
    FileNotFoundError,
    PermissionError
)


class FileHandler:
    """
    Handles file system operations for the image converter.
    
    Provides functionality for file existence checking, directory scanning,
    and file saving operations.
    """
    
    def __init__(self):
        """Initialize the FileHandler."""
        # Supported image file extensions
        self.supported_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'
        }
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists and is accessible.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file exists and is readable, False otherwise
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If the file exists but is not readable
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Path is not a file: {file_path}")
        
        # Check if file is readable
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"Permission denied: Cannot read file {file_path}")
        
        return True
    
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
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        if not os.path.isdir(directory_path):
            raise FileNotFoundError(f"Path is not a directory: {directory_path}")
        
        # Check if directory is readable
        if not os.access(directory_path, os.R_OK):
            raise PermissionError(f"Permission denied: Cannot read directory {directory_path}")
        
        image_files = []
        
        try:
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
        
        except (OSError, IOError) as e:
            raise PermissionError(f"Error scanning directory {directory_path}: {str(e)}")
        
        # Sort the results for consistent ordering
        return sorted(image_files)
    
    def save_to_file(self, content: str, output_path: str, overwrite: bool = False) -> bool:
        """
        Save content to a file with optional overwrite confirmation.
        
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
        # Check if file already exists
        if os.path.exists(output_path) and not overwrite:
            raise FileExistsError(f"File already exists: {output_path}")
        
        # Create directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                raise PermissionError(f"Cannot create directory {output_dir}: {str(e)}")
        
        # Check if we can write to the directory
        if output_dir and not os.access(output_dir, os.W_OK):
            raise PermissionError(f"Permission denied: Cannot write to directory {output_dir}")
        
        try:
            # Write content to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"File saved successfully: {output_path}")
            return True
            
        except (OSError, IOError) as e:
            raise PermissionError(f"Error writing file {output_path}: {str(e)}")
        except Exception as e:
            raise ImageConverterError(f"Unexpected error saving file {output_path}: {str(e)}")