"""
Tests for memory optimization features.

This module tests the memory optimization utilities including:
- Memory pool management
- Streaming image processing
- Memory monitoring
- Garbage collection optimization
"""
import io
import os
import tempfile
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from src.core.memory_optimizer import (
    MemoryPool, StreamingImageProcessor, MemoryMonitor,
    GarbageCollectionOptimizer, optimized_memory_context,
    get_memory_pool, get_memory_monitor, get_gc_optimizer
)
from src.models.models import ConversionError


class TestMemoryPool(unittest.TestCase):
    """Test cases for MemoryPool class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.pool = MemoryPool(initial_size=2, max_size=5, buffer_size=1024)
    
    def test_initialization(self):
        """Test memory pool initialization."""
        self.assertEqual(self.pool.max_size, 5)
        self.assertEqual(self.pool.buffer_size, 1024)
        self.assertEqual(len(self.pool._pool), 2)  # Initial size
        self.assertEqual(self.pool._stats['created'], 2)
    
    def test_get_buffer(self):
        """Test getting a buffer from the pool."""
        buffer = self.pool.get_buffer()
        self.assertIsInstance(buffer, io.BytesIO)
        self.assertEqual(buffer.tell(), 0)  # Should be at beginning
        
        # Pool should have one less buffer
        self.assertEqual(len(self.pool._pool), 1)
        self.assertEqual(self.pool._stats['reused'], 1)
    
    def test_return_buffer(self):
        """Test returning a buffer to the pool."""
        buffer = self.pool.get_buffer()
        buffer.write(b"test data")
        
        self.pool.return_buffer(buffer)
        
        # Pool should have the buffer back
        self.assertEqual(len(self.pool._pool), 2)
        self.assertEqual(self.pool._stats['returned'], 1)
        
        # Buffer should be cleared when returned
        returned_buffer = self.pool.get_buffer()
        self.assertEqual(returned_buffer.tell(), 0)
        self.assertEqual(returned_buffer.read(), b"")
    
    def test_pool_size_limit(self):
        """Test that pool respects maximum size limit."""
        # Fill the pool to maximum
        buffers = []
        for _ in range(7):  # More than max_size
            buffers.append(self.pool.get_buffer())
        
        # Return all buffers
        for buffer in buffers:
            self.pool.return_buffer(buffer)
        
        # Pool should not exceed max_size
        self.assertEqual(len(self.pool._pool), self.pool.max_size)
        # 7 buffers returned, but pool started with 2 and max is 5, so 2 should be discarded
        self.assertEqual(self.pool._stats['discarded'], 2)
    
    def test_managed_buffer_context(self):
        """Test managed buffer context manager."""
        initial_pool_size = len(self.pool._pool)
        
        with self.pool.get_managed_buffer() as buffer:
            self.assertIsInstance(buffer, io.BytesIO)
            buffer.write(b"test data")
            # Pool should have one less buffer
            self.assertEqual(len(self.pool._pool), initial_pool_size - 1)
        
        # Buffer should be returned to pool
        self.assertEqual(len(self.pool._pool), initial_pool_size)
    
    def test_get_stats(self):
        """Test getting pool statistics."""
        buffer = self.pool.get_buffer()
        self.pool.return_buffer(buffer)
        
        stats = self.pool.get_stats()
        
        self.assertIn('pool_size', stats)
        self.assertIn('max_size', stats)
        self.assertIn('buffer_size', stats)
        self.assertIn('stats', stats)
        self.assertEqual(stats['max_size'], 5)
        self.assertEqual(stats['buffer_size'], 1024)
    
    def test_clear(self):
        """Test clearing the pool."""
        self.pool.clear()
        self.assertEqual(len(self.pool._pool), 0)


class TestStreamingImageProcessor(unittest.TestCase):
    """Test cases for StreamingImageProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = StreamingImageProcessor(chunk_size=1024)
        
        # Create a temporary test image
        self.temp_dir = tempfile.mkdtemp()
        self.test_image_path = os.path.join(self.temp_dir, "test_image.png")
        
        # Create a simple test image
        test_image = Image.new('RGB', (100, 100), color='red')
        test_image.save(self.test_image_path, 'PNG')
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_image_path):
            os.remove(self.test_image_path)
        os.rmdir(self.temp_dir)
    
    def test_initialization(self):
        """Test streaming processor initialization."""
        self.assertEqual(self.processor.chunk_size, 1024)
        self.assertIsInstance(self.processor.memory_pool, MemoryPool)
    
    def test_stream_file_to_buffer(self):
        """Test streaming a file to buffer."""
        buffer = self.processor.stream_file_to_buffer(self.test_image_path)
        
        self.assertIsInstance(buffer, io.BytesIO)
        # Buffer should be positioned at start (seek(0) is called in the method)
        self.assertEqual(buffer.tell(), 0)
        
        # Buffer should contain valid image data
        image = Image.open(buffer)
        self.assertEqual(image.size, (100, 100))
    
    def test_stream_file_size_limit(self):
        """Test file size limit enforcement."""
        with self.assertRaises(ConversionError) as context:
            self.processor.stream_file_to_buffer(self.test_image_path, max_size=100)  # Very small limit
        
        self.assertIn("File too large", str(context.exception))
    
    def test_stream_nonexistent_file(self):
        """Test streaming a nonexistent file."""
        with self.assertRaises(ConversionError) as context:
            self.processor.stream_file_to_buffer("nonexistent.png")
        
        self.assertIn("File not found", str(context.exception))
    
    def test_stream_image_from_buffer(self):
        """Test loading image from buffer."""
        buffer = self.processor.stream_file_to_buffer(self.test_image_path)
        image = self.processor.stream_image_from_buffer(buffer)
        
        self.assertIsInstance(image, Image.Image)
        self.assertEqual(image.size, (100, 100))
        self.assertEqual(image.mode, 'RGB')
    
    def test_get_image_info_streaming(self):
        """Test getting image info without loading full image."""
        info = self.processor.get_image_info_streaming(self.test_image_path)
        
        self.assertIn('size', info)
        self.assertIn('width', info)
        self.assertIn('height', info)
        self.assertIn('format', info)
        self.assertIn('file_size', info)
        
        self.assertEqual(info['size'], (100, 100))
        self.assertEqual(info['width'], 100)
        self.assertEqual(info['height'], 100)
        self.assertEqual(info['format'], 'PNG')
        self.assertGreater(info['file_size'], 0)
    
    def test_process_large_image_streaming(self):
        """Test processing large image with streaming."""
        def dummy_processor(image):
            # Simple processor that resizes image
            return image.resize((50, 50))
        
        result = self.processor.process_large_image_streaming(
            self.test_image_path, 
            dummy_processor,
            max_memory_mb=10
        )
        
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.size, (50, 50))


