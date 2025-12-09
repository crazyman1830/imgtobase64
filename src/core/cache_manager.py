"""
Cache management system for the image base64 converter.

This module provides caching functionality to improve performance by storing
previously processed conversion results and avoiding redundant processing.
"""

import hashlib
import json
import os
import pickle
import time
from collections import OrderedDict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..models.models import CacheError, ConversionResult
from ..models.processing_options import ProcessingOptions


class CacheManager:
    """
    Manages caching of image conversion results using LRU policy.

    Features:
    - File hash-based cache key generation
    - LRU (Least Recently Used) cache policy
    - Disk-based cache storage and loading
    - Automatic cache size management
    - Cache statistics tracking
    """

    def __init__(
        self,
        cache_dir: str = "cache",
        max_size_mb: int = 100,
        max_entries: int = 1000,
        max_age_hours: int = 24,
        cleanup_interval_minutes: int = 60,
    ):
        """
        Initialize the cache manager.

        Args:
            cache_dir: Directory to store cache files
            max_size_mb: Maximum cache size in megabytes
            max_entries: Maximum number of cache entries
            max_age_hours: Maximum age of cache entries in hours
            cleanup_interval_minutes: Interval between automatic cleanup runs in minutes
        """
        self.cache_dir = Path(cache_dir)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self.max_age_hours = max_age_hours
        self.cleanup_interval_seconds = cleanup_interval_minutes * 60

        # In-memory LRU cache for quick access
        self._memory_cache: OrderedDict[str, ConversionResult] = OrderedDict()

        # Cache metadata
        self._cache_metadata: Dict[str, Dict[str, Any]] = {}

        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "disk_reads": 0,
            "disk_writes": 0,
            "errors": 0,
            "cleanup_runs": 0,
            "expired_entries_removed": 0,
            "size_based_evictions": 0,
        }

        # Cleanup tracking
        self._last_cleanup_time = time.time()

        # Ensure cache directory exists
        self._ensure_cache_directory()

        # Load existing cache metadata
        self._load_cache_metadata()

        # Run initial cleanup
        self._auto_cleanup_if_needed()

    def _ensure_cache_directory(self) -> None:
        """Ensure the cache directory exists."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            # Create subdirectories for organization
            (self.cache_dir / "data").mkdir(exist_ok=True)
            (self.cache_dir / "metadata").mkdir(exist_ok=True)

        except Exception as e:
            raise CacheError(f"Failed to create cache directory: {e}")

    def get_cache_key(
        self, file_path: str, options: Optional[ProcessingOptions] = None
    ) -> str:
        """
        Generate a cache key based on file content and processing options.

        Args:
            file_path: Path to the image file
            options: Processing options used for conversion

        Returns:
            Unique cache key string

        Raises:
            CacheError: If file cannot be read or hashed
        """
        try:
            # Read file content for hashing
            with open(file_path, "rb") as f:
                file_content = f.read()

            # Create hash of file content
            file_hash = hashlib.sha256(file_content).hexdigest()

            # Include processing options in the key
            options_str = ""
            if options:
                # Convert options to a consistent string representation
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
            # Run automatic cleanup if needed
            self._auto_cleanup_if_needed()

            # Check memory cache first
            if cache_key in self._memory_cache:
                # Check if expired before returning
                if self._is_cache_expired(cache_key):
                    # Remove expired entry
                    self._remove_cache_entry(cache_key)
                    self._stats["misses"] += 1
                    self._stats["expired_entries_removed"] += 1
                    return None

                # Move to end (most recently used)
                result = self._memory_cache.pop(cache_key)
                result.cache_hit = True  # Mark as cache hit
                self._memory_cache[cache_key] = result
                self._stats["hits"] += 1

                # Update last accessed time
                if cache_key in self._cache_metadata:
                    self._cache_metadata[cache_key]["last_accessed"] = time.time()

                return result

            # Check disk cache
            disk_result = self._load_from_disk(cache_key)
            if disk_result:
                # Add to memory cache
                self._add_to_memory_cache(cache_key, disk_result)
                self._stats["hits"] += 1
                self._stats["disk_reads"] += 1

                # Update last accessed time
                if cache_key in self._cache_metadata:
                    self._cache_metadata[cache_key]["last_accessed"] = time.time()

                return disk_result

            # Cache miss
            self._stats["misses"] += 1
            return None

        except Exception as e:
            self._stats["errors"] += 1
            # Log error but don't raise - cache failures shouldn't break the app
            print(f"Cache retrieval error: {e}")
            return None

    def store_result(self, cache_key: str, result: ConversionResult) -> None:
        """
        Store a conversion result in the cache.

        Args:
            cache_key: Cache key for the result
            result: ConversionResult to store
        """
        try:
            # Run automatic cleanup if needed
            self._auto_cleanup_if_needed()

            # Mark as cache hit for the stored result
            result.cache_hit = False  # This is the original result, not from cache

            # Add to memory cache
            self._add_to_memory_cache(cache_key, result)

            # Save to disk
            self._save_to_disk(cache_key, result)

            # Update metadata
            self._update_cache_metadata(cache_key, result)

            # Cleanup if necessary
            self._cleanup_if_needed()

        except Exception as e:
            self._stats["errors"] += 1
            # Log error but don't raise - cache failures shouldn't break the app
            print(f"Cache storage error: {e}")

    def _add_to_memory_cache(self, cache_key: str, result: ConversionResult) -> None:
        """Add result to memory cache with LRU management."""
        # Remove if already exists (to update position)
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]

        # Add to end (most recently used)
        self._memory_cache[cache_key] = result

        # Enforce memory cache size limit
        while len(self._memory_cache) > self.max_entries:
            # Remove least recently used (first item)
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]
            self._stats["evictions"] += 1

    def _save_to_disk(self, cache_key: str, result: ConversionResult) -> None:
        """Save conversion result to disk."""
        try:
            cache_file = self.cache_dir / "data" / f"{cache_key}.pkl"

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
                cache_hit=result.cache_hit,
                security_scan_result=result.security_scan_result,
                thumbnail_data=result.thumbnail_data,
            )

            with open(cache_file, "wb") as f:
                pickle.dump(result_copy, f)

            self._stats["disk_writes"] += 1

        except Exception as e:
            raise CacheError(f"Failed to save cache to disk: {e}")

    def _load_from_disk(self, cache_key: str) -> Optional[ConversionResult]:
        """Load conversion result from disk."""
        try:
            cache_file = self.cache_dir / "data" / f"{cache_key}.pkl"

            if not cache_file.exists():
                return None

            # Check if cache entry is expired
            if self._is_cache_expired(cache_key):
                self._remove_cache_entry(cache_key)
                return None

            with open(cache_file, "rb") as f:
                result = pickle.load(f)

            # Mark as cache hit
            result.cache_hit = True

            return result

        except Exception as e:
            # If we can't load the cache file, remove it
            self._remove_cache_entry(cache_key)
            return None

    def _update_cache_metadata(self, cache_key: str, result: ConversionResult) -> None:
        """Update cache metadata for an entry."""
        self._cache_metadata[cache_key] = {
            "created_time": time.time(),
            "last_accessed": time.time(),
            "file_size": result.file_size,
            "success": result.success,
            "processing_time": result.processing_time,
        }

        # Save metadata to disk
        self._save_cache_metadata()

    def _load_cache_metadata(self) -> None:
        """Load cache metadata from disk."""
        try:
            metadata_file = self.cache_dir / "metadata" / "cache_metadata.json"

            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    self._cache_metadata = json.load(f)

        except Exception as e:
            # If metadata is corrupted, start fresh
            self._cache_metadata = {}

    def _save_cache_metadata(self) -> None:
        """Save cache metadata to disk."""
        try:
            metadata_file = self.cache_dir / "metadata" / "cache_metadata.json"

            with open(metadata_file, "w") as f:
                json.dump(self._cache_metadata, f, indent=2)

        except Exception as e:
            print(f"Failed to save cache metadata: {e}")

    def _is_cache_expired(
        self, cache_key: str, max_age_hours: Optional[int] = None
    ) -> bool:
        """Check if a cache entry is expired."""
        if cache_key not in self._cache_metadata:
            return True

        if max_age_hours is None:
            max_age_hours = self.max_age_hours

        created_time = self._cache_metadata[cache_key].get("created_time", 0)
        max_age_seconds = max_age_hours * 3600

        return (time.time() - created_time) > max_age_seconds

    def _remove_cache_entry(self, cache_key: str) -> None:
        """Remove a cache entry from both memory and disk."""
        # Remove from memory cache
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]

        # Remove from disk
        cache_file = self.cache_dir / "data" / f"{cache_key}.pkl"
        if cache_file.exists():
            try:
                cache_file.unlink()
            except Exception:
                pass

        # Remove from metadata
        if cache_key in self._cache_metadata:
            del self._cache_metadata[cache_key]

    def _cleanup_if_needed(self) -> None:
        """Cleanup cache if size limits are exceeded."""
        try:
            # Get current cache size
            current_size = self._get_cache_size()

            if current_size > self.max_size_bytes:
                self._cleanup_by_size()

            # Also cleanup expired entries
            self._cleanup_expired_entries()

        except Exception as e:
            print(f"Cache cleanup error: {e}")

    def _auto_cleanup_if_needed(self) -> None:
        """Run automatic cleanup if enough time has passed."""
        current_time = time.time()

        if (current_time - self._last_cleanup_time) >= self.cleanup_interval_seconds:
            self.cleanup_cache()
            self._last_cleanup_time = current_time

    def _get_cache_size(self) -> int:
        """Get total size of cache in bytes."""
        total_size = 0

        try:
            data_dir = self.cache_dir / "data"
            if data_dir.exists():
                for cache_file in data_dir.glob("*.pkl"):
                    total_size += cache_file.stat().st_size
        except Exception:
            pass

        return total_size

    def _cleanup_by_size(self) -> None:
        """Remove oldest cache entries to stay within size limit."""
        # Sort cache entries by last accessed time
        sorted_entries = sorted(
            self._cache_metadata.items(), key=lambda x: x[1].get("last_accessed", 0)
        )

        current_size = self._get_cache_size()

        # Remove oldest entries until we're under the size limit
        for cache_key, metadata in sorted_entries:
            if current_size <= self.max_size_bytes:
                break

            # Estimate file size (rough approximation)
            estimated_size = (
                metadata.get("file_size", 0) * 2
            )  # Base64 is ~1.33x + overhead

            self._remove_cache_entry(cache_key)
            current_size -= estimated_size
            self._stats["evictions"] += 1
            self._stats["size_based_evictions"] += 1

    def _cleanup_expired_entries(self) -> None:
        """Remove expired cache entries."""
        expired_keys = []

        for cache_key in self._cache_metadata:
            if self._is_cache_expired(cache_key):
                expired_keys.append(cache_key)

        for cache_key in expired_keys:
            self._remove_cache_entry(cache_key)
            self._stats["evictions"] += 1
            self._stats["expired_entries_removed"] += 1

    def cleanup_cache(self) -> Dict[str, int]:
        """
        Manually run cache cleanup and return cleanup statistics.

        Returns:
            Dictionary with cleanup statistics
        """
        initial_entries = len(self._cache_metadata)
        initial_size = self._get_cache_size()

        try:
            # Cleanup expired entries
            self._cleanup_expired_entries()

            # Cleanup by size if needed
            if self._get_cache_size() > self.max_size_bytes:
                self._cleanup_by_size()

            self._stats["cleanup_runs"] += 1

            final_entries = len(self._cache_metadata)
            final_size = self._get_cache_size()

            return {
                "entries_removed": initial_entries - final_entries,
                "bytes_freed": initial_size - final_size,
                "entries_remaining": final_entries,
                "size_remaining_bytes": final_size,
            }

        except Exception as e:
            self._stats["errors"] += 1
            raise CacheError(f"Cache cleanup failed: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.

        Returns:
            Dictionary containing cache statistics
        """
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (
            (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        # Calculate cache efficiency
        cache_size_mb = self._get_cache_size() / (1024 * 1024)
        size_utilization = (
            (cache_size_mb / (self.max_size_bytes / (1024 * 1024)) * 100)
            if self.max_size_bytes > 0
            else 0
        )

        return {
            # Hit/Miss Statistics
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            # Cache Size and Entries
            "memory_entries": len(self._memory_cache),
            "disk_entries": len(self._cache_metadata),
            "max_entries": self.max_entries,
            "cache_size_bytes": self._get_cache_size(),
            "cache_size_mb": round(cache_size_mb, 2),
            "max_size_mb": round(self.max_size_bytes / (1024 * 1024), 2),
            "size_utilization_percent": round(size_utilization, 2),
            # Operations Statistics
            "disk_reads": self._stats["disk_reads"],
            "disk_writes": self._stats["disk_writes"],
            "evictions": self._stats["evictions"],
            "size_based_evictions": self._stats["size_based_evictions"],
            "expired_entries_removed": self._stats["expired_entries_removed"],
            "cleanup_runs": self._stats["cleanup_runs"],
            "errors": self._stats["errors"],
            # Configuration
            "max_age_hours": self.max_age_hours,
            "cleanup_interval_minutes": self.cleanup_interval_seconds / 60,
        }

    def clear_cache(self) -> None:
        """Clear all cache entries."""
        try:
            # Clear memory cache
            self._memory_cache.clear()

            # Clear disk cache
            data_dir = self.cache_dir / "data"
            if data_dir.exists():
                for cache_file in data_dir.glob("*.pkl"):
                    cache_file.unlink()

            # Clear metadata
            self._cache_metadata.clear()
            self._save_cache_metadata()

            # Reset stats (but keep existing stats for testing purposes)
            # Only reset the counters that should be reset
            self._stats.update(
                {
                    "hits": 0,
                    "misses": 0,
                    "evictions": 0,
                    "disk_reads": 0,
                    "disk_writes": 0,
                    "errors": 0,
                    "cleanup_runs": 0,
                    "expired_entries_removed": 0,
                    "size_based_evictions": 0,
                }
            )

        except Exception as e:
            raise CacheError(f"Failed to clear cache: {e}")
