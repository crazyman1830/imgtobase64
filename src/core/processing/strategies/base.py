"""
Base interface for processing strategies.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Callable, Optional
from ..manager import ProcessingQueue
from ....models.models import ConversionResult
from ....models.processing_options import ProcessingOptions

class ProcessingStrategy(ABC):
    """
    Abstract base class for file processing strategies.
    """

    @abstractmethod
    async def execute(
        self,
        queue: ProcessingQueue,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult]
    ) -> AsyncGenerator[ConversionResult, None]:
        """
        Execute processing for items in the queue.
        
        Args:
            queue: The queue to process
            processor_func: Function to call for each file
            
        Yields:
            ConversionResult for each processed file
        """
        pass

    @abstractmethod
    async def cancel(self, queue_id: str):
        """
        Cancel ongoing processing for a queue.
        """
        pass
