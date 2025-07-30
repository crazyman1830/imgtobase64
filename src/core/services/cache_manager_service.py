"""
Cache manager service implementation.

This module provides the CacheManagerService class that implements
unified caching with support for memory, disk, and Redis backends.
"""
import hashlib
import json
import pickle
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Any, Dict, Union

from ..interfaces.cache_manager import ICacheManager
from ...models.models import ConversionResult
from ...models.processing_options import ProcessingOptions
from ...domain.exceptions.cache import CacheError


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the cache."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend using LRU policy."""
    
    def __init__(self, max_entries: int = 1000, max_age_seconds: int = 3600):
        """
        Initialize memory cache backend.
        
        Args:
            max_entries: Maximum number of cache entries
            max_age_seconds: Maximum age of cache entries in seconds
        """
        self.max_entries = max_entries
        self.max_age_seconds = max_age_seconds
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the memory cache."""
        if key not in self._cache:
            self._stats['misses'] += 1
            return None
        
        entry = self._cache[key]
        
        # Check if expired
        if self._is_expired(entry):
            del self._cache[key]
            self._stats['misses'] += 1
            self._stats['evictions'] += 1
            return None
        
        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._stats['hits'] += 1
        
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the memory cache."""
        try:
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]
            
            # Create cache entry
            entry = {
                'value': value,
                'created_at': time.time(),
                'ttl': ttl or self.max_age_seconds
            }
            
            # Add to cache
            self._cache[key] = entry
            
            # Enforce size limit
            while len(self._cache) > self.max_entries:
                # Remove least recently used
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats['evictions'] += 1
            
            self._stats['sets'] += 1
            return True
            
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a key from the memory cache."""
        if key in self._cache:
            del self._cache[key]
            self._stats['deletes'] += 1
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory cache statistics."""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'backend_type': 'memory',
            'entries': len(self._cache),
            'max_entries': self.max_entries,
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate_percent': round(hit_rate, 2),
            'sets': self._stats['sets'],
            'deletes': self._stats['deletes'],
            'evictions': self._stats['evictions']
        }
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if a cache entry is expired."""
        created_at = entry.get('created_at', 0)
        ttl = entry.get('ttl', self.max_age_seconds)
        return (time.time() - created_at) > ttl


class DiskCacheBackend(CacheBackend):
    """Disk-based cache backend."""
    
    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 100, max_age_seconds: int = 3600):
        """
        Initialize disk cache backend.
        
        Args:
            cache_dir: Directory to store cache files
            max_size_mb: Maximum cache size in megabytes
            max_age_seconds: Maximum age of cache entries in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_age_seconds = max_age_seconds
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0
        }
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "data").mkdir(exist_ok=True)
        (self.cache_dir / "metadata").mkdir(exist_ok=True)
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the disk cache."""
        try:
            cache_file = self.cache_dir / "data" / f"{key}.pkl"
            metadata_file = self.cache_dir / "metadata" / f"{key}.json"
            
            if not cache_file.exists() or not metadata_file.exists():
                self._stats['misses'] += 1
                return None
            
            # Check metadata for expiration
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            if self._is_expired(metadata):
                # Clean up expired entry
                cache_file.unlink(missing_ok=True)
                metadata_file.unlink(missing_ok=True)
                self._stats['misses'] += 1
                self._stats['evictions'] += 1
                return None
            
            # Load cached value
            with open(cache_file, 'rb') as f:
                value = pickle.load(f)
            
            # Update access time
            metadata['last_accessed'] = time.time()
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f)
            
            self._stats['hits'] += 1
            return value
            
        except Exception:
            self._stats['misses'] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the disk cache."""
        try:
            cache_file = self.cache_dir / "data" / f"{key}.pkl"
            metadata_file = self.cache_dir / "metadata" / f"{key}.json"
            
            # Save value to disk
            with open(cache_file, 'wb') as f:
                pickle.dump(value, f)
            
            # Save metadata
            metadata = {
                'created_at': time.time(),
                'last_accessed': time.time(),
                'ttl': ttl or self.max_age_seconds,
                'size': cache_file.stat().st_size
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f)
            
            # Cleanup if needed
            self._cleanup_if_needed()
            
            self._stats['sets'] += 1
            return True
            
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a key from the disk cache."""
        try:
            cache_file = self.cache_dir / "data" / f"{key}.pkl"
            metadata_file = self.cache_dir / "metadata" / f"{key}.json"
            
            deleted = False
            if cache_file.exists():
                cache_file.unlink()
                deleted = True
            
            if metadata_file.exists():
                metadata_file.unlink()
                deleted = True
            
            if deleted:
                self._stats['deletes'] += 1
            
            return deleted
            
        except Exception:
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        try:
            # Remove all data files
            data_dir = self.cache_dir / "data"
            for cache_file in data_dir.glob("*.pkl"):
                cache_file.unlink(missing_ok=True)
            
            # Remove all metadata files
            metadata_dir = self.cache_dir / "metadata"
            for metadata_file in metadata_dir.glob("*.json"):
                metadata_file.unlink(missing_ok=True)
                
        except Exception:
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get disk cache statistics."""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate current cache size
        current_size = self._get_cache_size()
        size_utilization = (current_size / self.max_size_bytes * 100) if self.max_size_bytes > 0 else 0
        
        # Count entries
        data_dir = self.cache_dir / "data"
        entry_count = len(list(data_dir.glob("*.pkl"))) if data_dir.exists() else 0
        
        return {
            'backend_type': 'disk',
            'entries': entry_count,
            'cache_size_bytes': current_size,
            'cache_size_mb': round(current_size / (1024 * 1024), 2),
            'max_size_mb': round(self.max_size_bytes / (1024 * 1024), 2),
            'size_utilization_percent': round(size_utilization, 2),
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate_percent': round(hit_rate, 2),
            'sets': self._stats['sets'],
            'deletes': self._stats['deletes'],
            'evictions': self._stats['evictions']
        }
    
    def _is_expired(self, metadata: Dict[str, Any]) -> bool:
        """Check if a cache entry is expired."""
        created_at = metadata.get('created_at', 0)
        ttl = metadata.get('ttl', self.max_age_seconds)
        return (time.time() - created_at) > ttl
    
    def _get_cache_size(self) -> int:
        """Get total cache size in bytes."""
        total_size = 0
        try:
            data_dir = self.cache_dir / "data"
            if data_dir.exists():
                for cache_file in data_dir.glob("*.pkl"):
                    total_size += cache_file.stat().st_size
        except Exception:
            pass
        return total_size
    
    def _cleanup_if_needed(self) -> None:
        """Cleanup cache if size limit is exceeded."""
        current_size = self._get_cache_size()
        
        if current_size <= self.max_size_bytes:
            return
        
        # Get all metadata files sorted by last access time
        metadata_dir = self.cache_dir / "metadata"
        if not metadata_dir.exists():
            return
        
        metadata_files = []
        for metadata_file in metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                metadata_files.append((metadata_file, metadata))
            except Exception:
                continue
        
        # Sort by last accessed time (oldest first)
        metadata_files.sort(key=lambda x: x[1].get('last_accessed', 0))
        
        # Remove oldest entries until under size limit
        for metadata_file, metadata in metadata_files:
            if current_size <= self.max_size_bytes:
                break
            
            key = metadata_file.stem
            if self.delete(key):
                file_size = metadata.get('size', 0)
                current_size -= file_size
                self._stats['evictions'] += 1


