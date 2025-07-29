"""
Utility functions for the image base64 converter.

This module provides common utility functions used across the application,
including file size formatting, progress display, and other helper functions.
"""
import os
import sys
from typing import Optional, Union


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted file size string (e.g., "1.5 KB", "2.3 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    # Define size units
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    # Convert to appropriate unit
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    # Format with appropriate decimal places
    if unit_index == 0:  # Bytes
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def format_progress(current: int, total: int, prefix: str = "Progress") -> str:
    """
    Format progress information as a string.
    
    Args:
        current: Current progress value
        total: Total progress value
        prefix: Prefix text for the progress display
        
    Returns:
        Formatted progress string (e.g., "Progress: [3/10] 30%")
    """
    if total == 0:
        return f"{prefix}: [0/0] 100%"
    
    percentage = (current / total) * 100
    return f"{prefix}: [{current}/{total}] {percentage:.1f}%"


def print_progress_bar(current: int, total: int, width: int = 50, 
                      prefix: str = "Progress", suffix: str = "") -> None:
    """
    Print a progress bar to stdout (optional feature).
    
    Args:
        current: Current progress value
        total: Total progress value  
        width: Width of the progress bar in characters
        prefix: Prefix text before the progress bar
        suffix: Suffix text after the progress bar
    """
    if total == 0:
        percentage = 100.0
        filled_length = width
    else:
        percentage = (current / total) * 100
        filled_length = int(width * current // total)
    
    # Create progress bar
    bar = '█' * filled_length + '-' * (width - filled_length)
    
    # Print progress bar (overwrite previous line)
    print(f'\r{prefix} |{bar}| {current}/{total} ({percentage:.1f}%) {suffix}', 
          end='', flush=True)
    
    # Print newline when complete
    if current == total:
        print()


def create_file_separator(title: str = "", width: int = 60, char: str = "=") -> str:
    """
    Create a formatted separator line for file output.
    
    Args:
        title: Optional title to include in the separator
        width: Width of the separator line
        char: Character to use for the separator
        
    Returns:
        Formatted separator string
    """
    if not title:
        return char * width
    
    # Calculate padding for centered title
    title_with_spaces = f" {title} "
    if len(title_with_spaces) >= width:
        return title_with_spaces[:width]
    
    padding = (width - len(title_with_spaces)) // 2
    left_padding = char * padding
    right_padding = char * (width - padding - len(title_with_spaces))
    
    return f"{left_padding}{title_with_spaces}{right_padding}"


def format_conversion_summary(successful: int, failed: int, total: int) -> str:
    """
    Format a summary of batch conversion results.
    
    Args:
        successful: Number of successful conversions
        failed: Number of failed conversions
        total: Total number of files processed
        
    Returns:
        Formatted summary string
    """
    summary_lines = [
        "Batch processing completed:",
        f"  Successful: {successful}",
        f"  Failed: {failed}",
        f"  Total: {total}"
    ]
    
    if total > 0:
        success_rate = (successful / total) * 100
        summary_lines.append(f"  Success rate: {success_rate:.1f}%")
    
    return "\n".join(summary_lines)


def get_file_info(file_path: str) -> dict:
    """
    Get basic information about a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary containing file information
    """
    try:
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'size_formatted': format_file_size(stat.st_size),
            'exists': True,
            'readable': os.access(file_path, os.R_OK),
            'writable': os.access(file_path, os.W_OK),
            'name': os.path.basename(file_path),
            'directory': os.path.dirname(file_path),
            'extension': os.path.splitext(file_path)[1].lower()
        }
    except (OSError, IOError):
        return {
            'size': 0,
            'size_formatted': '0 B',
            'exists': False,
            'readable': False,
            'writable': False,
            'name': os.path.basename(file_path) if file_path else '',
            'directory': os.path.dirname(file_path) if file_path else '',
            'extension': os.path.splitext(file_path)[1].lower() if file_path else ''
        }


def confirm_overwrite(file_path: str) -> bool:
    """
    Ask user for confirmation to overwrite an existing file.
    
    Args:
        file_path: Path to the file that would be overwritten
        
    Returns:
        True if user confirms overwrite, False otherwise
    """
    try:
        response = input(f"File '{file_path}' already exists. Overwrite? (y/N): ").strip().lower()
        return response in ('y', 'yes')
    except (EOFError, KeyboardInterrupt):
        return False


def safe_print(message: str, file=None, end: str = '\n') -> None:
    """
    Safely print a message, handling encoding errors.
    
    Args:
        message: Message to print
        file: File object to write to (default: stdout)
        end: String appended after the message
    """
    if file is None:
        file = sys.stdout
    
    try:
        print(message, file=file, end=end)
    except UnicodeEncodeError:
        # Fallback for systems with encoding issues
        safe_message = message.encode('utf-8', errors='replace').decode('utf-8')
        print(safe_message, file=file, end=end)


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length with optional suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length of the result
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    if len(suffix) >= max_length:
        return suffix[:max_length]
    
    return text[:max_length - len(suffix)] + suffix