"""
Path handling utilities.

This module provides common path manipulation and validation functions
that are used across multiple modules in the application.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from ...domain.exceptions import FileSystemError, ValidationError


class PathUtils:
    """Utility class for path handling operations."""

    # Common image file extensions
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

    # MIME type mapping for image formats
    MIME_TYPE_MAPPING = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
    }

    @staticmethod
    def normalize_path(path: Union[str, Path]) -> Path:
        """
        Normalize a path to a Path object with resolved absolute path.

        Args:
            path: Path as string or Path object

        Returns:
            Normalized Path object

        Raises:
            ValidationError: If path is invalid
        """
        if not path:
            raise ValidationError("Path cannot be empty")

        try:
            return Path(path).resolve()
        except (OSError, ValueError) as e:
            raise ValidationError(f"Invalid path '{path}': {e}")

    @staticmethod
    def get_file_extension(file_path: Union[str, Path]) -> str:
        """
        Get the file extension in lowercase.

        Args:
            file_path: Path to the file

        Returns:
            File extension in lowercase (e.g., '.jpg')
        """
        return Path(file_path).suffix.lower()

    @staticmethod
    def get_filename_without_extension(file_path: Union[str, Path]) -> str:
        """
        Get filename without extension.

        Args:
            file_path: Path to the file

        Returns:
            Filename without extension
        """
        return Path(file_path).stem

    @staticmethod
    def get_parent_directory(file_path: Union[str, Path]) -> Path:
        """
        Get the parent directory of a file path.

        Args:
            file_path: Path to the file

        Returns:
            Parent directory as Path object
        """
        return Path(file_path).parent

    @staticmethod
    def ensure_directory_exists(
        directory_path: Union[str, Path], create_if_missing: bool = True
    ) -> Path:
        """
        Ensure a directory exists, optionally creating it.

        Args:
            directory_path: Path to the directory
            create_if_missing: Whether to create the directory if it doesn't exist

        Returns:
            Directory path as Path object

        Raises:
            FileSystemError: If directory operations fail
        """
        dir_path = PathUtils.normalize_path(directory_path)

        if dir_path.exists():
            if not dir_path.is_dir():
                raise FileSystemError(f"Path exists but is not a directory: {dir_path}")
            return dir_path

        if create_if_missing:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                return dir_path
            except OSError as e:
                raise FileSystemError(f"Cannot create directory {dir_path}: {e}")
        else:
            raise FileSystemError(f"Directory does not exist: {dir_path}")

    @staticmethod
    def is_image_file(file_path: Union[str, Path]) -> bool:
        """
        Check if a file has an image extension.

        Args:
            file_path: Path to the file

        Returns:
            True if file has image extension, False otherwise
        """
        extension = PathUtils.get_file_extension(file_path)
        return extension in PathUtils.IMAGE_EXTENSIONS

    @staticmethod
    def get_mime_type(file_path: Union[str, Path]) -> Optional[str]:
        """
        Get MIME type for an image file.

        Args:
            file_path: Path to the image file

        Returns:
            MIME type string or None if not an image file
        """
        extension = PathUtils.get_file_extension(file_path)
        return PathUtils.MIME_TYPE_MAPPING.get(extension)

    @staticmethod
    def validate_file_exists(file_path: Union[str, Path]) -> Path:
        """
        Validate that a file exists and is accessible.

        Args:
            file_path: Path to the file

        Returns:
            Normalized file path

        Raises:
            FileSystemError: If file doesn't exist or is not accessible
        """
        normalized_path = PathUtils.normalize_path(file_path)

        if not normalized_path.exists():
            raise FileSystemError(f"File not found: {normalized_path}")

        if not normalized_path.is_file():
            raise FileSystemError(f"Path is not a file: {normalized_path}")

        if not os.access(normalized_path, os.R_OK):
            raise FileSystemError(f"File is not readable: {normalized_path}")

        return normalized_path

    @staticmethod
    def validate_directory_exists(directory_path: Union[str, Path]) -> Path:
        """
        Validate that a directory exists and is accessible.

        Args:
            directory_path: Path to the directory

        Returns:
            Normalized directory path

        Raises:
            FileSystemError: If directory doesn't exist or is not accessible
        """
        normalized_path = PathUtils.normalize_path(directory_path)

        if not normalized_path.exists():
            raise FileSystemError(f"Directory not found: {normalized_path}")

        if not normalized_path.is_dir():
            raise FileSystemError(f"Path is not a directory: {normalized_path}")

        if not os.access(normalized_path, os.R_OK):
            raise FileSystemError(f"Directory is not readable: {normalized_path}")

        return normalized_path

    @staticmethod
    def find_files_by_extension(
        directory_path: Union[str, Path],
        extensions: Optional[set] = None,
        recursive: bool = True,
    ) -> List[Path]:
        """
        Find files with specific extensions in a directory.

        Args:
            directory_path: Directory to search in
            extensions: Set of extensions to search for (default: image extensions)
            recursive: Whether to search recursively in subdirectories

        Returns:
            List of file paths matching the criteria

        Raises:
            FileSystemError: If directory operations fail
        """
        if extensions is None:
            extensions = PathUtils.IMAGE_EXTENSIONS

        directory = PathUtils.validate_directory_exists(directory_path)
        found_files = []

        try:
            if recursive:
                pattern = "**/*"
                files = directory.glob(pattern)
            else:
                files = directory.iterdir()

            for file_path in files:
                if file_path.is_file():
                    extension = file_path.suffix.lower()
                    if extension in extensions:
                        # Verify file is accessible
                        if os.access(file_path, os.R_OK):
                            found_files.append(file_path)

        except OSError as e:
            raise FileSystemError(f"Error scanning directory {directory}: {e}")

        return sorted(found_files)

    @staticmethod
    def get_file_info(file_path: Union[str, Path]) -> Dict[str, any]:
        """
        Get comprehensive information about a file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary containing file information
        """
        try:
            path = PathUtils.normalize_path(file_path)
            stat = path.stat()

            return {
                "path": str(path),
                "name": path.name,
                "stem": path.stem,
                "extension": path.suffix.lower(),
                "parent": str(path.parent),
                "size": stat.st_size,
                "exists": True,
                "is_file": path.is_file(),
                "is_dir": path.is_dir(),
                "readable": os.access(path, os.R_OK),
                "writable": os.access(path, os.W_OK),
                "is_image": PathUtils.is_image_file(path),
                "mime_type": PathUtils.get_mime_type(path),
            }
        except (OSError, IOError, ValidationError):
            return {
                "path": str(file_path),
                "name": Path(file_path).name if file_path else "",
                "stem": Path(file_path).stem if file_path else "",
                "extension": Path(file_path).suffix.lower() if file_path else "",
                "parent": str(Path(file_path).parent) if file_path else "",
                "size": 0,
                "exists": False,
                "is_file": False,
                "is_dir": False,
                "readable": False,
                "writable": False,
                "is_image": False,
                "mime_type": None,
            }

    @staticmethod
    def create_safe_filename(filename: str, max_length: int = 255) -> str:
        """
        Create a safe filename by removing/replacing invalid characters.

        Args:
            filename: Original filename
            max_length: Maximum length for the filename

        Returns:
            Safe filename string
        """
        # Characters that are invalid in filenames on most systems
        invalid_chars = '<>:"/\\|?*'

        # Replace invalid characters with underscores
        safe_name = "".join("_" if c in invalid_chars else c for c in filename)

        # Remove leading/trailing whitespace and dots
        safe_name = safe_name.strip(" .")

        # Ensure filename is not empty
        if not safe_name:
            safe_name = "unnamed_file"

        # Truncate if too long
        if len(safe_name) > max_length:
            name_part, ext_part = os.path.splitext(safe_name)
            available_length = max_length - len(ext_part)
            if available_length > 0:
                safe_name = name_part[:available_length] + ext_part
            else:
                safe_name = safe_name[:max_length]

        return safe_name

    @staticmethod
    def generate_unique_filename(
        directory: Union[str, Path], base_name: str, extension: str = ""
    ) -> Path:
        """
        Generate a unique filename in a directory by adding numbers if needed.

        Args:
            directory: Directory where the file will be created
            base_name: Base name for the file
            extension: File extension (with or without leading dot)

        Returns:
            Unique file path
        """
        directory = PathUtils.normalize_path(directory)

        # Ensure extension starts with dot
        if extension and not extension.startswith("."):
            extension = "." + extension

        # Create initial filename
        filename = base_name + extension
        file_path = directory / filename

        # If file doesn't exist, return it
        if not file_path.exists():
            return file_path

        # Generate numbered variants
        counter = 1
        while True:
            filename = f"{base_name}_{counter}{extension}"
            file_path = directory / filename

            if not file_path.exists():
                return file_path

            counter += 1

            # Prevent infinite loop
            if counter > 9999:
                raise FileSystemError(f"Cannot generate unique filename in {directory}")