class RedisCacheBackend(CacheBackend):
    """Redis cache backend (placeholder implementation)."""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, max_age_seconds: int = 3600):
        """
        Initialize Redis cache backend.
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            max_age_seconds: Default TTL for cache entries
        """
        self.host = host
        self.port = port
        self.db = db
        self.max_age_seconds = max_age_seconds
        self._redis = None
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0
        }
        
        # Try to connect to Redis
        self._connect()
    
    def _connect(self) -> None:
        """Connect to Redis server."""
        try:
            import redis
            self._redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=False
            )
            # Test connection
            self._redis.ping()
        except ImportError:
            raise CacheError("Redis library not installed. Install with: pip install redis")
        except Exception as e:
            raise CacheError(f"Failed to connect to Redis: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis cache."""
        if not self._redis:
            self._stats['misses'] += 1
            return None
        
        try:
            data = self._redis.get(key)
            if data is None:
                self._stats['misses'] += 1
                return None
            
            value = pickle.loads(data)
            self._stats['hits'] += 1
            return value
            
        except Exception:
            self._stats['misses'] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in Redis cache."""
        if not self._redis:
            return False
        
        try:
            data = pickle.dumps(value)
            ttl_seconds = ttl or self.max_age_seconds
            
            result = self._redis.setex(key, ttl_seconds, data)
            if result:
                self._stats['sets'] += 1
            
            return bool(result)
            
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a key from Redis cache."""
        if not self._redis:
            return False
        
        try:
            result = self._redis.delete(key)
            if result:
                self._stats['deletes'] += 1
            
            return bool(result)
            
        except Exception:
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        if not self._redis:
            return
        
        try:
            self._redis.flushdb()
        except Exception:
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        redis_info = {}
        if self._redis:
            try:
                info = self._redis.info()
                redis_info = {
                    'used_memory': info.get('used_memory', 0),
                    'used_memory_human': info.get('used_memory_human', '0B'),
                    'connected_clients': info.get('connected_clients', 0)
                }
            except Exception:
                pass
        
        return {
            'backend_type': 'redis',
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate_percent': round(hit_rate, 2),
            'sets': self._stats['sets'],
            'deletes': self._stats['deletes'],
            'evictions': self._stats['evictions'],
            'redis_info': redis_info
        }


class CacheManagerService(ICacheManager):
    """
    Unified cache manager service supporting multiple backends.
    
    This service provides a unified interface for caching operations
    with support for memory, disk, and Redis backends.
    """
    
    def __init__(
        self,
        backend_type: str = 'memory',
        backend_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the cache manager service.
        
        Args:
            backend_type: Type of cache backend ('memory', 'disk', 'redis')
            backend_config: Configuration for the cache backend
        """
        self.backend_type = backend_type
        self.backend_config = backend_config or {}
        self._backend = self._create_backend()
    
    def _create_backend(self) -> CacheBackend:
        """Create the appropriate cache backend."""
        if self.backend_type == 'memory':
            return MemoryCacheBackend(**self.backend_config)
        elif self.backend_type == 'disk':
            return DiskCacheBackend(**self.backend_config)
        elif self.backend_type == 'redis':
            return RedisCacheBackend(**self.backend_config)
        else:
            raise CacheError(f"Unsupported cache backend type: {self.backend_type}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.
        
        Args:
            key: Cache key to look up
            
        Returns:
            Cached value if found, None otherwise
        """
        try:
            return self._backend.get(key)
        except Exception as e:
            raise CacheError(f"Error retrieving from cache: {e}")
    
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
        try:
            return self._backend.set(key, value, ttl)
        except Exception as e:
            raise CacheError(f"Error storing in cache: {e}")
    
    def invalidate(self, key: str) -> bool:
        """
        Remove a specific key from the cache.
        
        Args:
            key: Cache key to remove
            
        Returns:
            True if key was removed, False if key didn't exist
        """
        try:
            return self._backend.delete(key)
        except Exception as e:
            raise CacheError(f"Error invalidating cache key: {e}")
    
    def get_cache_key(self, file_path: str, options: Optional[ProcessingOptions] = None) -> str:
        """
        Generate a cache key based on file content and processing options.
        
        Args:
            file_path: Path to the image file
            options: Processing options used for conversion
            
        Returns:
            Unique cache key string
        """
        try:
            # Read file content for hashing
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Create hash of file content
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # Include processing options in the key
            options_str = ""
            if options:
                # Convert options to a consistent string representation
                from dataclasses import asdict
                options_dict = asdict(options)
                # Sort keys for consistent hashing
                options_str = json.dumps(options_dict, sort_keys=True)
            
            # Combine file hash and options
            combined_data = f"{file_hash}:{options_str}"
            cache_key = hashlib.md5(combined_data.encode()).hexdigest()
            
            return cache_key
            
        except Exception as e:
            raise CacheError(f"Failed to generate cache key: {e}")
    
    def get_cached_result(self, cache_key: str) -> Optional[ConversionResult]:
        """
        Retrieve a cached conversion result.
        
        Args:
            cache_key: Cache key to look up
            
        Returns:
            ConversionResult if found in cache, None otherwise
        """
        try:
            result = self._backend.get(cache_key)
            if result and isinstance(result, ConversionResult):
                result.cache_hit = True
                return result
            return None
        except Exception as e:
            raise CacheError(f"Error retrieving cached result: {e}")
    
    def store_result(self, cache_key: str, result: ConversionResult) -> None:
        """
        Store a conversion result in the cache.
        
        Args:
            cache_key: Cache key for the result
            result: ConversionResult to store
        """
        try:
            # Create a copy without the PIL Image object for serialization
            result_copy = ConversionResult(
                file_path=result.file_path,
                success=result.success,
                base64_data=result.base64_data,
                data_uri=result.data_uri,
                error_message=result.error_message,
                file_size=result.file_size,
                mime_type=result.mime_type,
                image=None,  # Don't serialize PIL Image
                format=result.format,
                size=result.size,
                processing_options=result.processing_options,
                processing_time=result.processing_time,
                cache_hit=False,  # Original result, not from cache
                security_scan_result=result.security_scan_result,
                thumbnail_data=result.thumbnail_data
            )
            
            self._backend.set(cache_key, result_copy)
            
        except Exception as e:
            raise CacheError(f"Error storing result in cache: {e}")
    
    def clear_cache(self) -> None:
        """Clear all cache entries."""
        try:
            self._backend.clear()
        except Exception as e:
            raise CacheError(f"Error clearing cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        try:
            stats = self._backend.get_stats()
            stats['backend_type'] = self.backend_type
            return stats
        except Exception as e:
            raise CacheError(f"Error getting cache stats: {e}")