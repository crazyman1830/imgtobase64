"""
Memory optimization utilities.

This module provides utilities for memory optimization including
garbage collection management, memory monitoring, and object lifecycle management.
"""
import gc
import sys
import threading
import weakref
import psutil
import os
from typing import Dict, Any, Optional, Callable, List, Set
from dataclasses import dataclass
from contextlib import contextmanager
from collections import defaultdict


@dataclass
class MemoryStats:
    """Memory statistics data structure."""
    total_memory: int
    available_memory: int
    used_memory: int
    memory_percent: float
    gc_collections: Dict[int, int]
    gc_objects: int


class MemoryMonitor:
    """
    Memory monitoring utility for tracking memory usage and optimization.
    
    This class provides methods to monitor memory usage, track object
    creation/destruction, and provide insights for memory optimization.
    """
    
    def __init__(self):
        """Initialize the memory monitor."""
        self._process = psutil.Process(os.getpid())
        self._baseline_memory = None
        self._peak_memory = 0
        self._object_counts: Dict[str, int] = defaultdict(int)
        self._weak_refs: Set[weakref.ref] = set()
        self._lock = threading.RLock()
    
    def get_current_memory_stats(self) -> MemoryStats:
        """
        Get current memory statistics.
        
        Returns:
            MemoryStats object with current memory information
        """
        try:
            # Get system memory info
            memory_info = self._process.memory_info()
            system_memory = psutil.virtual_memory()
            
            # Get garbage collection stats
            gc_stats = {}
            for i in range(3):  # Python has 3 GC generations
                gc_stats[i] = gc.get_count()[i]
            
            return MemoryStats(
                total_memory=system_memory.total,
                available_memory=system_memory.available,
                used_memory=memory_info.rss,
                memory_percent=system_memory.percent,
                gc_collections=gc_stats,
                gc_objects=len(gc.get_objects())
            )
        except Exception:
            # Return empty stats if monitoring fails
            return MemoryStats(0, 0, 0, 0.0, {}, 0)
    
    def set_baseline(self) -> None:
        """Set the current memory usage as baseline for comparison."""
        with self._lock:
            stats = self.get_current_memory_stats()
            self._baseline_memory = stats.used_memory
    
    def get_memory_delta(self) -> int:
        """
        Get memory usage change since baseline.
        
        Returns:
            Memory delta in bytes (positive = increase, negative = decrease)
        """
        if self._baseline_memory is None:
            return 0
        
        current_stats = self.get_current_memory_stats()
        return current_stats.used_memory - self._baseline_memory
    
    def update_peak_memory(self) -> None:
        """Update peak memory usage tracking."""
        with self._lock:
            current_stats = self.get_current_memory_stats()
            if current_stats.used_memory > self._peak_memory:
                self._peak_memory = current_stats.used_memory
    
    def get_peak_memory(self) -> int:
        """
        Get peak memory usage since monitoring started.
        
        Returns:
            Peak memory usage in bytes
        """
        with self._lock:
            return self._peak_memory
    
    def track_object(self, obj: Any, obj_type: str = None) -> None:
        """
        Track an object for lifecycle monitoring.
        
        Args:
            obj: Object to track
            obj_type: Optional type name for categorization
        """
        if obj_type is None:
            obj_type = type(obj).__name__
        
        with self._lock:
            self._object_counts[obj_type] += 1
            
            # Create weak reference with cleanup callback
            def cleanup_callback(ref):
                with self._lock:
                    self._object_counts[obj_type] -= 1
                    self._weak_refs.discard(ref)
            
            weak_ref = weakref.ref(obj, cleanup_callback)
            self._weak_refs.add(weak_ref)
    
    def get_object_counts(self) -> Dict[str, int]:
        """
        Get current object counts by type.
        
        Returns:
            Dictionary mapping object types to counts
        """
        with self._lock:
            return dict(self._object_counts)
    
    def cleanup_dead_references(self) -> int:
        """
        Clean up dead weak references.
        
        Returns:
            Number of references cleaned up
        """
        with self._lock:
            dead_refs = [ref for ref in self._weak_refs if ref() is None]
            for ref in dead_refs:
                self._weak_refs.discard(ref)
            return len(dead_refs)


