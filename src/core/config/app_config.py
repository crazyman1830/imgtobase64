"""
Simplified application configuration.

This module defines a streamlined AppConfig class that focuses on
essential configuration settings with sensible defaults.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AppConfig:
    """
    Simplified application configuration with essential settings only.

    This configuration class focuses on the most commonly used settings
    and provides sensible defaults for all options.
    """

    # File processing settings
    max_file_size_mb: int = 10
    supported_formats: List[str] = field(
        default_factory=lambda: [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
    )

    # Cache settings
    cache_enabled: bool = True
    cache_dir: str = "cache"
    cache_max_size_mb: int = 100
    cache_max_age_hours: int = 24

    # Logging settings
    log_level: str = "INFO"
    log_dir: str = "logs"
    enable_file_logging: bool = True

    # Processing settings
    max_concurrent_files: int = 3
    enable_memory_optimization: bool = True

    # Web settings (for web interface)
    web_host: str = "0.0.0.0"
    web_port: int = 5000
    web_debug: bool = False

    # Security settings
    enable_security_scan: bool = True
    rate_limit_per_minute: int = 60

    # Directory settings
    temp_dir: str = "temp"
    data_dir: str = "data"

    def __post_init__(self):
        """Validate and normalize configuration values after initialization."""
        # Ensure directories are Path objects for easier handling
        self._cache_dir_path = Path(self.cache_dir).resolve()
        self._log_dir_path = Path(self.log_dir).resolve()
        self._temp_dir_path = Path(self.temp_dir).resolve()
        self._data_dir_path = Path(self.data_dir).resolve()

        # Validate numeric values
        if self.max_file_size_mb <= 0:
            self.max_file_size_mb = 10

        if self.cache_max_size_mb <= 0:
            self.cache_max_size_mb = 100

        if self.max_concurrent_files <= 0:
            self.max_concurrent_files = 1

        # Normalize log level
        self.log_level = self.log_level.upper()
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            self.log_level = "INFO"

        # Ensure supported formats start with dot
        self.supported_formats = [
            fmt if fmt.startswith(".") else f".{fmt}" for fmt in self.supported_formats
        ]

    @property
    def cache_dir_path(self) -> Path:
        """Get cache directory as Path object."""
        return self._cache_dir_path

    @property
    def log_dir_path(self) -> Path:
        """Get log directory as Path object."""
        return self._log_dir_path

    @property
    def temp_dir_path(self) -> Path:
        """Get temp directory as Path object."""
        return self._temp_dir_path

    @property
    def data_dir_path(self) -> Path:
        """Get data directory as Path object."""
        return self._data_dir_path

    @property
    def max_file_size_bytes(self) -> int:
        """Get maximum file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def cache_max_size_bytes(self) -> int:
        """Get maximum cache size in bytes."""
        return self.cache_max_size_mb * 1024 * 1024

    def is_format_supported(self, file_extension: str) -> bool:
        """
        Check if a file format is supported.

        Args:
            file_extension: File extension to check (with or without dot)

        Returns:
            True if format is supported, False otherwise
        """
        if not file_extension.startswith("."):
            file_extension = f".{file_extension}"

        return file_extension.lower() in [fmt.lower() for fmt in self.supported_formats]

    def get_mime_type_mapping(self) -> Dict[str, str]:
        """
        Get MIME type mapping for supported formats.

        Returns:
            Dictionary mapping file extensions to MIME types
        """
        return {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }

    def ensure_directories(self) -> None:
        """Create all configured directories if they don't exist."""
        directories = [
            self.cache_dir_path,
            self.log_dir_path,
            self.temp_dir_path,
            self.data_dir_path,
        ]

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create directory {directory}: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of the configuration
        """
        return {
            "max_file_size_mb": self.max_file_size_mb,
            "supported_formats": self.supported_formats,
            "cache_enabled": self.cache_enabled,
            "cache_dir": self.cache_dir,
            "cache_max_size_mb": self.cache_max_size_mb,
            "cache_max_age_hours": self.cache_max_age_hours,
            "log_level": self.log_level,
            "log_dir": self.log_dir,
            "enable_file_logging": self.enable_file_logging,
            "max_concurrent_files": self.max_concurrent_files,
            "enable_memory_optimization": self.enable_memory_optimization,
            "web_host": self.web_host,
            "web_port": self.web_port,
            "web_debug": self.web_debug,
            "enable_security_scan": self.enable_security_scan,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "temp_dir": self.temp_dir,
            "data_dir": self.data_dir,
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "AppConfig":
        """
        Create AppConfig from dictionary.

        Args:
            config_dict: Dictionary containing configuration values

        Returns:
            AppConfig instance
        """
        # Filter out unknown keys
        valid_keys = {
            "max_file_size_mb",
            "supported_formats",
            "cache_enabled",
            "cache_dir",
            "cache_max_size_mb",
            "cache_max_age_hours",
            "log_level",
            "log_dir",
            "enable_file_logging",
            "max_concurrent_files",
            "enable_memory_optimization",
            "web_host",
            "web_port",
            "web_debug",
            "enable_security_scan",
            "rate_limit_per_minute",
            "temp_dir",
            "data_dir",
        }

        filtered_dict = {k: v for k, v in config_dict.items() if k in valid_keys}

        return cls(**filtered_dict)
