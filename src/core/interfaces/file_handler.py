"""
File handler interface definition.

This module defines the IFileHandler protocol that establishes the contract
for file system operations.
"""

from typing import Protocol, List


class IFileHandler(Protocol):
    """
    Protocol defining the interface for file system operations.
    
    This interface establishes the contract for file existence checking,
    directory scanning, and file saving operations.
    """
    
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
        ...
    
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
        ...
    
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
        ...
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists and is accessible.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file exists and is readable, False otherwise
        """
        ...
    
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
        ...