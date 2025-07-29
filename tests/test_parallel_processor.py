"""
Tests for parallel processing optimization features.

This module tests the parallel processing utilities including:
- Multiprocessing for CPU-intensive tasks
- Threading for I/O-intensive tasks
- Adaptive concurrency control
- Performance benchmarking
"""
import os
import time
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import threading

from src.core.parallel_processor import (
    ProcessingTask, WorkerStats, AdaptiveConcurrencyController,
    ParallelProcessor, get_parallel_processor, shutdown_parallel_processor
)
from src.models.models import ConversionResult
from src.models.processing_options import ProcessingOptions


class TestProcessingTask(unittest.TestCase):
    """Test cases for ProcessingTask class."""
    
    def test_initialization(self):
        """Test processing task initialization."""
        options = ProcessingOptions()
        task = ProcessingTask(
            task_id="test_task_1",
            file_path="/path/to/file.jpg",
            options=options,
            priority=5
        )
        
        self.assertEqual(task.task_id, "test_task_1")
        self.assertEqual(task.file_path, "/path/to/file.jpg")
        self.assertEqual(task.options, options)
        self.assertEqual(task.priority, 5)
        self.assertIsNone(task.started_time)
        self.assertIsNone(task.completed_time)
        self.assertIsNone(task.result)
        self.assertIsNone(task.error)
        self.assertGreater(task.created_time, 0)
    
    def test_post_init_time(self):
        """Test that created_time is set automatically."""
        task = ProcessingTask(
            task_id="test_task_2",
            file_path="/path/to/file.jpg",
            options=ProcessingOptions()
        )
        
        self.assertGreater(task.created_time, 0)
        self.assertLessEqual(task.created_time, time.time())


class TestWorkerStats(unittest.TestCase):
    """Test cases for WorkerStats class."""
    
    def test_initialization(self):
        """Test worker stats initialization."""
        stats = WorkerStats(
            worker_id="worker_1",
            worker_type="thread"
        )
        
        self.assertEqual(stats.worker_id, "worker_1")
        self.assertEqual(stats.worker_type, "thread")
        self.assertEqual(stats.tasks_completed, 0)
        self.assertEqual(stats.total_processing_time, 0.0)
        self.assertEqual(stats.average_processing_time, 0.0)
        self.assertEqual(stats.errors, 0)
        self.assertGreater(stats.created_time, 0)
        self.assertIsNone(stats.last_active_time)
    
    def test_update_stats_success(self):
        """Test updating stats for successful task."""
        stats = WorkerStats(worker_id="worker_1", worker_type="thread")
        
        stats.update_stats(processing_time=2.5, success=True)
        
        self.assertEqual(stats.tasks_completed, 1)
        self.assertEqual(stats.total_processing_time, 2.5)
        self.assertEqual(stats.average_processing_time, 2.5)
        self.assertEqual(stats.errors, 0)
        self.assertIsNotNone(stats.last_active_time)
    
    def test_update_stats_failure(self):
        """Test updating stats for failed task."""
        stats = WorkerStats(worker_id="worker_1", worker_type="thread")
        
        stats.update_stats(processing_time=1.0, success=False)
        
        self.assertEqual(stats.tasks_completed, 1)
        self.assertEqual(stats.total_processing_time, 1.0)
        self.assertEqual(stats.average_processing_time, 1.0)
        self.assertEqual(stats.errors, 1)
    
    def test_update_stats_multiple(self):
        """Test updating stats for multiple tasks."""
        stats = WorkerStats(worker_id="worker_1", worker_type="thread")
        
        stats.update_stats(processing_time=2.0, success=True)
        stats.update_stats(processing_time=4.0, success=True)
        stats.update_stats(processing_time=1.0, success=False)
        
        self.assertEqual(stats.tasks_completed, 3)
        self.assertEqual(stats.total_processing_time, 7.0)
        self.assertAlmostEqual(stats.average_processing_time, 7.0 / 3, places=2)
        self.assertEqual(stats.errors, 1)


