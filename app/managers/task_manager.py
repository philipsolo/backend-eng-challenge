import asyncio
import time
import uuid
from typing import Dict, List

from app.core.logger import task_logger, log_task_event
from app.models import Task, TaskStatus
from app.tasks.handlers import TASK_HANDLERS


def _verify_task_status(task: Task, expected_status: TaskStatus, operation: str) -> None:
    """Verify that a task has the expected status.

    Args:
        task: The Task object to check
        expected_status: The TaskStatus that the task should have
        operation: The operation being performed (for error messages)

    Raises:
        ValueError: If the task is not in the expected status
    """
    if task.status != expected_status:
        task_logger.warning(f"Cannot {operation} task {task.task_id}: Invalid status {task.status}")
        raise ValueError(f"Cannot {operation} task with status {task.status}")

async def _execute_task_handler(task):
    """Execute the appropriate handler for a task.

    Sets up the progress callback and executes the handler for the task type.

    Args:
        task: The Task object to execute

    Returns:
        The result from the task handler
    """

    handler = TASK_HANDLERS[task.task_type]

    def progress_callback(current, total, message):
        task.progress = {"current": current, "total": total, "message": message}

    return await handler(
        params=task.parameters,
        progress_callback=progress_callback,
        is_cancelled=lambda: task.cancel_requested,
        is_paused=lambda: not task.pause_event.is_set()
    )


def _process_task_result(task, result):
    """Process the result after task execution.

    Updates task state based on execution result and whether cancellation was requested.

    Args:
        task: The Task object that was executed
        result: The result from the task handler
    """

    if task.cancel_requested:
        task.status = TaskStatus.CANCELLED
        task_logger.info(f"Task {task.task_id} was cancelled")
    else:
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.completed_at = time.time()
        task_logger.info(f"Task {task.task_id} completed successfully")


def _handle_task_failure(task, exception):
    """Handle task failure by updating task state and logging the error.

    Args:
        task: The Task object that failed
        exception: The exception that caused the failure
    """

    task.status = TaskStatus.FAILED
    task.result = str(exception)
    task.completed_at = time.time()
    task_logger.error(f"Task {task.task_id} failed: {str(exception)}")


