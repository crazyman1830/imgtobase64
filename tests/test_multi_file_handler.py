"""
Unit tests for the MultiFileHandler class.
"""
import unittest
import tempfile
import time
import os
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.multi_file_handler import MultiFileHandler, FileQueueItem, ProcessingQueue
from src.models.processing_options import ProcessingOptions, ProgressInfo
from src.models.models import ProcessingQueueFullError, ConversionResult, ConversionError


class TestFileQueueItem(unittest.TestCase):
    """Test cases for FileQueueItem class."""
    
    def test_file_queue_item_creation(self):
        """Test basic FileQueueItem creation."""
        options = ProcessingOptions(quality=90)
        item = FileQueueItem(
            file_path="/test/image.jpg",
            options=options,
            priority=1
        )
        
        self.assertEqual(item.file_path, "/test/image.jpg")
        self.assertEqual(item.options, options)
        self.assertEqual(item.priority, 1)
        self.assertIsNone(item.started_time)
        self.assertIsNone(item.completed_time)
        self.assertIsNone(item.result)
        self.assertIsNone(item.error)
        self.assertGreater(item.added_time, 0)
    
    def test_file_queue_item_with_custom_time(self):
        """Test FileQueueItem with custom added_time."""
        custom_time = 1234567890.0
        options = ProcessingOptions()
        item = FileQueueItem(
            file_path="/test/image.jpg",
            options=options,
            added_time=custom_time
        )
        
        self.assertEqual(item.added_time, custom_time)


class TestProcessingQueue(unittest.TestCase):
    """Test cases for ProcessingQueue class."""
    
    def test_processing_queue_creation(self):
        """Test basic ProcessingQueue creation."""
        items = [
            FileQueueItem("/test/image1.jpg", ProcessingOptions()),
            FileQueueItem("/test/image2.jpg", ProcessingOptions())
        ]
        
        queue = ProcessingQueue(
            queue_id="test-queue-123",
            items=items,
            max_concurrent=2
        )
        
        self.assertEqual(queue.queue_id, "test-queue-123")
        self.assertEqual(len(queue.items), 2)
        self.assertEqual(queue.status, "pending")
        self.assertEqual(queue.max_concurrent, 2)
        self.assertFalse(queue.cancelled)
        self.assertGreater(queue.created_time, 0)
    
    def test_processing_queue_with_custom_time(self):
        """Test ProcessingQueue with custom created_time."""
        custom_time = 1234567890.0
        queue = ProcessingQueue(
            queue_id="test-queue",
            items=[],
            created_time=custom_time
        )
        
        self.assertEqual(queue.created_time, custom_time)


