"""
Validation utilities.

This module provides common validation functions that are used across
multiple modules to ensure data integrity and type safety.
"""

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

from ...domain.exceptions import ValidationError


class ValidationUtils:
    """Utility class for data validation operations."""

    # Common validation patterns
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    FILENAME_PATTERN = re.compile(r'^[^<>:"/\\|?*]+$')

    @staticmethod
    def validate_not_none(value: Any, field_name: str = "value") -> Any:
        """
        Validate that a value is not None.

        Args:
            value: Value to validate
            field_name: Name of the field for error messages

        Returns:
            The validated value

        Raises:
            ValidationError: If value is None
        """
        if value is None:
            raise ValidationError(f"{field_name} cannot be None")
        return value

    @staticmethod
    def validate_not_empty(
        value: Union[str, List, Dict], field_name: str = "value"
    ) -> Union[str, List, Dict]:
        """
        Validate that a value is not empty.

        Args:
            value: Value to validate (string, list, or dict)
            field_name: Name of the field for error messages

        Returns:
            The validated value

        Raises:
            ValidationError: If value is empty
        """
        ValidationUtils.validate_not_none(value, field_name)

        if not value:
            raise ValidationError(f"{field_name} cannot be empty")

        return value

    @staticmethod
    def validate_string(
        value: Any,
        field_name: str = "value",
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[re.Pattern] = None,
    ) -> str:
        """
        Validate that a value is a string with optional constraints.

        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            min_length: Minimum length requirement
            max_length: Maximum length requirement
            pattern: Regex pattern to match

        Returns:
            The validated string

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, str):
            raise ValidationError(
                f"{field_name} must be a string, got {type(value).__name__}"
            )

        if min_length is not None and len(value) < min_length:
            raise ValidationError(
                f"{field_name} must be at least {min_length} characters long"
            )

        if max_length is not None and len(value) > max_length:
            raise ValidationError(
                f"{field_name} must be at most {max_length} characters long"
            )

        if pattern is not None and not pattern.match(value):
            raise ValidationError(f"{field_name} does not match required pattern")

        return value

    @staticmethod
    def validate_integer(
        value: Any,
        field_name: str = "value",
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
    ) -> int:
        """
        Validate that a value is an integer with optional range constraints.

        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            min_value: Minimum value requirement
            max_value: Maximum value requirement

        Returns:
            The validated integer

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, int):
            raise ValidationError(
                f"{field_name} must be an integer, got {type(value).__name__}"
            )

        if min_value is not None and value < min_value:
            raise ValidationError(f"{field_name} must be at least {min_value}")

        if max_value is not None and value > max_value:
            raise ValidationError(f"{field_name} must be at most {max_value}")

        return value

    @staticmethod
    def validate_float(
        value: Any,
        field_name: str = "value",
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> float:
        """
        Validate that a value is a float with optional range constraints.

        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            min_value: Minimum value requirement
            max_value: Maximum value requirement

        Returns:
            The validated float

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, (int, float)):
            raise ValidationError(
                f"{field_name} must be a number, got {type(value).__name__}"
            )

        value = float(value)

        if min_value is not None and value < min_value:
            raise ValidationError(f"{field_name} must be at least {min_value}")

        if max_value is not None and value > max_value:
            raise ValidationError(f"{field_name} must be at most {max_value}")

        return value

    @staticmethod
    def validate_boolean(value: Any, field_name: str = "value") -> bool:
        """
        Validate that a value is a boolean.

        Args:
            value: Value to validate
            field_name: Name of the field for error messages

        Returns:
            The validated boolean

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, bool):
            raise ValidationError(
                f"{field_name} must be a boolean, got {type(value).__name__}"
            )

        return value

    @staticmethod
    def validate_list(
        value: Any,
        field_name: str = "value",
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        item_validator: Optional[Callable] = None,
    ) -> List:
        """
        Validate that a value is a list with optional constraints.

        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            min_length: Minimum length requirement
            max_length: Maximum length requirement
            item_validator: Function to validate each item in the list

        Returns:
            The validated list

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, list):
            raise ValidationError(
                f"{field_name} must be a list, got {type(value).__name__}"
            )

        if min_length is not None and len(value) < min_length:
            raise ValidationError(f"{field_name} must have at least {min_length} items")

        if max_length is not None and len(value) > max_length:
            raise ValidationError(f"{field_name} must have at most {max_length} items")

        if item_validator is not None:
            for i, item in enumerate(value):
                try:
                    item_validator(item)
                except ValidationError as e:
                    raise ValidationError(f"{field_name}[{i}]: {e}")

        return value

    @staticmethod
    def validate_dict(
        value: Any,
        field_name: str = "value",
        required_keys: Optional[List[str]] = None,
        key_validator: Optional[Callable] = None,
        value_validator: Optional[Callable] = None,
    ) -> Dict:
        """
        Validate that a value is a dictionary with optional constraints.

        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            required_keys: List of required keys
            key_validator: Function to validate each key
            value_validator: Function to validate each value

        Returns:
            The validated dictionary

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, dict):
            raise ValidationError(
                f"{field_name} must be a dictionary, got {type(value).__name__}"
            )

        if required_keys:
            missing_keys = set(required_keys) - set(value.keys())
            if missing_keys:
                raise ValidationError(
                    f"{field_name} missing required keys: {', '.join(missing_keys)}"
                )

        if key_validator is not None:
            for key in value.keys():
                try:
                    key_validator(key)
                except ValidationError as e:
                    raise ValidationError(f"{field_name} key '{key}': {e}")

        if value_validator is not None:
            for key, val in value.items():
                try:
                    value_validator(val)
                except ValidationError as e:
                    raise ValidationError(f"{field_name}['{key}']: {e}")

        return value

    @staticmethod
    def validate_choice(
        value: Any, choices: List[Any], field_name: str = "value"
    ) -> Any:
        """
        Validate that a value is one of the allowed choices.

        Args:
            value: Value to validate
            choices: List of allowed values
            field_name: Name of the field for error messages

        Returns:
            The validated value

        Raises:
            ValidationError: If value is not in choices
        """
        if value not in choices:
            raise ValidationError(f"{field_name} must be one of {choices}, got {value}")

        return value

    @staticmethod
    def validate_file_path(
        file_path: Union[str, Path],
        field_name: str = "file_path",
        must_exist: bool = True,
        must_be_file: bool = True,
    ) -> str:
        """
        Validate a file path.

        Args:
            file_path: Path to validate
            field_name: Name of the field for error messages
            must_exist: Whether the file must exist
            must_be_file: Whether the path must be a file (not directory)

        Returns:
            The validated file path as string

        Raises:
            ValidationError: If validation fails
        """
        if not file_path:
            raise ValidationError(f"{field_name} cannot be empty")

        path_str = str(file_path)
        path_obj = Path(path_str)

        if must_exist:
            if not path_obj.exists():
                raise ValidationError(f"{field_name} does not exist: {path_str}")

            if must_be_file and not path_obj.is_file():
                raise ValidationError(f"{field_name} is not a file: {path_str}")

        return path_str

    @staticmethod
    def validate_email(email: str, field_name: str = "email") -> str:
        """
        Validate an email address format.

        Args:
            email: Email address to validate
            field_name: Name of the field for error messages

        Returns:
            The validated email address

        Raises:
            ValidationError: If email format is invalid
        """
        email = ValidationUtils.validate_string(email, field_name)

        if not ValidationUtils.EMAIL_PATTERN.match(email):
            raise ValidationError(f"{field_name} is not a valid email address")

        return email

    @staticmethod
    def validate_filename(filename: str, field_name: str = "filename") -> str:
        """
        Validate a filename for safety.

        Args:
            filename: Filename to validate
            field_name: Name of the field for error messages

        Returns:
            The validated filename

        Raises:
            ValidationError: If filename is invalid
        """
        filename = ValidationUtils.validate_string(filename, field_name, min_length=1)

        if not ValidationUtils.FILENAME_PATTERN.match(filename):
            raise ValidationError(f"{field_name} contains invalid characters")

        # Check for reserved names on Windows
        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }

        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            raise ValidationError(f"{field_name} uses a reserved system name")

        return filename

    @staticmethod
    def validate_url(url: str, field_name: str = "url") -> str:
        """
        Validate a URL format.

        Args:
            url: URL to validate
            field_name: Name of the field for error messages

        Returns:
            The validated URL

        Raises:
            ValidationError: If URL format is invalid
        """
        url = ValidationUtils.validate_string(url, field_name)

        # Basic URL validation
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        if not url_pattern.match(url):
            raise ValidationError(f"{field_name} is not a valid URL")

        return url

    @staticmethod
    def validate_type(
        value: Any, expected_type: Type, field_name: str = "value"
    ) -> Any:
        """
        Validate that a value is of the expected type.

        Args:
            value: Value to validate
            expected_type: Expected type
            field_name: Name of the field for error messages

        Returns:
            The validated value

        Raises:
            ValidationError: If type validation fails
        """
        if not isinstance(value, expected_type):
            raise ValidationError(
                f"{field_name} must be of type {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )

        return value

    @staticmethod
    def validate_range(
        value: Union[int, float],
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        field_name: str = "value",
    ) -> Union[int, float]:
        """
        Validate that a numeric value is within a specified range.

        Args:
            value: Value to validate
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            field_name: Name of the field for error messages

        Returns:
            The validated value

        Raises:
            ValidationError: If value is outside the range
        """
        if not isinstance(value, (int, float)):
            raise ValidationError(
                f"{field_name} must be a number, got {type(value).__name__}"
            )

        if min_value is not None and value < min_value:
            raise ValidationError(
                f"{field_name} must be at least {min_value}, got {value}"
            )

        if max_value is not None and value > max_value:
            raise ValidationError(
                f"{field_name} must be at most {max_value}, got {value}"
            )

        return value

    @staticmethod
    def validate_image_format(
        file_path: Union[str, Path], field_name: str = "file_path"
    ) -> str:
        """
        Validate that a file has a supported image format.

        Args:
            file_path: Path to the image file
            field_name: Name of the field for error messages

        Returns:
            The validated file path as string

        Raises:
            ValidationError: If file format is not supported
        """
        path_str = ValidationUtils.validate_file_path(file_path, field_name)

        # Import here to avoid circular imports
        from .path_utils import PathUtils

        if not PathUtils.is_image_file(path_str):
            extension = PathUtils.get_file_extension(path_str)
            supported = ", ".join(sorted(PathUtils.IMAGE_EXTENSIONS))
            raise ValidationError(
                f"{field_name} has unsupported format '{extension}'. "
                f"Supported formats: {supported}"
            )

        return path_str