class TestAdaptiveConcurrencyController(unittest.TestCase):
    """Test cases for AdaptiveConcurrencyController class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.controller = AdaptiveConcurrencyController(min_workers=1, max_workers=8)
    
    def test_initialization(self):
        """Test controller initialization."""
        self.assertEqual(self.controller.min_workers, 1)
        self.assertEqual(self.controller.max_workers, 8)
        self.assertEqual(self.controller.current_workers, 1)
        self.assertEqual(len(self.controller.performance_history), 0)
        self.assertEqual(len(self.controller.adjustment_history), 0)
    
    def test_should_adjust_workers(self):
        """Test worker adjustment timing."""
        # Initially should not adjust (just created)
        self.assertFalse(self.controller.should_adjust_workers())
        
        # Simulate time passing
        self.controller.last_adjustment_time = time.time() - 35.0  # 35 seconds ago
        self.assertTrue(self.controller.should_adjust_workers())
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_get_system_metrics(self, mock_memory, mock_cpu):
        """Test getting system metrics."""
        # Mock system metrics
        mock_cpu.return_value = 75.0
        mock_memory.return_value = Mock(percent=60.0, available=2048*1024*1024)
        
        metrics = self.controller.get_system_metrics()
        
        self.assertEqual(metrics['cpu_percent'], 75.0)
        self.assertEqual(metrics['memory_percent'], 60.0)
        self.assertEqual(metrics['available_memory_mb'], 2048.0)
        self.assertIn('load_average', metrics)
    
    def test_calculate_throughput(self):
        """Test throughput calculation."""
        # Create mock worker stats
        stats = [
            WorkerStats(worker_id="w1", worker_type="thread"),
            WorkerStats(worker_id="w2", worker_type="thread")
        ]
        
        # Simulate completed tasks
        stats[0].tasks_completed = 10
        stats[0].total_processing_time = 5.0
        stats[1].tasks_completed = 8
        stats[1].total_processing_time = 4.0
        
        throughput = self.controller.calculate_throughput(stats)
        
        # Total: 18 tasks in 9 seconds = 2 tasks/second
        self.assertAlmostEqual(throughput, 2.0, places=1)
    
    def test_calculate_throughput_empty(self):
        """Test throughput calculation with no stats."""
        throughput = self.controller.calculate_throughput([])
        self.assertEqual(throughput, 0.0)
    
    @patch.object(AdaptiveConcurrencyController, 'get_system_metrics')
    @patch.object(AdaptiveConcurrencyController, 'should_adjust_workers')
    def test_adjust_worker_count(self, mock_should_adjust, mock_get_metrics):
        """Test worker count adjustment."""
        mock_should_adjust.return_value = True
        mock_get_metrics.return_value = {
            'cpu_percent': 40.0,  # Low CPU
            'memory_percent': 50.0,  # Normal memory
            'available_memory_mb': 1000.0,
            'load_average': 0.4
        }
        
        # Should increase workers due to low resource usage
        new_count = self.controller.adjust_worker_count([])
        
        self.assertGreaterEqual(new_count, self.controller.min_workers)
        self.assertLessEqual(new_count, self.controller.max_workers)
    
    def test_get_stats(self):
        """Test getting controller statistics."""
        stats = self.controller.get_stats()
        
        self.assertIn('current_workers', stats)
        self.assertIn('min_workers', stats)
        self.assertIn('max_workers', stats)
        self.assertIn('performance_history', stats)
        self.assertIn('adjustment_history', stats)
        self.assertIn('last_adjustment_time', stats)
        
        self.assertEqual(stats['current_workers'], 1)
        self.assertEqual(stats['min_workers'], 1)
        self.assertEqual(stats['max_workers'], 8)


class TestParallelProcessor(unittest.TestCase):
    """Test cases for ParallelProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = ParallelProcessor(
            cpu_workers=2,
            io_workers=4,
            enable_adaptive_concurrency=False,  # Disable for predictable testing
            max_memory_mb=100
        )
        
        # Create temporary test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []
        
        for i in range(3):
            file_path = os.path.join(self.temp_dir, f"test_image_{i}.png")
            test_image = Image.new('RGB', (50, 50), color='red')
            test_image.save(file_path, 'PNG')
            self.test_files.append(file_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.processor.shutdown()
        
        # Clean up test files
        for file_path in self.test_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        os.rmdir(self.temp_dir)
    
    def test_initialization(self):
        """Test processor initialization."""
        self.assertEqual(self.processor.cpu_workers, 2)
        self.assertEqual(self.processor.io_workers, 4)
        self.assertFalse(self.processor.enable_adaptive_concurrency)
        self.assertEqual(self.processor.max_memory_mb, 100)
        self.assertIsNone(self.processor.process_executor)
        self.assertIsNone(self.processor.thread_executor)
    
    def test_create_processing_tasks(self):
        """Test creating processing tasks."""
        tasks = []
        for i, file_path in enumerate(self.test_files):
            task = ProcessingTask(
                task_id=f"task_{i}",
                file_path=file_path,
                options=ProcessingOptions(),
                priority=i
            )
            tasks.append(task)
        
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0].task_id, "task_0")
        self.assertEqual(tasks[1].priority, 1)
    
    def test_dummy_processor_function(self):
        """Test with a dummy processor function."""
        def dummy_processor(file_path: str, options: ProcessingOptions) -> ConversionResult:
            # Simulate some processing time
            time.sleep(0.01)
            
            return ConversionResult(
                file_path=file_path,
                success=True,
                base64_data="dummy_base64_data",
                file_size=1000,
                processing_time=0.01
            )
        
        # Test the dummy processor
        result = dummy_processor(self.test_files[0], ProcessingOptions())
        self.assertTrue(result.success)
        self.assertEqual(result.base64_data, "dummy_base64_data")
    
    def test_process_io_intensive_batch(self):
        """Test processing I/O intensive batch."""
        def dummy_processor(file_path: str, options: ProcessingOptions) -> ConversionResult:
            return ConversionResult(
                file_path=file_path,
                success=True,
                base64_data="dummy_data",
                file_size=1000,
                processing_time=0.01
            )
        
        # Create tasks
        tasks = []
        for i, file_path in enumerate(self.test_files):
            task = ProcessingTask(
                task_id=f"io_task_{i}",
                file_path=file_path,
                options=ProcessingOptions()
            )
            tasks.append(task)
        
        # Process tasks
        results = self.processor.process_io_intensive_batch(tasks, dummy_processor)
        
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertTrue(result.success)
            self.assertEqual(result.base64_data, "dummy_data")
    
    def test_process_cpu_intensive_batch(self):
        """Test processing CPU intensive batch."""
        # For CPU intensive testing, we'll test the structure without actual multiprocessing
        # due to pickling issues in test environment
        
        # Test that the method exists and handles empty batches
        results = self.processor.process_cpu_intensive_batch([], lambda x, y: None)
        self.assertEqual(len(results), 0)
        
        # Test initialization of executors
        self.processor._initialize_executors()
        self.assertIsNotNone(self.processor.process_executor)
        self.assertIsNotNone(self.processor.thread_executor)
    
    def test_get_performance_stats(self):
        """Test getting performance statistics."""
        stats = self.processor.get_performance_stats()
        
        self.assertIn('global_metrics', stats)
        self.assertIn('worker_stats', stats)
        self.assertIn('active_tasks', stats)
        self.assertIn('completed_tasks', stats)
        self.assertIn('cpu_workers', stats)
        self.assertIn('io_workers', stats)
        
        self.assertEqual(stats['cpu_workers'], 2)
        self.assertEqual(stats['io_workers'], 4)
        self.assertEqual(stats['active_tasks'], 0)
        self.assertEqual(stats['completed_tasks'], 0)
    
    def test_error_handling(self):
        """Test error handling in parallel processing."""
        def failing_processor(file_path: str, options: ProcessingOptions) -> ConversionResult:
            raise Exception("Simulated processing error")
        
        # Create tasks
        tasks = []
        for i, file_path in enumerate(self.test_files[:1]):  # Just one task
            task = ProcessingTask(
                task_id=f"error_task_{i}",
                file_path=file_path,
                options=ProcessingOptions()
            )
            tasks.append(task)
        
        # Process tasks (should handle errors gracefully)
        results = self.processor.process_io_intensive_batch(tasks, failing_processor)
        
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)
        self.assertIn("error", results[0].error_message.lower())
    
    def test_empty_batch(self):
        """Test processing empty batch."""
        def dummy_processor(file_path: str, options: ProcessingOptions) -> ConversionResult:
            return ConversionResult(file_path=file_path, success=True)
        
        results = self.processor.process_io_intensive_batch([], dummy_processor)
        self.assertEqual(len(results), 0)
        
        results = self.processor.process_cpu_intensive_batch([], dummy_processor)
        self.assertEqual(len(results), 0)
    
    def test_shutdown(self):
        """Test processor shutdown."""
        # Initialize executors
        self.processor._initialize_executors()
        self.assertIsNotNone(self.processor.process_executor)
        self.assertIsNotNone(self.processor.thread_executor)
        
        # Shutdown
        self.processor.shutdown()
        self.assertIsNone(self.processor.process_executor)
        self.assertIsNone(self.processor.thread_executor)