class TestMultiFileHandler(unittest.TestCase):
    """Test cases for MultiFileHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = MultiFileHandler(max_concurrent=2, max_queue_size=10)
        
        # Create temporary test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []
        for i in range(3):
            file_path = os.path.join(self.temp_dir, f"test_image_{i}.jpg")
            with open(file_path, 'w') as f:
                f.write(f"test image content {i}")
            self.test_files.append(file_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        for file_path in self.test_files:
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass
        
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass
    
    def test_handler_initialization(self):
        """Test MultiFileHandler initialization."""
        handler = MultiFileHandler(max_concurrent=5, max_queue_size=50)
        
        self.assertEqual(handler.max_concurrent, 5)
        self.assertEqual(handler.max_queue_size, 50)
        self.assertEqual(len(handler._queues), 0)
        self.assertIsNotNone(handler._thread_pool)
        self.assertIsNotNone(handler._lock)
    
    def test_add_to_queue_basic(self):
        """Test basic file addition to queue."""
        options = ProcessingOptions(quality=85)
        queue_id = self.handler.add_to_queue(
            files=self.test_files[:2],
            options=options,
            priority=1
        )
        
        self.assertIsInstance(queue_id, str)
        self.assertIn(queue_id, self.handler._queues)
        
        queue = self.handler._queues[queue_id]
        self.assertEqual(len(queue.items), 2)
        self.assertEqual(queue.items[0].options, options)
        self.assertEqual(queue.items[0].priority, 1)
    
    def test_add_to_queue_empty_files(self):
        """Test adding empty files list raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.handler.add_to_queue(files=[])
        
        self.assertIn("Files list cannot be empty", str(context.exception))
    
    def test_add_to_queue_nonexistent_file(self):
        """Test adding nonexistent file raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.handler.add_to_queue(files=["/nonexistent/file.jpg"])
        
        self.assertIn("File not found", str(context.exception))
    
    def test_add_to_queue_size_limit(self):
        """Test queue size limit enforcement."""
        # Create handler with small queue size
        small_handler = MultiFileHandler(max_queue_size=2)
        
        with self.assertRaises(ProcessingQueueFullError) as context:
            small_handler.add_to_queue(files=self.test_files)  # 3 files > limit of 2
        
        self.assertIn("Queue size limit exceeded", str(context.exception))
    
    def test_add_to_queue_with_callback(self):
        """Test adding queue with progress callback."""
        callback = Mock()
        queue_id = self.handler.add_to_queue(
            files=self.test_files[:1],
            progress_callback=callback
        )
        
        self.assertIn(queue_id, self.handler._progress_callbacks)
        self.assertIn(callback, self.handler._progress_callbacks[queue_id])
    
    def test_get_queue_info_existing(self):
        """Test getting info for existing queue."""
        queue_id = self.handler.add_to_queue(files=self.test_files[:2])
        queue_info = self.handler.get_queue_info(queue_id)
        
        self.assertIsNotNone(queue_info)
        self.assertEqual(queue_info['queue_id'], queue_id)
        self.assertEqual(queue_info['total_files'], 2)
        self.assertEqual(queue_info['pending_files'], 2)
        self.assertEqual(queue_info['processing_files'], 0)
        self.assertEqual(queue_info['completed_files'], 0)
        self.assertEqual(queue_info['error_files'], 0)
        self.assertEqual(queue_info['status'], 'pending')
        self.assertFalse(queue_info['cancelled'])
    
    def test_get_queue_info_nonexistent(self):
        """Test getting info for nonexistent queue."""
        queue_info = self.handler.get_queue_info("nonexistent-queue")
        self.assertIsNone(queue_info)
    
    def test_get_progress_existing(self):
        """Test getting progress for existing queue."""
        queue_id = self.handler.add_to_queue(files=self.test_files[:2])
        progress = self.handler.get_progress(queue_id)
        
        self.assertIsNotNone(progress)
        self.assertIsInstance(progress, ProgressInfo)
        self.assertEqual(progress.queue_id, queue_id)
        self.assertEqual(progress.total_files, 2)
        self.assertEqual(progress.completed_files, 0)
        self.assertEqual(progress.status, 'pending')
        self.assertEqual(progress.error_count, 0)
    
    def test_get_progress_nonexistent(self):
        """Test getting progress for nonexistent queue."""
        progress = self.handler.get_progress("nonexistent-queue")
        self.assertIsNone(progress)
    
    def test_cancel_processing_existing(self):
        """Test cancelling processing for existing queue."""
        queue_id = self.handler.add_to_queue(files=self.test_files[:1])
        result = self.handler.cancel_processing(queue_id)
        
        self.assertTrue(result)
        
        queue = self.handler._queues[queue_id]
        self.assertTrue(queue.cancelled)
        self.assertEqual(queue.status, "cancelled")
    
    def test_cancel_processing_nonexistent(self):
        """Test cancelling processing for nonexistent queue."""
        result = self.handler.cancel_processing("nonexistent-queue")
        self.assertFalse(result)
    
    def test_remove_queue_completed(self):
        """Test removing a completed queue."""
        queue_id = self.handler.add_to_queue(files=self.test_files[:1])
        
        # Manually set queue status to completed
        queue = self.handler._queues[queue_id]
        queue.status = "completed"
        
        result = self.handler.remove_queue(queue_id)
        self.assertTrue(result)
        self.assertNotIn(queue_id, self.handler._queues)
    
    def test_remove_queue_processing(self):
        """Test removing a processing queue (should fail)."""
        queue_id = self.handler.add_to_queue(files=self.test_files[:1])
        
        # Set queue status to processing
        queue = self.handler._queues[queue_id]
        queue.status = "processing"
        
        result = self.handler.remove_queue(queue_id)
        self.assertFalse(result)
        self.assertIn(queue_id, self.handler._queues)
    
    def test_remove_queue_nonexistent(self):
        """Test removing nonexistent queue."""
        result = self.handler.remove_queue("nonexistent-queue")
        self.assertFalse(result)
    
    def test_get_all_queues(self):
        """Test getting information about all queues."""
        queue_id1 = self.handler.add_to_queue(files=self.test_files[:1])
        queue_id2 = self.handler.add_to_queue(files=self.test_files[1:2])
        
        all_queues = self.handler.get_all_queues()
        
        self.assertEqual(len(all_queues), 2)
        self.assertIn(queue_id1, all_queues)
        self.assertIn(queue_id2, all_queues)
        self.assertEqual(all_queues[queue_id1]['total_files'], 1)
        self.assertEqual(all_queues[queue_id2]['total_files'], 1)
    
    def test_cleanup_completed_queues(self):
        """Test cleanup of old completed queues."""
        # Create a queue and mark it as completed with old timestamp
        queue_id = self.handler.add_to_queue(files=self.test_files[:1])
        queue = self.handler._queues[queue_id]
        queue.status = "completed"
        queue.completed_time = time.time() - (25 * 3600)  # 25 hours ago
        
        # Cleanup queues older than 24 hours
        cleanup_count = self.handler.cleanup_completed_queues(max_age_hours=24.0)
        
        self.assertEqual(cleanup_count, 1)
        self.assertNotIn(queue_id, self.handler._queues)
    
    def test_cleanup_completed_queues_recent(self):
        """Test that recent completed queues are not cleaned up."""
        # Create a queue and mark it as completed with recent timestamp
        queue_id = self.handler.add_to_queue(files=self.test_files[:1])
        queue = self.handler._queues[queue_id]
        queue.status = "completed"
        queue.completed_time = time.time() - (1 * 3600)  # 1 hour ago
        
        # Cleanup queues older than 24 hours
        cleanup_count = self.handler.cleanup_completed_queues(max_age_hours=24.0)
        
        self.assertEqual(cleanup_count, 0)
        self.assertIn(queue_id, self.handler._queues)
    
    def test_calculate_estimated_time_no_completed(self):
        """Test estimated time calculation with no completed items."""
        queue_id = self.handler.add_to_queue(files=self.test_files[:2])
        queue = self.handler._queues[queue_id]
        queue.started_time = time.time()
        
        estimated_time = self.handler._calculate_estimated_time(queue)
        self.assertEqual(estimated_time, 0.0)
    
    def test_calculate_estimated_time_with_completed(self):
        """Test estimated time calculation with completed items."""
        queue_id = self.handler.add_to_queue(files=self.test_files[:3])
        queue = self.handler._queues[queue_id]
        queue.started_time = time.time() - 10  # Started 10 seconds ago
        
        # Mark first item as completed (took 5 seconds)
        queue.items[0].started_time = queue.started_time
        queue.items[0].completed_time = queue.started_time + 5
        
        estimated_time = self.handler._calculate_estimated_time(queue)
        
        # Should estimate based on average time (5 seconds) for remaining 2 files
        # With max_concurrent=2, should be about 5 seconds total
        self.assertGreater(estimated_time, 0)
        self.assertLessEqual(estimated_time, 10)  # Should be reasonable
    
    def test_notify_progress_with_callback(self):
        """Test progress notification with callback."""
        callback = Mock()
        queue_id = self.handler.add_to_queue(
            files=self.test_files[:1],
            progress_callback=callback
        )
        
        progress_info = ProgressInfo(
            queue_id=queue_id,
            total_files=1,
            completed_files=0,
            status="processing"
        )
        
        self.handler._notify_progress(queue_id, progress_info)
        callback.assert_called_once_with(progress_info)
    
    def test_notify_progress_callback_error(self):
        """Test progress notification handles callback errors gracefully."""
        def failing_callback(progress):
            raise Exception("Callback error")
        
        queue_id = self.handler.add_to_queue(
            files=self.test_files[:1],
            progress_callback=failing_callback
        )
        
        progress_info = ProgressInfo(
            queue_id=queue_id,
            total_files=1,
            completed_files=0,
            status="processing"
        )
        
        # Should not raise exception
        self.handler._notify_progress(queue_id, progress_info)
    
    def test_get_statistics(self):
        """Test getting handler statistics."""
        # Create some queues with different statuses
        queue_id1 = self.handler.add_to_queue(files=self.test_files[:1])
        queue_id2 = self.handler.add_to_queue(files=self.test_files[1:3])
        
        # Set different statuses
        self.handler._queues[queue_id1].status = "completed"
        self.handler._queues[queue_id2].status = "processing"
        
        stats = self.handler.get_statistics()
        
        self.assertEqual(stats['total_queues'], 2)
        self.assertEqual(stats['active_queues'], 1)  # processing
        self.assertEqual(stats['completed_queues'], 1)
        self.assertEqual(stats['cancelled_queues'], 0)
        self.assertEqual(stats['error_queues'], 0)
        self.assertEqual(stats['total_files'], 3)  # 1 + 2 files
        self.assertEqual(stats['completed_files'], 0)  # No items marked as completed
        self.assertEqual(stats['max_concurrent'], 2)
        self.assertEqual(stats['max_queue_size'], 10)
    
    def test_progress_info_properties(self):
        """Test ProgressInfo calculated properties."""
        progress = ProgressInfo(
            queue_id="test",
            total_files=10,
            completed_files=3,
            error_count=1,
            current_file_progress=0.5
        )
        
        # Test progress_percentage calculation
        expected_percentage = (3 + 0.5) / 10 * 100  # 35%
        self.assertEqual(progress.progress_percentage, expected_percentage)
        
        # Test success_rate calculation
        successful_files = 3 - 1  # completed - errors
        expected_success_rate = (successful_files / 3) * 100  # 66.67%
        self.assertAlmostEqual(progress.success_rate, expected_success_rate, places=2)
    
    def test_progress_info_edge_cases(self):
        """Test ProgressInfo edge cases."""
        # Test with zero total files
        progress = ProgressInfo(
            queue_id="test",
            total_files=0,
            completed_files=0
        )
        self.assertEqual(progress.progress_percentage, 100.0)
        
        # Test with zero completed files
        progress = ProgressInfo(
            queue_id="test",
            total_files=5,
            completed_files=0
        )
        self.assertEqual(progress.success_rate, 100.0)


class TestBatchProcessing(unittest.TestCase):
    """Test cases for batch processing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = MultiFileHandler(max_concurrent=2, max_queue_size=10)
        
        # Create temporary test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []
        for i in range(3):
            file_path = os.path.join(self.temp_dir, f"test_image_{i}.jpg")
            with open(file_path, 'w') as f:
                f.write(f"test image content {i}")
            self.test_files.append(file_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        for file_path in self.test_files:
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass
        
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass
    
    def mock_processor_func(self, file_path: str, options: ProcessingOptions) -> ConversionResult:
        """Mock processor function for testing."""
        # Simulate processing time
        time.sleep(0.1)
        
        return ConversionResult(
            file_path=file_path,
            success=True,
            base64_data="mock_base64_data",
            processing_time=0.1
        )
    
    def mock_failing_processor_func(self, file_path: str, options: ProcessingOptions) -> ConversionResult:
        """Mock processor function that fails for testing."""
        if "test_image_1" in file_path:
            raise ConversionError("Mock processing error")
        
        return ConversionResult(
            file_path=file_path,
            success=True,
            base64_data="mock_base64_data",
            processing_time=0.1
        )
    
    def test_process_queue_basic(self):
        """Test basic queue processing."""
        async def run_test():
            queue_id = self.handler.add_to_queue(files=self.test_files[:2])
            
            results = []
            async for result in self.handler.process_queue(queue_id, self.mock_processor_func):
                results.append(result)
            
            self.assertEqual(len(results), 2)
            for result in results:
                self.assertTrue(result.success)
                self.assertEqual(result.base64_data, "mock_base64_data")
            
            # Check queue status
            progress = self.handler.get_progress(queue_id)
            self.assertEqual(progress.status, "completed")
            self.assertEqual(progress.completed_files, 2)
        
        # Run the async test
        asyncio.run(run_test())
    
    def test_process_queue_with_failures(self):
        """Test queue processing with some failures."""
        async def run_test():
            queue_id = self.handler.add_to_queue(files=self.test_files)
            
            results = []
            async for result in self.handler.process_queue(queue_id, self.mock_failing_processor_func):
                results.append(result)
            
            self.assertEqual(len(results), 3)
            
            # Check that one failed and two succeeded
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]
            
            self.assertEqual(len(successful_results), 2)
            self.assertEqual(len(failed_results), 1)
            
            # Check failed files
            failed_files = self.handler.get_failed_files(queue_id)
            self.assertEqual(len(failed_files), 1)
            self.assertIn("test_image_1", failed_files[0]['file_path'])
        
        # Run the async test
        asyncio.run(run_test())
    
    def test_process_queue_cancellation(self):
        """Test queue processing cancellation."""
        async def run_test():
            queue_id = self.handler.add_to_queue(files=self.test_files)
            
            # Start processing and cancel immediately
            process_task = asyncio.create_task(
                self._collect_results(self.handler.process_queue(queue_id, self.mock_processor_func))
            )
            
            # Cancel after a short delay
            await asyncio.sleep(0.05)
            self.handler.cancel_processing(queue_id)
            
            try:
                results = await process_task
            except asyncio.CancelledError:
                results = []
            
            # Check that processing was cancelled
            progress = self.handler.get_progress(queue_id)
            self.assertEqual(progress.status, "cancelled")
        
        # Run the async test
        asyncio.run(run_test())
    
    async def _collect_results(self, async_generator):
        """Helper to collect results from async generator."""
        results = []
        async for result in async_generator:
            results.append(result)
        return results
    
    def test_start_processing_sync(self):
        """Test starting processing synchronously."""
        queue_id = self.handler.add_to_queue(files=self.test_files[:1])
        
        # This test just verifies the method doesn't crash
        # Full async testing would require more complex setup
        try:
            task = self.handler.start_processing(queue_id, self.mock_processor_func)
            self.assertIsNotNone(task)
        except RuntimeError:
            # Expected if no event loop is running
            pass
    
    def test_get_processing_results(self):
        """Test getting processing results."""
        queue_id = self.handler.add_to_queue(files=self.test_files[:2])
        
        # Manually set some results for testing
        queue = self.handler._queues[queue_id]
        queue.items[0].result = ConversionResult(
            file_path=self.test_files[0],
            success=True,
            base64_data="result1"
        )
        queue.items[1].result = ConversionResult(
            file_path=self.test_files[1],
            success=True,
            base64_data="result2"
        )
        
        results = self.handler.get_processing_results(queue_id)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].base64_data, "result1")
        self.assertEqual(results[1].base64_data, "result2")
    
    def test_get_processing_summary(self):
        """Test getting processing summary."""
        queue_id = self.handler.add_to_queue(files=self.test_files)
        
        # Manually set processing times and results
        queue = self.handler._queues[queue_id]
        queue.started_time = time.time() - 10
        queue.completed_time = time.time()
        queue.status = "completed"
        
        # Set some items as completed
        for i, item in enumerate(queue.items):
            item.started_time = queue.started_time + i
            item.completed_time = queue.started_time + i + 1
            if i == 1:  # Make second item fail
                item.error = "Test error"
            else:
                item.result = ConversionResult(
                    file_path=item.file_path,
                    success=True,
                    base64_data=f"result{i}"
                )
        
        summary = self.handler.get_processing_summary(queue_id)
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary['total_files'], 3)
        self.assertEqual(summary['completed_files'], 3)
        self.assertEqual(summary['successful_files'], 2)
        self.assertEqual(summary['failed_files'], 1)
        self.assertAlmostEqual(summary['success_rate'], 66.67, places=1)
        self.assertEqual(summary['average_processing_time'], 1.0)
        self.assertFalse(summary['cancelled'])


