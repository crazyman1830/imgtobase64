"""
Optimized cache manager with advanced caching strategies.

This module provides an enhanced cache manager with optimized cache key generation,
intelligent TTL management, and advanced LRU policies for better performance.
"""

import hashlib
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...domain.exceptions.cache import CacheError
from ...models.models import ConversionResult
from ...models.processing_options import ProcessingOptions
from ..interfaces.cache_manager import ICacheManager
from .cache_manager_service import (
    CacheManagerService,
    DiskCacheBackend,
    MemoryCacheBackend,
)


class OptimizedCacheKey:
    """
    Optimized cache key generator with intelligent hashing strategies.

    This class provides efficient cache key generation based on file content,
    metadata, and processing options with optimizations for different scenarios.
    """

    def __init__(self, use_file_metadata: bool = True, chunk_size: int = 8192):
        """
        Initialize the cache key generator.

        Args:
            use_file_metadata: Whether to include file metadata in key generation
            chunk_size: Chunk size for file content hashing
        """
        self.use_file_metadata = use_file_metadata
        self.chunk_size = chunk_size
        self._hash_cache: Dict[str, Tuple[str, float]] = {}  # path -> (hash, mtime)

    def generate_key(
        self, file_path: str, options: Optional[ProcessingOptions] = None
    ) -> str:
        """
        Generate an optimized cache key for the given file and options.

        Args:
            file_path: Path to the file
            options: Processing options

        Returns:
            Optimized cache key string
        """
        try:
            # Get file hash (with caching for performance)
            file_hash = self._get_file_hash_cached(file_path)

            # Generate options hash
            options_hash = self._get_options_hash(options)

            # Combine hashes
            combined_data = f"{file_hash}:{options_hash}"

            # Add file metadata if enabled
            if self.use_file_metadata:
                metadata_hash = self._get_metadata_hash(file_path)
                combined_data = f"{combined_data}:{metadata_hash}"

            # Generate final key
            cache_key = hashlib.sha256(combined_data.encode()).hexdigest()[
                :32
            ]  # Truncate for efficiency

            return cache_key

        except Exception as e:
            raise CacheError(f"Failed to generate optimized cache key: {e}")

    def _get_file_hash_cached(self, file_path: str) -> str:
        """
        Get file hash with caching based on modification time.

        Args:
            file_path: Path to the file

        Returns:
            File content hash
        """
        try:
            # Get file modification time
            mtime = os.path.getmtime(file_path)

            # Check if we have a cached hash
            if file_path in self._hash_cache:
                cached_hash, cached_mtime = self._hash_cache[file_path]
                if abs(cached_mtime - mtime) < 1.0:  # Within 1 second tolerance
                    return cached_hash

            # Calculate new hash
            file_hash = self._calculate_file_hash(file_path)

            # Cache the result
            self._hash_cache[file_path] = (file_hash, mtime)

            # Cleanup old cache entries (keep only last 100)
            if len(self._hash_cache) > 100:
                # Remove oldest entries
                sorted_items = sorted(self._hash_cache.items(), key=lambda x: x[1][1])
                self._hash_cache = dict(sorted_items[-50:])  # Keep last 50

            return file_hash

        except Exception as e:
            raise CacheError(f"Error calculating file hash: {e}")

    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate file hash using streaming for large files.

        Args:
            file_path: Path to the file

        Returns:
            SHA256 hash of file content
        """
        hasher = hashlib.sha256()

        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(self.chunk_size):
                    hasher.update(chunk)

            return hasher.hexdigest()

        except Exception as e:
            raise CacheError(f"Error reading file for hashing: {e}")

    def _get_options_hash(self, options: Optional[ProcessingOptions]) -> str:
        """
        Generate hash for processing options.

        Args:
            options: Processing options

        Returns:
            Hash string for options
        """
        if options is None:
            return "no_options"

        try:
            # Convert options to dictionary
            options_dict = asdict(options)

            # Sort keys for consistent hashing
            options_json = json.dumps(options_dict, sort_keys=True, default=str)

            # Generate hash
            return hashlib.md5(options_json.encode()).hexdigest()

        except Exception:
            return "invalid_options"

    def _get_metadata_hash(self, file_path: str) -> str:
        """
        Generate hash for file metadata.

        Args:
            file_path: Path to the file

        Returns:
            Hash string for metadata
        """
        try:
            stat = os.stat(file_path)

            # Include relevant metadata
            metadata = {
                "size": stat.st_size,
                "mtime": int(stat.st_mtime),
                "mode": stat.st_mode,
            }

            metadata_json = json.dumps(metadata, sort_keys=True)
            return hashlib.md5(metadata_json.encode()).hexdigest()

        except Exception:
            return "no_metadata"


class IntelligentTTLManager:
    """
    Intelligent TTL (Time To Live) manager for cache entries.

    This class provides dynamic TTL calculation based on file characteristics,
    usage patterns, and system resources.
    """

    def __init__(self):
        """Initialize the TTL manager."""
        self.base_ttl = 3600  # 1 hour default
        self.min_ttl = 300  # 5 minutes minimum
        self.max_ttl = 86400  # 24 hours maximum

        # Usage tracking
        self._access_counts: Dict[str, int] = {}
        self._last_access: Dict[str, float] = {}

    def calculate_ttl(
        self, file_path: str, file_size: int, processing_time: float, cache_key: str
    ) -> int:
        """
        Calculate intelligent TTL for a cache entry.

        Args:
            file_path: Path to the original file
            file_size: Size of the file in bytes
            processing_time: Time taken to process the file
            cache_key: Cache key for tracking usage

        Returns:
            TTL in seconds
        """
        try:
            # Base TTL calculation factors
            size_factor = self._calculate_size_factor(file_size)
            processing_factor = self._calculate_processing_factor(processing_time)
            usage_factor = self._calculate_usage_factor(cache_key)
            frequency_factor = self._calculate_frequency_factor(cache_key)

            # Combine factors
            combined_factor = (
                size_factor + processing_factor + usage_factor + frequency_factor
            ) / 4

            # Calculate final TTL
            calculated_ttl = int(self.base_ttl * combined_factor)

            # Apply bounds
            final_ttl = max(self.min_ttl, min(self.max_ttl, calculated_ttl))

            # Update usage tracking
            self._update_usage_tracking(cache_key)

            return final_ttl

        except Exception:
            return self.base_ttl

    def _calculate_size_factor(self, file_size: int) -> float:
        """
        Calculate TTL factor based on file size.
        Larger files get longer TTL since they're more expensive to process.

        Args:
            file_size: File size in bytes

        Returns:
            Size factor (0.5 to 2.0)
        """
        # Size thresholds
        small_threshold = 1024 * 1024  # 1MB
        large_threshold = 50 * 1024 * 1024  # 50MB

        if file_size < small_threshold:
            return 0.5  # Shorter TTL for small files
        elif file_size > large_threshold:
            return 2.0  # Longer TTL for large files
        else:
            # Linear interpolation between thresholds
            ratio = (file_size - small_threshold) / (large_threshold - small_threshold)
            return 0.5 + (1.5 * ratio)

    def _calculate_processing_factor(self, processing_time: float) -> float:
        """
        Calculate TTL factor based on processing time.
        Longer processing time gets longer TTL.

        Args:
            processing_time: Processing time in seconds

        Returns:
            Processing factor (0.5 to 2.0)
        """
        # Processing time thresholds
        fast_threshold = 0.1  # 100ms
        slow_threshold = 5.0  # 5 seconds

        if processing_time < fast_threshold:
            return 0.5  # Shorter TTL for fast processing
        elif processing_time > slow_threshold:
            return 2.0  # Longer TTL for slow processing
        else:
            # Linear interpolation
            ratio = (processing_time - fast_threshold) / (
                slow_threshold - fast_threshold
            )
            return 0.5 + (1.5 * ratio)

    def _calculate_usage_factor(self, cache_key: str) -> float:
        """
        Calculate TTL factor based on usage frequency.
        More frequently accessed items get longer TTL.

        Args:
            cache_key: Cache key for tracking

        Returns:
            Usage factor (0.5 to 2.0)
        """
        access_count = self._access_counts.get(cache_key, 0)

        if access_count == 0:
            return 1.0  # Default for new items
        elif access_count < 3:
            return 0.7  # Shorter TTL for rarely accessed
        elif access_count > 10:
            return 1.8  # Longer TTL for frequently accessed
        else:
            # Linear interpolation
            ratio = (access_count - 3) / 7
            return 0.7 + (1.1 * ratio)

    def _calculate_frequency_factor(self, cache_key: str) -> float:
        """
        Calculate TTL factor based on access frequency (time between accesses).

        Args:
            cache_key: Cache key for tracking

        Returns:
            Frequency factor (0.5 to 2.0)
        """
        current_time = time.time()
        last_access = self._last_access.get(cache_key, current_time)
        time_since_last = current_time - last_access

        # Frequency thresholds
        frequent_threshold = 300  # 5 minutes
        infrequent_threshold = 3600  # 1 hour

        if time_since_last < frequent_threshold:
            return 1.5  # Longer TTL for frequently accessed
        elif time_since_last > infrequent_threshold:
            return 0.8  # Shorter TTL for infrequently accessed
        else:
            # Linear interpolation
            ratio = (time_since_last - frequent_threshold) / (
                infrequent_threshold - frequent_threshold
            )
            return 1.5 - (0.7 * ratio)

    def _update_usage_tracking(self, cache_key: str) -> None:
        """
        Update usage tracking for a cache key.

        Args:
            cache_key: Cache key to update
        """
        current_time = time.time()

        # Update access count
        self._access_counts[cache_key] = self._access_counts.get(cache_key, 0) + 1

        # Update last access time
        self._last_access[cache_key] = current_time

        # Cleanup old tracking data (keep only last 1000 entries)
        if len(self._access_counts) > 1000:
            # Remove oldest entries based on last access time
            sorted_items = sorted(self._last_access.items(), key=lambda x: x[1])
            keys_to_keep = set(item[0] for item in sorted_items[-500:])  # Keep last 500

            self._access_counts = {
                k: v for k, v in self._access_counts.items() if k in keys_to_keep
            }
            self._last_access = {
                k: v for k, v in self._last_access.items() if k in keys_to_keep
            }

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics.

        Returns:
            Dictionary with usage statistics
        """
        return {
            "tracked_keys": len(self._access_counts),
            "total_accesses": sum(self._access_counts.values()),
            "average_accesses": (
                sum(self._access_counts.values()) / len(self._access_counts)
                if self._access_counts
                else 0
            ),
            "base_ttl": self.base_ttl,
            "min_ttl": self.min_ttl,
            "max_ttl": self.max_ttl,
        }


