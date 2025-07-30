"""
Memory pool utilities for object reuse and memory optimization.

This module provides memory pooling capabilities to reduce garbage collection
pressure and improve performance by reusing objects.
"""
import threading
import weakref
from typing import TypeVar, Generic, Callable, Optional, Dict, Any, List
from collections import deque
from contextlib import contextmanager

T = TypeVar('T')


class ObjectPool(Generic[T]):
    """
    Generic object pool for reusing objects to reduce memory allocation overhead.
    
    This pool maintains a collection of reusable objects and provides
    thread-safe access to them. Objects are created on-demand and
    reused when returned to the pool.
    """
    
    def __init__(
        self, 
        factory: Callable[[], T], 
        reset_func: Optional[Callable[[T], None]] = None,
        max_size: int = 100,
        initial_size: int = 0
    ):
        """
        Initialize the object pool.
        
        Args:
            factory: Function to create new objects
            reset_func: Optional function to reset objects before reuse
            max_size: Maximum number of objects to keep in pool
            initial_size: Number of objects to create initially
        """
        self._factory = factory
        self._reset_func = reset_func
        self._max_size = max_size
        self._pool: deque = deque()
        self._lock = threading.RLock()
        self._created_count = 0
        self._reused_count = 0
        
        # Pre-populate pool with initial objects
        for _ in range(initial_size):
            try:
                obj = self._factory()
                self._pool.append(obj)
                self._created_count += 1
            except Exception:
                # If object creation fails during initialization, continue
                break
    
    def acquire(self) -> T:
        """
        Acquire an object from the pool.
        
        Returns:
            Object from pool or newly created object
        """
        with self._lock:
            if self._pool:
                obj = self._pool.popleft()
                self._reused_count += 1
                return obj
            else:
                # Create new object if pool is empty
                obj = self._factory()
                self._created_count += 1
                return obj
    
    def release(self, obj: T) -> None:
        """
        Return an object to the pool for reuse.
        
        Args:
            obj: Object to return to pool
        """
        if obj is None:
            return
        
        with self._lock:
            # Don't exceed maximum pool size
            if len(self._pool) >= self._max_size:
                return
            
            try:
                # Reset object if reset function is provided
                if self._reset_func:
                    self._reset_func(obj)
                
                self._pool.append(obj)
            except Exception:
                # If reset fails, don't add object back to pool
                pass
    
    @contextmanager
    def get_object(self):
        """
        Context manager for automatic object acquisition and release.
        
        Yields:
            Object from pool
        """
        obj = self.acquire()
        try:
            yield obj
        finally:
            self.release(obj)
    
    def clear(self) -> None:
        """Clear all objects from the pool."""
        with self._lock:
            self._pool.clear()
    
    def size(self) -> int:
        """Get current number of objects in pool."""
        with self._lock:
            return len(self._pool)
    
    def stats(self) -> Dict[str, int]:
        """Get pool statistics."""
        with self._lock:
            return {
                'pool_size': len(self._pool),
                'created_count': self._created_count,
                'reused_count': self._reused_count,
                'max_size': self._max_size
            }


class ByteArrayPool(ObjectPool[bytearray]):
    """
    Specialized pool for bytearray objects commonly used in file processing.
    """
    
    def __init__(self, buffer_size: int = 64 * 1024, max_size: int = 50, initial_size: int = 5):
        """
        Initialize the bytearray pool.
        
        Args:
            buffer_size: Size of each bytearray buffer
            max_size: Maximum number of buffers to keep in pool
            initial_size: Number of buffers to create initially
        """
        self.buffer_size = buffer_size
        
        def create_buffer() -> bytearray:
            return bytearray(buffer_size)
        
        def reset_buffer(buffer: bytearray) -> None:
            # Clear the buffer by setting all bytes to 0
            buffer[:] = b'\x00' * len(buffer)
        
        super().__init__(
            factory=create_buffer,
            reset_func=reset_buffer,
            max_size=max_size,
            initial_size=initial_size
        )


class StringBuilderPool(ObjectPool[List[str]]):
    """
    Pool for string builder lists to reduce string concatenation overhead.
    """
    
    def __init__(self, max_size: int = 20, initial_size: int = 2):
        """
        Initialize the string builder pool.
        
        Args:
            max_size: Maximum number of builders to keep in pool
            initial_size: Number of builders to create initially
        """
        def create_builder() -> List[str]:
            return []
        
        def reset_builder(builder: List[str]) -> None:
            builder.clear()
        
        super().__init__(
            factory=create_builder,
            reset_func=reset_builder,
            max_size=max_size,
            initial_size=initial_size
        )


