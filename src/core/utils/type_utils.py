"""
Type utilities and helper functions.

This module provides type-safe utility functions and type conversion
helpers that are used across multiple modules.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from ...domain.exceptions import ValidationError

T = TypeVar("T")


class TypeUtils:
    """Utility class for type operations and conversions."""

    @staticmethod
    def safe_cast(
        value: Any, target_type: Type[T], default: Optional[T] = None
    ) -> Optional[T]:
        """
        Safely cast a value to a target type.

        Args:
            value: Value to cast
            target_type: Target type to cast to
            default: Default value if casting fails

        Returns:
            Casted value or default if casting fails
        """
        if value is None:
            return default

        if isinstance(value, target_type):
            return value

        try:
            if target_type == str:
                return str(value)
            elif target_type == int:
                return int(value)
            elif target_type == float:
                return float(value)
            elif target_type == bool:
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on")
                return bool(value)
            elif target_type == Path:
                return Path(value)
            else:
                return target_type(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def ensure_list(value: Any) -> List[Any]:
        """
        Ensure a value is a list, wrapping single values if necessary.

        Args:
            value: Value to ensure is a list

        Returns:
            List containing the value(s)
        """
        if value is None:
            return []
        elif isinstance(value, list):
            return value
        elif isinstance(value, (tuple, set)):
            return list(value)
        else:
            return [value]

    @staticmethod
    def ensure_dict(value: Any) -> Dict[str, Any]:
        """
        Ensure a value is a dictionary.

        Args:
            value: Value to ensure is a dictionary

        Returns:
            Dictionary representation of the value

        Raises:
            ValidationError: If value cannot be converted to dict
        """
        if value is None:
            return {}
        elif isinstance(value, dict):
            return value
        elif isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValidationError(f"Cannot parse string as JSON: {value}")
        else:
            raise ValidationError(f"Cannot convert {type(value).__name__} to dict")

    @staticmethod
    def deep_merge_dicts(
        dict1: Dict[str, Any], dict2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.

        Args:
            dict1: First dictionary
            dict2: Second dictionary (takes precedence)

        Returns:
            Merged dictionary
        """
        result = dict1.copy()

        for key, value in dict2.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = TypeUtils.deep_merge_dicts(result[key], value)
            else:
                result[key] = value

        return result

    @staticmethod
    def flatten_dict(
        data: Dict[str, Any], separator: str = ".", prefix: str = ""
    ) -> Dict[str, Any]:
        """
        Flatten a nested dictionary.

        Args:
            data: Dictionary to flatten
            separator: Separator for nested keys
            prefix: Prefix for keys

        Returns:
            Flattened dictionary
        """
        result = {}

        for key, value in data.items():
            new_key = f"{prefix}{separator}{key}" if prefix else key

            if isinstance(value, dict):
                result.update(TypeUtils.flatten_dict(value, separator, new_key))
            else:
                result[new_key] = value

        return result

    @staticmethod
    def unflatten_dict(data: Dict[str, Any], separator: str = ".") -> Dict[str, Any]:
        """
        Unflatten a dictionary with dot-separated keys.

        Args:
            data: Flattened dictionary
            separator: Separator used in keys

        Returns:
            Nested dictionary
        """
        result = {}

        for key, value in data.items():
            keys = key.split(separator)
            current = result

            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]

            current[keys[-1]] = value

        return result

    @staticmethod
    def get_nested_value(
        data: Dict[str, Any], key_path: str, separator: str = ".", default: Any = None
    ) -> Any:
        """
        Get a value from a nested dictionary using a dot-separated path.

        Args:
            data: Dictionary to search in
            key_path: Dot-separated path to the value
            separator: Separator used in the path
            default: Default value if key is not found

        Returns:
            Value at the specified path or default
        """
        keys = key_path.split(separator)
        current = data

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    @staticmethod
    def set_nested_value(
        data: Dict[str, Any], key_path: str, value: Any, separator: str = "."
    ) -> None:
        """
        Set a value in a nested dictionary using a dot-separated path.

        Args:
            data: Dictionary to modify
            key_path: Dot-separated path to set
            value: Value to set
            separator: Separator used in the path
        """
        keys = key_path.split(separator)
        current = data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    @staticmethod
    def is_json_serializable(obj: Any) -> bool:
        """
        Check if an object is JSON serializable.

        Args:
            obj: Object to check

        Returns:
            True if object is JSON serializable, False otherwise
        """
        try:
            json.dumps(obj)
            return True
        except (TypeError, ValueError):
            return False

    @staticmethod
    def make_json_serializable(obj: Any) -> Any:
        """
        Convert an object to a JSON-serializable format.

        Args:
            obj: Object to convert

        Returns:
            JSON-serializable representation of the object
        """
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
        elif isinstance(obj, (list, tuple)):
            return [TypeUtils.make_json_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {str(k): TypeUtils.make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, "__dict__"):
            return TypeUtils.make_json_serializable(obj.__dict__)
        else:
            return str(obj)

    @staticmethod
    def coerce_to_type(value: Any, type_hint: str) -> Any:
        """
        Coerce a value to a specific type based on a string hint.

        Args:
            value: Value to coerce
            type_hint: String representation of the target type

        Returns:
            Coerced value

        Raises:
            ValidationError: If coercion fails
        """
        if value is None:
            return None

        type_hint = type_hint.lower().strip()

        try:
            if type_hint in ("str", "string"):
                return str(value)
            elif type_hint in ("int", "integer"):
                return int(value)
            elif type_hint in ("float", "number"):
                return float(value)
            elif type_hint in ("bool", "boolean"):
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on")
                return bool(value)
            elif type_hint in ("list", "array"):
                return TypeUtils.ensure_list(value)
            elif type_hint in ("dict", "object"):
                return TypeUtils.ensure_dict(value)
            elif type_hint == "path":
                return Path(value)
            else:
                raise ValidationError(f"Unknown type hint: {type_hint}")
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Cannot coerce {value} to {type_hint}: {e}")

    @staticmethod
    def get_type_name(obj: Any) -> str:
        """
        Get a human-readable type name for an object.

        Args:
            obj: Object to get type name for

        Returns:
            Human-readable type name
        """
        if obj is None:
            return "None"

        type_obj = type(obj)

        # Handle common types with more readable names
        type_names = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "list",
            dict: "dictionary",
            tuple: "tuple",
            set: "set",
        }

        return type_names.get(type_obj, type_obj.__name__)

    @staticmethod
    def sanitize_for_logging(obj: Any, max_length: int = 1000) -> str:
        """
        Sanitize an object for safe logging.

        Args:
            obj: Object to sanitize
            max_length: Maximum length of the result

        Returns:
            Sanitized string representation
        """
        try:
            # Convert to JSON-serializable format first
            serializable = TypeUtils.make_json_serializable(obj)

            # Convert to string
            if isinstance(serializable, str):
                result = serializable
            else:
                result = json.dumps(serializable, indent=None, separators=(",", ":"))

            # Truncate if too long
            if len(result) > max_length:
                result = result[: max_length - 3] + "..."

            return result
        except Exception:
            # Fallback to basic string representation
            result = str(obj)
            if len(result) > max_length:
                result = result[: max_length - 3] + "..."
            return result

    @staticmethod
    def compare_versions(version1: str, version2: str) -> int:
        """
        Compare two version strings.

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """

        def normalize_version(version: str) -> List[int]:
            """Convert version string to list of integers."""
            parts = version.split(".")
            return [int(part) for part in parts if part.isdigit()]

        v1_parts = normalize_version(version1)
        v2_parts = normalize_version(version2)

        # Pad shorter version with zeros
        max_length = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_length - len(v1_parts)))
        v2_parts.extend([0] * (max_length - len(v2_parts)))

        for v1, v2 in zip(v1_parts, v2_parts):
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1

        return 0
