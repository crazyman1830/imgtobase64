"""
Progress monitoring for processing queues.
"""

from typing import Optional, Dict, Any
from pathlib import Path
from ...models.processing_options import ProgressInfo
from .manager import QueueManager, ProcessingQueue, FileQueueItem


class ProgressMonitor:
    """
    Monitors progress of processing queues.
    """

    def __init__(self, queue_manager: QueueManager):
        self.queue_manager = queue_manager

    def get_progress(self, queue_id: str) -> Optional[ProgressInfo]:
        """
        Get current progress information for a processing queue.
        """
        queue = self.queue_manager.get_queue(queue_id)
        if not queue:
            return None

        # Calculate metrics
        total_files = len(queue.items)
        completed_files = sum(1 for item in queue.items if item.completed_time is not None)
        error_count = sum(1 for item in queue.items if item.error is not None)

        # Find currently processing file
        current_file = ""
        current_file_progress = 0.0
        
        # We need to lock the queue manager or queue to iterate safely? 
        # The queue object itself is returned by reference, iterating over list is generally safe in Python GIL 
        # but for consistency we might want to respect the manager's lock if we were strict. 
        # For this version, we access directly.
        
        for item in queue.items:
            if item.started_time is not None and item.completed_time is None:
                current_file = Path(item.file_path).name
                current_file_progress = 0.5  # Approximate
                break
        
        estimated_time = self._calculate_estimated_time(queue)
        
        status = queue.status
        if status == "processing" and completed_files == total_files:
            status = "completed"

        return ProgressInfo(
            queue_id=queue_id,
            total_files=total_files,
            completed_files=completed_files,
            current_file=current_file,
            estimated_time_remaining=estimated_time,
            status=status,
            error_count=error_count,
            start_time=queue.started_time or 0.0,
            current_file_progress=current_file_progress,
        )

    def _calculate_estimated_time(self, queue: ProcessingQueue) -> float:
        if not queue.started_time:
            return 0.0

        completed_items = [i for i in queue.items if i.completed_time is not None]
        if not completed_items:
            return 0.0

        total_proc_time = 0.0
        count = 0
        for item in completed_items:
            if item.started_time and item.completed_time:
                total_proc_time += (item.completed_time - item.started_time)
                count += 1
        
        if count == 0:
            return 0.0
        
        avg_time = total_proc_time / count
        remaining = sum(1 for i in queue.items if i.completed_time is None)
        
        if remaining == 0:
            return 0.0

        concurrent_factor = min(queue.max_concurrent, remaining) if remaining > 0 else 1
        # Avoid division by zero
        concurrent_factor = max(1, concurrent_factor)
        
        return (remaining * avg_time) / concurrent_factor
