"""
Configuration adapter for backward compatibility.

This module provides adapter classes that maintain compatibility with
existing configuration interfaces while using the new unified system.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.path_utils import PathUtils
from .unified_config_manager import UnifiedConfigManager, get_config_manager


@dataclass
class LegacyAppConfig:
    """
    Legacy AppConfig adapter that maintains compatibility with existing code.

    This class provides the same interface as the old AppConfig classes
    while internally using the unified configuration manager.
    """

    def __init__(self, config_manager: Optional[UnifiedConfigManager] = None):
        """Initialize with optional config manager."""
        self._config_manager = config_manager or get_config_manager()
        self._config_manager.load_configuration()

    # File processing properties
    @property
    def max_file_size_mb(self) -> int:
        return self._config_manager.get("processing.max_file_size_mb", 10)

    @property
    def supported_formats(self) -> List[str]:
        return self._config_manager.get(
            "processing.supported_formats",
            [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],
        )

    @property
    def max_concurrent_files(self) -> int:
        return self._config_manager.get("processing.max_concurrent_files", 3)

    @property
    def enable_memory_optimization(self) -> bool:
        return self._config_manager.get("processing.enable_memory_optimization", True)

    # Cache properties
    @property
    def cache_enabled(self) -> bool:
        return self._config_manager.get("cache.enabled", True)

    @property
    def cache_dir(self) -> str:
        return self._config_manager.get("cache.directory", "cache")

    @property
    def cache_max_size_mb(self) -> int:
        return self._config_manager.get("cache.max_size_mb", 100)

    @property
    def cache_max_age_hours(self) -> int:
        return self._config_manager.get("cache.max_age_hours", 24)

    # Logging properties
    @property
    def log_level(self) -> str:
        return self._config_manager.get("logging.level", "INFO")

    @property
    def log_dir(self) -> str:
        return self._config_manager.get("logging.directory", "logs")

    @property
    def enable_file_logging(self) -> bool:
        return self._config_manager.get("logging.enable_file_logging", True)

    # Web properties
    @property
    def web_host(self) -> str:
        return self._config_manager.get("web.host", "0.0.0.0")

    @property
    def web_port(self) -> int:
        return self._config_manager.get("web.port", 5000)

    @property
    def web_debug(self) -> bool:
        return self._config_manager.get("web.debug", False)

    # Security properties
    @property
    def enable_security_scan(self) -> bool:
        return self._config_manager.get("security.enable_content_scan", True)

    @property
    def rate_limit_per_minute(self) -> int:
        return self._config_manager.get("security.rate_limit_per_minute", 60)

    # Directory properties
    @property
    def temp_dir(self) -> str:
        return self._config_manager.get("directories.temp", "temp")

    @property
    def data_dir(self) -> str:
        return self._config_manager.get("directories.data", "data")

    # Path properties (for compatibility)
    @property
    def cache_dir_path(self) -> Path:
        return PathUtils.normalize_path(self.cache_dir)

    @property
    def log_dir_path(self) -> Path:
        return PathUtils.normalize_path(self.log_dir)

    @property
    def temp_dir_path(self) -> Path:
        return PathUtils.normalize_path(self.temp_dir)

    @property
    def data_dir_path(self) -> Path:
        return PathUtils.normalize_path(self.data_dir)

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def cache_max_size_bytes(self) -> int:
        return self.cache_max_size_mb * 1024 * 1024

    # Compatibility methods
    def is_format_supported(self, file_extension: str) -> bool:
        """Check if a file format is supported."""
        if not file_extension.startswith("."):
            file_extension = f".{file_extension}"

        return file_extension.lower() in [fmt.lower() for fmt in self.supported_formats]

    def get_mime_type_mapping(self) -> Dict[str, str]:
        """Get MIME type mapping for supported formats."""
        return PathUtils.MIME_TYPE_MAPPING

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
                PathUtils.ensure_directory_exists(directory)
            except Exception as e:
                print(f"Warning: Could not create directory {directory}: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
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
    def from_dict(cls, config_dict: Dict[str, Any]) -> "LegacyAppConfig":
        """Create LegacyAppConfig from dictionary."""
        # This method is kept for compatibility but doesn't actually use the dict
        # since the unified manager handles all configuration loading
        return cls()


class ConfigurationMigrator:
    """Helper class for migrating from old configuration systems."""

    @staticmethod
    def migrate_old_config_file(old_file_path: str, new_file_path: str) -> None:
        """
        Migrate an old configuration file to the new unified format.

        Args:
            old_file_path: Path to the old configuration file
            new_file_path: Path where to save the new configuration file
        """
        import json

        try:
            # Load old configuration
            with open(old_file_path, "r", encoding="utf-8") as f:
                old_config = json.load(f)

            # Create mapping from old keys to new keys
            key_mappings = {
                "max_file_size_mb": "processing.max_file_size_mb",
                "supported_formats": "processing.supported_formats",
                "cache_enabled": "cache.enabled",
                "cache_dir": "cache.directory",
                "cache_max_size_mb": "cache.max_size_mb",
                "cache_max_age_hours": "cache.max_age_hours",
                "log_level": "logging.level",
                "log_dir": "logging.directory",
                "enable_file_logging": "logging.enable_file_logging",
                "max_concurrent_files": "processing.max_concurrent_files",
                "enable_memory_optimization": "processing.enable_memory_optimization",
                "web_host": "web.host",
                "web_port": "web.port",
                "web_debug": "web.debug",
                "enable_security_scan": "security.enable_content_scan",
                "rate_limit_per_minute": "security.rate_limit_per_minute",
                "temp_dir": "directories.temp",
                "data_dir": "directories.data",
            }

            # Convert to new format
            new_config = {}
            for old_key, new_key in key_mappings.items():
                if old_key in old_config:
                    # Create nested structure
                    from ..utils.type_utils import TypeUtils

                    TypeUtils.set_nested_value(new_config, new_key, old_config[old_key])

            # Save new configuration
            PathUtils.ensure_directory_exists(Path(new_file_path).parent)
            with open(new_file_path, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)

            print(f"Configuration migrated from {old_file_path} to {new_file_path}")

        except Exception as e:
            print(f"Error migrating configuration: {e}")

    @staticmethod
    def detect_old_config_usage(file_path: str) -> List[str]:
        """
        Detect usage of old configuration patterns in a Python file.

        Args:
            file_path: Path to the Python file to analyze

        Returns:
            List of detected old configuration patterns
        """
        patterns = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Look for old import patterns
            old_imports = [
                "from config import",
                "from src.config import",
                "import config",
                "from .config import",
                "from ..config import",
            ]

            for pattern in old_imports:
                if pattern in content:
                    patterns.append(f"Old import pattern: {pattern}")

            # Look for old configuration access patterns
            old_access_patterns = [
                "AppConfig(",
                "ConfigManager(",
                "get_config(",
                "config.get(",
                ".security.",
                ".cache.",
                ".processing.",
                ".web.",
                ".logging.",
            ]

            for pattern in old_access_patterns:
                if pattern in content:
                    patterns.append(f"Old access pattern: {pattern}")

        except Exception as e:
            patterns.append(f"Error analyzing file: {e}")

        return patterns


# Global legacy config instance for backward compatibility
_legacy_config: Optional[LegacyAppConfig] = None


def get_legacy_config() -> LegacyAppConfig:
    """Get the global legacy configuration instance."""
    global _legacy_config

    if _legacy_config is None:
        _legacy_config = LegacyAppConfig()

    return _legacy_config


# Compatibility functions that match old interfaces
def get_config() -> LegacyAppConfig:
    """Get configuration (legacy compatibility function)."""
    return get_legacy_config()


def reload_config() -> LegacyAppConfig:
    """Reload configuration (legacy compatibility function)."""
    global _legacy_config
    _legacy_config = None
    return get_legacy_config()