class GarbageCollectionOptimizer:
    """
    Garbage collection optimization utility.
    
    This class provides methods to optimize garbage collection behavior
    for better memory management and performance.
    """
    
    def __init__(self):
        """Initialize the GC optimizer."""
        self._original_thresholds = gc.get_threshold()
        self._gc_disabled = False
        self._lock = threading.RLock()
    
    def optimize_for_large_objects(self) -> None:
        """
        Optimize GC settings for applications that create many large objects.
        
        This increases the thresholds to reduce GC frequency for better performance
        when dealing with large objects that are short-lived.
        """
        with self._lock:
            # Increase thresholds to reduce GC frequency
            # Default is usually (700, 10, 10)
            gc.set_threshold(2000, 25, 25)
    
    def optimize_for_small_objects(self) -> None:
        """
        Optimize GC settings for applications that create many small objects.
        
        This decreases the thresholds to increase GC frequency for better
        memory management when dealing with many small objects.
        """
        with self._lock:
            # Decrease thresholds to increase GC frequency
            gc.set_threshold(400, 5, 5)
    
    def restore_default_settings(self) -> None:
        """Restore original GC settings."""
        with self._lock:
            gc.set_threshold(*self._original_thresholds)
            if self._gc_disabled:
                gc.enable()
                self._gc_disabled = False
    
    def disable_gc_temporarily(self) -> None:
        """
        Temporarily disable garbage collection.
        
        Use this for performance-critical sections where you want to
        avoid GC pauses. Remember to re-enable GC afterwards.
        """
        with self._lock:
            if gc.isenabled():
                gc.disable()
                self._gc_disabled = True
    
    def enable_gc(self) -> None:
        """Re-enable garbage collection."""
        with self._lock:
            if self._gc_disabled:
                gc.enable()
                self._gc_disabled = False
    
    def force_full_collection(self) -> Dict[str, int]:
        """
        Force a full garbage collection cycle.
        
        Returns:
            Dictionary with collection statistics
        """
        with self._lock:
            # Collect statistics before
            before_objects = len(gc.get_objects())
            before_counts = gc.get_count()
            
            # Force collection of all generations
            collected = []
            for generation in range(3):
                collected.append(gc.collect(generation))
            
            # Collect statistics after
            after_objects = len(gc.get_objects())
            after_counts = gc.get_count()
            
            return {
                'objects_before': before_objects,
                'objects_after': after_objects,
                'objects_collected': before_objects - after_objects,
                'gen0_collected': collected[0],
                'gen1_collected': collected[1],
                'gen2_collected': collected[2],
                'counts_before': before_counts,
                'counts_after': after_counts
            }
    
    @contextmanager
    def gc_disabled(self):
        """
        Context manager to temporarily disable garbage collection.
        
        Usage:
            with optimizer.gc_disabled():
                # Performance-critical code here
                pass
        """
        was_enabled = gc.isenabled()
        try:
            if was_enabled:
                gc.disable()
            yield
        finally:
            if was_enabled:
                gc.enable()
    
    @contextmanager
    def optimized_for_large_objects(self):
        """
        Context manager to temporarily optimize GC for large objects.
        
        Usage:
            with optimizer.optimized_for_large_objects():
                # Code that creates large objects
                pass
        """
        original_thresholds = gc.get_threshold()
        try:
            self.optimize_for_large_objects()
            yield
        finally:
            gc.set_threshold(*original_thresholds)