class TestProgressTracking(unittest.TestCase):
    """Test cases for progress tracking functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = MultiFileHandler(max_concurrent=2)
        
        # Create temporary test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []
        for i in range(5):
            file_path = os.path.join(self.temp_dir, f"test_image_{i}.jpg")
            with open(file_path, 'w') as f:
                f.write(f"test image content {i}")
            self.test_files.append(file_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        for file_path in self.test_files:
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass
        
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass
    
    def test_progress_tracking_during_processing(self):
        """Test progress tracking during processing."""
        queue_id = self.handler.add_to_queue(files=self.test_files)
        queue = self.handler._queues[queue_id]
        
        # Simulate processing progress
        queue.started_time = time.time() - 10
        
        # Mark some items as completed
        queue.items[0].started_time = queue.started_time
        queue.items[0].completed_time = queue.started_time + 2
        queue.items[1].started_time = queue.started_time + 1
        queue.items[1].completed_time = queue.started_time + 3
        
        # Mark one as currently processing
        queue.items[2].started_time = queue.started_time + 4
        
        progress = self.handler.get_progress(queue_id)
        
        self.assertEqual(progress.total_files, 5)
        self.assertEqual(progress.completed_files, 2)
        self.assertIn("test_image_2", progress.current_file)
        self.assertEqual(progress.current_file_progress, 0.5)
        self.assertGreater(progress.estimated_time_remaining, 0)
    
    def test_estimated_time_calculation_accuracy(self):
        """Test accuracy of estimated time calculation."""
        queue_id = self.handler.add_to_queue(files=self.test_files)
        queue = self.handler._queues[queue_id]
        
        # Set up realistic processing scenario
        base_time = time.time() - 20
        queue.started_time = base_time
        
        # Complete first 3 files with consistent timing (2 seconds each)
        for i in range(3):
            queue.items[i].started_time = base_time + (i * 2)
            queue.items[i].completed_time = base_time + (i * 2) + 2
        
        estimated_time = self.handler._calculate_estimated_time(queue)
        
        # Should estimate ~2 seconds for remaining 2 files with concurrency=2
        # So approximately 2 seconds total (since they can run in parallel)
        self.assertGreater(estimated_time, 0)
        self.assertLess(estimated_time, 5)  # Should be reasonable
    
    def test_progress_callback_notifications(self):
        """Test progress callback notifications."""
        callback_calls = []
        
        def progress_callback(progress_info):
            callback_calls.append(progress_info)
        
        queue_id = self.handler.add_to_queue(
            files=self.test_files[:2],
            progress_callback=progress_callback
        )
        
        # Simulate progress updates
        progress_info = ProgressInfo(
            queue_id=queue_id,
            total_files=2,
            completed_files=1,
            status="processing"
        )
        
        self.handler._notify_progress(queue_id, progress_info)
        
        self.assertEqual(len(callback_calls), 1)
        self.assertEqual(callback_calls[0].completed_files, 1)
        self.assertEqual(callback_calls[0].status, "processing")
    
    def test_progress_percentage_calculation(self):
        """Test progress percentage calculation."""
        progress = ProgressInfo(
            queue_id="test",
            total_files=10,
            completed_files=4,
            current_file_progress=0.6
        )
        
        # Expected: (4 + 0.6) / 10 * 100 = 46%
        expected_percentage = 46.0
        self.assertEqual(progress.progress_percentage, expected_percentage)
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        progress = ProgressInfo(
            queue_id="test",
            total_files=10,
            completed_files=5,
            error_count=2
        )
        
        # Expected: (5 - 2) / 5 * 100 = 60%
        expected_success_rate = 60.0
        self.assertEqual(progress.success_rate, expected_success_rate)


if __name__ == '__main__':
    unittest.main()