class TestParallelProcessorWithAdaptiveConcurrency(unittest.TestCase):
    """Test cases for ParallelProcessor with adaptive concurrency enabled."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = ParallelProcessor(
            cpu_workers=2,
            io_workers=4,
            enable_adaptive_concurrency=True,
            max_memory_mb=100
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.processor.shutdown()
    
    def test_adaptive_concurrency_initialization(self):
        """Test initialization with adaptive concurrency."""
        self.assertTrue(self.processor.enable_adaptive_concurrency)
        self.assertIsNotNone(self.processor.cpu_controller)
        self.assertIsNotNone(self.processor.io_controller)
    
    def test_performance_stats_with_adaptive_concurrency(self):
        """Test performance stats include adaptive concurrency data."""
        stats = self.processor.get_performance_stats()
        
        self.assertIn('cpu_controller', stats)
        self.assertIn('io_controller', stats)
        
        # Check controller stats structure
        cpu_stats = stats['cpu_controller']
        self.assertIn('current_workers', cpu_stats)
        self.assertIn('min_workers', cpu_stats)
        self.assertIn('max_workers', cpu_stats)


class TestGlobalParallelProcessor(unittest.TestCase):
    """Test cases for global parallel processor functions."""
    
    def tearDown(self):
        """Clean up after each test."""
        shutdown_parallel_processor()
    
    def test_get_parallel_processor(self):
        """Test getting global parallel processor."""
        processor1 = get_parallel_processor()
        processor2 = get_parallel_processor()
        
        # Should return the same instance
        self.assertIs(processor1, processor2)
        self.assertIsInstance(processor1, ParallelProcessor)
    
    def test_get_parallel_processor_with_args(self):
        """Test getting global parallel processor with arguments."""
        processor = get_parallel_processor(cpu_workers=3, io_workers=6)
        
        self.assertEqual(processor.cpu_workers, 3)
        self.assertEqual(processor.io_workers, 6)
    
    def test_shutdown_parallel_processor(self):
        """Test shutting down global parallel processor."""
        processor = get_parallel_processor()
        self.assertIsNotNone(processor)
        
        shutdown_parallel_processor()
        
        # Getting processor again should create a new instance
        new_processor = get_parallel_processor()
        self.assertIsNotNone(new_processor)
        # Note: We can't easily test that it's a different instance
        # because the global variable gets reset


class TestBenchmarking(unittest.TestCase):
    """Test cases for performance benchmarking."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = ParallelProcessor(
            enable_adaptive_concurrency=False,
            max_memory_mb=100
        )
        
        # Create temporary test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []
        
        for i in range(2):  # Small number for quick testing
            file_path = os.path.join(self.temp_dir, f"bench_image_{i}.png")
            test_image = Image.new('RGB', (30, 30), color='blue')
            test_image.save(file_path, 'PNG')
            self.test_files.append(file_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.processor.shutdown()
        
        # Clean up test files
        for file_path in self.test_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        os.rmdir(self.temp_dir)
    
    def test_benchmark_performance(self):
        """Test performance benchmarking."""
        def dummy_processor(file_path: str, options: ProcessingOptions) -> ConversionResult:
            time.sleep(0.001)  # Very short processing time
            return ConversionResult(
                file_path=file_path,
                success=True,
                base64_data="benchmark_data",
                file_size=500,
                processing_time=0.001
            )
        
        # Create test tasks
        tasks = []
        for i, file_path in enumerate(self.test_files):
            task = ProcessingTask(
                task_id=f"bench_task_{i}",
                file_path=file_path,
                options=ProcessingOptions()
            )
            tasks.append(task)
        
        # Define test configurations
        test_configs = [
            {'cpu_workers': 1, 'io_workers': 2},
            {'cpu_workers': 2, 'io_workers': 4}
        ]
        
        # Run benchmark
        results = self.processor.benchmark_performance(tasks, dummy_processor, test_configs)
        
        self.assertIn('benchmark_results', results)
        self.assertIn('best_configuration', results)
        self.assertIn('recommendation', results)
        
        # Check benchmark results structure
        benchmark_results = results['benchmark_results']
        self.assertEqual(len(benchmark_results), 2)
        
        for result in benchmark_results:
            if 'error' not in result:
                self.assertIn('configuration', result)
                self.assertIn('total_time', result)
                self.assertIn('total_tasks', result)
                self.assertIn('successful_tasks', result)
                self.assertIn('throughput', result)
                self.assertIn('success_rate', result)
        
        # Check recommendation
        recommendation = results['recommendation']
        self.assertIn('cpu_workers', recommendation)
        self.assertIn('io_workers', recommendation)
        self.assertIn('expected_throughput', recommendation)


if __name__ == '__main__':
    unittest.main()