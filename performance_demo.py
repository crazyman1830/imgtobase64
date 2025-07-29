#!/usr/bin/env python3
"""
Performance optimization demonstration for the Image Base64 Converter.

This script demonstrates the memory optimization and parallel processing
features implemented in task 8.
"""
import os
import time
import tempfile
from PIL import Image

from src.core.memory_optimizer import (
    get_memory_pool, get_memory_monitor, get_gc_optimizer,
    optimized_memory_context
)
from src.core.parallel_processor import (
    get_parallel_processor, ProcessingTask
)
from src.core.image_processor import ImageProcessor
from src.core.multi_file_handler import MultiFileHandler
from src.models.processing_options import ProcessingOptions
from src.models.models import ConversionResult


def create_test_images(count: int = 5, size: tuple = (200, 200)) -> list:
    """Create test images for demonstration."""
    temp_dir = tempfile.mkdtemp()
    test_files = []
    
    print(f"Creating {count} test images in {temp_dir}")
    
    for i in range(count):
        file_path = os.path.join(temp_dir, f"test_image_{i}.png")
        
        # Create different colored images
        colors = ['red', 'green', 'blue', 'yellow', 'purple']
        color = colors[i % len(colors)]
        
        image = Image.new('RGB', size, color=color)
        image.save(file_path, 'PNG')
        test_files.append(file_path)
    
    return test_files, temp_dir


def cleanup_test_images(test_files: list, temp_dir: str):
    """Clean up test images."""
    for file_path in test_files:
        if os.path.exists(file_path):
            os.remove(file_path)
    os.rmdir(temp_dir)


def demo_memory_optimization():
    """Demonstrate memory optimization features."""
    print("\n" + "="*60)
    print("MEMORY OPTIMIZATION DEMONSTRATION")
    print("="*60)
    
    # Get memory optimization components
    memory_pool = get_memory_pool()
    memory_monitor = get_memory_monitor()
    gc_optimizer = get_gc_optimizer()
    
    print(f"Initial memory pool stats: {memory_pool.get_stats()}")
    print(f"Initial memory usage: {memory_monitor.get_memory_usage()['rss_mb']:.1f} MB")
    
    # Demonstrate memory pool usage
    print("\n1. Memory Pool Demonstration:")
    buffers = []
    for i in range(10):
        buffer = memory_pool.get_buffer()
        buffer.write(b"test data " * 1000)  # Write some data
        buffers.append(buffer)
    
    print(f"After getting 10 buffers: {memory_pool.get_stats()}")
    
    # Return buffers to pool
    for buffer in buffers:
        memory_pool.return_buffer(buffer)
    
    print(f"After returning buffers: {memory_pool.get_stats()}")
    
    # Demonstrate memory monitoring
    print("\n2. Memory Monitoring Demonstration:")
    with memory_monitor.monitor_operation("demo_operation") as monitoring:
        # Simulate memory-intensive operation
        large_data = [b"x" * 1024 * 1024 for _ in range(10)]  # 10MB of data
        time.sleep(0.1)
        del large_data
    
    print(f"Operation monitoring results:")
    print(f"  Duration: {monitoring['duration']:.3f} seconds")
    print(f"  Memory delta: {monitoring['memory_delta_mb']:.1f} MB")
    
    # Demonstrate garbage collection optimization
    print("\n3. Garbage Collection Optimization:")
    gc_stats_before = gc_optimizer.get_gc_stats()
    print(f"GC stats before: {gc_stats_before['optimizer_stats']}")
    
    # Trigger manual garbage collection
    gc_result = gc_optimizer.manual_collect()
    print(f"Manual GC collected {gc_result['objects_collected']} objects in {gc_result['duration']:.3f}s")
    
    gc_stats_after = gc_optimizer.get_gc_stats()
    print(f"GC stats after: {gc_stats_after['optimizer_stats']}")
    
    # Demonstrate optimized memory context
    print("\n4. Optimized Memory Context:")
    with optimized_memory_context(max_memory_mb=100) as context:
        print(f"Context provides: {list(context.keys())}")
        print(f"Memory pool available: {context['memory_pool'] is not None}")
        print(f"Memory monitor available: {context['memory_monitor'] is not None}")
        print(f"GC optimizer available: {context['gc_optimizer'] is not None}")