class OptimizedLRUCache(MemoryCacheBackend):
    """
    Optimized LRU cache with advanced eviction policies.

    This cache extends the basic LRU cache with intelligent eviction
    based on access patterns, entry size, and processing cost.
    """

    def __init__(
        self,
        max_entries: int = 1000,
        max_memory_mb: int = 100,
        max_age_seconds: int = 3600,
    ):
        """
        Initialize the optimized LRU cache.

        Args:
            max_entries: Maximum number of cache entries
            max_memory_mb: Maximum memory usage in MB
            max_age_seconds: Maximum age of cache entries
        """
        super().__init__(max_entries, max_age_seconds)
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_memory_usage = 0

        # Enhanced tracking
        self._entry_sizes: Dict[str, int] = {}
        self._access_frequencies: Dict[str, int] = {}
        self._processing_costs: Dict[str, float] = {}

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        processing_cost: float = 0.0,
    ) -> bool:
        """
        Set a value with enhanced tracking.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live
            processing_cost: Cost of generating this value (for eviction priority)

        Returns:
            True if value was cached successfully
        """
        try:
            # Estimate memory usage of the value
            value_size = self._estimate_size(value)

            # Remove existing entry if present
            if key in self._cache:
                old_size = self._entry_sizes.get(key, 0)
                self.current_memory_usage -= old_size
                del self._cache[key]
                self._entry_sizes.pop(key, None)
                self._access_frequencies.pop(key, None)
                self._processing_costs.pop(key, None)

            # Check if we need to make space
            self._make_space_if_needed(value_size)

            # Create cache entry
            entry = {
                "value": value,
                "created_at": time.time(),
                "ttl": ttl or self.max_age_seconds,
                "access_count": 0,
                "last_accessed": time.time(),
            }

            # Add to cache
            self._cache[key] = entry
            self._entry_sizes[key] = value_size
            self._access_frequencies[key] = 0
            self._processing_costs[key] = processing_cost
            self.current_memory_usage += value_size

            self._stats["sets"] += 1
            return True

        except Exception:
            return False

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value with enhanced tracking.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if key not in self._cache:
            self._stats["misses"] += 1
            return None

        entry = self._cache[key]

        # Check if expired
        if self._is_expired(entry):
            self._remove_entry(key)
            self._stats["misses"] += 1
            self._stats["evictions"] += 1
            return None

        # Update access tracking
        entry["access_count"] += 1
        entry["last_accessed"] = time.time()
        self._access_frequencies[key] = self._access_frequencies.get(key, 0) + 1

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._stats["hits"] += 1

        return entry["value"]

    def _make_space_if_needed(self, required_size: int) -> None:
        """
        Make space in cache if needed using intelligent eviction.

        Args:
            required_size: Size of new entry that needs to be added
        """
        # Check if we need to make space
        while (
            len(self._cache) >= self.max_entries
            or self.current_memory_usage + required_size > self.max_memory_bytes
        ):

            if not self._cache:
                break

            # Find best candidate for eviction
            eviction_candidate = self._find_eviction_candidate()

            if eviction_candidate:
                self._remove_entry(eviction_candidate)
                self._stats["evictions"] += 1
            else:
                # Fallback to LRU if no candidate found
                oldest_key = next(iter(self._cache))
                self._remove_entry(oldest_key)
                self._stats["evictions"] += 1

    def _find_eviction_candidate(self) -> Optional[str]:
        """
        Find the best candidate for eviction using multiple factors.

        Returns:
            Key of entry to evict, or None if no candidate found
        """
        if not self._cache:
            return None

        best_candidate = None
        best_score = float("inf")
        current_time = time.time()

        for key, entry in self._cache.items():
            # Calculate eviction score (lower is better for eviction)
            score = self._calculate_eviction_score(key, entry, current_time)

            if score < best_score:
                best_score = score
                best_candidate = key

        return best_candidate

    def _calculate_eviction_score(
        self, key: str, entry: Dict[str, Any], current_time: float
    ) -> float:
        """
        Calculate eviction score for an entry.
        Lower scores are better candidates for eviction.

        Args:
            key: Cache key
            entry: Cache entry
            current_time: Current timestamp

        Returns:
            Eviction score
        """
        # Factors for eviction score
        age = current_time - entry.get("created_at", current_time)
        last_accessed = current_time - entry.get("last_accessed", current_time)
        access_count = entry.get("access_count", 0)
        entry_size = self._entry_sizes.get(key, 1)
        processing_cost = self._processing_costs.get(key, 1.0)

        # Normalize factors (0-1 range)
        age_factor = min(age / 3600, 1.0)  # Normalize to 1 hour
        recency_factor = min(last_accessed / 1800, 1.0)  # Normalize to 30 minutes
        frequency_factor = 1.0 / (1.0 + access_count)  # Inverse of access count
        size_factor = min(entry_size / (1024 * 1024), 1.0)  # Normalize to 1MB
        cost_factor = 1.0 / (1.0 + processing_cost)  # Inverse of processing cost

        # Weighted combination (higher weight = more important for eviction)
        score = (
            age_factor * 0.3  # Older entries are better candidates
            + recency_factor * 0.3  # Less recently accessed are better candidates
            + frequency_factor * 0.2  # Less frequently accessed are better candidates
            + size_factor * 0.1  # Larger entries are slightly better candidates
            + cost_factor * 0.1  # Lower processing cost are slightly better candidates
        )

        return score

    def _remove_entry(self, key: str) -> None:
        """
        Remove an entry and update tracking.

        Args:
            key: Key to remove
        """
        if key in self._cache:
            del self._cache[key]

        # Update memory tracking
        entry_size = self._entry_sizes.pop(key, 0)
        self.current_memory_usage -= entry_size

        # Clean up tracking data
        self._access_frequencies.pop(key, None)
        self._processing_costs.pop(key, None)

    def _estimate_size(self, value: Any) -> int:
        """
        Estimate memory size of a value.

        Args:
            value: Value to estimate

        Returns:
            Estimated size in bytes
        """
        try:
            if isinstance(value, str):
                return len(value.encode("utf-8"))
            elif isinstance(value, bytes):
                return len(value)
            elif isinstance(value, ConversionResult):
                # Estimate ConversionResult size
                size = 1000  # Base object overhead
                if value.base64_content:
                    size += len(value.base64_content.encode("utf-8"))
                if value.data_uri:
                    size += len(value.data_uri.encode("utf-8"))
                return size
            else:
                # Rough estimate for other objects
                return 1000
        except Exception:
            return 1000  # Default estimate

    def get_stats(self) -> Dict[str, Any]:
        """Get enhanced cache statistics."""
        base_stats = super().get_stats()

        # Add memory usage stats
        base_stats.update(
            {
                "memory_usage_bytes": self.current_memory_usage,
                "memory_usage_mb": round(self.current_memory_usage / (1024 * 1024), 2),
                "max_memory_mb": round(self.max_memory_bytes / (1024 * 1024), 2),
                "memory_utilization_percent": round(
                    (
                        (self.current_memory_usage / self.max_memory_bytes * 100)
                        if self.max_memory_bytes > 0
                        else 0
                    ),
                    2,
                ),
                "average_entry_size_bytes": round(
                    self.current_memory_usage / len(self._cache) if self._cache else 0,
                    2,
                ),
                "total_access_frequency": sum(self._access_frequencies.values()),
                "average_processing_cost": round(
                    (
                        sum(self._processing_costs.values())
                        / len(self._processing_costs)
                        if self._processing_costs
                        else 0
                    ),
                    2,
                ),
            }
        )

        return base_stats


