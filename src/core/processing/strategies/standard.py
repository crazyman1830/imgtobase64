"""
Standard processing strategy using AsyncIO and ThreadPoolExecutor.
"""

import asyncio
import time
from concurrent.futures import Executor, ThreadPoolExecutor
from typing import AsyncGenerator, Callable, Optional, Dict, Set

from .base import ProcessingStrategy
from ..manager import ProcessingQueue, FileQueueItem
from ....models.models import ConversionResult, ConversionError
from ....models.processing_options import ProcessingOptions


class StandardStrategy(ProcessingStrategy):
    """
    Standard strategy using a shared or internal executor.
    """

    def __init__(self, executor: Optional[Executor] = None):
        """
        Args:
            executor: ThreadPoolExecutor to use. If None, one will be created per execution (not recommended for high load).
        """
        self._executor = executor
        self._active_tasks: Dict[str, Set[asyncio.Task]] = {}

    async def execute(
        self,
        queue: ProcessingQueue,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult]
    ) -> AsyncGenerator[ConversionResult, None]:
        
        queue_id = queue.queue_id
        
        # Initialize queue status
        queue.status = "processing"
        queue.started_time = time.time()
        
        if queue_id not in self._active_tasks:
            self._active_tasks[queue_id] = set()

        local_executor = self._executor
        internal_executor = False
        if local_executor is None:
            # Fallback if no shared executor provided
            local_executor = ThreadPoolExecutor(max_workers=queue.max_concurrent)
            internal_executor = True

        try:
            semaphore = asyncio.Semaphore(queue.max_concurrent)
            pending_tasks = []

            for item in queue.items:
                if queue.cancelled:
                    break
                
                # Skip already completed items
                if item.completed_time:
                    continue

                task = asyncio.create_task(
                    self._process_single_item(item, processor_func, local_executor, semaphore)
                )
                pending_tasks.append(task)
                self._active_tasks[queue_id].add(task)

            # Process tasks as they complete
            for completed_task in asyncio.as_completed(pending_tasks):
                # Clean up task reference
                # Note: as_completed yields futures/coroutines, finding the original task object might be tricky directly
                # but we just need to yield results. We clean up _active_tasks at the end or on cancellation.
                
                if queue.cancelled:
                    break
                
                try:
                    result = await completed_task
                    if result:
                        yield result
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    # Generic error catching just in case
                    print(f"Unexpected error in strategy loop: {e}")

            # Wait for remaining if any (in case of break)
            # Actually if we break, we should cancel pending
            
        except Exception as e:
            queue.status = "error"
            raise ConversionError(f"Strategy execution failed: {str(e)}")
            
        finally:
            if internal_executor and isinstance(local_executor, ThreadPoolExecutor):
                local_executor.shutdown(wait=False)
            
            # Cleanup active tasks tracking
            if queue_id in self._active_tasks:
                for t in self._active_tasks[queue_id]:
                    if not t.done():
                        t.cancel()
                del self._active_tasks[queue_id]

            if not queue.cancelled and queue.status != "error":
                queue.status = "completed"
            queue.completed_time = time.time()

    async def _process_single_item(
        self,
        item: FileQueueItem,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
        executor: Executor,
        semaphore: asyncio.Semaphore
    ) -> Optional[ConversionResult]:
        
        async with semaphore:
            item.started_time = time.time()
            try:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    executor,
                    processor_func,
                    item.file_path,
                    item.options
                )
                
                item.completed_time = time.time()
                item.result = result
                if not result.success:
                    item.error = result.error_message
                
                return result

            except Exception as e:
                item.completed_time = time.time()
                item.error = str(e)
                error_result = ConversionResult(
                    file_path=item.file_path,
                    success=False,
                    error_message=str(e)
                )
                item.result = error_result
                return error_result

    async def cancel(self, queue_id: str):
        if queue_id in self._active_tasks:
            for task in self._active_tasks[queue_id]:
                if not task.done():
                    task.cancel()