class TestMemoryMonitor(unittest.TestCase):
    """Test cases for MemoryMonitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitor = MemoryMonitor(warning_threshold_mb=100, critical_threshold_mb=200)
    
    def test_initialization(self):
        """Test memory monitor initialization."""
        self.assertEqual(self.monitor.warning_threshold, 100 * 1024 * 1024)
        self.assertEqual(self.monitor.critical_threshold, 200 * 1024 * 1024)
    
    def test_get_memory_usage(self):
        """Test getting memory usage information."""
        usage = self.monitor.get_memory_usage()
        
        self.assertIn('rss', usage)
        self.assertIn('vms', usage)
        self.assertIn('percent', usage)
        self.assertIn('rss_mb', usage)
        self.assertIn('vms_mb', usage)
        self.assertIn('system_total_mb', usage)
        self.assertIn('system_available_mb', usage)
        
        # Values should be reasonable
        self.assertGreater(usage['rss'], 0)
        self.assertGreater(usage['rss_mb'], 0)
    
    def test_check_memory_thresholds(self):
        """Test memory threshold checking."""
        result = self.monitor.check_memory_thresholds()
        
        self.assertIn('usage', result)
        self.assertIn('warning', result)
        self.assertIn('critical', result)
        self.assertIn('warning_threshold_mb', result)
        self.assertIn('critical_threshold_mb', result)
        
        self.assertIsInstance(result['warning'], bool)
        self.assertIsInstance(result['critical'], bool)
    
    def test_add_callback(self):
        """Test adding memory threshold callbacks."""
        callback_called = []
        
        def test_callback(threshold_type, usage):
            callback_called.append((threshold_type, usage))
        
        self.monitor.add_callback(test_callback, 'warning')
        
        # Manually trigger callback
        self.monitor._trigger_callbacks('warning', {'test': 'data'})
        
        self.assertEqual(len(callback_called), 1)
        self.assertEqual(callback_called[0][0], 'warning')
        self.assertEqual(callback_called[0][1], {'test': 'data'})
    
    def test_monitor_operation_context(self):
        """Test operation monitoring context manager."""
        with self.monitor.monitor_operation("test_operation") as monitoring_data:
            self.assertIn('operation_name', monitoring_data)
            self.assertIn('start_usage', monitoring_data)
            self.assertIn('start_time', monitoring_data)
            self.assertEqual(monitoring_data['operation_name'], "test_operation")
            
            # Simulate some work
            time.sleep(0.01)
        
        # After context, should have end data
        self.assertIn('end_usage', monitoring_data)
        self.assertIn('end_time', monitoring_data)
        self.assertIn('duration', monitoring_data)
        self.assertIn('memory_delta_mb', monitoring_data)
        self.assertGreater(monitoring_data['duration'], 0)


class TestGarbageCollectionOptimizer(unittest.TestCase):
    """Test cases for GarbageCollectionOptimizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.optimizer = GarbageCollectionOptimizer()
    
    def test_initialization(self):
        """Test GC optimizer initialization."""
        self.assertIsNotNone(self.optimizer.original_thresholds)
        self.assertIn('manual_collections', self.optimizer.stats)
        self.assertIn('objects_collected', self.optimizer.stats)
        self.assertIn('time_spent', self.optimizer.stats)
    
    def test_manual_collect(self):
        """Test manual garbage collection."""
        result = self.optimizer.manual_collect()
        
        self.assertIn('objects_collected', result)
        self.assertIn('duration', result)
        self.assertIn('generation', result)
        self.assertIn('total_stats', result)
        
        self.assertIsInstance(result['objects_collected'], int)
        self.assertGreaterEqual(result['objects_collected'], 0)
        self.assertGreater(result['duration'], 0)
        
        # Stats should be updated
        self.assertEqual(self.optimizer.stats['manual_collections'], 1)
    
    def test_get_gc_stats(self):
        """Test getting GC statistics."""
        stats = self.optimizer.get_gc_stats()
        
        self.assertIn('thresholds', stats)
        self.assertIn('counts', stats)
        self.assertIn('stats', stats)
        self.assertIn('optimizer_stats', stats)
        self.assertIn('enabled', stats)
        
        self.assertIsInstance(stats['enabled'], bool)
    
    def test_optimized_context(self):
        """Test optimized GC context manager."""
        import gc
        
        original_enabled = gc.isenabled()
        original_thresholds = gc.get_threshold()
        
        with self.optimizer.optimized_context():
            # GC should be disabled during optimization
            self.assertFalse(gc.isenabled())
        
        # Should be restored after context
        self.assertEqual(gc.isenabled(), original_enabled)
        self.assertEqual(gc.get_threshold(), original_thresholds)


