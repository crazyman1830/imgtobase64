"""
Configuration factory for creating AppConfig instances.

This module provides factory methods for loading configuration from
various sources including environment variables and files.
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

from .app_config import AppConfig


class ConfigFactory:
    """
    Factory class for creating AppConfig instances from various sources.
    
    Supports loading configuration from:
    1. Environment variables
    2. JSON configuration files
    3. Default values
    """
    
    @staticmethod
    def from_env() -> AppConfig:
        """
        Create AppConfig from environment variables.
        
        Environment variables are mapped to configuration keys with the
        prefix 'IMG_CONVERTER_' (e.g., IMG_CONVERTER_MAX_FILE_SIZE_MB).
        
        Returns:
            AppConfig instance with values from environment variables
        """
        env_config = {}
        
        # Define environment variable mappings
        env_mappings = {
            'IMG_CONVERTER_MAX_FILE_SIZE_MB': ('max_file_size_mb', int),
            'IMG_CONVERTER_CACHE_ENABLED': ('cache_enabled', lambda x: x.lower() == 'true'),
            'IMG_CONVERTER_CACHE_DIR': ('cache_dir', str),
            'IMG_CONVERTER_CACHE_MAX_SIZE_MB': ('cache_max_size_mb', int),
            'IMG_CONVERTER_CACHE_MAX_AGE_HOURS': ('cache_max_age_hours', int),
            'IMG_CONVERTER_LOG_LEVEL': ('log_level', str),
            'IMG_CONVERTER_LOG_DIR': ('log_dir', str),
            'IMG_CONVERTER_ENABLE_FILE_LOGGING': ('enable_file_logging', lambda x: x.lower() == 'true'),
            'IMG_CONVERTER_MAX_CONCURRENT_FILES': ('max_concurrent_files', int),
            'IMG_CONVERTER_ENABLE_MEMORY_OPTIMIZATION': ('enable_memory_optimization', lambda x: x.lower() == 'true'),
            'IMG_CONVERTER_WEB_HOST': ('web_host', str),
            'IMG_CONVERTER_WEB_PORT': ('web_port', int),
            'IMG_CONVERTER_WEB_DEBUG': ('web_debug', lambda x: x.lower() == 'true'),
            'IMG_CONVERTER_ENABLE_SECURITY_SCAN': ('enable_security_scan', lambda x: x.lower() == 'true'),
            'IMG_CONVERTER_RATE_LIMIT_PER_MINUTE': ('rate_limit_per_minute', int),
            'IMG_CONVERTER_TEMP_DIR': ('temp_dir', str),
            'IMG_CONVERTER_DATA_DIR': ('data_dir', str),
        }
        
        # Process environment variables
        for env_var, (config_key, converter) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    env_config[config_key] = converter(env_value)
                except (ValueError, TypeError) as e:
                    print(f"Warning: Invalid value for {env_var}: {env_value} ({e})")
        
        # Handle supported formats (comma-separated list)
        supported_formats_env = os.getenv('IMG_CONVERTER_SUPPORTED_FORMATS')
        if supported_formats_env:
            try:
                formats = [fmt.strip() for fmt in supported_formats_env.split(',')]
                env_config['supported_formats'] = formats
            except Exception as e:
                print(f"Warning: Invalid supported formats: {supported_formats_env} ({e})")
        
        return AppConfig.from_dict(env_config)
    
    @staticmethod
    def from_file(file_path: str) -> AppConfig:
        """
        Create AppConfig from a JSON configuration file.
        
        Args:
            file_path: Path to the JSON configuration file
            
        Returns:
            AppConfig instance with values from the file
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the file contains invalid JSON or configuration
        """
        config_path = Path(file_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            if not isinstance(config_dict, dict):
                raise ValueError("Configuration file must contain a JSON object")
            
            return AppConfig.from_dict(config_dict)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ValueError(f"Error reading configuration file: {e}")
    
    @staticmethod
    def from_env_and_file(file_path: Optional[str] = None) -> AppConfig:
        """
        Create AppConfig from both environment variables and file.
        
        Environment variables take precedence over file settings.
        If no file is provided, looks for 'config.json' in the current directory.
        
        Args:
            file_path: Optional path to configuration file
            
        Returns:
            AppConfig instance with merged configuration
        """
        # Start with default configuration
        config_dict = {}
        
        # Load from file if available
        if file_path is None:
            file_path = 'config.json'
        
        if os.path.exists(file_path):
            try:
                file_config = ConfigFactory.from_file(file_path)
                config_dict.update(file_config.to_dict())
            except Exception as e:
                print(f"Warning: Could not load config file {file_path}: {e}")
        
        # Override with environment variables
        try:
            env_config = ConfigFactory.from_env()
            config_dict.update(env_config.to_dict())
        except Exception as e:
            print(f"Warning: Error loading environment configuration: {e}")
        
        return AppConfig.from_dict(config_dict)
    
    @staticmethod
    def create_default() -> AppConfig:
        """
        Create AppConfig with default values only.
        
        Returns:
            AppConfig instance with default configuration
        """
        return AppConfig()
    
    @staticmethod
    def save_to_file(config: AppConfig, file_path: str) -> None:
        """
        Save AppConfig to a JSON file.
        
        Args:
            config: AppConfig instance to save
            file_path: Path where to save the configuration file
            
        Raises:
            ValueError: If the configuration cannot be serialized
            IOError: If the file cannot be written
        """
        try:
            config_dict = config.to_dict()
            
            # Ensure directory exists
            config_path = Path(file_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise IOError(f"Error saving configuration to {file_path}: {e}")
    
    @staticmethod
    def create_sample_config_file(file_path: str = 'config.json') -> None:
        """
        Create a sample configuration file with default values and comments.
        
        Args:
            file_path: Path where to create the sample configuration file
        """
        sample_config = {
            "_comment": "Image Converter Configuration File",
            "_description": "This file contains configuration settings for the image converter application",
            
            "max_file_size_mb": 10,
            "_max_file_size_mb_comment": "Maximum file size in megabytes",
            
            "supported_formats": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],
            "_supported_formats_comment": "List of supported image file extensions",
            
            "cache_enabled": True,
            "_cache_enabled_comment": "Enable or disable caching",
            
            "cache_dir": "cache",
            "_cache_dir_comment": "Directory for cache storage",
            
            "cache_max_size_mb": 100,
            "_cache_max_size_mb_comment": "Maximum cache size in megabytes",
            
            "cache_max_age_hours": 24,
            "_cache_max_age_hours_comment": "Maximum age of cache entries in hours",
            
            "log_level": "INFO",
            "_log_level_comment": "Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
            
            "log_dir": "logs",
            "_log_dir_comment": "Directory for log files",
            
            "enable_file_logging": True,
            "_enable_file_logging_comment": "Enable logging to files",
            
            "max_concurrent_files": 3,
            "_max_concurrent_files_comment": "Maximum number of files to process concurrently",
            
            "enable_memory_optimization": True,
            "_enable_memory_optimization_comment": "Enable memory optimization features",
            
            "web_host": "0.0.0.0",
            "_web_host_comment": "Web interface host address",
            
            "web_port": 5000,
            "_web_port_comment": "Web interface port number",
            
            "web_debug": False,
            "_web_debug_comment": "Enable web interface debug mode",
            
            "enable_security_scan": True,
            "_enable_security_scan_comment": "Enable security scanning of uploaded files",
            
            "rate_limit_per_minute": 60,
            "_rate_limit_per_minute_comment": "Maximum requests per minute per client",
            
            "temp_dir": "temp",
            "_temp_dir_comment": "Temporary files directory",
            
            "data_dir": "data",
            "_data_dir_comment": "Data storage directory"
        }
        
        try:
            config_path = Path(file_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(sample_config, f, indent=2, ensure_ascii=False)
            
            print(f"Sample configuration file created: {file_path}")
            
        except Exception as e:
            print(f"Error creating sample configuration file: {e}")