#!/usr/bin/env python3
"""
Main entry point for the image base64 converter application.

This module provides the main entry point for the command line interface
of the image base64 converter. It handles global exception handling and
initializes the CLI application.
"""
import sys
import os

# Add the src directory to the Python path to enable imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.cli import CLI
from src.converter import ImageConverter
from src.file_handler import FileHandler
from src.models import ImageConverterError


def main() -> None:
    """
    Main entry point for the application.
    
    Creates CLI instance with dependencies and runs the application
    with global exception handling.
    """
    try:
        # Create dependencies
        converter = ImageConverter()
        file_handler = FileHandler()
        
        # Create and run CLI
        cli = CLI(converter=converter, file_handler=file_handler)
        cli.run()
        
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
        
    except ImageConverterError as e:
        # Handle application-specific errors
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
        
    except SystemExit:
        # Re-raise SystemExit to preserve exit codes from CLI
        raise
        
    except Exception as e:
        # Handle unexpected errors
        print(f"Unexpected error: {e}", file=sys.stderr)
        if os.getenv('DEBUG'):
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()