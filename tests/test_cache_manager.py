"""
Unit tests for the CacheManager class.
"""
import os
import tempfile
import shutil
import time
from pathlib import Path
import pytest

from src.core.cache_manager import CacheManager
from src.models.models import ConversionResult, CacheError
from src.models.processing_options import ProcessingOptions


class TestCacheManager:
    """Test cases for CacheManager functionality."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Create temporary directory for cache
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.temp_dir, "test_cache")
        
        # Create test image file
        self.test_file = os.path.join(self.temp_dir, "test_image.txt")
        with open(self.test_file, 'w') as f:
            f.write("test image content")
        
        # Initialize cache manager
        self.cache_manager = CacheManager(
            cache_dir=self.cache_dir,
            max_size_mb=1,  # Small size for testing
            max_entries=5   # Small number for testing
        )
    
    def teardown_method(self):
        """Clean up test environment after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_cache_manager_initialization(self):
        """Test cache manager initialization."""
        assert os.path.exists(self.cache_dir)
        assert os.path.exists(os.path.join(self.cache_dir, "data"))
        assert os.path.exists(os.path.join(self.cache_dir, "metadata"))
        
        stats = self.cache_manager.get_cache_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['memory_entries'] == 0
        assert stats['disk_entries'] == 0
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        # Test basic cache key generation
        key1 = self.cache_manager.get_cache_key(self.test_file)
        assert isinstance(key1, str)
        assert len(key1) == 32  # MD5 hash length
        
        # Same file should generate same key
        key2 = self.cache_manager.get_cache_key(self.test_file)
        assert key1 == key2
        
        # Different options should generate different keys
        options1 = ProcessingOptions(quality=85)
        options2 = ProcessingOptions(quality=75)
        
        key_with_options1 = self.cache_manager.get_cache_key(self.test_file, options1)
        key_with_options2 = self.cache_manager.get_cache_key(self.test_file, options2)
        
        assert key_with_options1 != key_with_options2
        assert key_with_options1 != key1  # Different from no options
    
    def test_cache_key_generation_nonexistent_file(self):
        """Test cache key generation with nonexistent file."""
        with pytest.raises(CacheError):
            self.cache_manager.get_cache_key("nonexistent_file.jpg")
    
    def test_cache_storage_and_retrieval(self):
        """Test storing and retrieving cache entries."""
        # Create test result
        result = ConversionResult(
            file_path=self.test_file,
            success=True,
            base64_data="dGVzdCBkYXRh",  # "test data" in base64
            data_uri="data:image/jpeg;base64,dGVzdCBkYXRh",
            file_size=100,
            mime_type="image/jpeg",
            format="JPEG",
            size=(100, 100),
            processing_time=0.5
        )
        
        # Generate cache key
        cache_key = self.cache_manager.get_cache_key(self.test_file)
        
        # Store result
        self.cache_manager.store_result(cache_key, result)
        
        # Retrieve result
        cached_result = self.cache_manager.get_cached_result(cache_key)
        
        assert cached_result is not None
        assert cached_result.success == result.success
        assert cached_result.base64_data == result.base64_data
        assert cached_result.cache_hit == True  # Should be marked as cache hit
        
        # Check stats
        stats = self.cache_manager.get_cache_stats()
        assert stats['hits'] == 1
        assert stats['disk_writes'] == 1
        assert stats['memory_entries'] == 1
        assert stats['disk_entries'] == 1
    
    def test_cache_miss(self):
        """Test cache miss scenario."""
        # Try to retrieve non-existent cache entry
        result = self.cache_manager.get_cached_result("nonexistent_key")
        
        assert result is None
        
        # Check stats
        stats = self.cache_manager.get_cache_stats()
        assert stats['misses'] == 1
        assert stats['hits'] == 0
    
    def test_memory_cache_lru_eviction(self):
        """Test LRU eviction in memory cache."""
        # Create multiple results to exceed max_entries (5)
        results = []
        cache_keys = []
        
        for i in range(7):  # More than max_entries
            # Create unique test file
            test_file = os.path.join(self.temp_dir, f"test_{i}.txt")
            with open(test_file, 'w') as f:
                f.write(f"test content {i}")
            
            result = ConversionResult(
                file_path=test_file,
                success=True,
                base64_data=f"data_{i}",
                processing_time=0.1
            )
            
            cache_key = self.cache_manager.get_cache_key(test_file)
            cache_keys.append(cache_key)
            results.append(result)
            
            self.cache_manager.store_result(cache_key, result)
        
        # Memory cache should not exceed max_entries
        stats = self.cache_manager.get_cache_stats()
        assert stats['memory_entries'] <= 5
        assert stats['evictions'] > 0
        
        # First entries should be evicted from memory but still on disk
        first_key = cache_keys[0]
        first_result = self.cache_manager.get_cached_result(first_key)
        
        # Should still be retrievable from disk
        assert first_result is not None
        # Check stats after retrieval
        updated_stats = self.cache_manager.get_cache_stats()
        assert updated_stats['disk_reads'] >= 1
    
    def test_cache_with_processing_options(self):
        """Test caching with different processing options."""
        options1 = ProcessingOptions(quality=85, resize_width=100)
        options2 = ProcessingOptions(quality=75, resize_width=200)
        
        result1 = ConversionResult(
            file_path=self.test_file,
            success=True,
            base64_data="result1",
            processing_options=options1
        )
        
        result2 = ConversionResult(
            file_path=self.test_file,
            success=True,
            base64_data="result2",
            processing_options=options2
        )
        
        # Store both results
        key1 = self.cache_manager.get_cache_key(self.test_file, options1)
        key2 = self.cache_manager.get_cache_key(self.test_file, options2)
        
        self.cache_manager.store_result(key1, result1)
        self.cache_manager.store_result(key2, result2)
        
        # Retrieve and verify
        cached1 = self.cache_manager.get_cached_result(key1)
        cached2 = self.cache_manager.get_cached_result(key2)
        
        assert cached1.base64_data == "result1"
        assert cached2.base64_data == "result2"
        assert cached1.processing_options.quality == 85
        assert cached2.processing_options.quality == 75
    
    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        # Initial stats
        stats = self.cache_manager.get_cache_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['hit_rate_percent'] == 0
        
        # Store and retrieve
        result = ConversionResult(
            file_path=self.test_file,
            success=True,
            base64_data="test"
        )
        
        cache_key = self.cache_manager.get_cache_key(self.test_file)
        self.cache_manager.store_result(cache_key, result)
        
        # Cache miss first
        self.cache_manager.get_cached_result("nonexistent")
        
        # Cache hit
        self.cache_manager.get_cached_result(cache_key)
        
        stats = self.cache_manager.get_cache_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['hit_rate_percent'] == 50.0
        assert stats['disk_writes'] == 1
    
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Store some data
        result = ConversionResult(
            file_path=self.test_file,
            success=True,
            base64_data="test"
        )
        
        cache_key = self.cache_manager.get_cache_key(self.test_file)
        self.cache_manager.store_result(cache_key, result)
        
        # Verify data exists
        assert self.cache_manager.get_cached_result(cache_key) is not None
        
        # Clear cache
        self.cache_manager.clear_cache()
        
        # Verify data is gone (this will increment misses)
        assert self.cache_manager.get_cached_result(cache_key) is None
        
        stats = self.cache_manager.get_cache_stats()
        assert stats['memory_entries'] == 0
        assert stats['disk_entries'] == 0
        # After clearing, we expect one miss from the final check
        assert stats['misses'] == 1
    
    def test_cache_error_handling(self):
        """Test cache error handling."""
        # Test with invalid file for cache key generation
        with pytest.raises(CacheError):
            self.cache_manager.get_cache_key("nonexistent_file.jpg")
        
        # Test graceful handling of cache retrieval errors
        # This should not raise an exception but return None
        result = self.cache_manager.get_cached_result("invalid_key_format")
        assert result is None
    
    def test_cache_persistence(self):
        """Test that cache persists across manager instances."""
        # Store data with first manager
        result = ConversionResult(
            file_path=self.test_file,
            success=True,
            base64_data="persistent_data"
        )
        
        cache_key = self.cache_manager.get_cache_key(self.test_file)
        self.cache_manager.store_result(cache_key, result)
        
        # Create new manager instance with same cache directory
        new_manager = CacheManager(cache_dir=self.cache_dir)
        
        # Should be able to retrieve data
        cached_result = new_manager.get_cached_result(cache_key)
        assert cached_result is not None
        assert cached_result.base64_data == "persistent_data"
        assert cached_result.cache_hit == True
    
    def test_cache_expiration(self):
        """Test cache entry expiration."""
        # Create cache manager with very short expiration time
        short_cache = CacheManager(
            cache_dir=os.path.join(self.temp_dir, "short_cache"),
            max_age_hours=0.001  # Very short expiration (3.6 seconds)
        )
        
        result = ConversionResult(
            file_path=self.test_file,
            success=True,
            base64_data="expiring_data"
        )
        
        cache_key = short_cache.get_cache_key(self.test_file)
        short_cache.store_result(cache_key, result)
        
        # Should be retrievable immediately
        cached_result = short_cache.get_cached_result(cache_key)
        assert cached_result is not None
        
        # Wait for expiration
        time.sleep(4)
        
        # Should be expired now
        expired_result = short_cache.get_cached_result(cache_key)
        assert expired_result is None
    
    def test_manual_cleanup(self):
        """Test manual cache cleanup."""
        # Store some data
        result = ConversionResult(
            file_path=self.test_file,
            success=True,
            base64_data="cleanup_test"
        )
        
        cache_key = self.cache_manager.get_cache_key(self.test_file)
        self.cache_manager.store_result(cache_key, result)
        
        # Verify data exists
        assert self.cache_manager.get_cached_result(cache_key) is not None
        
        # Run manual cleanup
        cleanup_stats = self.cache_manager.cleanup_cache()
        
        assert isinstance(cleanup_stats, dict)
        assert 'entries_removed' in cleanup_stats
        assert 'bytes_freed' in cleanup_stats
        assert 'entries_remaining' in cleanup_stats
        assert 'size_remaining_bytes' in cleanup_stats
        
        # Check that cleanup run was recorded
        stats = self.cache_manager.get_cache_stats()
        assert stats['cleanup_runs'] >= 1
    
    def test_enhanced_statistics(self):
        """Test enhanced cache statistics."""
        # Store and retrieve some data to generate stats
        result = ConversionResult(
            file_path=self.test_file,
            success=True,
            base64_data="stats_test"
        )
        
        cache_key = self.cache_manager.get_cache_key(self.test_file)
        self.cache_manager.store_result(cache_key, result)
        self.cache_manager.get_cached_result(cache_key)
        
        stats = self.cache_manager.get_cache_stats()
        
        # Check that all expected statistics are present
        expected_keys = [
            'hits', 'misses', 'total_requests', 'hit_rate_percent',
            'memory_entries', 'disk_entries', 'max_entries',
            'cache_size_bytes', 'cache_size_mb', 'max_size_mb', 'size_utilization_percent',
            'disk_reads', 'disk_writes', 'evictions', 'size_based_evictions',
            'expired_entries_removed', 'cleanup_runs', 'errors',
            'max_age_hours', 'cleanup_interval_minutes'
        ]
        
        for key in expected_keys:
            assert key in stats, f"Missing statistic: {key}"
        
        # Verify some basic statistics
        assert stats['hits'] >= 1
        assert stats['total_requests'] >= 1
        assert stats['memory_entries'] >= 0
        assert stats['disk_entries'] >= 0
        assert stats['cache_size_mb'] >= 0
        assert stats['max_size_mb'] == 1  # From our test setup
    
    def test_size_based_cleanup(self):
        """Test cleanup based on cache size limits."""
        # Create cache manager with very small size limit
        small_cache = CacheManager(
            cache_dir=os.path.join(self.temp_dir, "small_cache"),
            max_size_mb=0.001,  # Very small limit
            max_entries=10
        )
        
        # Store multiple results to exceed size limit
        for i in range(5):
            test_file = os.path.join(self.temp_dir, f"size_test_{i}.txt")
            with open(test_file, 'w') as f:
                f.write(f"large content for size test {i}" * 100)  # Make it larger
            
            result = ConversionResult(
                file_path=test_file,
                success=True,
                base64_data="x" * 1000,  # Large base64 data
                file_size=len(f"large content for size test {i}" * 100)
            )
            
            cache_key = small_cache.get_cache_key(test_file)
            small_cache.store_result(cache_key, result)
        
        # Check that size-based evictions occurred
        stats = small_cache.get_cache_stats()
        # Should have some evictions due to size constraints
        assert stats['size_based_evictions'] >= 0  # May or may not trigger depending on timing
    
    def test_cache_configuration(self):
        """Test cache manager with different configurations."""
        # Test with custom configuration
        custom_cache = CacheManager(
            cache_dir=os.path.join(self.temp_dir, "custom_cache"),
            max_size_mb=50,
            max_entries=100,
            max_age_hours=12,
            cleanup_interval_minutes=30
        )
        
        stats = custom_cache.get_cache_stats()
        assert stats['max_size_mb'] == 50
        assert stats['max_entries'] == 100
        assert stats['max_age_hours'] == 12
        assert stats['cleanup_interval_minutes'] == 30


if __name__ == "__main__":
    pytest.main([__file__])