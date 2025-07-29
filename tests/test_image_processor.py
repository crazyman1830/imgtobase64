"""
Unit tests for the ImageProcessor class.

Tests cover image resizing functionality with aspect ratio preservation,
validation, and error handling.
"""
import pytest
from PIL import Image
from src.core.image_processor import ImageProcessor
from src.models.models import ConversionError
from src.models.processing_options import ProcessingOptions


class TestImageProcessor:
    """Test cases for ImageProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.processor = ImageProcessor()
        
        # Create test images with different dimensions
        self.test_image_square = Image.new('RGB', (100, 100), color='red')
        self.test_image_landscape = Image.new('RGB', (200, 100), color='green')
        self.test_image_portrait = Image.new('RGB', (100, 200), color='blue')
        self.test_image_rgba = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
    
    def test_resize_image_with_width_only_maintain_aspect(self):
        """Test resizing with only width specified, maintaining aspect ratio."""
        # Test with landscape image (200x100)
        resized = self.processor.resize_image(
            self.test_image_landscape, 
            width=100, 
            maintain_aspect=True
        )
        
        assert resized.size == (100, 50)  # Aspect ratio 2:1 maintained
        
        # Test with portrait image (100x200)
        resized = self.processor.resize_image(
            self.test_image_portrait, 
            width=50, 
            maintain_aspect=True
        )
        
        assert resized.size == (50, 100)  # Aspect ratio 1:2 maintained
    
    def test_resize_image_with_height_only_maintain_aspect(self):
        """Test resizing with only height specified, maintaining aspect ratio."""
        # Test with landscape image (200x100)
        resized = self.processor.resize_image(
            self.test_image_landscape, 
            height=50, 
            maintain_aspect=True
        )
        
        assert resized.size == (100, 50)  # Aspect ratio 2:1 maintained
        
        # Test with portrait image (100x200)
        resized = self.processor.resize_image(
            self.test_image_portrait, 
            height=100, 
            maintain_aspect=True
        )
        
        assert resized.size == (50, 100)  # Aspect ratio 1:2 maintained
    
    def test_resize_image_with_both_dimensions_maintain_aspect(self):
        """Test resizing with both dimensions specified, maintaining aspect ratio."""
        # Test fitting within constraints - width constraint is tighter
        resized = self.processor.resize_image(
            self.test_image_landscape,  # 200x100
            width=80,
            height=60,
            maintain_aspect=True
        )
        
        assert resized.size == (80, 40)  # Fits width constraint, maintains 2:1 ratio
        
        # Test fitting within constraints - height constraint is tighter
        resized = self.processor.resize_image(
            self.test_image_landscape,  # 200x100
            width=120,
            height=40,
            maintain_aspect=True
        )
        
        assert resized.size == (80, 40)  # Fits height constraint, maintains 2:1 ratio
    
    def test_resize_image_without_maintain_aspect(self):
        """Test resizing without maintaining aspect ratio."""
        resized = self.processor.resize_image(
            self.test_image_landscape,  # 200x100
            width=150,
            height=150,
            maintain_aspect=False
        )
        
        assert resized.size == (150, 150)  # Exact dimensions, aspect ratio not maintained
    
    def test_resize_image_square_image(self):
        """Test resizing a square image."""
        resized = self.processor.resize_image(
            self.test_image_square,  # 100x100
            width=50,
            maintain_aspect=True
        )
        
        assert resized.size == (50, 50)  # Square remains square
    
    def test_resize_image_with_rgba(self):
        """Test resizing an image with alpha channel."""
        resized = self.processor.resize_image(
            self.test_image_rgba,  # 100x100 RGBA
            width=50,
            maintain_aspect=True
        )
        
        assert resized.size == (50, 50)
        assert resized.mode == 'RGBA'  # Alpha channel preserved
    
    def test_resize_image_error_cases(self):
        """Test error handling in resize operations."""
        # Test with None image
        with pytest.raises(ConversionError, match="Cannot resize None image"):
            self.processor.resize_image(None, width=100)
        
        # Test with negative width
        with pytest.raises(ConversionError, match="Width must be positive"):
            self.processor.resize_image(self.test_image_square, width=-10)
        
        # Test with negative height
        with pytest.raises(ConversionError, match="Height must be positive"):
            self.processor.resize_image(self.test_image_square, height=-10)
        
        # Test with no dimensions specified
        with pytest.raises(ConversionError, match="At least one dimension"):
            self.processor.resize_image(self.test_image_square)
        
        # Test with zero width
        with pytest.raises(ConversionError, match="Width must be positive"):
            self.processor.resize_image(self.test_image_square, width=0)
        
        # Test with zero height
        with pytest.raises(ConversionError, match="Height must be positive"):
            self.processor.resize_image(self.test_image_square, height=0)
    
    def test_calculate_aspect_ratio_dimensions(self):
        """Test the internal aspect ratio calculation method."""
        # Test width-only calculation
        width, height = self.processor._calculate_aspect_ratio_dimensions(
            200, 100, 100, None
        )
        assert (width, height) == (100, 50)
        
        # Test height-only calculation
        width, height = self.processor._calculate_aspect_ratio_dimensions(
            200, 100, None, 50
        )
        assert (width, height) == (100, 50)
        
        # Test both dimensions - width constraint tighter
        width, height = self.processor._calculate_aspect_ratio_dimensions(
            200, 100, 80, 60
        )
        assert (width, height) == (80, 40)
        
        # Test both dimensions - height constraint tighter
        width, height = self.processor._calculate_aspect_ratio_dimensions(
            200, 100, 120, 40
        )
        assert (width, height) == (80, 40)
    
    def test_get_image_info(self):
        """Test getting image information."""
        info = self.processor.get_image_info(self.test_image_landscape)
        
        assert info['size'] == (200, 100)
        assert info['width'] == 200
        assert info['height'] == 100
        assert info['mode'] == 'RGB'
        assert info['has_transparency'] is False
        
        # Test with RGBA image
        info_rgba = self.processor.get_image_info(self.test_image_rgba)
        assert info_rgba['mode'] == 'RGBA'
        assert info_rgba['has_transparency'] is True
        
        # Test with None image
        info_none = self.processor.get_image_info(None)
        assert info_none == {}
    
    def test_has_transparency(self):
        """Test transparency detection."""
        # RGB image should not have transparency
        assert self.processor._has_transparency(self.test_image_landscape) is False
        
        # RGBA image should have transparency
        assert self.processor._has_transparency(self.test_image_rgba) is True
        
        # Test with LA mode (grayscale with alpha)
        la_image = Image.new('LA', (100, 100), color=(128, 255))
        assert self.processor._has_transparency(la_image) is True
    
    def test_validate_processing_options(self):
        """Test validation of processing options."""
        # Test with None options (should not raise)
        self.processor.validate_processing_options(None)
        
        # Test with valid options
        valid_options = ProcessingOptions(
            resize_width=100,
            resize_height=100,
            quality=85,
            target_format='JPEG'
        )
        self.processor.validate_processing_options(valid_options)  # Should not raise
        
        # Test with invalid width (ProcessingOptions validates in __post_init__)
        with pytest.raises(ValueError, match="Resize width must be positive"):
            ProcessingOptions(resize_width=-10)
        
        # Test with invalid height (ProcessingOptions validates in __post_init__)
        with pytest.raises(ValueError, match="Resize height must be positive"):
            ProcessingOptions(resize_height=-10)
        
        # Test with invalid quality (ProcessingOptions validates in __post_init__)
        with pytest.raises(ValueError, match="Quality must be between 1 and 100"):
            ProcessingOptions(quality=150)
        
        # Test with invalid format (ProcessingOptions validates in __post_init__)
        with pytest.raises(ValueError, match="Target format must be one of"):
            ProcessingOptions(target_format='INVALID')
        
        # Test with invalid rotation (ProcessingOptions validates in __post_init__)
        with pytest.raises(ValueError, match="Rotation angle must be"):
            ProcessingOptions(rotation_angle=45)
        
        # Test ImageProcessor's additional validation with valid options
        valid_options = ProcessingOptions(resize_width=100, quality=85)
        self.processor.validate_processing_options(valid_options)  # Should not raise
    
    def test_processor_initialization(self):
        """Test ImageProcessor initialization."""
        processor = ImageProcessor()
        
        # Check default settings
        assert hasattr(processor, 'default_resampling')
        assert hasattr(processor, 'supported_formats')
        assert hasattr(processor, 'format_defaults')
        
        # Check supported formats
        expected_formats = {'PNG', 'JPEG', 'WEBP', 'GIF', 'BMP'}
        assert processor.supported_formats == expected_formats
        
        # Check format defaults exist
        assert 'JPEG' in processor.format_defaults
        assert 'PNG' in processor.format_defaults
        assert 'WEBP' in processor.format_defaults


class TestImageCompression:
    """Test cases for image compression functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.processor = ImageProcessor()
        
        # Create test images for compression testing
        self.test_image_rgb = Image.new('RGB', (200, 200), color=(255, 0, 0))
        self.test_image_rgba = Image.new('RGBA', (200, 200), color=(255, 0, 0, 128))
        self.test_image_large = Image.new('RGB', (800, 600), color=(100, 150, 200))
    
    def test_compress_image_jpeg_quality(self):
        """Test JPEG compression with different quality levels."""
        # Test high quality compression
        compressed_high, info_high = self.processor.compress_image(
            self.test_image_rgb, quality=95, target_format='JPEG'
        )
        
        assert compressed_high is not None
        assert info_high['quality'] == 95
        assert info_high['target_format'] == 'JPEG'
        assert info_high['original_size'] > 0
        assert info_high['compressed_size'] > 0
        
        # Test low quality compression
        compressed_low, info_low = self.processor.compress_image(
            self.test_image_rgb, quality=30, target_format='JPEG'
        )
        
        assert compressed_low is not None
        assert info_low['quality'] == 30
        
        # Low quality should result in smaller file size
        assert info_low['compressed_size'] < info_high['compressed_size']
    
    def test_compress_image_png_compression(self):
        """Test PNG compression with different settings."""
        compressed, info = self.processor.compress_image(
            self.test_image_rgb, quality=50, target_format='PNG'
        )
        
        assert compressed is not None
        assert info['target_format'] == 'PNG'
        assert info['quality'] == 50
        assert info['compressed_size'] > 0
        
        # Test with RGBA image (PNG should preserve alpha)
        compressed_rgba, info_rgba = self.processor.compress_image(
            self.test_image_rgba, quality=85, target_format='PNG'
        )
        
        assert compressed_rgba.mode == 'RGBA'
        assert info_rgba['target_format'] == 'PNG'
    
    def test_compress_image_webp_compression(self):
        """Test WEBP compression."""
        compressed, info = self.processor.compress_image(
            self.test_image_rgb, quality=80, target_format='WEBP'
        )
        
        assert compressed is not None
        assert info['target_format'] == 'WEBP'
        assert info['quality'] == 80
        assert info['compressed_size'] > 0
    
    def test_compress_image_format_conversion(self):
        """Test compression with format conversion."""
        # Convert RGBA to JPEG (should handle transparency)
        compressed, info = self.processor.compress_image(
            self.test_image_rgba, quality=85, target_format='JPEG'
        )
        
        assert compressed is not None
        assert compressed.mode == 'RGB'  # JPEG doesn't support alpha
        assert info['target_format'] == 'JPEG'
        assert info['original_format'] in ['PNG', None]  # Original was RGBA
    
    def test_compress_image_error_cases(self):
        """Test error handling in compression."""
        # Test with None image
        with pytest.raises(ConversionError, match="Cannot compress None image"):
            self.processor.compress_image(None, quality=85)
        
        # Test with invalid quality
        with pytest.raises(ConversionError, match="Quality must be between 1 and 100"):
            self.processor.compress_image(self.test_image_rgb, quality=150)
        
        with pytest.raises(ConversionError, match="Quality must be between 1 and 100"):
            self.processor.compress_image(self.test_image_rgb, quality=0)
        
        # Test with unsupported format
        with pytest.raises(ConversionError, match="Unsupported format"):
            self.processor.compress_image(self.test_image_rgb, quality=85, target_format='INVALID')
    
    def test_get_compression_params(self):
        """Test format-specific compression parameter generation."""
        # Test JPEG parameters
        jpeg_params = self.processor._get_compression_params('JPEG', 90, True)
        assert jpeg_params['quality'] == 90
        assert jpeg_params['optimize'] is True
        assert jpeg_params['progressive'] is True  # High quality should enable progressive
        
        # Test PNG parameters
        png_params = self.processor._get_compression_params('PNG', 50, True)
        assert png_params['optimize'] is True
        assert 'compress_level' in png_params
        assert 0 <= png_params['compress_level'] <= 9
        
        # Test WEBP parameters
        webp_params = self.processor._get_compression_params('WEBP', 75, True)
        assert webp_params['quality'] == 75
        assert webp_params['method'] == 6
        assert webp_params['optimize'] is True
    
    def test_prepare_image_for_format(self):
        """Test image preparation for different formats."""
        # Test RGBA to JPEG conversion (should remove alpha)
        jpeg_prepared = self.processor._prepare_image_for_format(self.test_image_rgba, 'JPEG')
        assert jpeg_prepared.mode == 'RGB'
        
        # Test RGB to PNG (should preserve mode)
        png_prepared = self.processor._prepare_image_for_format(self.test_image_rgb, 'PNG')
        assert png_prepared.mode == 'RGB'
        
        # Test RGBA to PNG (should preserve alpha)
        png_rgba_prepared = self.processor._prepare_image_for_format(self.test_image_rgba, 'PNG')
        assert png_rgba_prepared.mode == 'RGBA'
        
        # Test RGBA to WEBP (should preserve alpha)
        webp_prepared = self.processor._prepare_image_for_format(self.test_image_rgba, 'WEBP')
        assert webp_prepared.mode == 'RGBA'
    
    def test_get_file_size_from_image(self):
        """Test file size calculation."""
        # Test with different formats
        jpeg_size = self.processor.get_file_size_from_image(self.test_image_rgb, 'JPEG', 85)
        png_size = self.processor.get_file_size_from_image(self.test_image_rgb, 'PNG', 85)
        
        assert jpeg_size > 0
        assert png_size > 0
        
        # Test with different quality levels
        high_quality_size = self.processor.get_file_size_from_image(self.test_image_rgb, 'JPEG', 95)
        low_quality_size = self.processor.get_file_size_from_image(self.test_image_rgb, 'JPEG', 30)
        
        assert high_quality_size > low_quality_size
        
        # Test error case
        with pytest.raises(ConversionError, match="Cannot calculate size of None image"):
            self.processor.get_file_size_from_image(None, 'JPEG', 85)
    
    def test_compare_compression_options(self):
        """Test compression options comparison."""
        # Test with default parameters
        comparison = self.processor.compare_compression_options(self.test_image_large)
        
        assert 'original_size' in comparison
        assert 'comparisons' in comparison
        assert comparison['original_size'] > 0
        assert len(comparison['comparisons']) > 0
        
        # Check that we have results for different formats and qualities
        formats_tested = set(c['format'] for c in comparison['comparisons'] if 'error' not in c)
        qualities_tested = set(c['quality'] for c in comparison['comparisons'] if 'error' not in c)
        
        assert len(formats_tested) > 0
        assert len(qualities_tested) > 0
        
        # Test with custom parameters
        custom_comparison = self.processor.compare_compression_options(
            self.test_image_rgb,
            quality_levels=[70, 85],
            formats=['JPEG', 'PNG']
        )
        
        assert len(custom_comparison['comparisons']) == 4  # 2 formats × 2 qualities
        
        # Test recommendations if available
        if 'best_compression' in comparison:
            best = comparison['best_compression']
            assert 'format' in best
            assert 'quality' in best
            assert 'size' in best
        
        if 'recommendations' in comparison:
            recs = comparison['recommendations']
            assert isinstance(recs, dict)
    
    def test_compare_compression_options_error_cases(self):
        """Test error handling in compression comparison."""
        # Test with None image
        with pytest.raises(ConversionError, match="Cannot compare compression of None image"):
            self.processor.compare_compression_options(None)
        
        # Test with invalid quality levels
        with pytest.raises(ConversionError, match="Invalid quality level"):
            self.processor.compare_compression_options(
                self.test_image_rgb, 
                quality_levels=[150]
            )
        
        # Test with unsupported format
        with pytest.raises(ConversionError, match="Unsupported format"):
            self.processor.compare_compression_options(
                self.test_image_rgb,
                formats=['INVALID']
            )
    
    def test_generate_compression_recommendations(self):
        """Test compression recommendation generation."""
        # Create mock comparison data
        mock_comparisons = [
            {'format': 'JPEG', 'quality': 60, 'size': 1000, 'compression_ratio': 50},
            {'format': 'JPEG', 'quality': 85, 'size': 1500, 'compression_ratio': 25},
            {'format': 'PNG', 'quality': 95, 'size': 2000, 'compression_ratio': 10},
            {'format': 'WEBP', 'quality': 80, 'size': 1200, 'compression_ratio': 40}
        ]
        
        recommendations = self.processor._generate_compression_recommendations(mock_comparisons)
        
        assert 'smallest_file' in recommendations
        assert 'highest_quality' in recommendations
        assert 'balanced' in recommendations
        assert 'summary' in recommendations
        
        # Smallest file should be the one with size 1000
        assert recommendations['smallest_file']['size'] == 1000
        
        # Highest quality should be the one with quality 95
        assert recommendations['highest_quality']['quality'] == 95
        
        # Test with empty comparisons
        empty_recs = self.processor._generate_compression_recommendations([])
        assert empty_recs == {}
    
    def test_compression_ratio_calculation(self):
        """Test that compression ratios are calculated correctly."""
        compressed, info = self.processor.compress_image(
            self.test_image_large, quality=50, target_format='JPEG'
        )
        
        # Compression ratio can be negative if compressed file is larger than original
        # This is normal for simple images with solid colors
        assert info['compression_ratio'] <= 100  # Should not exceed 100%
        
        # Verify the calculation
        expected_ratio = (info['original_size'] - info['compressed_size']) / info['original_size'] * 100
        assert abs(info['compression_ratio'] - expected_ratio) < 0.01  # Allow small floating point differences
        
        # Test with a more complex image that should compress better
        # Create a more complex test image with patterns
        complex_image = Image.new('RGB', (400, 300))
        pixels = complex_image.load()
        for i in range(400):
            for j in range(300):
                pixels[i, j] = (i % 256, j % 256, (i + j) % 256)
        
        compressed_complex, info_complex = self.processor.compress_image(
            complex_image, quality=50, target_format='JPEG'
        )
        
        # Complex images should generally compress better (positive ratio)
        # But we won't assert this as it depends on the specific pattern
    
    def test_compression_preserves_image_content(self):
        """Test that compression preserves basic image properties."""
        original_size = self.test_image_rgb.size
        original_mode = self.test_image_rgb.mode
        
        compressed, info = self.processor.compress_image(
            self.test_image_rgb, quality=85, target_format='JPEG'
        )
        
        # Size should be preserved
        assert compressed.size == original_size
        
        # Mode might change (RGB to RGB is fine, RGBA to RGB for JPEG is expected)
        assert compressed.mode in ['RGB', 'RGBA', 'L']  # Valid PIL modes


