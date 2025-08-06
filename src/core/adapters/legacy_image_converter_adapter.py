"""
Adapter for legacy ImageConverter to implement IImageConverter interface.

This adapter wraps the legacy ImageConverter class to make it compatible
with the new IImageConverter interface.
"""
import os
import base64
import time
from typing import Optional, Set
from PIL import Image
from ..interfaces.image_converter import IImageConverter
from ...models.models import ConversionResult
from ...models.processing_options import ProcessingOptions
from ...domain.exceptions.validation import ValidationError
from ...domain.exceptions.file_system import FileNotFoundError
from ...domain.exceptions.processing import ProcessingError


class LegacyImageConverterAdapter(IImageConverter):
    """
    Adapter that wraps the legacy ImageConverter to implement IImageConverter.
    
    This adapter provides compatibility between the legacy ImageConverter
    and the new service layer architecture by implementing a simplified
    version of the conversion logic.
    """
    
    def __init__(self):
        """Initialize the adapter with supported formats."""
        # Supported image file extensions
        self.supported_formats: Set[str] = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'
        }
        
        # MIME type mapping for supported formats
        self.mime_type_mapping = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }
    
    def convert_to_base64(
        self, 
        file_path: str, 
        options: Optional[ProcessingOptions] = None
    ) -> ConversionResult:
        """
        Convert an image file to base64 format.
        
        Args:
            file_path: Path to the image file to convert
            options: Optional processing options (basic support)
            
        Returns:
            ConversionResult object containing conversion details and result
        """
        start_time = time.time()
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Validate format
            if not self.validate_format(file_path):
                raise ValidationError(f"Unsupported file format: {file_path}")
            
            # Read and convert the image
            with open(file_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Get image info
            try:
                with Image.open(file_path) as img:
                    image_format = img.format
                    image_size = img.size
            except Exception:
                # Fallback to extension-based format detection
                ext = os.path.splitext(file_path)[1].lower()
                format_map = {'.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG', 
                             '.gif': 'GIF', '.bmp': 'BMP', '.webp': 'WEBP'}
                image_format = format_map.get(ext, 'Unknown')
                image_size = (0, 0)
            
            # Convert to base64
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
            # Get MIME type
            mime_type = self.get_mime_type(file_path)
            
            # Create data URI
            data_uri = f"data:{mime_type};base64,{base64_data}"
            
            # Create result
            result = ConversionResult(
                file_path=file_path,
                success=True,
                base64_data=base64_data,
                data_uri=data_uri,
                format=image_format,
                size=image_size,
                file_size=len(image_data),
                mime_type=mime_type
            )
            
            # Set processing time
            result.processing_time = time.time() - start_time
            
            return result
            
        except (FileNotFoundError, ValidationError):
            # Re-raise known errors
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise ProcessingError(f"Image conversion failed: {str(e)}")
    
    def validate_format(self, file_path: str) -> bool:
        """
        Validate if the given file has a supported image format.
        
        Args:
            file_path: Path to the image file to validate
            
        Returns:
            True if the file format is supported, False otherwise
        """
        try:
            # Get file extension
            _, ext = os.path.splitext(file_path.lower())
            return ext in self.supported_formats
        except Exception:
            return False
    
    def get_mime_type(self, file_path: str) -> str:
        """
        Get the MIME type for the given image file.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            MIME type string for the file
            
        Raises:
            ValidationError: If the file format is not supported
        """
        try:
            # Get file extension
            _, ext = os.path.splitext(file_path.lower())
            
            if ext not in self.supported_formats:
                raise ValidationError(f"Unsupported file format: {ext}")
            
            return self.mime_type_mapping.get(ext, 'application/octet-stream')
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Unable to determine MIME type: {str(e)}")
    
    def get_supported_formats(self) -> Set[str]:
        """
        Get the set of supported image file extensions.
        
        Returns:
            Set of supported file extensions
        """
        return self.supported_formats.copy()