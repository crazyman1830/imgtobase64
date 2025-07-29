"""
Advanced image processing module for the image base64 converter.

This module provides advanced image processing capabilities including:
- Image resizing with aspect ratio preservation
- Image compression and quality adjustment
- Format conversion between PNG, JPEG, WEBP
- Image rotation and flipping operations
- Memory-optimized processing for large files
"""
import io
import math
import gc
from typing import Tuple, Optional, Union, List
from PIL import Image, ImageOps
from PIL.Image import Resampling

from ..models.models import ConversionError
from ..models.processing_options import ProcessingOptions
from .memory_optimizer import (
    get_memory_pool, get_memory_monitor, get_gc_optimizer,
    StreamingImageProcessor, optimized_memory_context
)


class ImageProcessor:
    """
    Advanced image processor for handling various image operations.
    
    This class provides methods for resizing, compressing, format conversion,
    and basic editing operations on PIL Image objects.
    """
    
    def __init__(self, enable_memory_optimization: bool = True):
        """Initialize the ImageProcessor with default settings."""
        # Default resampling algorithm for high-quality resizing
        self.default_resampling = Resampling.LANCZOS
        
        # Supported formats for conversion
        self.supported_formats = {'PNG', 'JPEG', 'WEBP', 'GIF', 'BMP'}
        
        # Format-specific default settings
        self.format_defaults = {
            'JPEG': {'quality': 85, 'optimize': True},
            'PNG': {'optimize': True, 'compress_level': 6},
            'WEBP': {'quality': 85, 'method': 6}
        }
        
        # Memory optimization settings
        self.enable_memory_optimization = enable_memory_optimization
        self.memory_pool = get_memory_pool() if enable_memory_optimization else None
        self.memory_monitor = get_memory_monitor() if enable_memory_optimization else None
        self.streaming_processor = StreamingImageProcessor() if enable_memory_optimization else None
        
        # Memory thresholds for large file handling (in MB)
        self.large_file_threshold_mb = 50
        self.max_memory_usage_mb = 200
    
    def resize_image(
        self, 
        image: Image.Image, 
        width: Optional[int] = None, 
        height: Optional[int] = None, 
        maintain_aspect: bool = True
    ) -> Image.Image:
        """
        Resize an image with optional aspect ratio preservation.
        
        Args:
            image: PIL Image object to resize
            width: Target width in pixels (None to calculate from height)
            height: Target height in pixels (None to calculate from width)
            maintain_aspect: Whether to maintain the original aspect ratio
            
        Returns:
            Resized PIL Image object
            
        Raises:
            ConversionError: If invalid dimensions are provided or resize fails
        """
        if image is None:
            raise ConversionError("Cannot resize None image")
        
        original_width, original_height = image.size
        
        # Validate input dimensions
        if width is not None and width <= 0:
            raise ConversionError("Width must be positive")
        if height is not None and height <= 0:
            raise ConversionError("Height must be positive")
        if width is None and height is None:
            raise ConversionError("At least one dimension (width or height) must be specified")
        
        try:
            # Calculate target dimensions
            if maintain_aspect:
                target_width, target_height = self._calculate_aspect_ratio_dimensions(
                    original_width, original_height, width, height
                )
            else:
                # Use provided dimensions or original if not specified
                target_width = width if width is not None else original_width
                target_height = height if height is not None else original_height
            
            # Perform the resize operation
            resized_image = image.resize(
                (target_width, target_height), 
                self.default_resampling
            )
            
            return resized_image
            
        except Exception as e:
            raise ConversionError(f"Failed to resize image: {str(e)}")
    
    def _calculate_aspect_ratio_dimensions(
        self, 
        original_width: int, 
        original_height: int, 
        target_width: Optional[int], 
        target_height: Optional[int]
    ) -> Tuple[int, int]:
        """
        Calculate target dimensions while maintaining aspect ratio.
        
        Args:
            original_width: Original image width
            original_height: Original image height
            target_width: Desired width (None if not specified)
            target_height: Desired height (None if not specified)
            
        Returns:
            Tuple of (calculated_width, calculated_height)
        """
        aspect_ratio = original_width / original_height
        
        if target_width is not None and target_height is not None:
            # Both dimensions specified - choose the one that maintains aspect ratio
            # and fits within both constraints
            width_based_height = int(target_width / aspect_ratio)
            height_based_width = int(target_height * aspect_ratio)
            
            if width_based_height <= target_height:
                return target_width, width_based_height
            else:
                return height_based_width, target_height
                
        elif target_width is not None:
            # Only width specified - calculate height
            calculated_height = int(target_width / aspect_ratio)
            return target_width, calculated_height
            
        elif target_height is not None:
            # Only height specified - calculate width
            calculated_width = int(target_height * aspect_ratio)
            return calculated_width, target_height
        
        # This should not happen due to validation above
        return original_width, original_height
    
    def get_image_info(self, image: Image.Image) -> dict:
        """
        Get detailed information about an image.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary containing image information
        """
        if image is None:
            return {}
        
        return {
            'size': image.size,
            'width': image.width,
            'height': image.height,
            'format': image.format,
            'mode': image.mode,
            'has_transparency': self._has_transparency(image)
        }
    
    def _has_transparency(self, image: Image.Image) -> bool:
        """
        Check if an image has transparency.
        
        Args:
            image: PIL Image object
            
        Returns:
            True if image has transparency, False otherwise
        """
        return (
            image.mode in ('RGBA', 'LA') or
            (image.mode == 'P' and 'transparency' in image.info)
        )
    
    def validate_processing_options(self, options: ProcessingOptions) -> None:
        """
        Validate processing options for image operations.
        
        Args:
            options: ProcessingOptions object to validate
            
        Raises:
            ConversionError: If options are invalid
        """
        if options is None:
            return
        
        # Validate resize dimensions
        if options.resize_width is not None and options.resize_width <= 0:
            raise ConversionError("Resize width must be positive")
        
        if options.resize_height is not None and options.resize_height <= 0:
            raise ConversionError("Resize height must be positive")
        
        # Validate quality
        if not (1 <= options.quality <= 100):
            raise ConversionError("Quality must be between 1 and 100")
        
        # Validate target format
        if options.target_format and options.target_format.upper() not in self.supported_formats:
            supported_list = ', '.join(sorted(self.supported_formats))
            raise ConversionError(
                f"Unsupported target format '{options.target_format}'. "
                f"Supported formats: {supported_list}"
            )
        
        # Validate rotation angle
        if options.rotation_angle not in [0, 90, 180, 270]:
            raise ConversionError("Rotation angle must be 0, 90, 180, or 270 degrees")
    
    def process_large_image_streaming(
        self,
        file_path: str,
        options: ProcessingOptions,
        max_memory_mb: Optional[int] = None
    ) -> Tuple[Image.Image, dict]:
        """
        Process a large image file using streaming to minimize memory usage.
        
        Args:
            file_path: Path to the image file
            options: Processing options to apply
            max_memory_mb: Maximum memory to use (None for default)
            
        Returns:
            Tuple of (processed_image, processing_info)
            
        Raises:
            ConversionError: If processing fails
        """
        if not self.enable_memory_optimization or not self.streaming_processor:
            raise ConversionError("Memory optimization not enabled")
        
        max_memory = max_memory_mb or self.max_memory_usage_mb
        
        try:
            with optimized_memory_context(max_memory) as context:
                # Get image info without loading full image
                image_info = self.streaming_processor.get_image_info_streaming(file_path)
                
                # Check if file is large enough to warrant streaming
                file_size_mb = image_info['file_size'] / (1024 * 1024)
                
                if file_size_mb < self.large_file_threshold_mb:
                    # Use regular processing for smaller files
                    with Image.open(file_path) as image:
                        image.load()
                        return self.apply_processing_options(image, options)
                
                # Use streaming for large files
                def process_func(image):
                    processed_image, info = self.apply_processing_options(image, options)
                    return processed_image
                
                processed_image = self.streaming_processor.process_large_image_streaming(
                    file_path, process_func, max_memory
                )
                
                processing_info = {
                    'streaming_used': True,
                    'file_size_mb': file_size_mb,
                    'max_memory_mb': max_memory,
                    'original_info': image_info,
                    'memory_stats': context['memory_monitor'].get_memory_usage()
                }
                
                return processed_image, processing_info
                
        except Exception as e:
            raise ConversionError(f"Failed to process large image: {str(e)}")
    
    def compress_image_optimized(
        self,
        image: Image.Image,
        quality: int = 85,
        target_format: Optional[str] = None,
        optimize: bool = True,
        use_memory_pool: bool = True
    ) -> Tuple[Image.Image, dict]:
        """
        Memory-optimized version of compress_image using buffer pooling.
        
        Args:
            image: PIL Image object to compress
            quality: Compression quality (1-100)
            target_format: Target format for compression
            optimize: Whether to enable format-specific optimization
            use_memory_pool: Whether to use memory pool for buffers
            
        Returns:
            Tuple of (compressed_image, compression_info)
            
        Raises:
            ConversionError: If compression fails
        """
        if self.enable_memory_optimization and use_memory_pool and self.memory_pool:
            return self._compress_with_memory_pool(image, quality, target_format, optimize)
        else:
            return self.compress_image(image, quality, target_format, optimize)
    
    def _compress_with_memory_pool(
        self,
        image: Image.Image,
        quality: int,
        target_format: Optional[str],
        optimize: bool
    ) -> Tuple[Image.Image, dict]:
        """
        Compress image using memory pool for buffer management.
        
        Args:
            image: PIL Image object to compress
            quality: Compression quality
            target_format: Target format
            optimize: Enable optimization
            
        Returns:
            Tuple of (compressed_image, compression_info)
        """
        if image is None:
            raise ConversionError("Cannot compress None image")
        
        if not (1 <= quality <= 100):
            raise ConversionError("Quality must be between 1 and 100")
        
        # Determine target format
        if target_format is None:
            target_format = image.format or 'PNG'
        
        target_format = target_format.upper()
        if target_format not in self.supported_formats:
            supported_list = ', '.join(sorted(self.supported_formats))
            raise ConversionError(
                f"Unsupported format '{target_format}'. "
                f"Supported formats: {supported_list}"
            )
        
        try:
            # Use memory pool for buffers
            with self.memory_pool.get_managed_buffer() as original_buffer:
                with self.memory_pool.get_managed_buffer() as compressed_buffer:
                    # Get original size
                    original_format = image.format or 'PNG'
                    image.save(original_buffer, format=original_format)
                    original_size = original_buffer.tell()
                    
                    # Prepare compression parameters
                    save_params = self._get_compression_params(target_format, quality, optimize)
                    
                    # Handle format conversion if needed
                    compressed_image = self._prepare_image_for_format(image, target_format)
                    
                    # Compress the image
                    compressed_image.save(compressed_buffer, format=target_format, **save_params)
                    compressed_size = compressed_buffer.tell()
                    
                    # Calculate compression ratio
                    compression_ratio = (original_size - compressed_size) / original_size * 100 if original_size > 0 else 0
                    
                    # Create compression info
                    compression_info = {
                        'original_size': original_size,
                        'compressed_size': compressed_size,
                        'compression_ratio': compression_ratio,
                        'original_format': original_format,
                        'target_format': target_format,
                        'quality': quality,
                        'optimized': optimize,
                        'memory_pool_used': True
                    }
                    
                    # Load compressed image from buffer for return
                    compressed_buffer.seek(0)
                    result_image = Image.open(compressed_buffer)
                    result_image.load()  # Ensure image data is loaded
                    
                    # Trigger garbage collection to free temporary objects
                    if self.enable_memory_optimization:
                        get_gc_optimizer().manual_collect()
                    
                    return result_image, compression_info
                    
        except Exception as e:
            raise ConversionError(f"Failed to compress image with memory optimization: {str(e)}")

    def compress_image(
        self, 
        image: Image.Image, 
        quality: int = 85, 
        target_format: Optional[str] = None,
        optimize: bool = True
    ) -> Tuple[Image.Image, dict]:
        """
        Compress an image with quality adjustment and format-specific optimization.
        
        Args:
            image: PIL Image object to compress
            quality: Compression quality (1-100, higher = better quality)
            target_format: Target format for compression (JPEG, PNG, WEBP)
            optimize: Whether to enable format-specific optimization
            
        Returns:
            Tuple of (compressed_image, compression_info)
            compression_info contains: original_size, compressed_size, compression_ratio
            
        Raises:
            ConversionError: If compression fails or invalid parameters
        """
        if image is None:
            raise ConversionError("Cannot compress None image")
        
        if not (1 <= quality <= 100):
            raise ConversionError("Quality must be between 1 and 100")
        
        # Determine target format
        if target_format is None:
            target_format = image.format or 'PNG'
        
        target_format = target_format.upper()
        if target_format not in self.supported_formats:
            supported_list = ', '.join(sorted(self.supported_formats))
            raise ConversionError(
                f"Unsupported format '{target_format}'. "
                f"Supported formats: {supported_list}"
            )
        
        try:
            # Get original size by saving to memory
            original_buffer = io.BytesIO()
            original_format = image.format or 'PNG'
            image.save(original_buffer, format=original_format)
            original_size = original_buffer.tell()
            
            # Prepare compression parameters
            save_params = self._get_compression_params(target_format, quality, optimize)
            
            # Handle format conversion if needed
            compressed_image = self._prepare_image_for_format(image, target_format)
            
            # Compress the image
            compressed_buffer = io.BytesIO()
            compressed_image.save(compressed_buffer, format=target_format, **save_params)
            compressed_size = compressed_buffer.tell()
            
            # Calculate compression ratio (can be negative if compressed is larger)
            compression_ratio = (original_size - compressed_size) / original_size * 100 if original_size > 0 else 0
            
            # Create compression info
            compression_info = {
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': compression_ratio,
                'original_format': original_format,
                'target_format': target_format,
                'quality': quality,
                'optimized': optimize
            }
            
            # Load compressed image from buffer for return
            compressed_buffer.seek(0)
            result_image = Image.open(compressed_buffer)
            result_image.load()  # Ensure image data is loaded
            
            return result_image, compression_info
            
        except Exception as e:
            raise ConversionError(f"Failed to compress image: {str(e)}")
    
    def _get_compression_params(self, format_name: str, quality: int, optimize: bool) -> dict:
        """
        Get format-specific compression parameters.
        
        Args:
            format_name: Target image format
            quality: Compression quality (1-100)
            optimize: Whether to enable optimization
            
        Returns:
            Dictionary of format-specific parameters
        """
        params = {}
        
        if format_name == 'JPEG':
            params.update({
                'quality': quality,
                'optimize': optimize,
                'progressive': True if quality >= 80 else False
            })
        elif format_name == 'PNG':
            # PNG compression level (0-9, where 9 is maximum compression)
            # Map quality (1-100) to compress_level (0-9)
            compress_level = max(0, min(9, int((100 - quality) / 11)))
            params.update({
                'optimize': optimize,
                'compress_level': compress_level
            })
        elif format_name == 'WEBP':
            params.update({
                'quality': quality,
                'method': 6,  # Compression method (0-6, 6 is slowest but best)
                'optimize': optimize
            })
        elif format_name in ['GIF', 'BMP']:
            # These formats have limited compression options
            params.update({
                'optimize': optimize
            })
        
        return params
    
    def _prepare_image_for_format(self, image: Image.Image, target_format: str) -> Image.Image:
        """
        Prepare an image for a specific format by handling mode conversions.
        
        Args:
            image: Source PIL Image
            target_format: Target format name
            
        Returns:
            Image prepared for the target format
        """
        # Create a copy to avoid modifying the original
        prepared_image = image.copy()
        
        if target_format == 'JPEG':
            # JPEG doesn't support transparency, convert RGBA to RGB
            if prepared_image.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparency
                if prepared_image.mode == 'P':
                    prepared_image = prepared_image.convert('RGBA')
                
                if prepared_image.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', prepared_image.size, (255, 255, 255))
                    if prepared_image.mode == 'LA':
                        prepared_image = prepared_image.convert('RGBA')
                    background.paste(prepared_image, mask=prepared_image.split()[-1])
                    prepared_image = background
            elif prepared_image.mode not in ('RGB', 'L'):
                prepared_image = prepared_image.convert('RGB')
                
        elif target_format == 'PNG':
            # PNG supports all modes, but optimize for common cases
            if prepared_image.mode == 'P':
                # Keep palette mode for smaller file size if possible
                pass
            elif prepared_image.mode not in ('RGB', 'RGBA', 'L', 'LA'):
                # Convert uncommon modes to RGBA to preserve any transparency
                prepared_image = prepared_image.convert('RGBA')
                
        elif target_format == 'WEBP':
            # WEBP supports RGB and RGBA
            if prepared_image.mode not in ('RGB', 'RGBA'):
                if self._has_transparency(prepared_image):
                    prepared_image = prepared_image.convert('RGBA')
                else:
                    prepared_image = prepared_image.convert('RGB')
        
        return prepared_image
    
    def get_file_size_from_image(
        self, 
        image: Image.Image, 
        format_name: str = 'PNG', 
        quality: int = 85
    ) -> int:
        """
        Calculate the file size of an image when saved with specific parameters.
        
        Args:
            image: PIL Image object
            format_name: Format to save as
            quality: Quality setting for compression
            
        Returns:
            File size in bytes
            
        Raises:
            ConversionError: If size calculation fails
        """
        if image is None:
            raise ConversionError("Cannot calculate size of None image")
        
        try:
            buffer = io.BytesIO()
            save_params = self._get_compression_params(format_name.upper(), quality, True)
            prepared_image = self._prepare_image_for_format(image, format_name.upper())
            prepared_image.save(buffer, format=format_name.upper(), **save_params)
            return buffer.tell()
        except Exception as e:
            raise ConversionError(f"Failed to calculate image size: {str(e)}")
    
    def compare_compression_options(
        self, 
        image: Image.Image, 
        quality_levels: List[int] = None,
        formats: List[str] = None
    ) -> dict:
        """
        Compare different compression options and their resulting file sizes.
        
        Args:
            image: PIL Image object to analyze
            quality_levels: List of quality levels to test (default: [60, 75, 85, 95])
            formats: List of formats to test (default: ['JPEG', 'PNG', 'WEBP'])
            
        Returns:
            Dictionary with compression comparison results
            
        Raises:
            ConversionError: If comparison fails
        """
        if image is None:
            raise ConversionError("Cannot compare compression of None image")
        
        if quality_levels is None:
            quality_levels = [60, 75, 85, 95]
        
        if formats is None:
            formats = ['JPEG', 'PNG', 'WEBP']
        
        # Validate inputs
        for quality in quality_levels:
            if not (1 <= quality <= 100):
                raise ConversionError(f"Invalid quality level: {quality}")
        
        for fmt in formats:
            if fmt.upper() not in self.supported_formats:
                raise ConversionError(f"Unsupported format: {fmt}")
        
        try:
            results = {
                'original_size': self.get_file_size_from_image(image, 'PNG', 100),
                'comparisons': []
            }
            
            for fmt in formats:
                for quality in quality_levels:
                    try:
                        compressed_image, compression_info = self.compress_image(
                            image, quality, fmt, optimize=True
                        )
                        
                        results['comparisons'].append({
                            'format': fmt,
                            'quality': quality,
                            'size': compression_info['compressed_size'],
                            'compression_ratio': compression_info['compression_ratio'],
                            'size_reduction_mb': (results['original_size'] - compression_info['compressed_size']) / (1024 * 1024)
                        })
                    except Exception as e:
                        # Log the error but continue with other combinations
                        results['comparisons'].append({
                            'format': fmt,
                            'quality': quality,
                            'error': str(e)
                        })
            
            # Sort by file size (smallest first)
            valid_comparisons = [c for c in results['comparisons'] if 'error' not in c]
            valid_comparisons.sort(key=lambda x: x['size'])
            
            if valid_comparisons:
                results['best_compression'] = valid_comparisons[0]
                results['recommendations'] = self._generate_compression_recommendations(valid_comparisons)
            
            return results
            
        except Exception as e:
            raise ConversionError(f"Failed to compare compression options: {str(e)}")
    
    def _generate_compression_recommendations(self, comparisons: List[dict]) -> dict:
        """
        Generate compression recommendations based on comparison results.
        
        Args:
            comparisons: List of compression comparison results
            
        Returns:
            Dictionary with recommendations
        """
        if not comparisons:
            return {}
        
        # Find best options for different use cases
        smallest_size = min(comparisons, key=lambda x: x['size'])
        best_quality = max(comparisons, key=lambda x: x['quality'])
        
        # Find balanced option (good quality/size ratio)
        balanced = None
        for comp in comparisons:
            if comp['quality'] >= 80 and comp['compression_ratio'] >= 20:
                if balanced is None or comp['size'] < balanced['size']:
                    balanced = comp
        
        if balanced is None:
            # Fallback to medium quality option
            medium_quality = [c for c in comparisons if 70 <= c['quality'] <= 90]
            if medium_quality:
                balanced = min(medium_quality, key=lambda x: x['size'])
            else:
                balanced = comparisons[len(comparisons) // 2]  # Middle option
        
        return {
            'smallest_file': smallest_size,
            'highest_quality': best_quality,
            'balanced': balanced,
            'summary': f"Best compression: {smallest_size['format']} at {smallest_size['quality']}% quality "
                      f"({smallest_size['compression_ratio']:.1f}% size reduction)"
        }
    
    def convert_format(
        self, 
        image: Image.Image, 
        target_format: str,
        quality: int = 85,
        optimize: bool = True
    ) -> Tuple[Image.Image, dict]:
        """
        Convert an image to a different format.
        
        Args:
            image: PIL Image object to convert
            target_format: Target format (PNG, JPEG, WEBP, GIF, BMP)
            quality: Quality setting for lossy formats (1-100)
            optimize: Whether to enable format-specific optimization
            
        Returns:
            Tuple of (converted_image, conversion_info)
            conversion_info contains: original_format, target_format, size_change
            
        Raises:
            ConversionError: If conversion fails or invalid parameters
        """
        if image is None:
            raise ConversionError("Cannot convert format of None image")
        
        if not (1 <= quality <= 100):
            raise ConversionError("Quality must be between 1 and 100")
        
        target_format = target_format.upper()
        if target_format not in self.supported_formats:
            supported_list = ', '.join(sorted(self.supported_formats))
            raise ConversionError(
                f"Unsupported target format '{target_format}'. "
                f"Supported formats: {supported_list}"
            )
        
        try:
            original_format = image.format or 'PNG'
            
            # Get original size
            original_buffer = io.BytesIO()
            image.save(original_buffer, format=original_format)
            original_size = original_buffer.tell()
            
            # Prepare image for target format
            converted_image = self._prepare_image_for_format(image, target_format)
            
            # Get format-specific parameters
            save_params = self._get_compression_params(target_format, quality, optimize)
            
            # Convert to target format
            converted_buffer = io.BytesIO()
            converted_image.save(converted_buffer, format=target_format, **save_params)
            converted_size = converted_buffer.tell()
            
            # Calculate size change
            size_change = converted_size - original_size
            size_change_percent = (size_change / original_size * 100) if original_size > 0 else 0
            
            # Create conversion info
            conversion_info = {
                'original_format': original_format,
                'target_format': target_format,
                'original_size': original_size,
                'converted_size': converted_size,
                'size_change': size_change,
                'size_change_percent': size_change_percent,
                'quality': quality,
                'optimized': optimize
            }
            
            # Load converted image from buffer for return
            converted_buffer.seek(0)
            result_image = Image.open(converted_buffer)
            result_image.load()  # Ensure image data is loaded
            
            return result_image, conversion_info
            
        except Exception as e:
            raise ConversionError(f"Failed to convert image format: {str(e)}")
    
    def rotate_image(
        self, 
        image: Image.Image, 
        angle: int,
        expand: bool = True
    ) -> Image.Image:
        """
        Rotate an image by the specified angle.
        
        Args:
            image: PIL Image object to rotate
            angle: Rotation angle in degrees (0, 90, 180, 270)
            expand: Whether to expand the image to fit the rotated content
            
        Returns:
            Rotated PIL Image object
            
        Raises:
            ConversionError: If rotation fails or invalid angle
        """
        if image is None:
            raise ConversionError("Cannot rotate None image")
        
        if angle not in [0, 90, 180, 270]:
            raise ConversionError("Rotation angle must be 0, 90, 180, or 270 degrees")
        
        try:
            if angle == 0:
                return image.copy()
            
            # Use PIL's rotate method for 90-degree increments
            # Note: PIL's rotate uses counter-clockwise rotation
            # We want clockwise rotation, so we negate the angle
            rotated_image = image.rotate(-angle, expand=expand)
            
            return rotated_image
            
        except Exception as e:
            raise ConversionError(f"Failed to rotate image: {str(e)}")
    
    def flip_image(
        self, 
        image: Image.Image, 
        direction: str
    ) -> Image.Image:
        """
        Flip an image horizontally or vertically.
        
        Args:
            image: PIL Image object to flip
            direction: Flip direction ('horizontal', 'vertical', or 'both')
            
        Returns:
            Flipped PIL Image object
            
        Raises:
            ConversionError: If flip fails or invalid direction
        """
        if image is None:
            raise ConversionError("Cannot flip None image")
        
        direction = direction.lower()
        valid_directions = ['horizontal', 'vertical', 'both']
        if direction not in valid_directions:
            raise ConversionError(
                f"Invalid flip direction '{direction}'. "
                f"Valid directions: {', '.join(valid_directions)}"
            )
        
        try:
            flipped_image = image.copy()
            
            if direction in ['horizontal', 'both']:
                flipped_image = flipped_image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            
            if direction in ['vertical', 'both']:
                flipped_image = flipped_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            
            return flipped_image
            
        except Exception as e:
            raise ConversionError(f"Failed to flip image: {str(e)}")
    
    def apply_processing_options(
        self, 
        image: Image.Image, 
        options: ProcessingOptions
    ) -> Tuple[Image.Image, dict]:
        """
        Apply all processing options to an image in the correct order.
        
        This method applies image processing operations in the optimal order:
        1. Rotation and flipping (geometric transformations)
        2. Resizing (dimension changes)
        3. Format conversion (if needed)
        4. Compression (quality adjustments)
        
        Args:
            image: PIL Image object to process
            options: ProcessingOptions containing all processing parameters
            
        Returns:
            Tuple of (processed_image, processing_info)
            processing_info contains details about applied operations
            
        Raises:
            ConversionError: If any processing step fails
        """
        """
        Apply all processing options to an image in the correct order.
        
        Args:
            image: PIL Image object to process
            options: ProcessingOptions containing all processing parameters
            
        Returns:
            Tuple of (processed_image, processing_info)
            processing_info contains details about each operation performed
            
        Raises:
            ConversionError: If processing fails
        """
        if image is None:
            raise ConversionError("Cannot process None image")
        
        if options is None:
            return image.copy(), {
                'operations': [],
                'original_size': image.size,
                'original_format': image.format or 'PNG',
                'final_size': image.size,
                'final_format': image.format or 'PNG'
            }
        
        # Validate options
        self.validate_processing_options(options)
        
        try:
            processed_image = image.copy()
            processing_info = {
                'operations': [],
                'original_size': image.size,
                'original_format': image.format or 'PNG'
            }
            
            # 1. Apply rotation first (affects dimensions)
            if options.rotation_angle != 0:
                processed_image = self.rotate_image(processed_image, options.rotation_angle)
                processing_info['operations'].append({
                    'operation': 'rotate',
                    'angle': options.rotation_angle,
                    'new_size': processed_image.size
                })
            
            # 2. Apply flipping
            if options.flip_horizontal or options.flip_vertical:
                if options.flip_horizontal and options.flip_vertical:
                    direction = 'both'
                elif options.flip_horizontal:
                    direction = 'horizontal'
                else:
                    direction = 'vertical'
                
                processed_image = self.flip_image(processed_image, direction)
                processing_info['operations'].append({
                    'operation': 'flip',
                    'direction': direction
                })
            
            # 3. Apply resizing (after rotation/flip to work with final orientation)
            if options.resize_width is not None or options.resize_height is not None:
                processed_image = self.resize_image(
                    processed_image,
                    width=options.resize_width,
                    height=options.resize_height,
                    maintain_aspect=options.maintain_aspect_ratio
                )
                processing_info['operations'].append({
                    'operation': 'resize',
                    'width': options.resize_width,
                    'height': options.resize_height,
                    'maintain_aspect': options.maintain_aspect_ratio,
                    'new_size': processed_image.size
                })
            
            # 4. Apply format conversion and compression (last step)
            if options.target_format is not None:
                processed_image, conversion_info = self.convert_format(
                    processed_image,
                    options.target_format,
                    quality=options.quality,
                    optimize=True
                )
                processing_info['operations'].append({
                    'operation': 'convert_format',
                    'target_format': options.target_format,
                    'quality': options.quality,
                    'conversion_info': conversion_info
                })
            elif options.quality != 85:  # Apply compression if quality is not default
                processed_image, compression_info = self.compress_image(
                    processed_image,
                    quality=options.quality,
                    optimize=True
                )
                processing_info['operations'].append({
                    'operation': 'compress',
                    'quality': options.quality,
                    'compression_info': compression_info
                })
            
            processing_info['final_size'] = processed_image.size
            processing_info['final_format'] = processed_image.format or options.target_format or 'PNG'
            
            return processed_image, processing_info
            
        except Exception as e:
            raise ConversionError(f"Failed to apply processing options: {str(e)}")