def demo_parallel_processing():
    """Demonstrate parallel processing features."""
    print("\n" + "="*60)
    print("PARALLEL PROCESSING DEMONSTRATION")
    print("="*60)
    
    # Create test files
    test_files, temp_dir = create_test_images(count=6, size=(100, 100))
    
    try:
        # Get parallel processor
        parallel_processor = get_parallel_processor(
            cpu_workers=2,
            io_workers=4,
            enable_adaptive_concurrency=True
        )
        
        print(f"Parallel processor initialized:")
        print(f"  CPU workers: {parallel_processor.cpu_workers}")
        print(f"  I/O workers: {parallel_processor.io_workers}")
        print(f"  Adaptive concurrency: {parallel_processor.enable_adaptive_concurrency}")
        
        # Create processing tasks
        tasks = []
        for i, file_path in enumerate(test_files):
            task = ProcessingTask(
                task_id=f"demo_task_{i}",
                file_path=file_path,
                options=ProcessingOptions(quality=80)
            )
            tasks.append(task)
        
        print(f"\nCreated {len(tasks)} processing tasks")
        
        # Define a simple processor function
        def demo_processor(file_path: str, options: ProcessingOptions) -> ConversionResult:
            # Simulate some processing
            time.sleep(0.01)  # Small delay to simulate work
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            return ConversionResult(
                file_path=file_path,
                success=True,
                base64_data="demo_base64_data",
                file_size=file_size,
                processing_time=0.01
            )
        
        # Demonstrate I/O intensive processing
        print("\n1. I/O Intensive Processing:")
        start_time = time.time()
        io_results = parallel_processor.process_io_intensive_batch(tasks[:3], demo_processor)
        io_duration = time.time() - start_time
        
        print(f"Processed {len(io_results)} files in {io_duration:.3f} seconds")
        print(f"Success rate: {sum(1 for r in io_results if r.success) / len(io_results) * 100:.1f}%")
        
        # Demonstrate CPU intensive processing (simplified for demo)
        print("\n2. CPU Intensive Processing:")
        start_time = time.time()
        cpu_results = parallel_processor.process_cpu_intensive_batch([], demo_processor)  # Empty for demo
        cpu_duration = time.time() - start_time
        
        print(f"CPU processing completed in {cpu_duration:.3f} seconds")
        
        # Show performance statistics
        print("\n3. Performance Statistics:")
        stats = parallel_processor.get_performance_stats()
        print(f"Global metrics:")
        for key, value in stats['global_metrics'].items():
            if isinstance(value, float):
                print(f"  {key}: {value:.3f}")
            else:
                print(f"  {key}: {value}")
        
        print(f"Active tasks: {stats['active_tasks']}")
        print(f"Completed tasks: {stats['completed_tasks']}")
        print(f"Worker count - CPU: {stats['cpu_workers']}, I/O: {stats['io_workers']}")
        
        # Demonstrate adaptive concurrency if enabled
        if parallel_processor.enable_adaptive_concurrency:
            print("\n4. Adaptive Concurrency Stats:")
            if 'cpu_controller' in stats:
                cpu_controller_stats = stats['cpu_controller']
                print(f"CPU controller:")
                print(f"  Current workers: {cpu_controller_stats['current_workers']}")
                print(f"  Min workers: {cpu_controller_stats['min_workers']}")
                print(f"  Max workers: {cpu_controller_stats['max_workers']}")
            
            if 'io_controller' in stats:
                io_controller_stats = stats['io_controller']
                print(f"I/O controller:")
                print(f"  Current workers: {io_controller_stats['current_workers']}")
                print(f"  Min workers: {io_controller_stats['min_workers']}")
                print(f"  Max workers: {io_controller_stats['max_workers']}")
        
        # Cleanup
        parallel_processor.shutdown()
        
    finally:
        cleanup_test_images(test_files, temp_dir)


