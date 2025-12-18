"""
Memory-optimized processing strategy.
"""

import asyncio
import time
from concurrent.futures import Executor
from typing import AsyncGenerator, Callable, Any, Dict, Optional

from .standard import StandardStrategy
from ..manager import FileQueueItem, ProcessingQueue
from ....models.models import ConversionResult
from ....models.processing_options import ProcessingOptions
from ...memory_optimizer import optimized_memory_context


class MemoryOptimizedStrategy(StandardStrategy):
    """
    Strategy with memory monitoring and optimization.
    """

    def __init__(self, executor: Optional[Executor] = None, max_memory_mb: int = 500):
        super().__init__(executor)
        self.max_memory_mb = max_memory_mb

    async def _process_single_item(
        self,
        item: FileQueueItem,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
        executor: Executor,
        semaphore: asyncio.Semaphore,
    ) -> Optional[ConversionResult]:

        async with semaphore:
            item.started_time = time.time()
            try:
                # Use optimized memory context
                # Note: We need a way to share the context or create one per item?
                # The original code created one context for the whole queue processing in 'process_queue_optimized',
                # but then inside the loop it just passed it.
                # Here we are inside the loop.
                # Let's create a context per task or use a shared one?
                # The original code used `with optimized_memory_context(max_memory_mb) as context:` wrapping the whole loop.
                # But here we are distinct tasks.
                # We can wrap the individual execution.

                loop = asyncio.get_running_loop()

                # We cannot easily share the context across threads in the way the original code did
                # because the original code was running the context manager in the main thread
                # and just passing the dict to threads.
                # We can replicate that pattern if we change execute() structure, but let's try to wrap the execution.

                # However, garbage collection is global.
                # Let's assume we want to protect this specific operation.

                # Re-implementation note:
                # To strictly follow the original behavior, we would need to initialize the context in execute()
                # and pass it down. But generic execute() doesn't support extra args.
                # So we will create the context here or in execute().
                pass
            except Exception:
                pass

        # To properly implement this, we override execute to set up the context
        return await super()._process_single_item(
            item, processor_func, executor, semaphore
        )

    async def execute(
        self,
        queue: ProcessingQueue,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
    ) -> AsyncGenerator[ConversionResult, None]:

        # We need to wrap the parent execute logic with memory context
        # But parent execute is a generator.

        try:
            with optimized_memory_context(self.max_memory_mb) as context:
                # We need to inject this context into the processor
                # We can bind it using a partial, or store it in self temporarily (not thread safe if shared strategy instance)
                # Better: Define a wrapper function

                def wrapped_processor(
                    file_path: str, options: ProcessingOptions
                ) -> ConversionResult:
                    # Check memory
                    if "memory_monitor" in context:
                        context["memory_monitor"].check_memory_thresholds()

                    result = processor_func(file_path, options)

                    if "gc_optimizer" in context:
                        context["gc_optimizer"].manual_collect()

                    return result

                # Call parent execute with wrapped processor
                async for result in super().execute(queue, wrapped_processor):
                    yield result

        except Exception as e:
            # If context fails
            raise e
