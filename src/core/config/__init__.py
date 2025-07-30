"""
Configuration management system.

This module provides configuration management functionality for the
image converter application.
"""

# Core configuration classes
from .app_config import AppConfig
from .config_factory import ConfigFactory

__all__ = [
    # Core interfaces
    'AppConfig',
    'ConfigFactory'
]