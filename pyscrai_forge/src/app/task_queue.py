"""TaskQueue - Formalized async task execution for UI operations.

This module provides a clean abstraction over the threading.Thread + root.after()
pattern used throughout the application for LLM calls and other long-running tasks.

Usage:
    task_queue = TaskQueue(root)
    
    async def my_llm_task():
        return await provider.complete(...)
    
    task_queue.submit(
        my_llm_task(),
        on_progress=lambda msg: status_label.config(text=msg),
        on_complete=lambda result: handle_result(result),
        on_error=lambda e: show_error(e)
    )
"""

from __future__ import annotations

import asyncio
import logging
import threading
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Optional
from queue import Queue
import uuid

if TYPE_CHECKING:
    import tkinter as tk

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a queued task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Result of a completed task."""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Exception | None = None
    error_traceback: str | None = None


@dataclass
class QueuedTask:
    """A task waiting to be executed."""
    task_id: str
    coroutine: Coroutine
    on_progress: Optional[Callable[[str], None]] = None
    on_complete: Optional[Callable[[Any], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None
    status: TaskStatus = TaskStatus.PENDING
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())[:8]


class TaskQueue:
    """Manages async task execution with Tkinter UI thread safety.
    
    This class provides:
    - Background thread execution of async coroutines
    - Progress callback support
    - Thread-safe result delivery to UI via root.after()
    - Task cancellation support
    - Queue management with optional concurrency limits
    """
    
    def __init__(
        self,
        root: "tk.Tk",
        poll_interval_ms: int = 100,
        max_concurrent: int = 3
    ):
        """Initialize the TaskQueue.
        
        Args:
            root: Tkinter root window for thread-safe UI updates
            poll_interval_ms: How often to check for completed tasks (default 100ms)
            max_concurrent: Maximum concurrent tasks (default 3)
        """
        self.root = root
        self.poll_interval_ms = poll_interval_ms
        self.max_concurrent = max_concurrent
        
        # Task tracking
        self._pending_tasks: Queue[QueuedTask] = Queue()
        self._running_tasks: dict[str, QueuedTask] = {}
        self._results: Queue[TaskResult] = Queue()
        
        # Threading
        self._lock = threading.Lock()
        self._shutdown = False
        
        # Start the result polling
        self._schedule_poll()
        
        logger.debug(f"TaskQueue initialized (poll={poll_interval_ms}ms, max_concurrent={max_concurrent})")
    
    def submit(
        self,
        coroutine: Coroutine,
        on_progress: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        task_id: Optional[str] = None
    ) -> str:
        """Submit an async task for background execution.
        
        Args:
            coroutine: The async coroutine to execute
            on_progress: Optional callback for progress updates (called from UI thread)
            on_complete: Optional callback when task completes (called from UI thread)
            on_error: Optional callback on task failure (called from UI thread)
            task_id: Optional custom task ID (auto-generated if not provided)
            
        Returns:
            The task ID for tracking/cancellation
        """
        task = QueuedTask(
            task_id=task_id or str(uuid.uuid4())[:8],
            coroutine=coroutine,
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error
        )
        
        self._pending_tasks.put(task)
        logger.debug(f"Task {task.task_id} submitted to queue")
        
        # Try to start execution immediately if under limit
        self._try_start_next()
        
        return task.task_id
    
    def cancel(self, task_id: str) -> bool:
        """Cancel a pending or running task.
        
        Args:
            task_id: The task ID to cancel
            
        Returns:
            True if task was found and cancelled, False otherwise
        """
        with self._lock:
            # Check running tasks
            if task_id in self._running_tasks:
                task = self._running_tasks[task_id]
                task.status = TaskStatus.CANCELLED
                # Note: Can't truly cancel a running coroutine, but we mark it
                logger.info(f"Task {task_id} marked for cancellation")
                return True
        
        # Can't easily cancel pending tasks in queue, but we could add that
        logger.warning(f"Task {task_id} not found for cancellation")
        return False
    
    def get_running_count(self) -> int:
        """Get the number of currently running tasks."""
        with self._lock:
            return len(self._running_tasks)
    
    def get_pending_count(self) -> int:
        """Get the number of pending tasks."""
        return self._pending_tasks.qsize()
    
    def shutdown(self) -> None:
        """Shutdown the task queue (stop polling)."""
        self._shutdown = True
        logger.info("TaskQueue shutdown initiated")
    
    def _try_start_next(self) -> None:
        """Try to start the next pending task if under concurrency limit."""
        with self._lock:
            if len(self._running_tasks) >= self.max_concurrent:
                return
            
            if self._pending_tasks.empty():
                return
            
            task = self._pending_tasks.get_nowait()
            task.status = TaskStatus.RUNNING
            self._running_tasks[task.task_id] = task
        
        # Start in background thread
        thread = threading.Thread(
            target=self._run_task_in_thread,
            args=(task,),
            daemon=True
        )
        thread.start()
        logger.debug(f"Task {task.task_id} started in background thread")
    
    def _run_task_in_thread(self, task: QueuedTask) -> None:
        """Execute the task in a background thread with its own event loop."""
        result = TaskResult(
            task_id=task.task_id,
            status=TaskStatus.RUNNING
        )
        
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Check if cancelled before running
                if task.status == TaskStatus.CANCELLED:
                    result.status = TaskStatus.CANCELLED
                else:
                    # Run the coroutine
                    result.result = loop.run_until_complete(task.coroutine)
                    result.status = TaskStatus.COMPLETED
                    logger.debug(f"Task {task.task_id} completed successfully")
            finally:
                loop.close()
                
        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error = e
            result.error_traceback = traceback.format_exc()
            logger.error(f"Task {task.task_id} failed: {e}")
        
        # Queue result for UI thread delivery
        self._results.put(result)
        
        # Remove from running tasks
        with self._lock:
            self._running_tasks.pop(task.task_id, None)
        
        # Try to start next task
        self._try_start_next()
    
    def _schedule_poll(self) -> None:
        """Schedule the next result poll."""
        if not self._shutdown:
            self.root.after(self.poll_interval_ms, self._poll_results)
    
    def _poll_results(self) -> None:
        """Poll for completed tasks and deliver results to UI thread."""
        if self._shutdown:
            return
        
        # Process all available results
        while not self._results.empty():
            try:
                result = self._results.get_nowait()
                self._deliver_result(result)
            except Exception as e:
                logger.error(f"Error delivering task result: {e}")
        
        # Schedule next poll
        self._schedule_poll()
    
    def _deliver_result(self, result: TaskResult) -> None:
        """Deliver a task result to the appropriate callback (in UI thread)."""
        # Find the original task to get callbacks
        task = None
        with self._lock:
            # Task might still be in running_tasks if we haven't cleaned up yet
            task = self._running_tasks.get(result.task_id)
        
        if task is None:
            logger.warning(f"No task found for result {result.task_id}")
            return
        
        try:
            if result.status == TaskStatus.COMPLETED:
                if task.on_complete:
                    task.on_complete(result.result)
            elif result.status == TaskStatus.FAILED:
                if task.on_error:
                    task.on_error(result.error)
                else:
                    logger.error(f"Unhandled task error: {result.error_traceback}")
            elif result.status == TaskStatus.CANCELLED:
                logger.info(f"Task {result.task_id} was cancelled")
        except Exception as e:
            logger.error(f"Error in task callback: {e}")


def create_progress_reporter(
    task_queue: TaskQueue,
    status_widget: "tk.Label"
) -> Callable[[str], None]:
    """Create a progress reporter that updates a label widget.
    
    Args:
        task_queue: The task queue (for thread-safe updates)
        status_widget: The label widget to update
        
    Returns:
        A progress callback function
    """
    def report_progress(message: str) -> None:
        # Use root.after to ensure UI thread safety
        task_queue.root.after(0, lambda: status_widget.config(text=message))
    
    return report_progress
