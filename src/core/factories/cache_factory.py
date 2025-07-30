"""
Cache factory for creating cache backend implementations.

This module provides the CacheFactory class that creates appropriate
cache backend implementations based on configuration settings.
"""

from typing import Dict, Any, Optional
from pathlib import Path

from ..interfaces.cache_manager import ICacheManager
from ..services.cache_manager_service import (
    CacheManagerService,
    MemoryCacheBackend,
    DiskCacheBackend,
    RedisCacheBackend
)
from ...domain.exceptions.cache import CacheError


class CacheFactory:
    """
    Factory class for creating cache manager instances with different backends.
    
    This factory supports creating cache managers with memory, disk, and Redis
    backends based on configuration settings.
    """
    
    # Default configurations for different cache backends
    DEFAULT_MEMORY_CONFIG = {
        'max_entries': 1000,
        'max_age_seconds': 3600  # 1 hour
    }
    
    DEFAULT_DISK_CONFIG = {
        'cache_dir': 'cache',
        'max_size_mb': 100,
        'max_age_seconds': 86400  # 24 hours
    }
    
    DEFAULT_REDIS_CONFIG = {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'max_age_seconds': 3600  # 1 hour
    }
    
    @classmethod
    def create_memory_cache(
        self,
        max_entries: int = 1000,
        max_age_seconds: int = 3600,
        **kwargs
    ) -> ICacheManager:
        """
        Create a memory-based cache manager.
        
        Args:
            max_entries: Maximum number of cache entries
            max_age_seconds: Maximum age of cache entries in seconds
            **kwargs: Additional configuration options
            
        Returns:
            ICacheManager with memory backend
            
        Raises:
            CacheError: If cache creation fails
        """
        try:
            config = {
                'max_entries': max_entries,
                'max_age_seconds': max_age_seconds,
                **kwargs
            }
            
            return CacheManagerService(
                backend_type='memory',
                backend_config=config
            )
            
        except Exception as e:
            raise CacheError(f"Failed to create memory cache: {str(e)}")
    
    @classmethod
    def create_disk_cache(
        self,
        cache_dir: str = 'cache',
        max_size_mb: int = 100,
        max_age_seconds: int = 86400,
        **kwargs
    ) -> ICacheManager:
        """
        Create a disk-based cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            max_size_mb: Maximum cache size in megabytes
            max_age_seconds: Maximum age of cache entries in seconds
            **kwargs: Additional configuration options
            
        Returns:
            ICacheManager with disk backend
            
        Raises:
            CacheError: If cache creation fails
        """
        try:
            # Ensure cache directory exists
            cache_path = Path(cache_dir)
            cache_path.mkdir(parents=True, exist_ok=True)
            
            config = {
                'cache_dir': cache_dir,
                'max_size_mb': max_size_mb,
                'max_age_seconds': max_age_seconds,
                **kwargs
            }
            
            return CacheManagerService(
                backend_type='disk',
                backend_config=config
            )
            
        except Exception as e:
            raise CacheError(f"Failed to create disk cache: {str(e)}")
    
    @classmethod
    def create_redis_cache(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        max_age_seconds: int = 3600,
        password: Optional[str] = None,
        **kwargs
    ) -> ICacheManager:
        """
        Create a Redis-based cache manager.
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            max_age_seconds: Default TTL for cache entries
            password: Redis password (optional)
            **kwargs: Additional configuration options
            
        Returns:
            ICacheManager with Redis backend
            
        Raises:
            CacheError: If cache creation fails or Redis is not available
        """
        try:
            config = {
                'host': host,
                'port': port,
                'db': db,
                'max_age_seconds': max_age_seconds,
                **kwargs
            }
            
            if password:
                config['password'] = password
            
            return CacheManagerService(
                backend_type='redis',
                backend_config=config
            )
            
        except Exception as e:
            raise CacheError(f"Failed to create Redis cache: {str(e)}")
    
    @classmethod
    def create_from_config(self, cache_config: Dict[str, Any]) -> ICacheManager:
        """
        Create a cache manager from configuration dictionary.
        
        Args:
            cache_config: Configuration dictionary with cache settings
            
        Returns:
            ICacheManager instance based on configuration
            
        Raises:
            CacheError: If configuration is invalid or cache creation fails
        """
        if not isinstance(cache_config, dict):
            raise CacheError("Cache configuration must be a dictionary")
        
        backend_type = cache_config.get('backend_type', 'memory').lower()
        
        try:
            if backend_type == 'memory':
                return self._create_memory_from_config(cache_config)
            elif backend_type == 'disk':
                return self._create_disk_from_config(cache_config)
            elif backend_type == 'redis':
                return self._create_redis_from_config(cache_config)
            else:
                raise CacheError(f"Unsupported cache backend type: {backend_type}")
                
        except Exception as e:
            raise CacheError(f"Failed to create cache from config: {str(e)}")
    
    @classmethod
    def create_hybrid_cache(
        self,
        primary_config: Dict[str, Any],
        fallback_config: Dict[str, Any]
    ) -> ICacheManager:
        """
        Create a hybrid cache with primary and fallback backends.
        
        Args:
            primary_config: Configuration for primary cache backend
            fallback_config: Configuration for fallback cache backend
            
        Returns:
            ICacheManager with hybrid backend support
            
        Raises:
            CacheError: If cache creation fails
        """
        try:
            primary_cache = self.create_from_config(primary_config)
            fallback_cache = self.create_from_config(fallback_config)
            
            return HybridCacheManager(primary_cache, fallback_cache)
            
        except Exception as e:
            raise CacheError(f"Failed to create hybrid cache: {str(e)}")
    
    @classmethod
    def create_auto_cache(
        self,
        cache_dir: str = 'cache',
        max_memory_entries: int = 500,
        max_disk_size_mb: int = 100,
        redis_host: Optional[str] = None,
        redis_port: int = 6379
    ) -> ICacheManager:
        """
        Create an automatically configured cache based on available resources.
        
        This method attempts to create the best available cache backend:
        1. Redis if available and configured
        2. Disk cache if directory is writable
        3. Memory cache as fallback
        
        Args:
            cache_dir: Directory for disk cache
            max_memory_entries: Maximum entries for memory cache
            max_disk_size_mb: Maximum size for disk cache
            redis_host: Redis host (if None, Redis is not attempted)
            redis_port: Redis port
            
        Returns:
            ICacheManager with the best available backend
        """
        # Try Redis first if host is provided
        if redis_host:
            try:
                return self.create_redis_cache(
                    host=redis_host,
                    port=redis_port
                )
            except CacheError:
                pass  # Fall back to other options
        
        # Try disk cache
        try:
            return self.create_disk_cache(
                cache_dir=cache_dir,
                max_size_mb=max_disk_size_mb
            )
        except CacheError:
            pass  # Fall back to memory cache
        
        # Fall back to memory cache
        return self.create_memory_cache(
            max_entries=max_memory_entries
        )
    
    @classmethod
    def _create_memory_from_config(self, config: Dict[str, Any]) -> ICacheManager:
        """Create memory cache from configuration."""
        memory_config = {**self.DEFAULT_MEMORY_CONFIG}
        memory_config.update(config.get('memory', {}))
        
        return self.create_memory_cache(**memory_config)
    
    @classmethod
    def _create_disk_from_config(self, config: Dict[str, Any]) -> ICacheManager:
        """Create disk cache from configuration."""
        disk_config = {**self.DEFAULT_DISK_CONFIG}
        disk_config.update(config.get('disk', {}))
        
        return self.create_disk_cache(**disk_config)
    
    @classmethod
    def _create_redis_from_config(self, config: Dict[str, Any]) -> ICacheManager:
        """Create Redis cache from configuration."""
        redis_config = {**self.DEFAULT_REDIS_CONFIG}
        redis_config.update(config.get('redis', {}))
        
        return self.create_redis_cache(**redis_config)


