"""
Command Line Interface for the image base64 converter.
"""
import argparse
import sys
from typing import Optional

from converter import ImageConverter
from file_handler import FileHandler
from models import ImageConverterError


class CLI:
    """
    Command Line Interface for the image base64 converter.
    
    Provides a user-friendly command line interface for converting images
    to base64 format, supporting both single file and batch processing.
    """
    
    def __init__(self, converter: Optional[ImageConverter] = None, 
                 file_handler: Optional[FileHandler] = None):
        """
        Initialize the CLI with converter and file handler dependencies.
        
        Args:
            converter: ImageConverter instance for handling conversions
            file_handler: FileHandler instance for file operations
        """
        self.converter = converter or ImageConverter()
        self.file_handler = file_handler or FileHandler()
    
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
            
            # Perform the conversion
            result = self.converter.convert_to_base64(file_path)
            
            if result.success:
                # Display success information
                if verbose:
                    print(f"✓ Conversion successful")
                    print(f"  File size: {result.file_size:,} bytes")
                    print(f"  MIME type: {result.mime_type}")
                    print(f"  Base64 length: {len(result.base64_data):,} characters")
                
                # Prepare output content
                output_content = result.data_uri
                
                if output_path:
                    # Save to file
                    try:
                        self.file_handler.save_to_file(
                            output_content, 
                            output_path, 
                            overwrite=force_overwrite
                        )
                        if verbose:
                            print(f"✓ Result saved to: {output_path}")
                    except FileExistsError:
                        print(f"Error: Output file already exists: {output_path}")
                        print("Use -f/--force to overwrite existing files")
                        sys.exit(1)
                    except Exception as e:
                        print(f"Error saving file: {e}")
                        sys.exit(1)
                else:
                    # Print to stdout
                    print(output_content)
            
            else:
                # Handle conversion failure
                print(f"Error: {result.error_message}", file=sys.stderr)
                sys.exit(1)
                
        except ImageConverterError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
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
            
            # Find all image files in the directory
            image_files = self.file_handler.find_image_files(directory_path)
            
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
                    result = self.converter.convert_to_base64(file_path)
                    
                    if result.success:
                        successful_conversions += 1
                        if verbose:
                            print(f"  ✓ Success ({result.file_size:,} bytes → {len(result.base64_data):,} chars)")
                        
                        # Format result for output
                        file_separator = "=" * 60
                        file_result = f"{file_separator}\n"
                        file_result += f"File: {file_path}\n"
                        file_result += f"MIME Type: {result.mime_type}\n"
                        file_result += f"Size: {result.file_size:,} bytes\n"
                        file_result += f"Base64 Data:\n{result.data_uri}\n"
                        
                        results.append(file_result)
                    else:
                        failed_conversions += 1
                        if verbose:
                            print(f"  ✗ Failed: {result.error_message}")
                        else:
                            print(f"Error processing {file_path}: {result.error_message}", file=sys.stderr)
                
                except Exception as e:
                    failed_conversions += 1
                    error_msg = f"Unexpected error processing {file_path}: {e}"
                    if verbose:
                        print(f"  ✗ {error_msg}")
                    else:
                        print(f"Error: {error_msg}", file=sys.stderr)
            
            # Display summary
            print(f"\nBatch processing completed:")
            print(f"  Successful: {successful_conversions}")
            print(f"  Failed: {failed_conversions}")
            print(f"  Total: {len(image_files)}")
            
            if results:
                # Combine all results
                output_content = "\n".join(results)
                
                if output_path:
                    # Save to file
                    try:
                        self.file_handler.save_to_file(
                            output_content,
                            output_path,
                            overwrite=force_overwrite
                        )
                        if verbose:
                            print(f"✓ Results saved to: {output_path}")
                    except FileExistsError:
                        print(f"Error: Output file already exists: {output_path}")
                        print("Use -f/--force to overwrite existing files")
                        sys.exit(1)
                    except Exception as e:
                        print(f"Error saving file: {e}")
                        sys.exit(1)
                else:
                    # Print to stdout
                    print("\n" + output_content)
            
            # Exit with error code if any conversions failed
            if failed_conversions > 0:
                sys.exit(1)
                
        except ImageConverterError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
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
            
            # Validate input path exists
            import os
            if not os.path.exists(args.input_path):
                print(f"Error: Input path does not exist: {args.input_path}", file=sys.stderr)
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
                print(f"Error: Input path is neither a file nor a directory: {args.input_path}", file=sys.stderr)
                sys.exit(1)
                
        except KeyboardInterrupt:
            print("\nOperation cancelled by user", file=sys.stderr)
            sys.exit(1)
        except SystemExit:
            # Re-raise SystemExit to preserve exit codes
            raise
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            sys.exit(1)