class TaskManager:
    def __init__(self, max_concurrent=3):
        """Initialize a new TaskManager instance.

        Args:
            max_concurrent: Maximum number of tasks that can run concurrently
        """
        self.tasks: Dict[str, Task] = {}
        self.queue: List[str] = []
        self.running_count = 0
        self.max_concurrent = max_concurrent
        self.lock = asyncio.Lock()
        task_logger.info(f"TaskManager initialized with max_concurrent={max_concurrent}")

    async def _run_task(self, task):
        """Main orchestrator for running a task.

        Handles the entire lifecycle of a task execution including:
        - Setting up the task's initial state
        - Executing the task handler
        - Processing the result
        - Error handling
        - Cleanup

        Args:
            task: The Task object to run
        """
        task_logger.info(f"Starting task {task.task_id} of type {task.task_type}")

        try:
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()

            result = await _execute_task_handler(task)
            _process_task_result(task, result)

        except Exception as e:
            _handle_task_failure(task, e)

        finally:
            await self._cleanup_task()

    async def _cleanup_task(self):
        """Clean up after task execution and manage queue.

        Decrements the running count and starts any queued tasks
        if there's now capacity available.
        """
        async with self.lock:
            self.running_count -= 1
            await self._start_queued_tasks()

    async def submit_task(self, task_type, parameters):
        """Submit a new task for execution.

        Creates a new task and either starts it immediately if there's
        capacity or queues it for later execution.

        Args:
            task_type: The type of task to run
            parameters: Parameters required by the task

        Returns:
            task_id: A unique identifier for the submitted task
        """

        task_id = str(uuid.uuid4())
        task = Task(task_id=task_id, task_type=task_type, parameters=parameters)
        self.tasks[task_id] = task

        async with self.lock:
            if self.running_count < self.max_concurrent:
                self.running_count += 1
                # Start task in background
                asyncio.create_task(self._run_task(task))
            else:
                # Queue task for later execution
                task_logger.info(f"Queuing task {task_id} (max concurrent tasks reached)")
                self.queue.append(task_id)

        return task_id

    async def _start_queued_tasks(self):
        """Start queued tasks if there's capacity.

        Checks the queue for pending tasks and starts them if the
        number of running tasks is below the maximum concurrent limit.
        """

        while self.queue and self.running_count < self.max_concurrent:
            task_id = self.queue.pop(0)
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if not task.cancel_requested:
                    self.running_count += 1
                    task_logger.info(f"Starting queued task {task_id}")
                    asyncio.create_task(self._run_task(task))

    def _get_task(self, task_id: str, operation: str) -> Task:
        """Get a task by ID with consistent error handling and logging.

        Args:
            task_id: The ID of the task to retrieve
            operation: The operation being performed (for logging purposes)

        Returns:
            The Task object if found

        Raises:
            KeyError: If the task with the given ID doesn't exist
        """
        if task_id not in self.tasks:
            task_logger.warning(f"Cannot {operation} task {task_id}: Task not found")
            raise KeyError(f"Task {task_id} not found")
        return self.tasks[task_id]

    async def pause_task(self, task_id: str):
        """Pause a running task.

        Args:
            task_id: The ID of the task to pause

        Raises:
            KeyError: If the task with the given ID doesn't exist
            ValueError: If the task is not in a RUNNING state
        """
        task_logger.info(f"Attempting to pause task {task_id}")
        task = self._get_task(task_id, "pause")
        _verify_task_status(task, TaskStatus.RUNNING, "pause")

        task.pause_event.clear()
        task.status = TaskStatus.PAUSED
        log_task_event(task_logger, task_id, "PAUSED", {"previous_status": "RUNNING"})

    async def resume_task(self, task_id: str):
        """Resume a paused task.

        Args:
            task_id: The ID of the task to resume

        Raises:
            KeyError: If the task with the given ID doesn't exist
            ValueError: If the task is not in a PAUSED state
        """
        task_logger.info(f"Attempting to resume task {task_id}")
        task = self._get_task(task_id, "resume")
        _verify_task_status(task, TaskStatus.PAUSED, "resume")

        task.pause_event.set()
        task.status = TaskStatus.RUNNING
        log_task_event(task_logger, task_id, "RESUMED", {"previous_status": "PAUSED"})

    async def cancel_task(self, task_id: str):
        """Cancel a task that is queued, running, or paused.

        For queued tasks, removes them from the queue.
        For running or paused tasks, sets the cancel flag and
        resumes paused tasks so they can detect cancellation.

        Args:
            task_id: The ID of the task to cancel

        Raises:
            KeyError: If the task with the given ID doesn't exist
            ValueError: If the task is already in a terminal state
        """
        task_logger.info(f"Attempting to cancel task {task_id}")
        task = self._get_task(task_id, "cancel")

        if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED]:
            task_logger.warning(f"Cannot cancel task {task_id}: Already in terminal state {task.status}")
            raise ValueError(f"Cannot cancel task that is already {task.status}")

        task.status = TaskStatus.CANCELLING
        log_task_event(task_logger, task_id, "CANCELLING", {"previous_status": str(task.status)})

        if task.status == TaskStatus.QUEUED:
            if task_id in self.queue:
                self.queue.remove(task_id)
            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()
            task_logger.info(f"Cancelled queued task {task_id}")
            return

        # For running or paused tasks, set the cancel flag
        task.cancel_requested = True

        # If task is paused, resume it so it can detect the cancellation
        if task.status == TaskStatus.PAUSED:
            task.pause_event.set()

    def get_task_result(self, task_id: str) -> Task:
        """Get the result of a completed task.

        Args:
            task_id: The ID of the task to get the result for

        Returns:
            The result of the task

        Raises:
            KeyError: If the task doesn't exist
            ValueError: If the task hasn't completed yet
        """
        task = self._get_task(task_id, "get result")

        if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task_logger.warning(f"Cannot get result for task {task_id}: Task is {task.status}")
            raise ValueError(f"Task result not available: Task is {task.status}")
        return task
