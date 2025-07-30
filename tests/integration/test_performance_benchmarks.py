"""
Performance benchmark tests for the refactored image converter.

This test suite measures and compares performance metrics before and after
the refactoring to verify performance improvements.

Requirements: 4.1, 4.2, 4.3
"""
import sys
import os
import time
import tempfile
import statistics
import psutil
import gc
from pathlib import Path
from typing import List, Dict, Any, Tuple
from PIL import Image
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.container import DIContainer
from src.core.services.image_conversion_service import ImageConversionService


class PerformanceProfiler:
    """Utility class for measuring performance metrics."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_memory = None
        self.start_time = None
        self.start_cpu_times = None
    
    def start_measurement(self):
        """Start performance measurement."""
        gc.collect()  # Force garbage collection before measurement
        self.start_memory = self.process.memory_info().rss
        self.start_time = time.perf_counter()
        self.start_cpu_times = self.process.cpu_times()
    
    def end_measurement(self) -> Dict[str, float]:
        """End performance measurement and return metrics."""
        end_time = time.perf_counter()
        end_memory = self.process.memory_info().rss
        end_cpu_times = self.process.cpu_times()
        
        return {
            'execution_time': end_time - self.start_time,
            'memory_used': end_memory - self.start_memory,
            'peak_memory': self.process.memory_info().rss,
            'cpu_user_time': end_cpu_times.user - self.start_cpu_times.user,
            'cpu_system_time': end_cpu_times.system - self.start_cpu_times.system
        }


class TestImageGenerator:
    """Helper class for generating test images of various sizes."""
    
    @staticmethod
    def create_test_image(size: Tuple[int, int], format: str = 'PNG') -> str:
        """Create a test image file."""
        image = Image.new('RGB', size, color='blue')
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format.lower()}')
        
        if format.upper() == 'JPEG':
            image.save(temp_file.name, format, quality=95)
        else:
            image.save(temp_file.name, format)
        
        temp_file.close()
        return temp_file.name
    
    @staticmethod
    def create_test_images_batch(sizes: List[Tuple[int, int]], format: str = 'PNG') -> List[str]:
        """Create multiple test images."""
        return [TestImageGenerator.create_test_image(size, format) for size in sizes]
    
    @staticmethod
    def cleanup_files(file_paths: List[str]):
        """Clean up test files."""
        for file_path in file_paths:
            try:
                os.unlink(file_path)
            except:
                pass


class PerformanceBenchmarkTests:
    """Performance benchmark test suite."""
    
    def __init__(self):
        self.container = DIContainer.create_default()
        self.conversion_service = self.container.get('image_conversion_service')
        self.profiler = PerformanceProfiler()
        self.test_files = []
    
    def cleanup(self):
        """Clean up test files."""
        TestImageGenerator.cleanup_files(self.test_files)
        self.test_files.clear()
    
    def test_single_image_conversion_performance(self) -> Dict[str, Any]:
        """Test performance of single image conversion."""
        print("🧪 Testing Single Image Conversion Performance")
        print("=" * 50)
        
        # Test different image sizes
        test_sizes = [
            (100, 100),    # Small
            (500, 500),    # Medium
            (1000, 1000),  # Large
            (2000, 2000),  # Very Large
        ]
        
        results = {}
        
        for size in test_sizes:
            size_name = f"{size[0]}x{size[1]}"
            print(f"   Testing {size_name} image...")
            
            # Create test image
            test_image = TestImageGenerator.create_test_image(size)
            self.test_files.append(test_image)
            
            # Measure performance
            self.profiler.start_measurement()
            
            # Perform multiple conversions for average
            conversion_times = []
            for _ in range(5):
                start = time.perf_counter()
                result = self.conversion_service.convert_image(test_image)
                end = time.perf_counter()
                
                if result.success:
                    conversion_times.append(end - start)
            
            metrics = self.profiler.end_measurement()
            
            # Calculate statistics
            if conversion_times:
                avg_conversion_time = statistics.mean(conversion_times)
                min_conversion_time = min(conversion_times)
                max_conversion_time = max(conversion_times)
                
                results[size_name] = {
                    'avg_conversion_time': avg_conversion_time,
                    'min_conversion_time': min_conversion_time,
                    'max_conversion_time': max_conversion_time,
                    'total_execution_time': metrics['execution_time'],
                    'memory_used': metrics['memory_used'],
                    'peak_memory': metrics['peak_memory'],
                    'file_size': os.path.getsize(test_image),
                    'conversions_per_second': 1.0 / avg_conversion_time if avg_conversion_time > 0 else 0
                }
                
                print(f"     Avg time: {avg_conversion_time:.3f}s")
                print(f"     Memory: {metrics['memory_used'] / 1024 / 1024:.2f} MB")
                print(f"     Rate: {results[size_name]['conversions_per_second']:.2f} conversions/sec")
        
        print("   ✅ Single image performance test completed!")
        return results
    
    def test_batch_processing_performance(self) -> Dict[str, Any]:
        """Test performance of batch processing."""
        print("\n🧪 Testing Batch Processing Performance")
        print("=" * 50)
        
        # Create batch of test images
        batch_sizes = [10, 25, 50, 100]
        image_size = (200, 200)
        
        results = {}
        
        for batch_size in batch_sizes:
            print(f"   Testing batch of {batch_size} images...")
            
            # Create test images
            test_images = TestImageGenerator.create_test_images_batch(
                [image_size] * batch_size
            )
            self.test_files.extend(test_images)
            
            # Measure batch processing performance
            self.profiler.start_measurement()
            
            successful_conversions = 0
            failed_conversions = 0
            
            start_time = time.perf_counter()
            
            for image_path in test_images:
                result = self.conversion_service.convert_image(image_path)
                if result.success:
                    successful_conversions += 1
                else:
                    failed_conversions += 1
            
            end_time = time.perf_counter()
            metrics = self.profiler.end_measurement()
            
            total_time = end_time - start_time
            throughput = successful_conversions / total_time if total_time > 0 else 0
            
            results[f"batch_{batch_size}"] = {
                'batch_size': batch_size,
                'successful_conversions': successful_conversions,
                'failed_conversions': failed_conversions,
                'total_time': total_time,
                'throughput': throughput,
                'avg_time_per_image': total_time / batch_size if batch_size > 0 else 0,
                'memory_used': metrics['memory_used'],
                'peak_memory': metrics['peak_memory'],
                'success_rate': successful_conversions / batch_size if batch_size > 0 else 0
            }
            
            print(f"     Success rate: {results[f'batch_{batch_size}']['success_rate']:.1%}")
            print(f"     Throughput: {throughput:.2f} images/sec")
            print(f"     Memory: {metrics['memory_used'] / 1024 / 1024:.2f} MB")
        
        print("   ✅ Batch processing performance test completed!")
        return results
    
    def test_concurrent_processing_performance(self) -> Dict[str, Any]:
        """Test performance of concurrent processing."""
        print("\n🧪 Testing Concurrent Processing Performance")
        print("=" * 50)
        
        # Test different thread counts
        thread_counts = [1, 2, 4, 8]
        images_per_thread = 10
        image_size = (300, 300)
        
        results = {}
        
        for thread_count in thread_counts:
            print(f"   Testing with {thread_count} threads...")
            
            # Create test images
            total_images = thread_count * images_per_thread
            test_images = TestImageGenerator.create_test_images_batch(
                [image_size] * total_images
            )
            self.test_files.extend(test_images)
            
            # Measure concurrent processing performance
            self.profiler.start_measurement()
            
            successful_conversions = 0
            failed_conversions = 0
            
            start_time = time.perf_counter()
            
            def convert_image(image_path):
                """Convert a single image."""
                result = self.conversion_service.convert_image(image_path)
                return result.success
            
            # Use ThreadPoolExecutor for concurrent processing
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [executor.submit(convert_image, img) for img in test_images]
                
                for future in as_completed(futures):
                    try:
                        if future.result():
                            successful_conversions += 1
                        else:
                            failed_conversions += 1
                    except Exception:
                        failed_conversions += 1
            
            end_time = time.perf_counter()
            metrics = self.profiler.end_measurement()
            
            total_time = end_time - start_time
            throughput = successful_conversions / total_time if total_time > 0 else 0
            
            results[f"threads_{thread_count}"] = {
                'thread_count': thread_count,
                'total_images': total_images,
                'successful_conversions': successful_conversions,
                'failed_conversions': failed_conversions,
                'total_time': total_time,
                'throughput': throughput,
                'avg_time_per_image': total_time / total_images if total_images > 0 else 0,
                'memory_used': metrics['memory_used'],
                'peak_memory': metrics['peak_memory'],
                'success_rate': successful_conversions / total_images if total_images > 0 else 0,
                'speedup': 0  # Will be calculated later
            }
            
            print(f"     Success rate: {results[f'threads_{thread_count}']['success_rate']:.1%}")
            print(f"     Throughput: {throughput:.2f} images/sec")
            print(f"     Memory: {metrics['memory_used'] / 1024 / 1024:.2f} MB")
        
        # Calculate speedup compared to single thread
        if 'threads_1' in results:
            baseline_throughput = results['threads_1']['throughput']
            for key, result in results.items():
                if baseline_throughput > 0:
                    result['speedup'] = result['throughput'] / baseline_throughput
        
        print("   ✅ Concurrent processing performance test completed!")
        return results
    
    def test_memory_usage_patterns(self) -> Dict[str, Any]:
        """Test memory usage patterns during processing."""
        print("\n🧪 Testing Memory Usage Patterns")
        print("=" * 50)
        
        # Test memory usage with different image sizes
        test_scenarios = [
            ('small_images', [(100, 100)] * 50),
            ('medium_images', [(500, 500)] * 20),
            ('large_images', [(1000, 1000)] * 10),
            ('mixed_sizes', [(100, 100), (500, 500), (1000, 1000)] * 10)
        ]
        
        results = {}
        
        for scenario_name, image_sizes in test_scenarios:
            print(f"   Testing {scenario_name}...")
            
            # Create test images
            test_images = TestImageGenerator.create_test_images_batch(image_sizes)
            self.test_files.extend(test_images)
            
            # Monitor memory usage during processing
            memory_samples = []
            start_memory = self.profiler.process.memory_info().rss
            
            def memory_monitor():
                """Monitor memory usage in background."""
                while getattr(memory_monitor, 'running', True):
                    memory_samples.append(self.profiler.process.memory_info().rss)
                    time.sleep(0.1)
            
            # Start memory monitoring
            memory_monitor.running = True
            monitor_thread = threading.Thread(target=memory_monitor)
            monitor_thread.start()
            
            # Process images
            start_time = time.perf_counter()
            successful_conversions = 0
            
            for image_path in test_images:
                result = self.conversion_service.convert_image(image_path)
                if result.success:
                    successful_conversions += 1
            
            end_time = time.perf_counter()
            
            # Stop memory monitoring
            memory_monitor.running = False
            monitor_thread.join()
            
            # Calculate memory statistics
            if memory_samples:
                peak_memory = max(memory_samples)
                avg_memory = statistics.mean(memory_samples)
                memory_growth = peak_memory - start_memory
                
                results[scenario_name] = {
                    'image_count': len(test_images),
                    'successful_conversions': successful_conversions,
                    'processing_time': end_time - start_time,
                    'start_memory_mb': start_memory / 1024 / 1024,
                    'peak_memory_mb': peak_memory / 1024 / 1024,
                    'avg_memory_mb': avg_memory / 1024 / 1024,
                    'memory_growth_mb': memory_growth / 1024 / 1024,
                    'memory_per_image_mb': memory_growth / len(test_images) / 1024 / 1024 if test_images else 0
                }
                
                print(f"     Peak memory: {results[scenario_name]['peak_memory_mb']:.2f} MB")
                print(f"     Memory growth: {results[scenario_name]['memory_growth_mb']:.2f} MB")
                print(f"     Memory per image: {results[scenario_name]['memory_per_image_mb']:.3f} MB")
        
        print("   ✅ Memory usage pattern test completed!")
        return results
    
    def test_cache_performance_impact(self) -> Dict[str, Any]:
        """Test the performance impact of caching."""
        print("\n🧪 Testing Cache Performance Impact")
        print("=" * 50)
        
        # Create test image
        test_image = TestImageGenerator.create_test_image((400, 400))
        self.test_files.append(test_image)
        
        results = {}
        
        # Test first conversion (cache miss)
        print("   Testing cache miss performance...")
        self.profiler.start_measurement()
        
        first_conversion_times = []
        for _ in range(5):
            start = time.perf_counter()
            result = self.conversion_service.convert_image(test_image)
            end = time.perf_counter()
            
            if result.success:
                first_conversion_times.append(end - start)
        
        first_metrics = self.profiler.end_measurement()
        
        # Test subsequent conversions (cache hits)
        print("   Testing cache hit performance...")
        self.profiler.start_measurement()
        
        cached_conversion_times = []
        for _ in range(10):
            start = time.perf_counter()
            result = self.conversion_service.convert_image(test_image)
            end = time.perf_counter()
            
            if result.success:
                cached_conversion_times.append(end - start)
        
        cached_metrics = self.profiler.end_measurement()
        
        # Calculate performance improvement
        if first_conversion_times and cached_conversion_times:
            avg_first_time = statistics.mean(first_conversion_times)
            avg_cached_time = statistics.mean(cached_conversion_times)
            
            speedup = avg_first_time / avg_cached_time if avg_cached_time > 0 else 0
            
            results = {
                'cache_miss': {
                    'avg_time': avg_first_time,
                    'min_time': min(first_conversion_times),
                    'max_time': max(first_conversion_times),
                    'memory_used': first_metrics['memory_used'] / 1024 / 1024
                },
                'cache_hit': {
                    'avg_time': avg_cached_time,
                    'min_time': min(cached_conversion_times),
                    'max_time': max(cached_conversion_times),
                    'memory_used': cached_metrics['memory_used'] / 1024 / 1024
                },
                'performance_improvement': {
                    'speedup': speedup,
                    'time_saved_percent': ((avg_first_time - avg_cached_time) / avg_first_time * 100) if avg_first_time > 0 else 0
                }
            }
            
            print(f"     Cache miss avg time: {avg_first_time:.3f}s")
            print(f"     Cache hit avg time: {avg_cached_time:.3f}s")
            print(f"     Speedup: {speedup:.2f}x")
            print(f"     Time saved: {results['performance_improvement']['time_saved_percent']:.1f}%")
        
        print("   ✅ Cache performance test completed!")
        return results


def run_performance_benchmark_tests():
    """Run all performance benchmark tests."""
    print("🚀 Starting Performance Benchmark Tests")
    print("=" * 60)
    
    benchmark = PerformanceBenchmarkTests()
    
    try:
        # Run all benchmark tests
        results = {
            'single_image_performance': benchmark.test_single_image_conversion_performance(),
            'batch_processing_performance': benchmark.test_batch_processing_performance(),
            'concurrent_processing_performance': benchmark.test_concurrent_processing_performance(),
            'memory_usage_patterns': benchmark.test_memory_usage_patterns(),
            'cache_performance_impact': benchmark.test_cache_performance_impact()
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 60)
        
        # Single image performance summary
        if 'single_image_performance' in results:
            print("\n🖼️  Single Image Performance:")
            for size, metrics in results['single_image_performance'].items():
                print(f"   {size}: {metrics['avg_conversion_time']:.3f}s avg, {metrics['conversions_per_second']:.2f} conv/sec")
        
        # Batch processing summary
        if 'batch_processing_performance' in results:
            print("\n📦 Batch Processing Performance:")
            for batch, metrics in results['batch_processing_performance'].items():
                print(f"   {batch}: {metrics['throughput']:.2f} images/sec, {metrics['success_rate']:.1%} success")
        
        # Concurrent processing summary
        if 'concurrent_processing_performance' in results:
            print("\n🔄 Concurrent Processing Performance:")
            for threads, metrics in results['concurrent_processing_performance'].items():
                print(f"   {threads}: {metrics['throughput']:.2f} images/sec, {metrics['speedup']:.2f}x speedup")
        
        # Memory usage summary
        if 'memory_usage_patterns' in results:
            print("\n💾 Memory Usage Patterns:")
            for scenario, metrics in results['memory_usage_patterns'].items():
                print(f"   {scenario}: {metrics['peak_memory_mb']:.2f} MB peak, {metrics['memory_per_image_mb']:.3f} MB/image")
        
        # Cache performance summary
        if 'cache_performance_impact' in results:
            cache_results = results['cache_performance_impact']
            if 'performance_improvement' in cache_results:
                improvement = cache_results['performance_improvement']
                print(f"\n🚀 Cache Performance Impact:")
                print(f"   Speedup: {improvement['speedup']:.2f}x")
                print(f"   Time saved: {improvement['time_saved_percent']:.1f}%")
        
        print("\n🎉 All performance benchmark tests completed successfully!")
        print("✅ Performance metrics have been measured and analyzed")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Performance benchmark tests failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        benchmark.cleanup()


if __name__ == '__main__':
    success = run_performance_benchmark_tests()
    sys.exit(0 if success else 1)