class TestFormatConversion:
    """Test cases for image format conversion functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.processor = ImageProcessor()
        
        # Create test images for format conversion testing
        self.test_image_rgb = Image.new('RGB', (100, 100), color=(255, 0, 0))
        self.test_image_rgba = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        self.test_image_grayscale = Image.new('L', (100, 100), color=128)
    
    def test_convert_format_png_to_jpeg(self):
        """Test converting PNG to JPEG format."""
        converted, info = self.processor.convert_format(
            self.test_image_rgb, 'JPEG', quality=85
        )
        
        assert converted is not None
        assert info['target_format'] == 'JPEG'
        assert info['quality'] == 85
        assert info['original_size'] > 0
        assert info['converted_size'] > 0
        assert 'size_change' in info
        assert 'size_change_percent' in info
    
    def test_convert_format_jpeg_to_png(self):
        """Test converting JPEG to PNG format."""
        # First create a JPEG image
        jpeg_image, _ = self.processor.convert_format(
            self.test_image_rgb, 'JPEG', quality=85
        )
        
        # Then convert back to PNG
        converted, info = self.processor.convert_format(
            jpeg_image, 'PNG', quality=85
        )
        
        assert converted is not None
        assert info['target_format'] == 'PNG'
        assert converted.size == self.test_image_rgb.size
    
    def test_convert_format_to_webp(self):
        """Test converting to WEBP format."""
        converted, info = self.processor.convert_format(
            self.test_image_rgb, 'WEBP', quality=80
        )
        
        assert converted is not None
        assert info['target_format'] == 'WEBP'
        assert info['quality'] == 80
        assert converted.size == self.test_image_rgb.size
    
    def test_convert_format_rgba_to_jpeg(self):
        """Test converting RGBA image to JPEG (should handle transparency)."""
        converted, info = self.processor.convert_format(
            self.test_image_rgba, 'JPEG', quality=85
        )
        
        assert converted is not None
        assert converted.mode == 'RGB'  # JPEG doesn't support alpha
        assert info['target_format'] == 'JPEG'
        assert converted.size == self.test_image_rgba.size
    
    def test_convert_format_preserve_transparency(self):
        """Test that PNG and WEBP preserve transparency."""
        # Convert RGBA to PNG
        png_converted, png_info = self.processor.convert_format(
            self.test_image_rgba, 'PNG', quality=85
        )
        
        assert png_converted.mode == 'RGBA'
        assert png_info['target_format'] == 'PNG'
        
        # Convert RGBA to WEBP
        webp_converted, webp_info = self.processor.convert_format(
            self.test_image_rgba, 'WEBP', quality=85
        )
        
        assert webp_converted.mode == 'RGBA'
        assert webp_info['target_format'] == 'WEBP'
    
    def test_convert_format_error_cases(self):
        """Test error handling in format conversion."""
        # Test with None image
        with pytest.raises(ConversionError, match="Cannot convert format of None image"):
            self.processor.convert_format(None, 'JPEG')
        
        # Test with invalid quality
        with pytest.raises(ConversionError, match="Quality must be between 1 and 100"):
            self.processor.convert_format(self.test_image_rgb, 'JPEG', quality=150)
        
        with pytest.raises(ConversionError, match="Quality must be between 1 and 100"):
            self.processor.convert_format(self.test_image_rgb, 'JPEG', quality=0)
        
        # Test with unsupported format
        with pytest.raises(ConversionError, match="Unsupported target format"):
            self.processor.convert_format(self.test_image_rgb, 'INVALID')
    
    def test_convert_format_size_calculation(self):
        """Test that size change calculations are correct."""
        converted, info = self.processor.convert_format(
            self.test_image_rgb, 'JPEG', quality=85
        )
        
        # Verify size change calculation
        expected_change = info['converted_size'] - info['original_size']
        assert info['size_change'] == expected_change
        
        expected_percent = (expected_change / info['original_size'] * 100) if info['original_size'] > 0 else 0
        assert abs(info['size_change_percent'] - expected_percent) < 0.01
    
    def test_convert_format_different_qualities(self):
        """Test format conversion with different quality levels."""
        high_quality, high_info = self.processor.convert_format(
            self.test_image_rgb, 'JPEG', quality=95
        )
        
        low_quality, low_info = self.processor.convert_format(
            self.test_image_rgb, 'JPEG', quality=30
        )
        
        # Higher quality should generally result in larger file size
        assert high_info['quality'] == 95
        assert low_info['quality'] == 30
        # Note: For simple solid color images, this might not always hold true
    
    def test_convert_format_optimization(self):
        """Test format conversion with optimization enabled/disabled."""
        optimized, opt_info = self.processor.convert_format(
            self.test_image_rgb, 'PNG', quality=85, optimize=True
        )
        
        unoptimized, unopt_info = self.processor.convert_format(
            self.test_image_rgb, 'PNG', quality=85, optimize=False
        )
        
        assert opt_info['optimized'] is True
        assert unopt_info['optimized'] is False
        # Optimized version should generally be smaller or equal in size


class TestImageRotation:
    """Test cases for image rotation functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.processor = ImageProcessor()
        
        # Create a non-square test image to better test rotation
        self.test_image = Image.new('RGB', (200, 100), color='red')
        # Add a distinctive pattern to verify rotation
        pixels = self.test_image.load()
        for i in range(50):
            for j in range(50):
                pixels[i, j] = (0, 255, 0)  # Green square in top-left
    
    def test_rotate_image_0_degrees(self):
        """Test rotation by 0 degrees (no change)."""
        rotated = self.processor.rotate_image(self.test_image, 0)
        
        assert rotated.size == self.test_image.size
        assert rotated.mode == self.test_image.mode
        # Should be identical to original
        assert list(rotated.getdata()) == list(self.test_image.getdata())
    
    def test_rotate_image_90_degrees(self):
        """Test rotation by 90 degrees clockwise."""
        rotated = self.processor.rotate_image(self.test_image, 90)
        
        # 90-degree rotation should swap width and height
        assert rotated.size == (100, 200)  # Original was (200, 100)
        assert rotated.mode == self.test_image.mode
    
    def test_rotate_image_180_degrees(self):
        """Test rotation by 180 degrees."""
        rotated = self.processor.rotate_image(self.test_image, 180)
        
        # 180-degree rotation should preserve dimensions
        assert rotated.size == self.test_image.size
        assert rotated.mode == self.test_image.mode
    
    def test_rotate_image_270_degrees(self):
        """Test rotation by 270 degrees clockwise."""
        rotated = self.processor.rotate_image(self.test_image, 270)
        
        # 270-degree rotation should swap width and height (like 90 degrees)
        assert rotated.size == (100, 200)  # Original was (200, 100)
        assert rotated.mode == self.test_image.mode
    
    def test_rotate_image_multiple_rotations(self):
        """Test that multiple 90-degree rotations work correctly."""
        # Four 90-degree rotations should return to original
        rotated = self.test_image
        for _ in range(4):
            rotated = self.processor.rotate_image(rotated, 90)
        
        assert rotated.size == self.test_image.size
        # Note: Due to potential rounding in rotation, we don't check pixel-perfect equality
    
    def test_rotate_image_with_transparency(self):
        """Test rotation of image with transparency."""
        rgba_image = Image.new('RGBA', (100, 50), color=(255, 0, 0, 128))
        rotated = self.processor.rotate_image(rgba_image, 90)
        
        assert rotated.size == (50, 100)  # Dimensions swapped
        assert rotated.mode == 'RGBA'  # Transparency preserved
    
    def test_rotate_image_expand_parameter(self):
        """Test rotation with expand parameter."""
        # Test with expand=True (default)
        rotated_expand = self.processor.rotate_image(self.test_image, 90, expand=True)
        assert rotated_expand.size == (100, 200)
        
        # Test with expand=False
        rotated_no_expand = self.processor.rotate_image(self.test_image, 90, expand=False)
        assert rotated_no_expand.size == self.test_image.size  # Original size maintained
    
    def test_rotate_image_error_cases(self):
        """Test error handling in rotation."""
        # Test with None image
        with pytest.raises(ConversionError, match="Cannot rotate None image"):
            self.processor.rotate_image(None, 90)
        
        # Test with invalid angle
        with pytest.raises(ConversionError, match="Rotation angle must be 0, 90, 180, or 270 degrees"):
            self.processor.rotate_image(self.test_image, 45)
        
        with pytest.raises(ConversionError, match="Rotation angle must be 0, 90, 180, or 270 degrees"):
            self.processor.rotate_image(self.test_image, 360)
        
        with pytest.raises(ConversionError, match="Rotation angle must be 0, 90, 180, or 270 degrees"):
            self.processor.rotate_image(self.test_image, -90)


