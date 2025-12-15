"""
Parallel processing strategy using multiprocessing.
"""

import asyncio
import time
from typing import AsyncGenerator, Callable, Optional, List

from .base import ProcessingStrategy
from ..manager import ProcessingQueue
from ....models.models import ConversionResult, ConversionError
from ....models.processing_options import ProcessingOptions
from ...parallel_processor import ParallelProcessor, ProcessingTask


class ParallelProcessStrategy(ProcessingStrategy):
    """
    Strategy using ParallelProcessor (multiprocessing).
    """

    def __init__(self, parallel_processor: ParallelProcessor, use_cpu_intensive: bool = False):
        self.parallel_processor = parallel_processor
        self.use_cpu_intensive = use_cpu_intensive

    async def execute(
        self,
        queue: ProcessingQueue,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult]
    ) -> AsyncGenerator[ConversionResult, None]:
        
        queue_id = queue.queue_id
        queue.status = "processing"
        queue.started_time = time.time()
        
        try:
            # Convert items to tasks
            tasks = [
                ProcessingTask(
                    task_id=f"{queue_id}_{item.file_path}",
                    file_path=item.file_path,
                    options=item.options
                )
                for item in queue.items
                if not item.completed_time
            ]
            
            # Since ParallelProcessor is synchronous (it uses ProcessPoolExecutor internally but returns list),
            # we need to wrap it in run_in_executor to not block the asyncio loop if it takes time to submit?
            # Actually ParallelProcessor.process_*_batch methods seem to return results directly (blocking).
            # We should wrap this block.
            
            loop = asyncio.get_running_loop()
            
            def run_parallel():
                if self.use_cpu_intensive:
                    return self.parallel_processor.process_cpu_intensive_batch(tasks, processor_func)
                else:
                    return self.parallel_processor.process_io_intensive_batch(tasks, processor_func)

            results: List[ConversionResult] = await loop.run_in_executor(None, run_parallel)
            
            # Now we update items and yield results
            # Note: ParallelProcessor returns results in same order if we preserve it, 
            # or `results` might be just a list. 
            # The original code zipped queue.items and results. ParallelProcessor preserves order usually.
            
            # Map results back to items
            # In original code: for i, (item, result) in enumerate(zip(queue.items, results)):
            
            # But here queue.items might contain completed items if we resumed.
            # We only selected pending items.
            
            # Let's match by file path to be safe or just assume order of `tasks` corresponds to `results`.
            
            for i, result in enumerate(results):
                if queue.cancelled:
                    break
                
                # Yield result one by one
                yield result
                
                # Update item in queue
                # We need to find the item. `tasks[i]` corresponds to `results[i]`
                task_item = tasks[i]
                
                # Find matching item in queue (inefficient O(N^2) but robust)
                for item in queue.items:
                    if item.file_path == task_item.file_path:
                        item.result = result
                        item.completed_time = time.time()
                        if not result.success:
                            item.error = result.error_message
                        break

        except Exception as e:
            queue.status = "error"
            raise ConversionError(f"Parallel strategy failed: {str(e)}")
            
        finally:
            if not queue.cancelled and queue.status != "error":
                queue.status = "completed"
            queue.completed_time = time.time()

    async def cancel(self, queue_id: str):
        # ParallelProcessor cancellation might not be granularly supported 
        # unless we terminate the pool.
        pass
