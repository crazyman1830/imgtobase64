"""
Cache manager interface definition.

This module defines the ICacheManager protocol that establishes the contract
for caching operations.
"""

from typing import Protocol, Optional, Any, Dict
from ...models.models import ConversionResult
from ...models.processing_options import ProcessingOptions


class ICacheManager(Protocol):
    """
    Protocol defining the interface for cache management operations.
    
    This interface establishes the contract for storing and retrieving
    cached conversion results to improve performance.
    """
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.
        
        Args:
            key: Cache key to look up
            
        Returns:
            Cached value if found, None otherwise
        """
        ...
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store a value in the cache.
        
        Args:
            key: Cache key for the value
            value: Value to store in the cache
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if value was stored successfully, False otherwise
        """
        ...
    
    def invalidate(self, key: str) -> bool:
        """
        Remove a specific key from the cache.
        
        Args:
            key: Cache key to remove
            
        Returns:
            True if key was removed, False if key didn't exist
        """
        ...
    
    def get_cache_key(self, file_path: str, options: Optional[ProcessingOptions] = None) -> str:
        """
        Generate a cache key based on file content and processing options.
        
        Args:
            file_path: Path to the image file
            options: Processing options used for conversion
            
        Returns:
            Unique cache key string
        """
        ...
    
    def get_cached_result(self, cache_key: str) -> Optional[ConversionResult]:
        """
        Retrieve a cached conversion result.
        
        Args:
            cache_key: Cache key to look up
            
        Returns:
            ConversionResult if found in cache, None otherwise
        """
        ...
    
    def store_result(self, cache_key: str, result: ConversionResult) -> None:
        """
        Store a conversion result in the cache.
        
        Args:
            cache_key: Cache key for the result
            result: ConversionResult to store
        """
        ...
    
    def clear_cache(self) -> None:
        """
        Clear all cache entries.
        """
        ...
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        ...