class HybridCacheManager:
    """
    Hybrid cache manager that uses primary and fallback cache backends.
    
    This cache manager attempts operations on the primary cache first,
    and falls back to the secondary cache if the primary fails.
    """
    
    def __init__(self, primary: ICacheManager, fallback: ICacheManager):
        """
        Initialize hybrid cache manager.
        
        Args:
            primary: Primary cache backend
            fallback: Fallback cache backend
        """
        self._primary = primary
        self._fallback = fallback
        self._stats = {
            'primary_hits': 0,
            'fallback_hits': 0,
            'primary_failures': 0,
            'total_operations': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache, trying primary first."""
        self._stats['total_operations'] += 1
        
        try:
            result = self._primary.get(key)
            if result is not None:
                self._stats['primary_hits'] += 1
                return result
        except Exception:
            self._stats['primary_failures'] += 1
        
        try:
            result = self._fallback.get(key)
            if result is not None:
                self._stats['fallback_hits'] += 1
                # Store in primary cache for future access
                try:
                    self._primary.set(key, result)
                except Exception:
                    pass  # Ignore primary cache failures
            return result
        except Exception:
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in both caches."""
        primary_success = False
        fallback_success = False
        
        try:
            primary_success = self._primary.set(key, value, ttl)
        except Exception:
            self._stats['primary_failures'] += 1
        
        try:
            fallback_success = self._fallback.set(key, value, ttl)
        except Exception:
            pass
        
        return primary_success or fallback_success
    
    def invalidate(self, key: str) -> bool:
        """Invalidate key in both caches."""
        primary_success = False
        fallback_success = False
        
        try:
            primary_success = self._primary.invalidate(key)
        except Exception:
            self._stats['primary_failures'] += 1
        
        try:
            fallback_success = self._fallback.invalidate(key)
        except Exception:
            pass
        
        return primary_success or fallback_success
    
    def get_cache_key(self, file_path: str, options: Optional[Any] = None) -> str:
        """Generate cache key using primary cache."""
        try:
            return self._primary.get_cache_key(file_path, options)
        except Exception:
            return self._fallback.get_cache_key(file_path, options)
    
    def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result, trying primary first."""
        try:
            result = self._primary.get_cached_result(cache_key)
            if result is not None:
                return result
        except Exception:
            self._stats['primary_failures'] += 1
        
        try:
            return self._fallback.get_cached_result(cache_key)
        except Exception:
            return None
    
    def store_result(self, cache_key: str, result: Any) -> None:
        """Store result in both caches."""
        try:
            self._primary.store_result(cache_key, result)
        except Exception:
            self._stats['primary_failures'] += 1
        
        try:
            self._fallback.store_result(cache_key, result)
        except Exception:
            pass
    
    def clear_cache(self) -> None:
        """Clear both caches."""
        try:
            self._primary.clear_cache()
        except Exception:
            pass
        
        try:
            self._fallback.clear_cache()
        except Exception:
            pass
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get combined cache statistics."""
        primary_stats = {}
        fallback_stats = {}
        
        try:
            primary_stats = self._primary.get_cache_stats()
        except Exception:
            primary_stats = {'error': 'Failed to get primary stats'}
        
        try:
            fallback_stats = self._fallback.get_cache_stats()
        except Exception:
            fallback_stats = {'error': 'Failed to get fallback stats'}
        
        total_ops = self._stats['total_operations']
        primary_success_rate = (
            (total_ops - self._stats['primary_failures']) / total_ops * 100
            if total_ops > 0 else 0
        )
        
        return {
            'backend_type': 'hybrid',
            'primary_stats': primary_stats,
            'fallback_stats': fallback_stats,
            'hybrid_stats': {
                'primary_hits': self._stats['primary_hits'],
                'fallback_hits': self._stats['fallback_hits'],
                'primary_failures': self._stats['primary_failures'],
                'total_operations': self._stats['total_operations'],
                'primary_success_rate_percent': round(primary_success_rate, 2)
            }
        }