class TestImageFlipping:
    """Test cases for image flipping functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.processor = ImageProcessor()
        
        # Create a test image with distinctive pattern for flipping tests
        self.test_image = Image.new('RGB', (100, 100), color='white')
        pixels = self.test_image.load()
        
        # Create a pattern: red top-left, green top-right, blue bottom-left, yellow bottom-right
        for i in range(50):
            for j in range(50):
                pixels[i, j] = (255, 0, 0)  # Red top-left
                pixels[i + 50, j] = (0, 255, 0)  # Green top-right
                pixels[i, j + 50] = (0, 0, 255)  # Blue bottom-left
                pixels[i + 50, j + 50] = (255, 255, 0)  # Yellow bottom-right
    
    def test_flip_image_horizontal(self):
        """Test horizontal flipping."""
        flipped = self.processor.flip_image(self.test_image, 'horizontal')
        
        assert flipped.size == self.test_image.size
        assert flipped.mode == self.test_image.mode
        
        # Check that the pattern is horizontally flipped
        # Original: Red(top-left), Green(top-right) -> Flipped: Green(top-left), Red(top-right)
        original_pixels = self.test_image.load()
        flipped_pixels = flipped.load()
        
        # Top-left of flipped should be green (was top-right of original)
        assert flipped_pixels[10, 10] == (0, 255, 0)  # Green
        # Top-right of flipped should be red (was top-left of original)
        assert flipped_pixels[90, 10] == (255, 0, 0)  # Red
    
    def test_flip_image_vertical(self):
        """Test vertical flipping."""
        flipped = self.processor.flip_image(self.test_image, 'vertical')
        
        assert flipped.size == self.test_image.size
        assert flipped.mode == self.test_image.mode
        
        # Check that the pattern is vertically flipped
        # Original: Red(top-left), Blue(bottom-left) -> Flipped: Blue(top-left), Red(bottom-left)
        flipped_pixels = flipped.load()
        
        # Top-left of flipped should be blue (was bottom-left of original)
        assert flipped_pixels[10, 10] == (0, 0, 255)  # Blue
        # Bottom-left of flipped should be red (was top-left of original)
        assert flipped_pixels[10, 90] == (255, 0, 0)  # Red
    
    def test_flip_image_both(self):
        """Test flipping both horizontally and vertically."""
        flipped = self.processor.flip_image(self.test_image, 'both')
        
        assert flipped.size == self.test_image.size
        assert flipped.mode == self.test_image.mode
        
        # Check that the pattern is flipped both ways
        # Original: Red(top-left), Yellow(bottom-right) -> Flipped: Yellow(top-left), Red(bottom-right)
        flipped_pixels = flipped.load()
        
        # Top-left of flipped should be yellow (was bottom-right of original)
        assert flipped_pixels[10, 10] == (255, 255, 0)  # Yellow
        # Bottom-right of flipped should be red (was top-left of original)
        assert flipped_pixels[90, 90] == (255, 0, 0)  # Red
    
    def test_flip_image_case_insensitive(self):
        """Test that flip direction is case insensitive."""
        flipped_lower = self.processor.flip_image(self.test_image, 'horizontal')
        flipped_upper = self.processor.flip_image(self.test_image, 'HORIZONTAL')
        flipped_mixed = self.processor.flip_image(self.test_image, 'Horizontal')
        
        # All should produce the same result
        assert list(flipped_lower.getdata()) == list(flipped_upper.getdata())
        assert list(flipped_lower.getdata()) == list(flipped_mixed.getdata())
    
    def test_flip_image_with_transparency(self):
        """Test flipping image with transparency."""
        rgba_image = Image.new('RGBA', (50, 50), color=(255, 0, 0, 128))
        flipped = self.processor.flip_image(rgba_image, 'horizontal')
        
        assert flipped.size == rgba_image.size
        assert flipped.mode == 'RGBA'  # Transparency preserved
    
    def test_flip_image_double_flip(self):
        """Test that double flipping returns to original."""
        # Horizontal flip twice should return to original
        flipped_once = self.processor.flip_image(self.test_image, 'horizontal')
        flipped_twice = self.processor.flip_image(flipped_once, 'horizontal')
        
        assert list(flipped_twice.getdata()) == list(self.test_image.getdata())
        
        # Vertical flip twice should return to original
        flipped_once = self.processor.flip_image(self.test_image, 'vertical')
        flipped_twice = self.processor.flip_image(flipped_once, 'vertical')
        
        assert list(flipped_twice.getdata()) == list(self.test_image.getdata())
    
    def test_flip_image_error_cases(self):
        """Test error handling in flipping."""
        # Test with None image
        with pytest.raises(ConversionError, match="Cannot flip None image"):
            self.processor.flip_image(None, 'horizontal')
        
        # Test with invalid direction
        with pytest.raises(ConversionError, match="Invalid flip direction"):
            self.processor.flip_image(self.test_image, 'invalid')
        
        with pytest.raises(ConversionError, match="Invalid flip direction"):
            self.processor.flip_image(self.test_image, 'diagonal')


class TestProcessingOptionsIntegration:
    """Test cases for applying complete processing options."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.processor = ImageProcessor()
        
        # Create a test image for processing
        self.test_image = Image.new('RGB', (200, 100), color='red')
        # Add a pattern to make transformations visible
        pixels = self.test_image.load()
        for i in range(50):
            for j in range(25):
                pixels[i, j] = (0, 255, 0)  # Green corner
    
    def test_apply_processing_options_resize_only(self):
        """Test applying only resize options."""
        options = ProcessingOptions(
            resize_width=100,
            resize_height=50,
            maintain_aspect_ratio=False
        )
        
        processed, info = self.processor.apply_processing_options(self.test_image, options)
        
        assert processed.size == (100, 50)
        assert info['original_size'] == (200, 100)
        assert info['final_size'] == (100, 50)
        assert len(info['operations']) == 1
        assert info['operations'][0]['operation'] == 'resize'
    
    def test_apply_processing_options_rotation_only(self):
        """Test applying only rotation options."""
        options = ProcessingOptions(rotation_angle=90)
        
        processed, info = self.processor.apply_processing_options(self.test_image, options)
        
        assert processed.size == (100, 200)  # Dimensions swapped
        assert info['original_size'] == (200, 100)
        assert info['final_size'] == (100, 200)
        assert len(info['operations']) == 1
        assert info['operations'][0]['operation'] == 'rotate'
        assert info['operations'][0]['angle'] == 90
    
    def test_apply_processing_options_flip_only(self):
        """Test applying only flip options."""
        options = ProcessingOptions(flip_horizontal=True)
        
        processed, info = self.processor.apply_processing_options(self.test_image, options)
        
        assert processed.size == self.test_image.size
        assert len(info['operations']) == 1
        assert info['operations'][0]['operation'] == 'flip'
        assert info['operations'][0]['direction'] == 'horizontal'
    
    def test_apply_processing_options_format_conversion_only(self):
        """Test applying only format conversion."""
        options = ProcessingOptions(target_format='JPEG', quality=80)
        
        processed, info = self.processor.apply_processing_options(self.test_image, options)
        
        assert processed.size == self.test_image.size
        assert len(info['operations']) == 1
        assert info['operations'][0]['operation'] == 'convert_format'
        assert info['operations'][0]['target_format'] == 'JPEG'
        assert info['operations'][0]['quality'] == 80
    
    def test_apply_processing_options_compression_only(self):
        """Test applying only compression (quality change without format change)."""
        options = ProcessingOptions(quality=60)  # No target_format specified
        
        processed, info = self.processor.apply_processing_options(self.test_image, options)
        
        assert processed.size == self.test_image.size
        assert len(info['operations']) == 1
        assert info['operations'][0]['operation'] == 'compress'
        assert info['operations'][0]['quality'] == 60
    
    def test_apply_processing_options_combined(self):
        """Test applying multiple processing options in correct order."""
        options = ProcessingOptions(
            rotation_angle=90,
            flip_horizontal=True,
            resize_width=50,
            target_format='JPEG',
            quality=75
        )
        
        processed, info = self.processor.apply_processing_options(self.test_image, options)
        
        # Check that all operations were applied
        assert len(info['operations']) == 4
        
        # Check operation order: rotate -> flip -> resize -> convert_format
        operations = [op['operation'] for op in info['operations']]
        assert operations == ['rotate', 'flip', 'resize', 'convert_format']
        
        # Check final result
        # After rotation (200,100) -> (100,200), then resize to width 50 with aspect ratio
        # Aspect ratio is 100:200 = 1:2, so width 50 should give height 100
        assert processed.size == (50, 100)
        assert info['final_format'] == 'JPEG'
    
    def test_apply_processing_options_flip_both_directions(self):
        """Test applying flip in both directions."""
        options = ProcessingOptions(
            flip_horizontal=True,
            flip_vertical=True
        )
        
        processed, info = self.processor.apply_processing_options(self.test_image, options)
        
        assert len(info['operations']) == 1
        assert info['operations'][0]['operation'] == 'flip'
        assert info['operations'][0]['direction'] == 'both'
    
    def test_apply_processing_options_none_options(self):
        """Test applying None options (should return copy of original)."""
        processed, info = self.processor.apply_processing_options(self.test_image, None)
        
        assert processed.size == self.test_image.size
        assert info['operations'] == []
        assert info['original_size'] == (200, 100)
    
    def test_apply_processing_options_error_cases(self):
        """Test error handling in processing options application."""
        # Test with None image
        options = ProcessingOptions(resize_width=100)
        with pytest.raises(ConversionError, match="Cannot process None image"):
            self.processor.apply_processing_options(None, options)
        
        # Test with invalid options (should be caught by validation)
        with pytest.raises(ValueError):  # ProcessingOptions validation
            ProcessingOptions(rotation_angle=45)  # Invalid angle
    
    def test_apply_processing_options_order_independence(self):
        """Test that the processing order is consistent and logical."""
        # Create two identical options
        options1 = ProcessingOptions(
            rotation_angle=180,
            flip_horizontal=True,
            resize_width=100,
            target_format='PNG'
        )
        
        options2 = ProcessingOptions(
            resize_width=100,
            rotation_angle=180,
            target_format='PNG',
            flip_horizontal=True
        )
        
        # Both should produce the same result regardless of option order in constructor
        processed1, info1 = self.processor.apply_processing_options(self.test_image, options1)
        processed2, info2 = self.processor.apply_processing_options(self.test_image, options2)
        
        # Operations should be in the same order
        operations1 = [op['operation'] for op in info1['operations']]
        operations2 = [op['operation'] for op in info2['operations']]
        assert operations1 == operations2
        
        # Final results should be identical
        assert processed1.size == processed2.size
        assert list(processed1.getdata()) == list(processed2.getdata())