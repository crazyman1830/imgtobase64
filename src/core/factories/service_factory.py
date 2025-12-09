"""
Service factory for creating service objects with dependency injection.

This module provides the ServiceFactory class that creates service objects
based on configuration and handles dependency injection.
"""

from typing import Any, Dict, Optional

from ...domain.exceptions.base import ImageConverterError
from ..config.app_config import AppConfig
from ..interfaces.cache_manager import ICacheManager
from ..interfaces.file_handler import IFileHandler
from ..interfaces.image_converter import IImageConverter
from ..security_validator import SecurityValidator
from ..services.cache_manager_service import CacheManagerService
from ..services.file_handler_service import FileHandlerService
from ..services.image_conversion_service import ImageConversionService


class ServiceFactory:
    """
    Factory class for creating service objects with proper dependency injection.

    This factory handles the creation and configuration of service objects
    based on the application configuration, ensuring proper dependency
    injection and component integration.
    """

    def __init__(self, config: AppConfig):
        """
        Initialize the service factory with configuration.

        Args:
            config: Application configuration object
        """
        self._config = config
        self._cache_manager: Optional[ICacheManager] = None
        self._file_handler: Optional[IFileHandler] = None
        self._image_converter: Optional[IImageConverter] = None
        self._security_validator: Optional[SecurityValidator] = None

    def create_image_conversion_service(self) -> ImageConversionService:
        """
        Create an ImageConversionService with all required dependencies.

        Returns:
            Configured ImageConversionService instance

        Raises:
            ImageConverterError: If service creation fails
        """
        try:
            # Create dependencies
            converter = self.get_image_converter()
            file_handler = self.get_file_handler()
            cache_manager = self.get_cache_manager()

            # Create and return the service
            return ImageConversionService(
                converter=converter,
                file_handler=file_handler,
                cache_manager=cache_manager,
            )

        except Exception as e:
            raise ImageConverterError(
                f"Failed to create ImageConversionService: {str(e)}"
            )

    def get_cache_manager(self) -> ICacheManager:
        """
        Get or create a cache manager instance.

        Returns:
            ICacheManager implementation based on configuration
        """
        if self._cache_manager is None:
            self._cache_manager = self._create_cache_manager()
        return self._cache_manager

    def get_file_handler(self) -> IFileHandler:
        """
        Get or create a file handler instance.

        Returns:
            IFileHandler implementation
        """
        if self._file_handler is None:
            self._file_handler = self._create_file_handler()
        return self._file_handler

    def get_image_converter(self) -> IImageConverter:
        """
        Get or create an image converter instance.

        Returns:
            IImageConverter implementation
        """
        if self._image_converter is None:
            self._image_converter = self._create_image_converter()
        return self._image_converter

    def get_security_validator(self) -> SecurityValidator:
        """
        Get or create a security validator instance.

        Returns:
            SecurityValidator instance configured with app settings
        """
        if self._security_validator is None:
            self._security_validator = self._create_security_validator()
        return self._security_validator

    def _create_cache_manager(self) -> ICacheManager:
        """
        Create a cache manager based on configuration.

        Returns:
            ICacheManager implementation
        """
        if not self._config.cache_enabled:
            # Return a no-op cache manager
            return self._create_no_op_cache_manager()

        # Determine cache backend type based on configuration
        # For now, we'll use memory cache as default, but this can be extended
        # to support different backends based on configuration
        backend_config = {
            "max_entries": 1000,
            "max_age_seconds": self._config.cache_max_age_hours * 3600,
        }

        return CacheManagerService(backend_type="memory", backend_config=backend_config)

    def _create_file_handler(self) -> IFileHandler:
        """
        Create a file handler service.

        Returns:
            IFileHandler implementation
        """
        return FileHandlerService()

    def _create_image_converter(self) -> IImageConverter:
        """
        Create an image converter implementation.

        Returns:
            IImageConverter implementation
        """
        # Import here to avoid circular imports
        from ..adapters.legacy_image_converter_adapter import (
            LegacyImageConverterAdapter,
        )

        return LegacyImageConverterAdapter()

    def _create_security_validator(self) -> SecurityValidator:
        """
        Create a security validator based on configuration.

        Returns:
            SecurityValidator instance
        """
        return SecurityValidator(
            max_file_size=self._config.max_file_size_bytes,
            allowed_mime_types=set(self._config.get_mime_type_mapping().values()),
            enable_content_scan=self._config.enable_security_scan,
            max_header_scan_size=1024,
        )

    def _create_no_op_cache_manager(self) -> ICacheManager:
        """
        Create a no-operation cache manager that doesn't cache anything.

        Returns:
            ICacheManager that performs no caching
        """
        return NoOpCacheManager()

    def reset_services(self) -> None:
        """
        Reset all cached service instances.

        This forces recreation of services on next access,
        useful for configuration changes or testing.
        """
        self._cache_manager = None
        self._file_handler = None
        self._image_converter = None
        self._security_validator = None

    def update_config(self, config: AppConfig) -> None:
        """
        Update the configuration and reset services.

        Args:
            config: New application configuration
        """
        self._config = config
        self.reset_services()

    @classmethod
    def create_default(cls) -> "ServiceFactory":
        """
        Create a service factory with default configuration.

        Returns:
            ServiceFactory with default AppConfig
        """
        from ..config.config_factory import ConfigFactory

        config = ConfigFactory.create_default_config()
        return cls(config)

    @classmethod
    def create_from_env(cls) -> "ServiceFactory":
        """
        Create a service factory with configuration from environment.

        Returns:
            ServiceFactory with configuration loaded from environment
        """
        from ..config.config_factory import ConfigFactory

        config = ConfigFactory.from_env()
        return cls(config)


class NoOpCacheManager:
    """
    No-operation cache manager that doesn't perform any caching.

    This is used when caching is disabled in the configuration.
    """

    def get(self, key: str) -> Optional[Any]:
        """Always return None (cache miss)."""
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Always return True but don't store anything."""
        return True

    def invalidate(self, key: str) -> bool:
        """Always return False (key not found)."""
        return False

    def get_cache_key(self, file_path: str, options: Optional[Any] = None) -> str:
        """Generate a cache key but don't use it."""
        import hashlib

        combined = f"{file_path}:{str(options) if options else ''}"
        return hashlib.md5(combined.encode()).hexdigest()

    def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Always return None (no cached result)."""
        return None

    def store_result(self, cache_key: str, result: Any) -> None:
        """Do nothing (don't store result)."""
        pass

    def clear_cache(self) -> None:
        """Do nothing (no cache to clear)."""
        pass

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return stats indicating caching is disabled."""
        return {
            "backend_type": "disabled",
            "entries": 0,
            "hits": 0,
            "misses": 0,
            "hit_rate_percent": 0.0,
            "enabled": False,
        }
