"""
Unified configuration management system.

This module provides a centralized configuration management system that
consolidates all configuration-related functionality and eliminates
duplication across the application.
"""

import os
import json
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum

from ..utils.path_utils import PathUtils
from ..utils.validation_utils import ValidationUtils
from ..utils.type_utils import TypeUtils
from ...domain.exceptions import ValidationError, FileSystemError


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
            print(f"Warning: Could not load configuration file {file_path}: {e}")\n    \n    def _load_from_environment(self) -> None:\n        \"\"\"Load configuration from environment variables.\"\"\"\n        for env_var, config_key in self.ENV_MAPPINGS.items():\n            env_value = os.getenv(env_var)\n            if env_value is not None:\n                try:\n                    # Convert environment variable value to appropriate type\n                    schema = self.DEFAULT_SCHEMA.get(config_key, {})\n                    target_type = schema.get('type', str)\n                    \n                    converted_value = TypeUtils.coerce_to_type(env_value, target_type.__name__)\n                    \n                    self._config_values[config_key] = ConfigValue(\n                        value=converted_value,\n                        source=ConfigSource.ENVIRONMENT,\n                        key_path=config_key,\n                        description=schema.get('description')\n                    )\n                    \n                except Exception as e:\n                    print(f\"Warning: Invalid environment variable {env_var}={env_value}: {e}\")\n    \n    def _validate_configuration(self) -> None:\n        \"\"\"Validate all configuration values against their schemas.\"\"\"\n        for key_path, config_value in self._config_values.items():\n            schema = self.DEFAULT_SCHEMA.get(key_path, {})\n            \n            try:\n                # Type validation\n                expected_type = schema.get('type')\n                if expected_type and not isinstance(config_value.value, expected_type):\n                    # Try to convert\n                    config_value.value = TypeUtils.safe_cast(\n                        config_value.value, expected_type, schema['default']\n                    )\n                \n                # Range validation for numeric values\n                if isinstance(config_value.value, (int, float)):\n                    min_value = schema.get('min_value')\n                    max_value = schema.get('max_value')\n                    \n                    if min_value is not None:\n                        ValidationUtils.validate_range(\n                            config_value.value, min_value=min_value, field_name=key_path\n                        )\n                    \n                    if max_value is not None:\n                        ValidationUtils.validate_range(\n                            config_value.value, max_value=max_value, field_name=key_path\n                        )\n                \n                # Choice validation\n                choices = schema.get('choices')\n                if choices:\n                    ValidationUtils.validate_choice(\n                        config_value.value, choices, field_name=key_path\n                    )\n                \n            except ValidationError as e:\n                print(f\"Warning: Invalid configuration value for {key_path}: {e}\")\n                # Reset to default value\n                config_value.value = schema['default']\n                config_value.source = ConfigSource.DEFAULT\n    \n    def _ensure_directories(self) -> None:\n        \"\"\"Ensure all configured directories exist.\"\"\"\n        directory_keys = [\n            'cache.directory',\n            'logging.directory', \n            'directories.temp',\n            'directories.data'\n        ]\n        \n        for key in directory_keys:\n            if key in self._config_values:\n                directory_path = self._config_values[key].value\n                try:\n                    PathUtils.ensure_directory_exists(directory_path)\n                except FileSystemError as e:\n                    print(f\"Warning: Could not create directory for {key}: {e}\")\n    \n    def get(self, key_path: str, default: Any = None) -> Any:\n        \"\"\"Get a configuration value by key path.\"\"\"\n        if not self._loaded:\n            self.load_configuration()\n        \n        config_value = self._config_values.get(key_path)\n        if config_value is not None:\n            return config_value.value\n        \n        return default\n    \n    def set(self, key_path: str, value: Any, source: ConfigSource = ConfigSource.OVERRIDE) -> None:\n        \"\"\"Set a configuration value.\"\"\"\n        if not self._loaded:\n            self.load_configuration()\n        \n        # Validate against schema if available\n        schema = self.DEFAULT_SCHEMA.get(key_path, {})\n        if schema:\n            expected_type = schema.get('type')\n            if expected_type:\n                value = TypeUtils.safe_cast(value, expected_type, value)\n        \n        old_value = self._config_values.get(key_path)\n        \n        self._config_values[key_path] = ConfigValue(\n            value=value,\n            source=source,\n            key_path=key_path,\n            description=schema.get('description')\n        )\n        \n        # Notify change listeners\n        self._notify_change_listeners(key_path, old_value.value if old_value else None, value)\n    \n    def get_all(self) -> Dict[str, Any]:\n        \"\"\"Get all configuration values as a flat dictionary.\"\"\"\n        if not self._loaded:\n            self.load_configuration()\n        \n        return {key: config_value.value for key, config_value in self._config_values.items()}\n    \n    def get_nested(self) -> Dict[str, Any]:\n        \"\"\"Get all configuration values as a nested dictionary.\"\"\"\n        flat_config = self.get_all()\n        return TypeUtils.unflatten_dict(flat_config)\n    \n    def get_config_info(self, key_path: str) -> Optional[ConfigValue]:\n        \"\"\"Get detailed information about a configuration value.\"\"\"\n        if not self._loaded:\n            self.load_configuration()\n        \n        return self._config_values.get(key_path)\n    \n    def list_all_config_info(self) -> Dict[str, ConfigValue]:\n        \"\"\"Get detailed information about all configuration values.\"\"\"\n        if not self._loaded:\n            self.load_configuration()\n        \n        return self._config_values.copy()\n    \n    def save_to_file(self, file_path: str) -> None:\n        \"\"\"Save current configuration to a file.\"\"\"\n        if not self._loaded:\n            self.load_configuration()\n        \n        config_dict = self.get_nested()\n        \n        try:\n            config_path = PathUtils.normalize_path(file_path)\n            PathUtils.ensure_directory_exists(config_path.parent)\n            \n            with open(config_path, 'w', encoding='utf-8') as f:\n                json.dump(config_dict, f, indent=2, ensure_ascii=False)\n                \n        except Exception as e:\n            raise FileSystemError(f\"Error saving configuration to {file_path}: {e}\")\n    \n    def reload(self) -> None:\n        \"\"\"Reload configuration from all sources.\"\"\"\n        self._config_values.clear()\n        self._loaded = False\n        self.load_configuration()\n    \n    def add_change_listener(self, listener: callable) -> None:\n        \"\"\"Add a listener for configuration changes.\"\"\"\n        self._change_listeners.append(listener)\n    \n    def remove_change_listener(self, listener: callable) -> None:\n        \"\"\"Remove a configuration change listener.\"\"\"\n        if listener in self._change_listeners:\n            self._change_listeners.remove(listener)\n    \n    def _notify_change_listeners(self, key_path: str, old_value: Any, new_value: Any) -> None:\n        \"\"\"Notify all change listeners of a configuration change.\"\"\"\n        for listener in self._change_listeners:\n            try:\n                listener(key_path, old_value, new_value)\n            except Exception as e:\n                print(f\"Warning: Configuration change listener failed: {e}\")\n    \n    def create_sample_config_file(self, file_path: str = 'config.json') -> None:\n        \"\"\"Create a sample configuration file with all available options.\"\"\"\n        sample_config = {}\n        \n        for key_path, schema in self.DEFAULT_SCHEMA.items():\n            # Create nested structure\n            TypeUtils.set_nested_value(\n                sample_config, \n                key_path, \n                {\n                    'value': schema['default'],\n                    'description': schema.get('description', ''),\n                    'type': schema['type'].__name__,\n                    'choices': schema.get('choices'),\n                    'min_value': schema.get('min_value'),\n                    'max_value': schema.get('max_value')\n                }\n            )\n        \n        try:\n            config_path = PathUtils.normalize_path(file_path)\n            PathUtils.ensure_directory_exists(config_path.parent)\n            \n            with open(config_path, 'w', encoding='utf-8') as f:\n                json.dump(sample_config, f, indent=2, ensure_ascii=False)\n            \n            print(f\"Sample configuration file created: {file_path}\")\n            \n        except Exception as e:\n            print(f\"Error creating sample configuration file: {e}\")\n    \n    def validate_config_file(self, file_path: str) -> List[str]:\n        \"\"\"Validate a configuration file and return any errors.\"\"\"\n        errors = []\n        \n        try:\n            config_path = PathUtils.normalize_path(file_path)\n            \n            if not config_path.exists():\n                errors.append(f\"Configuration file not found: {file_path}\")\n                return errors\n            \n            with open(config_path, 'r', encoding='utf-8') as f:\n                file_config = json.load(f)\n            \n            if not isinstance(file_config, dict):\n                errors.append(\"Configuration file must contain a JSON object\")\n                return errors\n            \n            # Validate each configuration value\n            flattened = TypeUtils.flatten_dict(file_config)\n            \n            for key, value in flattened.items():\n                if key not in self.DEFAULT_SCHEMA:\n                    errors.append(f\"Unknown configuration key: {key}\")\n                    continue\n                \n                schema = self.DEFAULT_SCHEMA[key]\n                \n                # Type validation\n                expected_type = schema.get('type')\n                if expected_type and not isinstance(value, expected_type):\n                    errors.append(\n                        f\"Invalid type for {key}: expected {expected_type.__name__}, \"\n                        f\"got {type(value).__name__}\"\n                    )\n                \n                # Range validation\n                if isinstance(value, (int, float)):\n                    min_value = schema.get('min_value')\n                    max_value = schema.get('max_value')\n                    \n                    if min_value is not None and value < min_value:\n                        errors.append(f\"Value for {key} is below minimum: {value} < {min_value}\")\n                    \n                    if max_value is not None and value > max_value:\n                        errors.append(f\"Value for {key} is above maximum: {value} > {max_value}\")\n                \n                # Choice validation\n                choices = schema.get('choices')\n                if choices and value not in choices:\n                    errors.append(f\"Invalid choice for {key}: {value} not in {choices}\")\n            \n        except json.JSONDecodeError as e:\n            errors.append(f\"Invalid JSON in configuration file: {e}\")\n        except Exception as e:\n            errors.append(f\"Error validating configuration file: {e}\")\n        \n        return errors\n\n\n# Global configuration manager instance\n_global_config_manager: Optional[UnifiedConfigManager] = None\n\n\ndef get_config_manager(config_file: Optional[str] = None) -> UnifiedConfigManager:\n    \"\"\"Get the global configuration manager instance.\"\"\"\n    global _global_config_manager\n    \n    if _global_config_manager is None:\n        _global_config_manager = UnifiedConfigManager(config_file)\n    \n    return _global_config_manager\n\n\ndef get_config(key_path: str, default: Any = None) -> Any:\n    \"\"\"Get a configuration value using the global manager.\"\"\"\n    return get_config_manager().get(key_path, default)\n\n\ndef set_config(key_path: str, value: Any) -> None:\n    \"\"\"Set a configuration value using the global manager.\"\"\"\n    get_config_manager().set(key_path, value)\n\n\ndef reload_config() -> None:\n    \"\"\"Reload configuration using the global manager.\"\"\"\n    get_config_manager().reload()