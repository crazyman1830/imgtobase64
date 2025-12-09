"""
Unified configuration management system.

This module provides a centralized configuration management system that
consolidates all configuration-related functionality and eliminates
duplication across the application.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ...domain.exceptions import FileSystemError, ValidationError
from ..utils.path_utils import PathUtils
from ..utils.type_utils import TypeUtils
from ..utils.validation_utils import ValidationUtils


class ConfigSource(Enum):
    """Configuration source types."""
    DEFAULT = "default"
    FILE = "file"
    ENVIRONMENT = "environment"
    OVERRIDE = "override"


@dataclass
class ConfigValue:
    """Represents a configuration value with metadata."""
    value: Any
    source: ConfigSource
    key_path: str
    description: Optional[str] = None
    
    def __str__(self) -> str:
        return f"{self.key_path}={self.value} (from {self.source.value})"


class UnifiedConfigManager:
    """
    Unified configuration manager that consolidates all configuration logic.
    
    This manager provides:
    - Centralized configuration loading from multiple sources
    - Priority-based configuration merging
    - Type validation and conversion
    - Configuration change tracking
    - Environment variable mapping
    """
    
    # Default configuration schema with types and descriptions
    DEFAULT_SCHEMA = {
        'app.name': {
            'default': 'Image Base64 Converter',
            'type': str,
            'description': 'Application name'
        },
        'app.version': {
            'default': '2.0.0',
            'type': str,
            'description': 'Application version'
        },
        'app.environment': {
            'default': 'development',
            'type': str,
            'choices': ['development', 'production', 'testing'],
            'description': 'Application environment'
        },
        
        # File processing settings
        'processing.max_file_size_mb': {
            'default': 10,
            'type': int,
            'min_value': 1,
            'max_value': 1000,
            'description': 'Maximum file size in megabytes'
        },
        'processing.supported_formats': {
            'default': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'],
            'type': list,
            'description': 'List of supported image file extensions'
        },
        'processing.max_concurrent_files': {
            'default': 3,
            'type': int,
            'min_value': 1,
            'max_value': 20,
            'description': 'Maximum number of files to process concurrently'
        },
        'processing.enable_memory_optimization': {
            'default': True,
            'type': bool,
            'description': 'Enable memory optimization features'
        },
        'processing.streaming_chunk_size_kb': {
            'default': 64,
            'type': int,
            'min_value': 1,
            'max_value': 1024,
            'description': 'Chunk size for streaming file processing in KB'
        },
        
        # Cache settings
        'cache.enabled': {
            'default': True,
            'type': bool,
            'description': 'Enable or disable caching'
        },
        'cache.backend': {
            'default': 'disk',
            'type': str,
            'choices': ['memory', 'disk', 'redis', 'disabled'],
            'description': 'Cache backend type'
        },
        'cache.directory': {
            'default': 'cache',
            'type': str,
            'description': 'Cache directory path'
        },
        'cache.max_size_mb': {
            'default': 100,
            'type': int,
            'min_value': 1,
            'max_value': 10000,
            'description': 'Maximum cache size in megabytes'
        },
        'cache.max_age_hours': {
            'default': 24,
            'type': int,
            'min_value': 1,
            'max_value': 8760,  # 1 year
            'description': 'Maximum age of cache entries in hours'
        },
        'cache.cleanup_interval_minutes': {
            'default': 60,
            'type': int,
            'min_value': 1,
            'max_value': 1440,  # 1 day
            'description': 'Cache cleanup interval in minutes'
        },
        
        # Logging settings
        'logging.level': {
            'default': 'INFO',
            'type': str,
            'choices': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            'description': 'Logging level'
        },
        'logging.directory': {
            'default': 'logs',
            'type': str,
            'description': 'Log files directory'
        },
        'logging.enable_file_logging': {
            'default': True,
            'type': bool,
            'description': 'Enable logging to files'
        },
        'logging.enable_structured_logging': {
            'default': True,
            'type': bool,
            'description': 'Enable structured logging format'
        },
        'logging.max_file_size_mb': {
            'default': 10,
            'type': int,
            'min_value': 1,
            'max_value': 100,
            'description': 'Maximum log file size in megabytes'
        },
        'logging.backup_count': {
            'default': 5,
            'type': int,
            'min_value': 1,
            'max_value': 50,
            'description': 'Number of log file backups to keep'
        },
        
        # Web interface settings
        'web.enabled': {
            'default': True,
            'type': bool,
            'description': 'Enable web interface'
        },
        'web.host': {
            'default': '0.0.0.0',
            'type': str,
            'description': 'Web interface host address'
        },
        'web.port': {
            'default': 5000,
            'type': int,
            'min_value': 1,
            'max_value': 65535,
            'description': 'Web interface port number'
        },
        'web.debug': {
            'default': False,
            'type': bool,
            'description': 'Enable web interface debug mode'
        },
        'web.max_content_length_mb': {
            'default': 16,
            'type': int,
            'min_value': 1,
            'max_value': 100,
            'description': 'Maximum HTTP request content length in megabytes'
        },
        
        # Security settings
        'security.enable_content_scan': {
            'default': True,
            'type': bool,
            'description': 'Enable security scanning of uploaded files'
        },
        'security.rate_limit_per_minute': {
            'default': 60,
            'type': int,
            'min_value': 1,
            'max_value': 1000,
            'description': 'Maximum requests per minute per client'
        },
        'security.allowed_mime_types': {
            'default': ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'],
            'type': list,
            'description': 'List of allowed MIME types'
        },
        
        # Directory settings
        'directories.temp': {
            'default': 'temp',
            'type': str,
            'description': 'Temporary files directory'
        },
        'directories.data': {
            'default': 'data',
            'type': str,
            'description': 'Data storage directory'
        }
    }
    
    # Environment variable mappings
    ENV_MAPPINGS = {
        'IMG_CONVERTER_MAX_FILE_SIZE_MB': 'processing.max_file_size_mb',
        'IMG_CONVERTER_CACHE_ENABLED': 'cache.enabled',
        'IMG_CONVERTER_CACHE_DIR': 'cache.directory',
        'IMG_CONVERTER_CACHE_MAX_SIZE_MB': 'cache.max_size_mb',
        'IMG_CONVERTER_LOG_LEVEL': 'logging.level',
        'IMG_CONVERTER_LOG_DIR': 'logging.directory',
        'IMG_CONVERTER_WEB_HOST': 'web.host',
        'IMG_CONVERTER_WEB_PORT': 'web.port',
        'IMG_CONVERTER_WEB_DEBUG': 'web.debug',
        'IMG_CONVERTER_TEMP_DIR': 'directories.temp',
        'IMG_CONVERTER_DATA_DIR': 'directories.data',
        'IMG_CONVERTER_ENVIRONMENT': 'app.environment',
        'IMG_CONVERTER_ENABLE_SECURITY_SCAN': 'security.enable_content_scan',
        'IMG_CONVERTER_RATE_LIMIT_PER_MINUTE': 'security.rate_limit_per_minute'
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the unified configuration manager.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = config_file
        self._config_values: Dict[str, ConfigValue] = {}
        self._loaded = False
        self._change_listeners: List[callable] = []
    
    def load_configuration(self) -> None:
        """Load configuration from all sources in priority order."""
        if self._loaded:
            return
        
        # 1. Load default values
        self._load_defaults()
        
        # 2. Load from configuration file
        if self.config_file and Path(self.config_file).exists():
            self._load_from_file(self.config_file)
        
        # 3. Load from environment variables (highest priority)
        self._load_from_environment()
        
        # 4. Validate all configuration values
        self._validate_configuration()
        
        # 5. Ensure required directories exist
        self._ensure_directories()
        
        self._loaded = True
    
    def _load_defaults(self) -> None:
        """Load default configuration values."""
        for key_path, schema in self.DEFAULT_SCHEMA.items():
            self._config_values[key_path] = ConfigValue(
                value=schema['default'],
                source=ConfigSource.DEFAULT,
                key_path=key_path,
                description=schema.get('description')
            )
    
    def _load_from_file(self, file_path: str) -> None:
        """Load configuration from a JSON file."""
        try:
            config_path = PathUtils.normalize_path(file_path)
            
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            
            if not isinstance(file_config, dict):
                raise ValidationError("Configuration file must contain a JSON object")
            
            # Flatten nested configuration
            flattened = TypeUtils.flatten_dict(file_config)
            
            # Update configuration values
            for key, value in flattened.items():
                if key in self.DEFAULT_SCHEMA:
                    self._config_values[key] = ConfigValue(
                        value=value,
                        source=ConfigSource.FILE,
                        key_path=key,
                        description=self.DEFAULT_SCHEMA[key].get('description')
                    )
                    
        except Exception as e:
            print(f"Warning: Could not load configuration file {file_path}: {e}")
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        for env_var, config_key in self.ENV_MAPPINGS.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # Convert environment variable value to appropriate type
                    schema = self.DEFAULT_SCHEMA.get(config_key, {})
                    target_type = schema.get('type', str)
                    
                    converted_value = TypeUtils.coerce_to_type(env_value, target_type.__name__)
                    
                    self._config_values[config_key] = ConfigValue(
                        value=converted_value,
                        source=ConfigSource.ENVIRONMENT,
                        key_path=config_key,
                        description=schema.get('description')
                    )
                    
                except Exception as e:
                    print(f"Warning: Invalid environment variable {env_var}={env_value}: {e}")
    
    def _validate_configuration(self) -> None:
        """Validate all configuration values against their schemas."""
        for key_path, config_value in self._config_values.items():
            schema = self.DEFAULT_SCHEMA.get(key_path, {})
            
            try:
                # Type validation
                expected_type = schema.get('type')
                if expected_type and not isinstance(config_value.value, expected_type):
                    # Try to convert
                    config_value.value = TypeUtils.safe_cast(
                        config_value.value, expected_type, schema['default']
                    )
                
                # Range validation for numeric values
                if isinstance(config_value.value, (int, float)):
                    min_value = schema.get('min_value')
                    max_value = schema.get('max_value')
                    
                    if min_value is not None:
                        ValidationUtils.validate_range(
                            config_value.value, min_value=min_value, field_name=key_path
                        )
                    
                    if max_value is not None:
                        ValidationUtils.validate_range(
                            config_value.value, max_value=max_value, field_name=key_path
                        )
                
                # Choice validation
                choices = schema.get('choices')
                if choices:
                    ValidationUtils.validate_choice(
                        config_value.value, choices, field_name=key_path
                    )
                
            except ValidationError as e:
                print(f"Warning: Invalid configuration value for {key_path}: {e}")
                # Reset to default value
                config_value.value = schema['default']
                config_value.source = ConfigSource.DEFAULT
    
    def _ensure_directories(self) -> None:
        """Ensure all configured directories exist."""
        directory_keys = [
            'cache.directory',
            'logging.directory', 
            'directories.temp',
            'directories.data'
        ]
        
        for key in directory_keys:
            if key in self._config_values:
                directory_path = self._config_values[key].value
                try:
                    PathUtils.ensure_directory_exists(directory_path)
                except FileSystemError as e:
                    print(f"Warning: Could not create directory for {key}: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value by key path."""
        if not self._loaded:
            self.load_configuration()
        
        config_value = self._config_values.get(key_path)
        if config_value is not None:
            return config_value.value
        
        return default
    
    def set(self, key_path: str, value: Any, source: ConfigSource = ConfigSource.OVERRIDE) -> None:
        """Set a configuration value."""
        if not self._loaded:
            self.load_configuration()
        
        # Validate against schema if available
        schema = self.DEFAULT_SCHEMA.get(key_path, {})
        if schema:
            expected_type = schema.get('type')
            if expected_type:
                value = TypeUtils.safe_cast(value, expected_type, value)
        
        old_value = self._config_values.get(key_path)
        
        self._config_values[key_path] = ConfigValue(
            value=value,
            source=source,
            key_path=key_path,
            description=schema.get('description')
        )
        
        # Notify change listeners
        self._notify_change_listeners(key_path, old_value.value if old_value else None, value)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values as a flat dictionary."""
        if not self._loaded:
            self.load_configuration()
        
        return {key: config_value.value for key, config_value in self._config_values.items()}
    
    def get_nested(self) -> Dict[str, Any]:
        """Get all configuration values as a nested dictionary."""
        flat_config = self.get_all()
        return TypeUtils.unflatten_dict(flat_config)
    
    def get_config_info(self, key_path: str) -> Optional[ConfigValue]:
        """Get detailed information about a configuration value."""
        if not self._loaded:
            self.load_configuration()
        
        return self._config_values.get(key_path)
    
    def list_all_config_info(self) -> Dict[str, ConfigValue]:
        """Get detailed information about all configuration values."""
        if not self._loaded:
            self.load_configuration()
        
        return self._config_values.copy()
    
    def save_to_file(self, file_path: str) -> None:
        """Save current configuration to a file."""
        if not self._loaded:
            self.load_configuration()
        
        config_dict = self.get_nested()
        
        try:
            config_path = PathUtils.normalize_path(file_path)
            PathUtils.ensure_directory_exists(config_path.parent)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise FileSystemError(f"Error saving configuration to {file_path}: {e}")
    
    def reload(self) -> None:
        """Reload configuration from all sources."""
        self._config_values.clear()
        self._loaded = False
        self.load_configuration()
    
    def add_change_listener(self, listener: callable) -> None:
        """Add a listener for configuration changes."""
        self._change_listeners.append(listener)
    
    def remove_change_listener(self, listener: callable) -> None:
        """Remove a configuration change listener."""
        if listener in self._change_listeners:
            self._change_listeners.remove(listener)
    
    def _notify_change_listeners(self, key_path: str, old_value: Any, new_value: Any) -> None:
        """Notify all change listeners of a configuration change."""
        for listener in self._change_listeners:
            try:
                listener(key_path, old_value, new_value)
            except Exception as e:
                print(f"Warning: Configuration change listener failed: {e}")
    
    def create_sample_config_file(self, file_path: str = 'config.json') -> None:
        """Create a sample configuration file with all available options."""
        sample_config = {}
        
        for key_path, schema in self.DEFAULT_SCHEMA.items():
            # Create nested structure
            TypeUtils.set_nested_value(
                sample_config, 
                key_path, 
                {
                    'value': schema['default'],
                    'description': schema.get('description', ''),
                    'type': schema['type'].__name__,
                    'choices': schema.get('choices'),
                    'min_value': schema.get('min_value'),
                    'max_value': schema.get('max_value')
                }
            )
        
        try:
            config_path = PathUtils.normalize_path(file_path)
            PathUtils.ensure_directory_exists(config_path.parent)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(sample_config, f, indent=2, ensure_ascii=False)
            
            print(f"Sample configuration file created: {file_path}")
            
        except Exception as e:
            print(f"Error creating sample configuration file: {e}")
    
    def validate_config_file(self, file_path: str) -> List[str]:
        """Validate a configuration file and return any errors."""
        errors = []
        
        try:
            config_path = PathUtils.normalize_path(file_path)
            
            if not config_path.exists():
                errors.append(f"Configuration file not found: {file_path}")
                return errors
            
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            
            if not isinstance(file_config, dict):
                errors.append("Configuration file must contain a JSON object")
                return errors
            
            # Validate each configuration value
            flattened = TypeUtils.flatten_dict(file_config)
            
            for key, value in flattened.items():
                if key not in self.DEFAULT_SCHEMA:
                    errors.append(f"Unknown configuration key: {key}")
                    continue
                
                schema = self.DEFAULT_SCHEMA[key]
                
                # Type validation
                expected_type = schema.get('type')
                if expected_type and not isinstance(value, expected_type):
                    errors.append(
                        f"Invalid type for {key}: expected {expected_type.__name__}, "
                        f"got {type(value).__name__}"
                    )
                
                # Range validation
                if isinstance(value, (int, float)):
                    min_value = schema.get('min_value')
                    max_value = schema.get('max_value')
                    
                    if min_value is not None and value < min_value:
                        errors.append(f"Value for {key} is below minimum: {value} < {min_value}")
                    
                    if max_value is not None and value > max_value:
                        errors.append(f"Value for {key} is above maximum: {value} > {max_value}")
                
                # Choice validation
                choices = schema.get('choices')
                if choices and value not in choices:
                    errors.append(f"Invalid choice for {key}: {value} not in {choices}")
            
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            errors.append(f"Error validating configuration file: {e}")
        
        return errors


# Global configuration manager instance
_global_config_manager: Optional[UnifiedConfigManager] = None


def get_config_manager(config_file: Optional[str] = None) -> UnifiedConfigManager:
    """Get the global configuration manager instance."""
    global _global_config_manager
    
    if _global_config_manager is None:
        _global_config_manager = UnifiedConfigManager(config_file)
    
    return _global_config_manager


def get_config(key_path: str, default: Any = None) -> Any:
    """Get a configuration value using the global manager."""
    return get_config_manager().get(key_path, default)


def set_config(key_path: str, value: Any) -> None:
    """Set a configuration value using the global manager."""
    get_config_manager().set(key_path, value)


def reload_config() -> None:
    """Reload configuration using the global manager."""
    get_config_manager().reload()