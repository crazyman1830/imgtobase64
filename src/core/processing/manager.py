"""
Queue management for multi-file processing.
Handles queue state, CRUD operations, and item tracking.
"""

import time
import uuid
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from ...models.models import ConversionResult, ProcessingQueueFullError
from ...models.processing_options import ProcessingOptions, ProgressInfo


@dataclass
class FileQueueItem:
    """
    Represents a single file in the processing queue.
    """

    file_path: str
    options: ProcessingOptions
    priority: int = 0
    added_time: float = 0.0
    started_time: Optional[float] = None
    completed_time: Optional[float] = None
    result: Optional[ConversionResult] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.added_time == 0.0:
            self.added_time = time.time()


@dataclass
class ProcessingQueue:
    """
    Represents a processing queue with metadata.
    """

    queue_id: str
    items: List[FileQueueItem]
    status: str = "pending"  # pending, processing, completed, error, cancelled
    created_time: float = 0.0
    started_time: Optional[float] = None
    completed_time: Optional[float] = None
    max_concurrent: int = 3
    cancelled: bool = False
    # Using Any for callback to avoid circular imports during refactoring
    progress_callback: Optional[Callable[[Any], None]] = None

    def __post_init__(self):
        if self.created_time == 0.0:
            self.created_time = time.time()


class QueueManager:
    """
    Manages processing queues and their items.
    """

    def __init__(self, max_queue_size: int = 100):
        self.max_queue_size = max_queue_size
        self._queues: Dict[str, ProcessingQueue] = {}
        self._lock = threading.RLock()

    def create_queue(
        self,
        files: List[str],
        options: Optional[ProcessingOptions] = None,
        priority: int = 0,
        max_concurrent: int = 3,
        progress_callback: Optional[Callable[[Any], None]] = None,
    ) -> str:
        """
        Create a new processing queue.
        """
        if not files:
            raise ValueError("Files list cannot be empty")

        if len(files) > self.max_queue_size:
            raise ProcessingQueueFullError(
                f"Queue size limit exceeded. Maximum {self.max_queue_size} files allowed."
            )

        # Validate file paths
        for file_path in files:
            if not file_path or not isinstance(file_path, str):
                raise ValueError(f"Invalid file path: {file_path}")

            # Check if file exists
            path_obj = Path(file_path)
            if not path_obj.exists():
                raise ValueError(f"File not found: {file_path}")

        queue_id = str(uuid.uuid4())

        if options is None:
            # Avoid circular dependency if ProcessingOptions needs to be instantiated inside
            # Ideally passed from outside
            options = ProcessingOptions()

        queue_items = [
            FileQueueItem(file_path=f, options=options, priority=priority)
            for f in files
        ]

        with self._lock:
            queue = ProcessingQueue(
                queue_id=queue_id,
                items=queue_items,
                max_concurrent=max_concurrent,
                progress_callback=progress_callback,
            )
            self._queues[queue_id] = queue

        return queue_id

    def get_queue(self, queue_id: str) -> Optional[ProcessingQueue]:
        """Get queue by ID safely."""
        with self._lock:
            return self._queues.get(queue_id)

    def get_queue_info(self, queue_id: str) -> Optional[Dict[str, Any]]:
        """Get summary info for a queue."""
        with self._lock:
            queue = self._queues.get(queue_id)
            if not queue:
                return None

            pending = sum(1 for i in queue.items if i.started_time is None)
            processing = sum(
                1 for i in queue.items if i.started_time and not i.completed_time
            )
            completed = sum(1 for i in queue.items if i.completed_time)
            errors = sum(1 for i in queue.items if i.error)

            return {
                "queue_id": queue.queue_id,
                "status": queue.status,
                "total_files": len(queue.items),
                "pending_files": pending,
                "processing_files": processing,
                "completed_files": completed,
                "error_files": errors,
                "created_time": queue.created_time,
                "started_time": queue.started_time,
                "completed_time": queue.completed_time,
                "cancelled": queue.cancelled,
                "max_concurrent": queue.max_concurrent,
            }

    def remove_queue(self, queue_id: str) -> bool:
        """Remove a queue if it is in valid state for removal."""
        with self._lock:
            queue = self._queues.get(queue_id)
            if not queue:
                return False

            if queue.status not in ["completed", "cancelled", "error"]:
                return False

            del self._queues[queue_id]
            return True

    def get_all_queues(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {qid: self.get_queue_info(qid) for qid in self._queues}

    def cleanup_old_queues(self, max_age_hours: float = 24.0) -> int:
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        to_remove = []

        with self._lock:
            for qid, queue in self._queues.items():
                if queue.status in ["completed", "cancelled", "error"]:
                    t = queue.completed_time or queue.created_time
                    if current_time - t > max_age_seconds:
                        to_remove.append(qid)

            for qid in to_remove:
                del self._queues[qid]

        return len(to_remove)

    def set_queue_status(self, queue_id: str, status: str):
        with self._lock:
            queue = self._queues.get(queue_id)
            if queue:
                queue.status = status

    def cancel_queue(self, queue_id: str) -> bool:
        with self._lock:
            queue = self._queues.get(queue_id)
            if not queue:
                return False
            queue.cancelled = True
            queue.status = "cancelled"
            return True