class MemoryPoolManager:
    """
    Manager for multiple object pools with automatic cleanup.
    
    This class manages multiple object pools and provides automatic
    cleanup of unused pools to prevent memory leaks.
    """
    
    def __init__(self):
        """Initialize the pool manager."""
        self._pools: Dict[str, ObjectPool] = {}
        self._lock = threading.RLock()
        self._weak_refs: Dict[str, weakref.ref] = {}
    
    def get_pool(self, name: str, factory: Callable[[], T], **kwargs) -> ObjectPool[T]:
        """
        Get or create a named object pool.
        
        Args:
            name: Name of the pool
            factory: Factory function for creating objects
            **kwargs: Additional arguments for ObjectPool constructor
            
        Returns:
            Object pool instance
        """
        with self._lock:
            if name not in self._pools:
                pool = ObjectPool(factory, **kwargs)
                self._pools[name] = pool
                
                # Create weak reference for automatic cleanup
                def cleanup_callback(ref):
                    with self._lock:
                        if name in self._pools:
                            del self._pools[name]
                        if name in self._weak_refs:
                            del self._weak_refs[name]
                
                self._weak_refs[name] = weakref.ref(pool, cleanup_callback)
            
            return self._pools[name]
    
    def get_bytearray_pool(self, buffer_size: int = 64 * 1024) -> ByteArrayPool:
        """
        Get a bytearray pool for the specified buffer size.
        
        Args:
            buffer_size: Size of buffers in the pool
            
        Returns:
            ByteArrayPool instance
        """
        pool_name = f"bytearray_{buffer_size}"
        
        with self._lock:
            if pool_name not in self._pools:
                pool = ByteArrayPool(buffer_size=buffer_size)
                self._pools[pool_name] = pool
            
            return self._pools[pool_name]
    
    def get_string_builder_pool(self) -> StringBuilderPool:
        """
        Get the string builder pool.
        
        Returns:
            StringBuilderPool instance
        """
        pool_name = "string_builder"
        
        with self._lock:
            if pool_name not in self._pools:
                pool = StringBuilderPool()
                self._pools[pool_name] = pool
            
            return self._pools[pool_name]
    
    def clear_all_pools(self) -> None:
        """Clear all managed pools."""
        with self._lock:
            for pool in self._pools.values():
                pool.clear()
    
    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics for all managed pools."""
        with self._lock:
            return {name: pool.stats() for name, pool in self._pools.items()}
    
    def cleanup_unused_pools(self) -> int:
        """
        Clean up pools that are no longer referenced.
        
        Returns:
            Number of pools cleaned up
        """
        cleaned_count = 0
        
        with self._lock:
            # Check for pools that are only referenced by this manager
            pools_to_remove = []
            
            for name, pool in self._pools.items():
                # If the pool has only 2 references (this dict and the weak ref dict),
                # it's not being used elsewhere
                ref_count = len(weakref.getweakrefs(pool))
                if ref_count <= 1:  # Only the weak reference we created
                    pools_to_remove.append(name)
            
            for name in pools_to_remove:
                if name in self._pools:
                    self._pools[name].clear()
                    del self._pools[name]
                    cleaned_count += 1
                
                if name in self._weak_refs:
                    del self._weak_refs[name]
        
        return cleaned_count


# Global pool manager instance
_global_pool_manager = MemoryPoolManager()


def get_global_pool_manager() -> MemoryPoolManager:
    """
    Get the global pool manager instance.
    
    Returns:
        Global MemoryPoolManager instance
    """
    return _global_pool_manager


def get_bytearray_pool(buffer_size: int = 64 * 1024) -> ByteArrayPool:
    """
    Get a global bytearray pool for the specified buffer size.
    
    Args:
        buffer_size: Size of buffers in the pool
        
    Returns:
        ByteArrayPool instance
    """
    return _global_pool_manager.get_bytearray_pool(buffer_size)


def get_string_builder_pool() -> StringBuilderPool:
    """
    Get the global string builder pool.
    
    Returns:
        StringBuilderPool instance
    """
    return _global_pool_manager.get_string_builder_pool()