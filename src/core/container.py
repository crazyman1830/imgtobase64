"""
Dependency injection container for the image converter application.

This module provides a comprehensive dependency injection container that manages
all application dependencies and their lifecycles.
"""

import os
from typing import Dict, Any, Optional, TypeVar, Type, Callable
from pathlib import Path

from .config.app_config import AppConfig
from .config.config_factory import ConfigFactory
from .factories.service_factory import ServiceFactory
from .factories.cache_factory import CacheFactory
from .services.image_conversion_service import ImageConversionService
from .services.file_handler_service import FileHandlerService
from .services.cache_manager_service import CacheManagerService
from .interfaces.image_converter import IImageConverter
from .interfaces.file_handler import IFileHandler
from .interfaces.cache_manager import ICacheManager
from .error_handler import ErrorHandler
from .structured_logger import StructuredLogger
from ..domain.exceptions.base import ImageConverterError

T = TypeVar('T')


class DIContainer:
    """
    Dependency injection container that manages application dependencies.
    
    This container handles the creation, configuration, and lifecycle of all
    application services and components based on the application configuration.
    """
    
    def __init__(self, config: Optional[AppConfig] = None):
        """
        Initialize the DI container with configuration.
        
        Args:
            config: Application configuration. If None, loads from environment.
        """
        self._config = config or self._load_config()
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._singletons: Dict[str, Any] = {}
        
        # Initialize the container
        self._setup_container()
    
    def _load_config(self) -> AppConfig:
        """
        Load configuration from environment or use defaults.
        
        Returns:
            AppConfig instance
        """
        try:
            # Try to load from environment first
            if os.getenv('CONFIG_FILE'):
                return ConfigFactory.from_file(os.getenv('CONFIG_FILE'))
            else:
                return ConfigFactory.from_env()
        except Exception:
            # Fall back to default configuration
            return ConfigFactory.create_default_config()
    
    def _setup_container(self) -> None:
        """Set up the dependency injection container with all services."""
        # Ensure required directories exist
        self._config.ensure_directories()
        
        # Register core services
        self._register_core_services()
        
        # Register application services
        self._register_application_services()
        
        # Register infrastructure services
        self._register_infrastructure_services()
    
    def _register_core_services(self) -> None:
        """Register core services in the container."""
        # Configuration (singleton)
        self._register_singleton('config', lambda: self._config)
        
        # Service factory (singleton)
        self._register_singleton('service_factory', lambda: ServiceFactory(self._config))
        
        # Cache factory (singleton)
        self._register_singleton('cache_factory', lambda: CacheFactory(self._config))
        
        # Error handler (singleton)
        self._register_singleton('error_handler', self._create_error_handler)
        
        # Logger (singleton)
        self._register_singleton('logger', self._create_logger)
    
    def _register_application_services(self) -> None:
        """Register application-level services."""
        # Image conversion service (singleton)
        self._register_singleton('image_conversion_service', self._create_image_conversion_service)
        
        # File handler service (singleton)
        self._register_singleton('file_handler_service', self._create_file_handler_service)
        
        # Cache manager service (singleton)
        self._register_singleton('cache_manager_service', self._create_cache_manager_service)
    
    def _register_infrastructure_services(self) -> None:
        """Register infrastructure services."""
        # Image converter interface (singleton)
        self._register_singleton('image_converter', self._create_image_converter)
        
        # File handler interface (singleton)
        self._register_singleton('file_handler', self._create_file_handler)
        
        # Cache manager interface (singleton)
        self._register_singleton('cache_manager', self._create_cache_manager)
    
    def _register_singleton(self, name: str, factory: Callable[[], T]) -> None:
        """
        Register a singleton service in the container.
        
        Args:
            name: Service name
            factory: Factory function to create the service
        """
        self._factories[name] = factory
    
    def _register_transient(self, name: str, factory: Callable[[], T]) -> None:
        """
        Register a transient service in the container.
        
        Args:
            name: Service name
            factory: Factory function to create the service
        """
        self._services[name] = factory
    
    def get(self, service_name: str) -> Any:
        """
        Get a service from the container.
        
        Args:
            service_name: Name of the service to retrieve
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service is not registered
            
        Raises:
            ImageConverterError: If service is not registered or creation fails
        """
        try:
            # Check if it's a singleton
            if service_name in self._singletons:
                return self._singletons[service_name]
            
            # Check if it's a registered singleton factory
            if service_name in self._factories:
                service = self._factories[service_name]()
                self._singletons[service_name] = service
                return service
            
            # Check if it's a transient service
            if service_name in self._services:
                return self._services[service_name]()
            
            raise ImageConverterError(f"Service '{service_name}' is not registered")
            
        except Exception as e:
            if isinstance(e, ImageConverterError):
                raise
            raise ImageConverterError(f"Failed to create service '{service_name}': {str(e)}")
    
    def get_typed(self, service_type: Type[T]) -> T:
        """
        Get a service by its type.
        
        Args:
            service_type: Type of the service to retrieve
            
        Returns:
            Service instance of the specified type
        """
        # Map common types to service names
        type_mapping = {
            AppConfig: 'config',
            ServiceFactory: 'service_factory',
            CacheFactory: 'cache_factory',
            ErrorHandler: 'error_handler',
            StructuredLogger: 'logger',
            ImageConversionService: 'image_conversion_service',
            FileHandlerService: 'file_handler_service',
            CacheManagerService: 'cache_manager_service',
            IImageConverter: 'image_converter',
            IFileHandler: 'file_handler',
            ICacheManager: 'cache_manager'
        }
        
        service_name = type_mapping.get(service_type)
        if not service_name:
            raise ImageConverterError(f"No service registered for type {service_type.__name__}")
        
        return self.get(service_name)
    
    def _create_error_handler(self) -> ErrorHandler:
        """Create error handler with logger dependency."""
        logger = self.get('logger')
        return ErrorHandler(logger)
    
    def _create_logger(self) -> StructuredLogger:
        """Create structured logger based on configuration."""
        return StructuredLogger(
            name="image_converter",
            log_dir=str(self._config.log_dir_path),
            console_level=self._config.log_level,
            file_level=self._config.log_level
        )
    
    def _create_image_conversion_service(self) -> ImageConversionService:
        """Create image conversion service with all dependencies."""
        service_factory = self.get('service_factory')
        return service_factory.create_image_conversion_service()
    
    def _create_file_handler_service(self) -> FileHandlerService:
        """Create file handler service."""
        service_factory = self.get('service_factory')
        return service_factory.get_file_handler()
    
    def _create_cache_manager_service(self) -> CacheManagerService:
        """Create cache manager service."""
        service_factory = self.get('service_factory')
        return service_factory.get_cache_manager()
    
    def _create_image_converter(self) -> IImageConverter:
        """Create image converter interface implementation."""
        service_factory = self.get('service_factory')
        return service_factory.get_image_converter()
    
    def _create_file_handler(self) -> IFileHandler:
        """Create file handler interface implementation."""
        service_factory = self.get('service_factory')
        return service_factory.get_file_handler()
    
    def _create_cache_manager(self) -> ICacheManager:
        """Create cache manager interface implementation."""
        service_factory = self.get('service_factory')
        return service_factory.get_cache_manager()
    
    def register_service(self, name: str, service: Any) -> None:
        """
        Register a service instance in the container.
        
        Args:
            name: Service name
            service: Service instance
        """
        self._singletons[name] = service
    
    def register_factory(self, name: str, factory: Callable[[], T]) -> None:
        """
        Register a factory function for a service.
        
        Args:
            name: Service name
            factory: Factory function
        """
        self._factories[name] = factory
    
    def has_service(self, name: str) -> bool:
        """
        Check if a service is registered.
        
        Args:
            name: Service name
            
        Returns:
            True if service is registered, False otherwise
        """
        return (name in self._singletons or 
                name in self._factories or 
                name in self._services)
    
    def clear_singletons(self) -> None:
        """Clear all singleton instances (useful for testing)."""
        self._singletons.clear()
    
    def update_config(self, config: AppConfig) -> None:
        """
        Update the configuration and reset dependent services.
        
        Args:
            config: New configuration
        """
        self._config = config
        
        # Clear singletons that depend on configuration
        config_dependent_services = [
            'service_factory', 'cache_factory', 'error_handler', 'logger',
            'image_conversion_service', 'file_handler_service', 'cache_manager_service',
            'image_converter', 'file_handler', 'cache_manager'
        ]
        
        for service_name in config_dependent_services:
            if service_name in self._singletons:
                del self._singletons[service_name]
        
        # Update config singleton
        self._singletons['config'] = config
        
        # Ensure directories exist with new config
        config.ensure_directories()
    
    def get_config(self) -> AppConfig:
        """
        Get the current configuration.
        
        Returns:
            Current AppConfig instance
        """
        return self._config
    
    def create_child_container(self, overrides: Optional[Dict[str, Any]] = None) -> 'DIContainer':
        """
        Create a child container with optional service overrides.
        
        Args:
            overrides: Dictionary of service name to service instance overrides
            
        Returns:
            New DIContainer instance with overrides
        """
        child = DIContainer(self._config)
        
        if overrides:
            for name, service in overrides.items():
                child.register_service(name, service)
        
        return child
    
    @classmethod
    def create_default(cls) -> 'DIContainer':
        """
        Create a DI container with default configuration.
        
        Returns:
            DIContainer with default configuration
        """
        return cls()
    
    @classmethod
    def create_from_config_file(cls, config_file: str) -> 'DIContainer':
        """
        Create a DI container from a configuration file.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            DIContainer with configuration loaded from file
        """
        config = ConfigFactory.from_file(config_file)
        return cls(config)
    
    @classmethod
    def create_for_testing(cls, test_config: Optional[AppConfig] = None) -> 'DIContainer':
        """
        Create a DI container optimized for testing.
        
        Args:
            test_config: Optional test configuration
            
        Returns:
            DIContainer configured for testing
        """
        if test_config is None:
            # Create minimal test configuration
            test_config = AppConfig(
                cache_enabled=False,
                enable_file_logging=False,
                log_level="ERROR",
                enable_security_scan=False
            )
        
        return cls(test_config)
    
    def __repr__(self) -> str:
        """String representation of the container."""
        registered_services = list(self._factories.keys()) + list(self._services.keys())
        active_singletons = list(self._singletons.keys())
        
        return (f"DIContainer(registered_services={len(registered_services)}, "
                f"active_singletons={len(active_singletons)})")