class OptimizedCacheManager(CacheManagerService):
    """
    Optimized cache manager with advanced caching strategies.

    This manager integrates optimized cache key generation, intelligent TTL management,
    and advanced LRU policies for superior caching performance.
    """

    def __init__(
        self,
        backend_type: str = "memory",
        backend_config: Optional[Dict[str, Any]] = None,
        enable_intelligent_ttl: bool = True,
        enable_optimized_keys: bool = True,
    ):
        """
        Initialize the optimized cache manager.

        Args:
            backend_type: Type of cache backend
            backend_config: Backend configuration
            enable_intelligent_ttl: Whether to use intelligent TTL calculation
            enable_optimized_keys: Whether to use optimized key generation
        """
        # Initialize with optimized backend if using memory cache
        if backend_type == "memory" and backend_config is None:
            backend_config = {
                "max_entries": 1000,
                "max_memory_mb": 100,
                "max_age_seconds": 3600,
            }

        super().__init__(backend_type, backend_config)

        # Replace backend with optimized version for memory cache
        if backend_type == "memory":
            self._backend = OptimizedLRUCache(**backend_config)

        # Initialize optimization components
        self.enable_intelligent_ttl = enable_intelligent_ttl
        self.enable_optimized_keys = enable_optimized_keys

        if enable_optimized_keys:
            self._key_generator = OptimizedCacheKey()

        if enable_intelligent_ttl:
            self._ttl_manager = IntelligentTTLManager()

    def get_cache_key(
        self, file_path: str, options: Optional[ProcessingOptions] = None
    ) -> str:
        """
        Generate optimized cache key.

        Args:
            file_path: Path to the file
            options: Processing options

        Returns:
            Optimized cache key
        """
        if self.enable_optimized_keys:
            return self._key_generator.generate_key(file_path, options)
        else:
            return super().get_cache_key(file_path, options)

    def store_result(self, cache_key: str, result: ConversionResult) -> None:
        """
        Store result with intelligent TTL and processing cost tracking.

        Args:
            cache_key: Cache key
            result: Conversion result to store
        """
        try:
            # Calculate intelligent TTL if enabled
            ttl = None
            processing_cost = result.processing_time or 0.0

            if self.enable_intelligent_ttl and hasattr(self, "_ttl_manager"):
                file_size = result.file_size or 0
                ttl = self._ttl_manager.calculate_ttl(
                    result.file_path, file_size, processing_cost, cache_key
                )

            # Prepare result for caching
            result_copy = ConversionResult(
                file_path=result.file_path,
                success=result.success,
                base64_content=result.base64_content,
                data_uri=result.data_uri,
                error_message=result.error_message,
                file_size=result.file_size,
                mime_type=result.mime_type,
                image=None,  # Don't serialize PIL Image
                format=result.format,
                size=result.size,
                processing_options=result.processing_options,
                processing_time=result.processing_time,
                cache_hit=False,
                security_scan_result=result.security_scan_result,
                thumbnail_data=result.thumbnail_data,
            )

            # Store with enhanced tracking for optimized cache
            if isinstance(self._backend, OptimizedLRUCache):
                self._backend.set(cache_key, result_copy, ttl, processing_cost)
            else:
                self._backend.set(cache_key, result_copy, ttl)

        except Exception as e:
            raise CacheError(f"Error storing optimized result in cache: {e}")

    def get_optimization_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive optimization statistics.

        Returns:
            Dictionary with optimization statistics
        """
        stats = self.get_cache_stats()

        # Add optimization-specific stats
        optimization_stats = {
            "intelligent_ttl_enabled": self.enable_intelligent_ttl,
            "optimized_keys_enabled": self.enable_optimized_keys,
        }

        if self.enable_intelligent_ttl and hasattr(self, "_ttl_manager"):
            optimization_stats["ttl_stats"] = self._ttl_manager.get_usage_stats()

        if self.enable_optimized_keys and hasattr(self, "_key_generator"):
            optimization_stats["key_cache_size"] = len(self._key_generator._hash_cache)

        stats["optimization"] = optimization_stats

        return stats

    def clear_optimization_caches(self) -> None:
        """Clear optimization-related caches."""
        if hasattr(self, "_key_generator"):
            self._key_generator._hash_cache.clear()

        if hasattr(self, "_ttl_manager"):
            self._ttl_manager._access_counts.clear()
            self._ttl_manager._last_access.clear()
