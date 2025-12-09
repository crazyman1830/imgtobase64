"""
Configuration management for the Image Base64 Converter.

This module provides centralized configuration management with support for
environment variables, configuration files, and default settings.
"""

import json
import os
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union


class LogLevel(Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CacheBackend(Enum):
    """Cache backend types."""

    MEMORY = "memory"
    DISK = "disk"
    REDIS = "redis"
    DISABLED = "disabled"


@dataclass
class SecurityConfig:
    """Security configuration settings."""

    max_file_size_mb: int = 10
    allowed_mime_types: list = None
    enable_content_scan: bool = True
    enable_header_validation: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst_size: int = 10
    enable_ip_blocking: bool = False
    blocked_ips: list = None

    def __post_init__(self):
        if self.allowed_mime_types is None:
            self.allowed_mime_types = [
                "image/jpeg",
                "image/jpg",
                "image/png",
                "image/gif",
                "image/webp",
                "image/bmp",
                "image/tiff",
                "image/x-icon",
            ]
        if self.blocked_ips is None:
            self.blocked_ips = []


@dataclass
class CacheConfig:
    """Cache configuration settings."""

    backend: str = CacheBackend.DISK.value
    max_size_mb: int = 100
    max_entries: int = 1000
    max_age_hours: int = 24
    cleanup_interval_minutes: int = 60
    cache_dir: str = "cache"
    redis_url: str = "redis://localhost:6379/0"
    enable_compression: bool = True

    def get_cache_dir_path(self) -> Path:
        """Get the cache directory as a Path object."""
        return Path(self.cache_dir).resolve()


@dataclass
class ProcessingConfig:
    """Image processing configuration settings."""

    max_concurrent_files: int = 3
    max_queue_size: int = 100
    enable_memory_optimization: bool = True
    max_memory_usage_mb: int = 500
    enable_parallel_processing: bool = True
    cpu_workers: int = None
    io_workers: int = None
    large_file_threshold_mb: int = 50
    streaming_chunk_size_kb: int = 64

    def __post_init__(self):
        if self.cpu_workers is None:
            self.cpu_workers = max(1, os.cpu_count() // 2)
        if self.io_workers is None:
            self.io_workers = min(32, (os.cpu_count() or 1) + 4)


@dataclass
class WebConfig:
    """Web application configuration settings."""

    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    secret_key: str = "change-this-in-production"
    max_content_length_mb: int = 16
    enable_cors: bool = True
    cors_origins: list = None
    enable_websocket: bool = True
    websocket_async_mode: str = "eventlet"

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]

    @property
    def max_content_length_bytes(self) -> int:
        """Get max content length in bytes."""
        return self.max_content_length_mb * 1024 * 1024


@dataclass
class LoggingConfig:
    """Logging configuration settings."""

    level: str = LogLevel.INFO.value
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_file_logging: bool = True
    log_dir: str = "logs"
    max_file_size_mb: int = 10
    backup_count: int = 5
    enable_structured_logging: bool = True
    enable_security_logging: bool = True
    enable_performance_logging: bool = True

    def get_log_dir_path(self) -> Path:
        """Get the log directory as a Path object."""
        return Path(self.log_dir).resolve()


@dataclass
class AppConfig:
    """Main application configuration."""

    # Sub-configurations
    security: SecurityConfig = None
    cache: CacheConfig = None
    processing: ProcessingConfig = None
    web: WebConfig = None
    logging: LoggingConfig = None

    # Global settings
    app_name: str = "Image Base64 Converter"
    app_version: str = "2.0.0"
    environment: str = "development"
    data_dir: str = "data"
    temp_dir: str = "temp"

    def __post_init__(self):
        if self.security is None:
            self.security = SecurityConfig()
        if self.cache is None:
            self.cache = CacheConfig()
        if self.processing is None:
            self.processing = ProcessingConfig()
        if self.web is None:
            self.web = WebConfig()
        if self.logging is None:
            self.logging = LoggingConfig()

    def get_data_dir_path(self) -> Path:
        """Get the data directory as a Path object."""
        return Path(self.data_dir).resolve()

    def get_temp_dir_path(self) -> Path:
        """Get the temp directory as a Path object."""
        return Path(self.temp_dir).resolve()

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


class ConfigManager:
    """
    Configuration manager for loading and managing application settings.

    Supports loading configuration from:
    1. Environment variables
    2. Configuration files (JSON, YAML)
    3. Default values
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the configuration manager.

        Args:
            config_file: Path to configuration file (optional)
        """
        self.config_file = config_file
        self._config: Optional[AppConfig] = None

    def load_config(self) -> AppConfig:
        """
        Load configuration from all sources.

        Returns:
            AppConfig: Loaded configuration
        """
        if self._config is not None:
            return self._config

        # Start with default configuration
        config_dict = {}

        # Load from configuration file if provided
        if self.config_file and os.path.exists(self.config_file):
            config_dict.update(self._load_from_file(self.config_file))

        # Override with environment variables
        config_dict.update(self._load_from_env())

        # Create configuration object
        self._config = self._create_config_from_dict(config_dict)

        # Ensure directories exist
        self._ensure_directories()

        return self._config

    def _load_from_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if file_path.endswith(".json"):
                    return json.load(f)
                elif file_path.endswith((".yml", ".yaml")):
                    try:
                        import yaml

                        return yaml.safe_load(f)
                    except ImportError:
                        print("PyYAML not installed, skipping YAML config file")
                        return {}
                else:
                    print(f"Unsupported config file format: {file_path}")
                    return {}
        except Exception as e:
            print(f"Error loading config file {file_path}: {e}")
            return {}

    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}

        # Security settings
        if os.getenv("MAX_FILE_SIZE_MB"):
            env_config.setdefault("security", {})["max_file_size_mb"] = int(
                os.getenv("MAX_FILE_SIZE_MB")
            )

        if os.getenv("ENABLE_SECURITY_SCAN"):
            env_config.setdefault("security", {})["enable_content_scan"] = (
                os.getenv("ENABLE_SECURITY_SCAN").lower() == "true"
            )

        if os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE"):
            env_config.setdefault("security", {})["rate_limit_requests_per_minute"] = (
                int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE"))
            )

        # Cache settings
        if os.getenv("CACHE_DIR"):
            env_config.setdefault("cache", {})["cache_dir"] = os.getenv("CACHE_DIR")

        if os.getenv("CACHE_MAX_SIZE_MB"):
            env_config.setdefault("cache", {})["max_size_mb"] = int(
                os.getenv("CACHE_MAX_SIZE_MB")
            )

        if os.getenv("CACHE_MAX_AGE_HOURS"):
            env_config.setdefault("cache", {})["max_age_hours"] = int(
                os.getenv("CACHE_MAX_AGE_HOURS")
            )

        if os.getenv("CACHE_BACKEND"):
            env_config.setdefault("cache", {})["backend"] = os.getenv("CACHE_BACKEND")

        # Processing settings
        if os.getenv("MAX_CONCURRENT_PROCESSING"):
            env_config.setdefault("processing", {})["max_concurrent_files"] = int(
                os.getenv("MAX_CONCURRENT_PROCESSING")
            )

        if os.getenv("ENABLE_MEMORY_OPTIMIZATION"):
            env_config.setdefault("processing", {})["enable_memory_optimization"] = (
                os.getenv("ENABLE_MEMORY_OPTIMIZATION").lower() == "true"
            )

        if os.getenv("PARALLEL_PROCESSING_WORKERS"):
            env_config.setdefault("processing", {})["cpu_workers"] = int(
                os.getenv("PARALLEL_PROCESSING_WORKERS")
            )

        # Web settings
        if os.getenv("WEB_HOST"):
            env_config.setdefault("web", {})["host"] = os.getenv("WEB_HOST")

        if os.getenv("WEB_PORT"):
            env_config.setdefault("web", {})["port"] = int(os.getenv("WEB_PORT"))

        if os.getenv("WEB_DEBUG"):
            env_config.setdefault("web", {})["debug"] = (
                os.getenv("WEB_DEBUG").lower() == "true"
            )

        if os.getenv("SECRET_KEY"):
            env_config.setdefault("web", {})["secret_key"] = os.getenv("SECRET_KEY")

        # Logging settings
        if os.getenv("LOG_LEVEL"):
            env_config.setdefault("logging", {})["level"] = os.getenv(
                "LOG_LEVEL"
            ).upper()

        if os.getenv("LOG_DIR"):
            env_config.setdefault("logging", {})["log_dir"] = os.getenv("LOG_DIR")

        # Global settings
        if os.getenv("ENVIRONMENT"):
            env_config["environment"] = os.getenv("ENVIRONMENT")

        if os.getenv("DATA_DIR"):
            env_config["data_dir"] = os.getenv("DATA_DIR")

        if os.getenv("TEMP_DIR"):
            env_config["temp_dir"] = os.getenv("TEMP_DIR")

        return env_config

    def _create_config_from_dict(self, config_dict: Dict[str, Any]) -> AppConfig:
        """Create AppConfig object from dictionary."""
        # Create sub-configurations
        security_config = SecurityConfig(**config_dict.get("security", {}))
        cache_config = CacheConfig(**config_dict.get("cache", {}))
        processing_config = ProcessingConfig(**config_dict.get("processing", {}))
        web_config = WebConfig(**config_dict.get("web", {}))
        logging_config = LoggingConfig(**config_dict.get("logging", {}))

        # Create main configuration
        main_config_dict = {
            k: v
            for k, v in config_dict.items()
            if k not in ["security", "cache", "processing", "web", "logging"]
        }

        return AppConfig(
            security=security_config,
            cache=cache_config,
            processing=processing_config,
            web=web_config,
            logging=logging_config,
            **main_config_dict,
        )

    def _ensure_directories(self):
        """Ensure all configured directories exist."""
        if self._config is None:
            return

        directories = [
            self._config.cache.get_cache_dir_path(),
            self._config.logging.get_log_dir_path(),
            self._config.get_data_dir_path(),
            self._config.get_temp_dir_path(),
        ]

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create directory {directory}: {e}")

    def save_config(self, file_path: str, format: str = "json"):
        """
        Save current configuration to a file.

        Args:
            file_path: Path to save the configuration
            format: File format ('json' or 'yaml')
        """
        if self._config is None:
            raise ValueError("No configuration loaded")

        config_dict = asdict(self._config)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                if format.lower() == "json":
                    json.dump(config_dict, f, indent=2, ensure_ascii=False)
                elif format.lower() in ["yml", "yaml"]:
                    try:
                        import yaml

                        yaml.dump(
                            config_dict, f, default_flow_style=False, allow_unicode=True
                        )
                    except ImportError:
                        raise ImportError(
                            "PyYAML not installed, cannot save YAML config"
                        )
                else:
                    raise ValueError(f"Unsupported format: {format}")
        except Exception as e:
            raise RuntimeError(f"Error saving config to {file_path}: {e}")

    def get_config(self) -> AppConfig:
        """Get the current configuration."""
        if self._config is None:
            return self.load_config()
        return self._config

    def reload_config(self) -> AppConfig:
        """Reload configuration from all sources."""
        self._config = None
        return self.load_config()


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_file: Optional[str] = None) -> ConfigManager:
    """
    Get the global configuration manager instance.

    Args:
        config_file: Path to configuration file (only used on first call)

    Returns:
        ConfigManager: Global configuration manager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_file)
    return _config_manager


def get_config() -> AppConfig:
    """
    Get the current application configuration.

    Returns:
        AppConfig: Current application configuration
    """
    return get_config_manager().get_config()


def reload_config() -> AppConfig:
    """
    Reload the application configuration.

    Returns:
        AppConfig: Reloaded application configuration
    """
    return get_config_manager().reload_config()
