"""
Command Line Interface for the image base64 converter.
"""
import argparse
import sys
from typing import Optional

from .core.container import DIContainer
from .core.services.image_conversion_service import ImageConversionService
from .core.interfaces.file_handler import IFileHandler
from .core.error_handler import ErrorHandler
from .core.structured_logger import StructuredLogger
from .core.base.result import Result
from .domain.exceptions.base import ImageConverterError


class CLI:
    """
    Command Line Interface for the image base64 converter.
    
    Provides a user-friendly command line interface for converting images
    to base64 format, supporting both single file and batch processing.
    Uses dependency injection for better testability and maintainability.
    """
    
    def __init__(self, container: Optional[DIContainer] = None):
        """
        Initialize the CLI with dependency injection container.
        
        Args:
            container: DI container with all required services
        """
        self._container = container or DIContainer.create_default()
        
        # Get services from container
        self._conversion_service: ImageConversionService = self._container.get('image_conversion_service')
        self._file_handler: IFileHandler = self._container.get('file_handler')
        self._error_handler: ErrorHandler = self._container.get('error_handler')
        self._logger: StructuredLogger = self._container.get('logger')
    
    def parse_arguments(self) -> argparse.Namespace:
        """
        Parse command line arguments.
        
        Returns:
            Parsed arguments namespace
        """
        parser = argparse.ArgumentParser(
            prog='image-base64-converter',
            description='Convert image files to base64 format',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s image.png                    # Convert single image to base64
  %(prog)s image.png -o output.txt      # Save result to file
  %(prog)s /path/to/images/             # Convert all images in directory
  %(prog)s /path/to/images/ -o out.txt  # Batch convert and save to file
  
Supported formats: PNG, JPG, JPEG, GIF, BMP, WEBP
            """
        )
        
        # Positional argument for input path (file or directory)
        parser.add_argument(
            'input_path',
            help='Path to image file or directory containing images'
        )
        
        # Optional output file argument
        parser.add_argument(
            '-o', '--output',
            dest='output_path',
            help='Output file path to save the base64 result'
        )
        
        # Force overwrite option
        parser.add_argument(
            '-f', '--force',
            action='store_true',
            help='Force overwrite existing output file without confirmation'
        )
        
        # Verbose output option
        parser.add_argument(
            '-v', '--verbose',
            action='store_true',
            help='Enable verbose output with detailed information'
        )
        
        # Version information
        parser.add_argument(
            '--version',
            action='version',
            version='%(prog)s 1.0.0'
        )
        
        return parser.parse_args()    

    def process_single_file(self, file_path: str, output_path: Optional[str] = None, 
                          force_overwrite: bool = False, verbose: bool = False) -> None:
        """
        Process a single image file and convert it to base64.
        
        Args:
            file_path: Path to the image file to convert
            output_path: Optional path to save the result
            force_overwrite: Whether to overwrite existing output file
            verbose: Whether to show verbose output
        """
        try:
            if verbose:
                print(f"Processing file: {file_path}")
                self._logger.info("Processing single file", extra={"file_path": file_path})
            
            # Perform the conversion using the new service layer
            result = self._conversion_service.convert_image(file_path)
            
            if result.success:
                conversion_data = result
                
                # Display success information
                if verbose:
                    print(f"✓ Conversion successful")
                    print(f"  File size: {conversion_data.file_size:,} bytes")
                    print(f"  MIME type: {conversion_data.mime_type}")
                    print(f"  Base64 length: {len(conversion_data.base64_data):,} characters")
                
                # Prepare output content
                output_content = conversion_data.data_uri if conversion_data.data_uri else conversion_data.base64_data
                
                if output_path:
                    # Save to file using the file handler service
                    save_result = self._file_handler.save_file(output_content, output_path)
                    
                    if save_result:
                        if verbose:
                            print(f"✓ Result saved to: {output_path}")
                            self._logger.info("File saved successfully", extra={"output_path": output_path})
                    else:
                        error_msg = "Failed to save file"
                        print(f"Error: {error_msg}", file=sys.stderr)
                        if not force_overwrite:
                            print("Use -f/--force to overwrite existing files")
                        sys.exit(1)
                else:
                    # Print to stdout
                    print(output_content)
            
            else:
                # Handle conversion failure with improved error handling
                error_msg = self._error_handler.get_user_friendly_message(result.error_message)
                print(f"Error: {error_msg}", file=sys.stderr)
                self._logger.error("Conversion failed", extra={
                    "file_path": file_path,
                    "error": str(result.error_message)
                })
                sys.exit(1)
                
        except ImageConverterError as e:
            error_msg = self._error_handler.get_user_friendly_message(e)
            print(f"Error: {error_msg}", file=sys.stderr)
            self._logger.error("Application error", extra={"error": str(e)})
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user", file=sys.stderr)
            self._logger.info("Operation cancelled by user")
            sys.exit(1)
        except Exception as e:
            error_response = self._error_handler.handle_error(e, {"operation": "single_file_conversion"})
            print(f"Unexpected error: {error_response.user_message}", file=sys.stderr)
            sys.exit(1)  
  
    def process_directory(self, directory_path: str, output_path: Optional[str] = None,
                         force_overwrite: bool = False, verbose: bool = False) -> None:
        """
        Process all image files in a directory and convert them to base64.
        
        Args:
            directory_path: Path to directory containing image files
            output_path: Optional path to save the results
            force_overwrite: Whether to overwrite existing output file
            verbose: Whether to show verbose output
        """
        try:
            if verbose:
                print(f"Scanning directory: {directory_path}")
                self._logger.info("Processing directory", extra={"directory_path": directory_path})
            
            # Find all image files in the directory using the file handler service
            find_result = self._file_handler.find_files(directory_path, "*.{png,jpg,jpeg,gif,bmp,webp}")
            
            if isinstance(find_result, list):
                image_files = find_result
            else:
                error_msg = self._error_handler.get_user_friendly_message(str(find_result))
                print(f"Error scanning directory: {error_msg}", file=sys.stderr)
                sys.exit(1)
            
            if not image_files:
                print(f"No image files found in directory: {directory_path}")
                return
            
            if verbose:
                print(f"Found {len(image_files)} image file(s)")
            
            # Process each file
            results = []
            successful_conversions = 0
            failed_conversions = 0
            
            for i, file_path in enumerate(image_files, 1):
                if verbose:
                    print(f"\n[{i}/{len(image_files)}] Processing: {file_path}")
                
                try:
                    result = self._conversion_service.convert_image(file_path)
                    
                    if result.success:
                        successful_conversions += 1
                        conversion_data = result
                        
                        if verbose:
                            file_size = conversion_data.file_size
                            base64_len = len(conversion_data.base64_data)
                            print(f"  ✓ Success ({file_size:,} bytes → {base64_len:,} chars)")
                        
                        # Format result for output
                        file_separator = "=" * 60
                        file_result = f"{file_separator}\n"
                        file_result += f"File: {file_path}\n"
                        file_result += f"MIME Type: {conversion_data.mime_type}\n"
                        file_result += f"Size: {conversion_data.file_size:,} bytes\n"
                        
                        data_uri = conversion_data.data_uri if conversion_data.data_uri else conversion_data.base64_data
                        file_result += f"Base64 Data:\n{data_uri}\n"
                        
                        results.append(file_result)
                    else:
                        failed_conversions += 1
                        error_msg = self._error_handler.get_user_friendly_message(result.error_message)
                        if verbose:
                            print(f"  ✗ Failed: {error_msg}")
                        else:
                            print(f"Error processing {file_path}: {error_msg}", file=sys.stderr)
                
                except Exception as e:
                    failed_conversions += 1
                    error_response = self._error_handler.handle_error(e, {"file_path": file_path})
                    if verbose:
                        print(f"  ✗ {error_response.user_message}")
                    else:
                        print(f"Error: {error_response.user_message}", file=sys.stderr)
            
            # Display summary
            print(f"\nBatch processing completed:")
            print(f"  Successful: {successful_conversions}")
            print(f"  Failed: {failed_conversions}")
            print(f"  Total: {len(image_files)}")
            
            self._logger.info("Batch processing completed", extra={
                "successful": successful_conversions,
                "failed": failed_conversions,
                "total": len(image_files)
            })
            
            if results:
                # Combine all results
                output_content = "\n".join(results)
                
                if output_path:
                    # Save to file using the file handler service
                    save_result = self._file_handler.save_file(output_content, output_path)
                    
                    if save_result:
                        if verbose:
                            print(f"✓ Results saved to: {output_path}")
                            self._logger.info("Batch results saved", extra={"output_path": output_path})
                    else:
                        error_msg = "Failed to save batch results"
                        print(f"Error: {error_msg}", file=sys.stderr)
                        if not force_overwrite:
                            print("Use -f/--force to overwrite existing files")
                        sys.exit(1)
                else:
                    # Print to stdout
                    print("\n" + output_content)
            
            # Exit with error code if any conversions failed
            if failed_conversions > 0:
                sys.exit(1)
                
        except ImageConverterError as e:
            error_msg = self._error_handler.get_user_friendly_message(e)
            print(f"Error: {error_msg}", file=sys.stderr)
            self._logger.error("Directory processing error", extra={"error": str(e)})
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user", file=sys.stderr)
            self._logger.info("Directory processing cancelled by user")
            sys.exit(1)
        except Exception as e:
            error_response = self._error_handler.handle_error(e, {"operation": "directory_processing"})
            print(f"Unexpected error: {error_response.user_message}", file=sys.stderr)
            sys.exit(1)    

    def run(self) -> None:
        """
        Main execution function that parses arguments and processes input.
        
        This function serves as the entry point for the CLI application.
        It parses command line arguments and delegates to appropriate processing methods.
        """
        try:
            # Parse command line arguments
            args = self.parse_arguments()
            
            self._logger.info("CLI started", extra={
                "input_path": args.input_path,
                "output_path": args.output_path,
                "verbose": args.verbose
            })
            
            # Validate input path exists
            import os
            if not os.path.exists(args.input_path):
                error_msg = f"Input path does not exist: {args.input_path}"
                print(f"Error: {error_msg}", file=sys.stderr)
                self._logger.error("Invalid input path", extra={"input_path": args.input_path})
                sys.exit(1)
            
            # Determine if input is a file or directory
            if os.path.isfile(args.input_path):
                # Process single file
                self.process_single_file(
                    file_path=args.input_path,
                    output_path=args.output_path,
                    force_overwrite=args.force,
                    verbose=args.verbose
                )
            elif os.path.isdir(args.input_path):
                # Process directory (batch processing)
                self.process_directory(
                    directory_path=args.input_path,
                    output_path=args.output_path,
                    force_overwrite=args.force,
                    verbose=args.verbose
                )
            else:
                error_msg = f"Input path is neither a file nor a directory: {args.input_path}"
                print(f"Error: {error_msg}", file=sys.stderr)
                self._logger.error("Invalid input path type", extra={"input_path": args.input_path})
                sys.exit(1)
                
        except KeyboardInterrupt:
            print("\nOperation cancelled by user", file=sys.stderr)
            self._logger.info("CLI cancelled by user")
            sys.exit(1)
        except SystemExit:
            # Re-raise SystemExit to preserve exit codes
            raise
        except Exception as e:
            error_response = self._error_handler.handle_error(e, {"operation": "cli_run"})
            print(f"Unexpected error: {error_response.user_message}", file=sys.stderr)
            sys.exit(1)