class TestOptimizedMemoryContext(unittest.TestCase):
    """Test cases for optimized memory context manager."""
    
    def test_optimized_memory_context(self):
        """Test the optimized memory context manager."""
        with optimized_memory_context(max_memory_mb=100) as context:
            self.assertIn('memory_pool', context)
            self.assertIn('memory_monitor', context)
            self.assertIn('gc_optimizer', context)
            self.assertIn('monitoring_data', context)
            
            self.assertIsInstance(context['memory_pool'], MemoryPool)
            self.assertIsInstance(context['memory_monitor'], MemoryMonitor)
            self.assertIsInstance(context['gc_optimizer'], GarbageCollectionOptimizer)


class TestGlobalInstances(unittest.TestCase):
    """Test cases for global instance functions."""
    
    def test_get_memory_pool(self):
        """Test getting global memory pool."""
        pool = get_memory_pool()
        self.assertIsInstance(pool, MemoryPool)
        
        # Should return the same instance
        pool2 = get_memory_pool()
        self.assertIs(pool, pool2)
    
    def test_get_memory_monitor(self):
        """Test getting global memory monitor."""
        monitor = get_memory_monitor()
        self.assertIsInstance(monitor, MemoryMonitor)
        
        # Should return the same instance
        monitor2 = get_memory_monitor()
        self.assertIs(monitor, monitor2)
    
    def test_get_gc_optimizer(self):
        """Test getting global GC optimizer."""
        optimizer = get_gc_optimizer()
        self.assertIsInstance(optimizer, GarbageCollectionOptimizer)
        
        # Should return the same instance
        optimizer2 = get_gc_optimizer()
        self.assertIs(optimizer, optimizer2)


if __name__ == '__main__':
    unittest.main()