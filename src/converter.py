"""
Image to base64 converter module.
"""
import base64
import os
from pathlib import Path
from typing import Dict, Set

from models import (
    ConversionResult,
    ImageConverterError,
    UnsupportedFormatError,
    FileNotFoundError,
    PermissionError,
    CorruptedFileError
)


class ImageConverter:
    """
    Handles conversion of image files to base64 format.
    
    Supports PNG, JPG, JPEG, GIF, BMP, and WEBP image formats.
    """
    
    def __init__(self):
        """Initialize the ImageConverter with supported formats and MIME type mappings."""
        # Supported image file extensions
        self.supported_formats: Set[str] = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'
        }
        
        # MIME type mapping for supported formats
        self.mime_type_mapping: Dict[str, str] = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }    

    def is_supported_format(self, file_path: str) -> bool:
        """
        Check if the given file has a supported image format.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            True if the file format is supported, False otherwise
        """
        file_extension = Path(file_path).suffix.lower()
        return file_extension in self.supported_formats
    
    def get_mime_type(self, file_path: str) -> str:
        """
        Get the MIME type for the given image file.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            MIME type string for the file
            
        Raises:
            UnsupportedFormatError: If the file format is not supported
        """
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension not in self.supported_formats:
            supported_list = ', '.join(sorted(self.supported_formats))
            raise UnsupportedFormatError(
                f"Unsupported file format '{file_extension}'. "
                f"Supported formats: {supported_list}"
            )
        
        return self.mime_type_mapping[file_extension]    

    def convert_to_base64(self, file_path: str) -> ConversionResult:
        """
        Convert an image file to base64 format.
        
        Args:
            file_path: Path to the image file to convert
            
        Returns:
            ConversionResult object containing conversion details
        """
        result = ConversionResult(file_path=file_path, success=False)
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                result.error_message = f"File not found: {file_path}"
                return result
            
            # Check if it's a file (not a directory)
            if not os.path.isfile(file_path):
                result.error_message = f"Path is not a file: {file_path}"
                return result
            
            # Check if format is supported
            if not self.is_supported_format(file_path):
                file_extension = Path(file_path).suffix.lower()
                supported_list = ', '.join(sorted(self.supported_formats))
                result.error_message = (
                    f"Unsupported file format '{file_extension}'. "
                    f"Supported formats: {supported_list}"
                )
                return result
            
            # Get MIME type
            try:
                mime_type = self.get_mime_type(file_path)
                result.mime_type = mime_type
            except UnsupportedFormatError as e:
                result.error_message = str(e)
                return result
            
            # Read file and get size
            try:
                with open(file_path, 'rb') as image_file:
                    image_data = image_file.read()
                    result.file_size = len(image_data)
                    
                    # Convert to base64
                    base64_encoded = base64.b64encode(image_data).decode('utf-8')
                    result.base64_data = base64_encoded
                    
                    # Create data URI
                    result.data_uri = f"data:{mime_type};base64,{base64_encoded}"
                    
                    result.success = True
                    
            except PermissionError:
                result.error_message = f"Permission denied: Cannot read file {file_path}"
            except IOError as e:
                result.error_message = f"Error reading file {file_path}: {str(e)}"
            except Exception as e:
                result.error_message = f"Unexpected error processing {file_path}: {str(e)}"
                
        except Exception as e:
            result.error_message = f"Unexpected error: {str(e)}"
        
        return result
    
    def base64_to_image(self, base64_data: str, output_format: str = 'PNG'):
        """
        Convert base64 data to image.
        
        Args:
            base64_data: Base64 encoded image data
            output_format: Output image format (PNG, JPEG, etc.)
            
        Returns:
            ConversionResult object with image data
        """
        from PIL import Image
        from io import BytesIO
        
        result = ConversionResult(file_path="base64_input", success=False)
        
        try:
            # Clean base64 data (remove data URI prefix if present)
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            # Decode base64
            image_data = base64.b64decode(base64_data)
            
            # Create PIL Image
            image = Image.open(BytesIO(image_data))
            
            # Store image info
            result.image = image
            result.format = output_format
            result.size = image.size
            result.file_size = len(image_data)
            result.success = True
            
            return result
            
        except Exception as e:
            result.error_message = f"Error converting base64 to image: {str(e)}"
            return result
    
    def validate_base64_image(self, base64_data: str) -> bool:
        """
        Validate if base64 data represents a valid image.
        
        Args:
            base64_data: Base64 encoded data to validate
            
        Returns:
            True if valid image data, False otherwise
        """
        try:
            from PIL import Image
            from io import BytesIO
            
            # Clean base64 data
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            # Try to decode and open as image
            image_data = base64.b64decode(base64_data)
            image = Image.open(BytesIO(image_data))
            
            # Try to verify the image
            image.verify()
            return True
            
        except Exception:
            return False