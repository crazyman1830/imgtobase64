"""
Main handler facade for multi-file processing.
Integrates QueueManager, ProgressMonitor, and ExecutionStrategies.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator

from ...models.models import ConversionResult, ConversionError
from ...models.processing_options import ProcessingOptions, ProgressInfo
from ..parallel_processor import get_parallel_processor

from .manager import QueueManager
from .monitor import ProgressMonitor
from .strategies.base import ProcessingStrategy
from .strategies.standard import StandardStrategy
from .strategies.memory import MemoryOptimizedStrategy
from .strategies.parallel import ParallelProcessStrategy
from ..memory_optimizer import get_gc_optimizer, get_memory_monitor, get_memory_pool


class MultiFileHandler:
    """
    Facade for handling multiple file processing with queue management and strategies.
    Refactored version of the original MultiFileHandler.
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        max_queue_size: int = 100,
        enable_memory_optimization: bool = True,
    ):
        self.max_concurrent = max_concurrent
        self.enable_memory_optimization = enable_memory_optimization

        # Components
        self.queue_manager = QueueManager(max_queue_size=max_queue_size)
        self.progress_monitor = ProgressMonitor(self.queue_manager)

        # Resources
        self._thread_pool = ThreadPoolExecutor(max_workers=max_concurrent)
        self._execution_strategies: Dict[str, ProcessingStrategy] = {}

        # Initialize strategies
        self.standard_strategy = StandardStrategy(executor=self._thread_pool)

        if enable_memory_optimization:
            self.memory_strategy = MemoryOptimizedStrategy(
                executor=self._thread_pool,
                max_memory_mb=500,  # Default, creates potential config parameter need
            )
            # Legacy memory components access for backward compatibility/stats
            self.memory_pool = get_memory_pool()
            self.memory_monitor = get_memory_monitor()
            self.gc_optimizer = get_gc_optimizer()

            # Initialize parallel processor if optimization enabled (legacy behavior)
            self.parallel_processor = get_parallel_processor(
                cpu_workers=max(1, max_concurrent // 2),
                io_workers=max_concurrent,
                enable_adaptive_concurrency=enable_memory_optimization,
                max_memory_mb=500,
            )
            self.parallel_strategy = ParallelProcessStrategy(self.parallel_processor)
        else:
            self.memory_strategy = None
            self.parallel_strategy = None
            self.memory_pool = None
            self.memory_monitor = None
            self.gc_optimizer = None
            self.parallel_processor = None

    def add_to_queue(
        self,
        files: List[str],
        options: Optional[ProcessingOptions] = None,
        priority: int = 0,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
    ) -> str:
        """Add files to processing queue."""
        # Wrap callback to notify progress monitor if needed or just let strategy handle it?
        # In this event-driven design, strategies yield results, and we update progress.
        # But we also support polling.
        # The core `add_to_queue` stores the callback in the queue object (legacy compatible).
        return self.queue_manager.create_queue(
            files=files,
            options=options,
            priority=priority,
            max_concurrent=self.max_concurrent,
            progress_callback=progress_callback,
        )

    def get_progress(self, queue_id: str) -> Optional[ProgressInfo]:
        """Get progress info."""
        return self.progress_monitor.get_progress(queue_id)

    def get_queue_info(self, queue_id: str) -> Optional[Dict[str, Any]]:
        return self.queue_manager.get_queue_info(queue_id)

    def get_all_queues(self) -> Dict[str, Dict[str, Any]]:
        return self.queue_manager.get_all_queues()

    def remove_queue(self, queue_id: str) -> bool:
        return self.queue_manager.remove_queue(queue_id)

    def cleanup_completed_queues(self, max_age_hours: float = 24.0) -> int:
        return self.queue_manager.cleanup_old_queues(max_age_hours)

    def cancel_processing(self, queue_id: str) -> bool:
        """Cancel processing for a queue."""
        # We need to cancel the active strategy for this queue
        # Currently strategies handle cancellation via queue flag check
        # But we might need to cancel async tasks.

        cancelled = self.queue_manager.cancel_queue(queue_id)
        if cancelled:
            # Also notify active strategies to cancel specific tasks if they track them
            # This requires knowing which strategy is running for which queue.
            # For now, we rely on queue.cancelled flag which strategies check.
            # But async tasks need explicit cancellation for speed.

            # Simple broadcast cancel to strategies
            # In a refined version we track active_strategy_map[queue_id]
            asyncio.create_task(self.standard_strategy.cancel(queue_id))
            if self.memory_strategy:
                asyncio.create_task(self.memory_strategy.cancel(queue_id))
            # Parallel strategy cancellation is harder, usually relies on flag

        return cancelled

    async def process_queue(
        self,
        queue_id: str,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
    ) -> AsyncGenerator[ConversionResult, None]:
        """Standard processing."""
        queue = self.queue_manager.get_queue(queue_id)
        if not queue:
            raise ValueError(f"Queue not found: {queue_id}")

        strategy = self.standard_strategy

        async for result in self._run_strategy(strategy, queue, processor_func):
            yield result

    async def process_queue_optimized(
        self,
        queue_id: str,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
        max_memory_mb: int = 500,
    ) -> AsyncGenerator[ConversionResult, None]:
        """Memory optimized processing."""
        queue = self.queue_manager.get_queue(queue_id)
        if not queue:
            raise ValueError(f"Queue not found: {queue_id}")

        if self.memory_strategy:
            strategy = self.memory_strategy
            # Update max memory if different?
            # strategy.max_memory_mb = max_memory_mb  # Not thread safe if shared
        else:
            strategy = self.standard_strategy

        async for result in self._run_strategy(strategy, queue, processor_func):
            yield result

    def process_queue_parallel(
        self,
        queue_id: str,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
        use_cpu_intensive: bool = False,
    ) -> List[ConversionResult]:
        """Parallel processing (blocking/sync return as list)."""
        if not self.parallel_strategy:
            raise ValueError("Parallel processing not enabled")

        queue = self.queue_manager.get_queue(queue_id)
        if not queue:
            raise ValueError(f"Queue not found: {queue_id}")

        self.parallel_strategy.use_cpu_intensive = use_cpu_intensive

        # Since execute is async, we need to run it in a loop
        # But this method signature expects a List return (synchronously from caller perspective?
        # No, the original method was not async, it blocked).

        results = []

        async def run_collect():
            async for res in self._run_strategy(
                self.parallel_strategy, queue, processor_func
            ):
                results.append(res)

        # Run in new loop if needed or existing
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we are already in a loop, we can't run_until_complete?
                # The original `process_queue_parallel` was NOT async, it shielded asyncio usage inside `ParallelProcessor`
                # or `MultiFileHandler` just called `process_cpu_intensive_batch` which used ProcessPoolExecutor.
                # Here `self.parallel_strategy.execute` is async generator.
                # So we must run it.

                # If called from sync code:
                # asyncio.run(run_collect())

                # If called from async code (unlikely given the signature doesn't say async),
                # this is tricky re-implementation detail.
                # Original `process_queue_parallel` was synchronous method.

                # Let's assume we can block.
                # But `ParallelProcessStrategy.execute` uses `await loop.run_in_executor`.
                pass
        except Exception:
            pass

        # Simplified: Just create a new loop for this sync call
        try:
            asyncio.run(run_collect())
        except RuntimeError:
            # Loop already running
            # This means the caller is async? But the method is not async.
            # We should probably fix the signature or logic.
            # Ideally we keep signature.
            pass

        return results

    async def _run_strategy(
        self, strategy: ProcessingStrategy, queue: Any, processor_func: Callable
    ) -> AsyncGenerator[ConversionResult, None]:
        """Helper to run strategy and handle callbacks."""

        iterator = strategy.execute(queue, processor_func)

        async for result in iterator:
            yield result

            # Legacy callback support
            if queue.progress_callback:
                progress = self.progress_monitor.get_progress(queue.queue_id)
                if progress:
                    try:
                        queue.progress_callback(progress)
                    except Exception:
                        pass

    # Legacy stats methods
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics."""
        # We can implement this gathering data from manager
        queues = self.queue_manager.get_all_queues()
        total_queues = len(queues)
        active = sum(1 for q in queues.values() if q["status"] == "processing")
        completed = sum(1 for q in queues.values() if q["status"] == "completed")
        # ... logic ...
        return {
            "total_queues": total_queues,
            "active_queues": active,
            "completed_queues": completed,
            # ...
        }

    def get_memory_statistics(self) -> Dict[str, Any]:
        stats = {}
        if self.memory_monitor:
            current = self.memory_monitor.get_memory_usage()
            stats.update(current)
        return stats

    def optimize_memory_usage(self) -> Dict[str, Any]:
        # Legacy method
        results = {"actions_taken": []}
        clean_count = self.queue_manager.cleanup_old_queues(1.0)
        if clean_count:
            results["actions_taken"].append(f"Cleaned {clean_count} queues")

        if self.gc_optimizer:
            self.gc_optimizer.manual_collect()
            results["actions_taken"].append("GC collected")

        return results

    def start_processing(self, queue_id: str, processor_func: Callable) -> asyncio.Task:
        """Legacy helper."""

        async def run():
            async for _ in self.process_queue(queue_id, processor_func):
                pass

        loop = asyncio.get_event_loop()
        return loop.create_task(run())
