"""
Result pattern implementation for error handling.

This module provides the Result pattern for handling operations that can
succeed or fail without using exceptions for control flow.
"""
from typing import Generic, TypeVar, Optional, Callable, Any

T = TypeVar('T')
E = TypeVar('E')


class Result(Generic[T, E]):
    """
    Result pattern implementation for handling success/failure states.
    
    This class encapsulates the result of an operation that can either succeed
    with a value or fail with an error, providing a functional approach to
    error handling.
    """
    
    def __init__(self, value: Optional[T] = None, error: Optional[E] = None):
        """
        Initialize a Result instance.
        
        Args:
            value: The success value (mutually exclusive with error)
            error: The error value (mutually exclusive with value)
            
        Raises:
            ValueError: If both value and error are provided or both are None
        """
        if (value is not None and error is not None) or (value is None and error is None):
            raise ValueError("Result must have either a value or an error, but not both or neither")
        
        self._value = value
        self._error = error
    
    @property
    def is_success(self) -> bool:
        """
        Check if the result represents a success.
        
        Returns:
            True if the result is successful, False otherwise
        """
        return self._error is None
    
    @property
    def is_failure(self) -> bool:
        """
        Check if the result represents a failure.
        
        Returns:
            True if the result is a failure, False otherwise
        """
        return self._error is not None
    
    @property
    def value(self) -> T:
        """
        Get the success value.
        
        Returns:
            The success value
            
        Raises:
            ValueError: If the result is a failure
        """
        if self._error is not None:
            raise ValueError("Cannot get value from failed result")
        return self._value
    
    @property
    def error(self) -> E:
        """
        Get the error value.
        
        Returns:
            The error value
            
        Raises:
            ValueError: If the result is successful
        """
        if self._value is not None:
            raise ValueError("Cannot get error from successful result")
        return self._error
    
    def map(self, func: Callable[[T], Any]) -> 'Result':
        """
        Transform the success value if the result is successful.
        
        Args:
            func: Function to apply to the success value
            
        Returns:
            New Result with transformed value or the same error
        """
        if self.is_success:
            try:
                new_value = func(self._value)
                return Result.success(new_value)
            except Exception as e:
                return Result.failure(e)
        else:
            return Result.failure(self._error)
    
    def map_error(self, func: Callable[[E], Any]) -> 'Result':
        """
        Transform the error value if the result is a failure.
        
        Args:
            func: Function to apply to the error value
            
        Returns:
            New Result with transformed error or the same value
        """
        if self.is_failure:
            try:
                new_error = func(self._error)
                return Result.failure(new_error)
            except Exception as e:
                return Result.failure(e)
        else:
            return Result.success(self._value)
    
    def flat_map(self, func: Callable[[T], 'Result']) -> 'Result':
        """
        Chain operations that return Results.
        
        Args:
            func: Function that takes the success value and returns a Result
            
        Returns:
            Result from the function or the original error
        """
        if self.is_success:
            try:
                return func(self._value)
            except Exception as e:
                return Result.failure(e)
        else:
            return Result.failure(self._error)
    
    def unwrap_or(self, default: T) -> T:
        """
        Get the success value or return a default value.
        
        Args:
            default: Default value to return if the result is a failure
            
        Returns:
            The success value or the default value
        """
        if self.is_success:
            return self._value
        else:
            return default
    
    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        """
        Get the success value or compute a value from the error.
        
        Args:
            func: Function to compute a value from the error
            
        Returns:
            The success value or the computed value
        """
        if self.is_success:
            return self._value
        else:
            return func(self._error)
    
    @classmethod
    def success(cls, value: T) -> 'Result[T, Any]':
        """
        Create a successful Result.
        
        Args:
            value: The success value
            
        Returns:
            Result representing success
        """
        return cls(value=value)
    
    @classmethod
    def failure(cls, error: E) -> 'Result[Any, E]':
        """
        Create a failed Result.
        
        Args:
            error: The error value
            
        Returns:
            Result representing failure
        """
        return cls(error=error)
    
    def __str__(self) -> str:
        """String representation of the Result."""
        if self.is_success:
            return f"Success({self._value})"
        else:
            return f"Failure({self._error})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the Result."""
        return self.__str__()
    
    def __eq__(self, other) -> bool:
        """Check equality with another Result."""
        if not isinstance(other, Result):
            return False
        
        if self.is_success and other.is_success:
            return self._value == other._value
        elif self.is_failure and other.is_failure:
            return self._error == other._error
        else:
            return False
    
    def __hash__(self) -> int:
        """Hash the Result."""
        if self.is_success:
            return hash(('success', self._value))
        else:
            return hash(('failure', self._error))