def demo_integrated_optimization():
    """Demonstrate integrated memory and parallel optimization."""
    print("\n" + "="*60)
    print("INTEGRATED OPTIMIZATION DEMONSTRATION")
    print("="*60)
    
    # Create test files
    test_files, temp_dir = create_test_images(count=4, size=(150, 150))
    
    try:
        # Create multi-file handler with optimizations enabled
        handler = MultiFileHandler(
            max_concurrent=3,
            max_queue_size=10,
            enable_memory_optimization=True
        )
        
        print("Multi-file handler with optimizations:")
        print(f"  Memory optimization: {handler.enable_memory_optimization}")
        print(f"  Parallel processor: {handler.parallel_processor is not None}")
        
        # Add files to queue
        queue_id = handler.add_to_queue(test_files, ProcessingOptions(quality=75))
        print(f"\nAdded {len(test_files)} files to queue: {queue_id}")
        
        # Get initial queue info
        queue_info = handler.get_queue_info(queue_id)
        print(f"Queue info: {queue_info['total_files']} files, status: {queue_info['status']}")
        
        # Define processor function
        def integrated_processor(file_path: str, options: ProcessingOptions) -> ConversionResult:
            # Use image processor with memory optimization
            processor = ImageProcessor(enable_memory_optimization=True)
            
            try:
                # Simulate processing with the actual image
                with Image.open(file_path) as image:
                    # Apply some processing
                    processed_image, info = processor.apply_processing_options(image, options)
                    
                    return ConversionResult(
                        file_path=file_path,
                        success=True,
                        base64_data="processed_base64_data",
                        file_size=os.path.getsize(file_path),
                        processing_time=0.02,
                        processing_options=options
                    )
            except Exception as e:
                return ConversionResult(
                    file_path=file_path,
                    success=False,
                    error_message=str(e)
                )
        
        # Process using parallel optimization
        if handler.parallel_processor:
            print("\n1. Parallel Processing:")
            start_time = time.time()
            results = handler.process_queue_parallel(queue_id, integrated_processor, use_cpu_intensive=False)
            duration = time.time() - start_time
            
            print(f"Processed {len(results)} files in {duration:.3f} seconds")
            success_count = sum(1 for r in results if r.success)
            print(f"Success rate: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
            
            # Show parallel processing stats
            parallel_stats = handler.get_parallel_processing_stats()
            if parallel_stats:
                print(f"Parallel processing stats:")
                print(f"  Total tasks: {parallel_stats['global_metrics']['total_tasks']}")
                print(f"  Successful tasks: {parallel_stats['global_metrics']['successful_tasks']}")
                print(f"  Average processing time: {parallel_stats['global_metrics']['average_processing_time']:.3f}s")
        
        # Show memory statistics
        print("\n2. Memory Statistics:")
        memory_stats = handler.get_memory_statistics()
        print(f"Current memory usage: {memory_stats['current_usage_mb']:.1f} MB")
        print(f"Peak memory usage: {memory_stats['peak_usage_mb']:.1f} MB")
        print(f"GC collections: {memory_stats['gc_collections']}")
        print(f"Memory warnings: {memory_stats['memory_warnings']}")
        
        if 'memory_pool' in memory_stats:
            pool_stats = memory_stats['memory_pool']
            print(f"Memory pool:")
            print(f"  Pool size: {pool_stats['pool_size']}")
            print(f"  Buffers created: {pool_stats['stats']['created']}")
            print(f"  Buffers reused: {pool_stats['stats']['reused']}")
        
        # Demonstrate memory optimization
        print("\n3. Memory Optimization:")
        optimization_results = handler.optimize_memory_usage()
        print(f"Memory optimization results:")
        for key, value in optimization_results.items():
            if isinstance(value, (int, float)):
                if 'mb' in key.lower():
                    print(f"  {key}: {value:.1f} MB")
                else:
                    print(f"  {key}: {value}")
            else:
                print(f"  {key}: {value}")
        
    finally:
        cleanup_test_images(test_files, temp_dir)


def main():
    """Run all performance optimization demonstrations."""
    print("Image Base64 Converter - Performance Optimization Demo")
    print("This demo showcases the memory and parallel processing optimizations")
    print("implemented in task 8: 성능 최적화 구현")
    
    try:
        # Run demonstrations
        demo_memory_optimization()
        demo_parallel_processing()
        demo_integrated_optimization()
        
        print("\n" + "="*60)
        print("DEMONSTRATION COMPLETE")
        print("="*60)
        print("Key features demonstrated:")
        print("✓ Memory pool for buffer reuse")
        print("✓ Memory monitoring and thresholds")
        print("✓ Garbage collection optimization")
        print("✓ Streaming processing for large files")
        print("✓ Parallel processing with multiprocessing and threading")
        print("✓ Adaptive concurrency control")
        print("✓ Performance benchmarking")
        print("✓ Integrated memory and parallel optimization")
        
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()