class ObjectLifecycleManager:
    """
    Manager for object lifecycle optimization.
    
    This class helps manage object creation, reuse, and cleanup
    to minimize memory allocation overhead.
    """
    
    def __init__(self):
        """Initialize the lifecycle manager."""
        self._cleanup_callbacks: List[Callable[[], None]] = []
        self._weak_refs: Set[weakref.ref] = set()
        self._lock = threading.RLock()
    
    def register_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a cleanup callback to be called during cleanup.
        
        Args:
            callback: Function to call during cleanup
        """
        with self._lock:
            self._cleanup_callbacks.append(callback)
    
    def track_object_lifecycle(self, obj: Any, cleanup_func: Optional[Callable[[Any], None]] = None) -> None:
        """
        Track an object's lifecycle and optionally call cleanup when it's destroyed.
        
        Args:
            obj: Object to track
            cleanup_func: Optional cleanup function to call when object is destroyed
        """
        with self._lock:
            def cleanup_callback(ref):
                if cleanup_func:
                    try:
                        cleanup_func(obj)
                    except Exception:
                        pass  # Ignore cleanup errors
                
                with self._lock:
                    self._weak_refs.discard(ref)
            
            weak_ref = weakref.ref(obj, cleanup_callback)
            self._weak_refs.add(weak_ref)
    
    def cleanup_all(self) -> None:
        """Run all registered cleanup callbacks."""
        with self._lock:
            for callback in self._cleanup_callbacks:
                try:
                    callback()
                except Exception:
                    pass  # Ignore cleanup errors
            
            self._cleanup_callbacks.clear()
    
    def get_tracked_object_count(self) -> int:
        """
        Get the number of currently tracked objects.
        
        Returns:
            Number of tracked objects still alive
        """
        with self._lock:
            # Clean up dead references first
            dead_refs = [ref for ref in self._weak_refs if ref() is None]
            for ref in dead_refs:
                self._weak_refs.discard(ref)
            
            return len(self._weak_refs)


class MemoryOptimizer:
    """
    Main memory optimization coordinator.
    
    This class coordinates various memory optimization strategies
    and provides a unified interface for memory management.
    """
    
    def __init__(self):
        """Initialize the memory optimizer."""
        self.monitor = MemoryMonitor()
        self.gc_optimizer = GarbageCollectionOptimizer()
        self.lifecycle_manager = ObjectLifecycleManager()
        self._optimization_active = False
        self._lock = threading.RLock()
    
    def start_optimization(self, strategy: str = 'balanced') -> None:
        """
        Start memory optimization with the specified strategy.
        
        Args:
            strategy: Optimization strategy ('balanced', 'large_objects', 'small_objects')
        """
        with self._lock:
            if self._optimization_active:
                return
            
            self.monitor.set_baseline()
            
            if strategy == 'large_objects':
                self.gc_optimizer.optimize_for_large_objects()
            elif strategy == 'small_objects':
                self.gc_optimizer.optimize_for_small_objects()
            # 'balanced' uses default settings
            
            self._optimization_active = True
    
    def stop_optimization(self) -> None:
        """Stop memory optimization and restore default settings."""
        with self._lock:
            if not self._optimization_active:
                return
            
            self.gc_optimizer.restore_default_settings()
            self.lifecycle_manager.cleanup_all()
            self._optimization_active = False
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive memory optimization report.
        
        Returns:
            Dictionary with optimization statistics and recommendations
        """
        stats = self.monitor.get_current_memory_stats()
        memory_delta = self.monitor.get_memory_delta()
        peak_memory = self.monitor.get_peak_memory()
        object_counts = self.monitor.get_object_counts()
        tracked_objects = self.lifecycle_manager.get_tracked_object_count()
        
        return {
            'current_memory_mb': stats.used_memory / (1024 * 1024),
            'memory_delta_mb': memory_delta / (1024 * 1024),
            'peak_memory_mb': peak_memory / (1024 * 1024),
            'memory_percent': stats.memory_percent,
            'gc_objects': stats.gc_objects,
            'gc_collections': stats.gc_collections,
            'object_counts': object_counts,
            'tracked_objects': tracked_objects,
            'optimization_active': self._optimization_active
        }
    
    def force_cleanup(self) -> Dict[str, Any]:
        """
        Force a comprehensive cleanup and return statistics.
        
        Returns:
            Dictionary with cleanup statistics
        """
        with self._lock:
            # Clean up tracked objects
            self.lifecycle_manager.cleanup_all()
            
            # Clean up dead references
            dead_refs_cleaned = self.monitor.cleanup_dead_references()
            
            # Force garbage collection
            gc_stats = self.gc_optimizer.force_full_collection()
            
            return {
                'dead_references_cleaned': dead_refs_cleaned,
                'gc_statistics': gc_stats
            }
    
    @contextmanager
    def optimized_context(self, strategy: str = 'balanced'):
        """
        Context manager for temporary memory optimization.
        
        Args:
            strategy: Optimization strategy to use
            
        Usage:
            with optimizer.optimized_context('large_objects'):
                # Memory-intensive code here
                pass
        """
        self.start_optimization(strategy)
        try:
            yield self
        finally:
            self.stop_optimization()


# Global memory optimizer instance
_global_optimizer = MemoryOptimizer()


def get_global_memory_optimizer() -> MemoryOptimizer:
    """
    Get the global memory optimizer instance.
    
    Returns:
        Global MemoryOptimizer instance
    """
    return _global_optimizer


def optimize_memory_for_large_files():
    """Convenience function to optimize memory for large file processing."""
    _global_optimizer.start_optimization('large_objects')


def restore_default_memory_settings():
    """Convenience function to restore default memory settings."""
    _global_optimizer.stop_optimization()