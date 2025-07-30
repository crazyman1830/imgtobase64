#!/usr/bin/env python3
"""
Main entry point for the image base64 converter application.

This module provides the main entry point for the command line interface
of the image base64 converter. It uses dependency injection for better
architecture and maintainability.
"""
import sys
import os

# Add the src directory to the Python path to enable imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.cli import CLI
from src.core.container import DIContainer
from src.domain.exceptions.base import ImageConverterError


def create_application_container() -> DIContainer:
    """
    Create and configure the application's dependency injection container.
    
    Returns:
        Configured DIContainer instance
    """
    try:
        # Check if a config file is specified via environment variable
        config_file = os.getenv('CONFIG_FILE')
        
        if config_file and os.path.exists(config_file):
            # Load from config file
            container = DIContainer.create_from_config_file(config_file)
        else:
            # Load from environment or use defaults
            container = DIContainer.create_default()
        
        return container
        
    except Exception as e:
        print(f"Failed to initialize application container: {e}", file=sys.stderr)
        if os.getenv('DEBUG'):
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main() -> None:
    """
    Main entry point for the application.
    
    Creates the dependency injection container, initializes the CLI
    with all required services, and runs the application with
    comprehensive error handling.
    """
    container = None
    
    try:
        # Create the dependency injection container
        container = create_application_container()
        
        # Get logger for main application logging
        logger = container.get('logger')
        logger.info("Application starting", extra={
            "version": "1.0.0",
            "python_version": sys.version,
            "platform": sys.platform
        })
        
        # Create and run CLI with dependency injection
        cli = CLI(container=container)
        cli.run()
        
        logger.info("Application completed successfully")
        
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\nOperation cancelled by user", file=sys.stderr)
        if container:
            logger = container.get('logger')
            logger.info("Application cancelled by user")
        sys.exit(1)
        
    except ImageConverterError as e:
        # Handle application-specific errors
        if container:
            error_handler = container.get('error_handler')
            error_context = error_handler.handle_error(e, operation="main_application")
            print(f"Error: {error_context.user_message}", file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
        
    except SystemExit:
        # Re-raise SystemExit to preserve exit codes from CLI
        raise
        
    except Exception as e:
        # Handle unexpected errors
        if container:
            try:
                error_handler = container.get('error_handler')
                error_context = error_handler.handle_error(e, operation="main_application")
                print(f"Unexpected error: {error_context.user_message}", file=sys.stderr)
            except Exception:
                # Fallback if error handler fails
                print(f"Unexpected error: {e}", file=sys.stderr)
        else:
            print(f"Unexpected error: {e}", file=sys.stderr)
        
        if os.getenv('DEBUG'):
            import traceback
            traceback.print_exc()
        sys.exit(1)


def create_web_application():
    """
    Create a web application instance with dependency injection.
    
    This function is used by the web interface to get a properly
    configured application instance.
    
    Returns:
        Configured application container for web use
    """
    return create_application_container()


if __name__ == "__main__":
    main()