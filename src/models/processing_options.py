"""
Processing options data models for the image base64 converter.
"""
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ProcessingOptions:
    """
    Data class to hold image processing options.
    
    Attributes:
        resize_width: Target width for resizing (None to maintain original)
        resize_height: Target height for resizing (None to maintain original)
        maintain_aspect_ratio: Whether to maintain aspect ratio during resize
        quality: Image quality for compression (1-100, default 85)
        target_format: Target image format (PNG, JPEG, WEBP, etc.)
        rotation_angle: Rotation angle in degrees (0, 90, 180, 270)
        flip_horizontal: Whether to flip image horizontally
        flip_vertical: Whether to flip image vertically
    """
    resize_width: Optional[int] = None
    resize_height: Optional[int] = None
    maintain_aspect_ratio: bool = True
    quality: int = 85
    target_format: Optional[str] = None
    rotation_angle: int = 0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    
    def __post_init__(self):
        """Validate processing options after initialization."""
        # Validate quality range
        if not (1 <= self.quality <= 100):
            raise ValueError("Quality must be between 1 and 100")
        
        # Validate rotation angle
        if self.rotation_angle not in [0, 90, 180, 270]:
            raise ValueError("Rotation angle must be 0, 90, 180, or 270 degrees")
        
        # Validate dimensions
        if self.resize_width is not None and self.resize_width <= 0:
            raise ValueError("Resize width must be positive")
        
        if self.resize_height is not None and self.resize_height <= 0:
            raise ValueError("Resize height must be positive")
        
        # Validate target format
        if self.target_format is not None:
            valid_formats = {'PNG', 'JPEG', 'WEBP', 'GIF', 'BMP'}
            if self.target_format.upper() not in valid_formats:
                raise ValueError(f"Target format must be one of: {', '.join(valid_formats)}")
            self.target_format = self.target_format.upper()


@dataclass
class ProgressInfo:
    """
    Data class to hold progress information for batch processing.
    
    Attributes:
        queue_id: Unique identifier for the processing queue
        total_files: Total number of files to process
        completed_files: Number of files already processed
        current_file: Name of the file currently being processed
        estimated_time_remaining: Estimated time remaining in seconds
        status: Current processing status
        error_count: Number of files that failed processing
        start_time: Processing start time (timestamp)
        current_file_progress: Progress of current file (0.0 to 1.0)
    """
    queue_id: str
    total_files: int
    completed_files: int = 0
    current_file: str = ""
    estimated_time_remaining: float = 0.0
    status: str = "pending"  # pending, processing, completed, error, cancelled
    error_count: int = 0
    start_time: float = 0.0
    current_file_progress: float = 0.0
    
    def __post_init__(self):
        """Validate progress information after initialization."""
        # Validate status
        valid_statuses = {'pending', 'processing', 'completed', 'error', 'cancelled'}
        if self.status not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        
        # Validate counts
        if self.total_files < 0:
            raise ValueError("Total files must be non-negative")
        
        if self.completed_files < 0:
            raise ValueError("Completed files must be non-negative")
        
        if self.completed_files > self.total_files:
            raise ValueError("Completed files cannot exceed total files")
        
        if self.error_count < 0:
            raise ValueError("Error count must be non-negative")
        
        # Validate progress
        if not (0.0 <= self.current_file_progress <= 1.0):
            raise ValueError("Current file progress must be between 0.0 and 1.0")
    
    @property
    def progress_percentage(self) -> float:
        """Calculate overall progress percentage."""
        if self.total_files == 0:
            return 100.0
        
        base_progress = self.completed_files / self.total_files
        current_progress = self.current_file_progress / self.total_files
        return (base_progress + current_progress) * 100.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.completed_files == 0:
            return 100.0
        
        successful_files = self.completed_files - self.error_count
        return (successful_files / self.completed_files) * 100.0


@dataclass
class SecurityScanResult:
    """
    Data class to hold security scan results.
    
    Attributes:
        is_safe: Whether the file is considered safe
        threat_level: Threat level assessment (low, medium, high)
        warnings: List of warning messages
        scan_time: Time taken to perform the scan in seconds
        file_size_check: Whether file size is within limits
        mime_type_check: Whether MIME type is valid
        header_check: Whether file header is valid
        content_check: Whether file content appears safe
        scan_details: Additional scan details
    """
    is_safe: bool
    threat_level: str = "low"
    warnings: List[str] = None
    scan_time: float = 0.0
    file_size_check: bool = True
    mime_type_check: bool = True
    header_check: bool = True
    content_check: bool = True
    scan_details: dict = None
    
    def __post_init__(self):
        """Initialize default values and validate scan result."""
        if self.warnings is None:
            self.warnings = []
        
        if self.scan_details is None:
            self.scan_details = {}
        
        # Validate threat level
        valid_levels = {'low', 'medium', 'high'}
        if self.threat_level not in valid_levels:
            raise ValueError(f"Threat level must be one of: {', '.join(valid_levels)}")
        
        # Validate scan time
        if self.scan_time < 0:
            raise ValueError("Scan time must be non-negative")
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message to the scan result."""
        if warning not in self.warnings:
            self.warnings.append(warning)
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0
    
    def get_summary(self) -> str:
        """Get a summary of the scan result."""
        status = "SAFE" if self.is_safe else "UNSAFE"
        threat = self.threat_level.upper()
        warning_count = len(self.warnings)
        
        summary = f"Status: {status} | Threat Level: {threat}"
        if warning_count > 0:
            summary += f" | Warnings: {warning_count}"
        
        return summary