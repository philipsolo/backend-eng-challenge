from abc import ABC, abstractmethod
from typing import Dict, Optional

from app.models import Task


class TaskRepository(ABC):
    """Abstract interface for task storage"""

    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID"""

    @abstractmethod
    async def store_task(self, task: Task) -> None:
        """Store a task in the repository"""

    @abstractmethod
    async def update_task(self, task: Task) -> None:
        """Update an existing task"""

    @abstractmethod
    async def get_all_tasks(self) -> Dict[str, Task]:
        """Get all tasks"""

    @abstractmethod
    async def get_running_count(self) -> int:
        """Get count of currently running tasks"""

    @abstractmethod
    async def add_to_queue(self, task_id: str) -> None:
        """Add a task to the queue"""

    @abstractmethod
    async def get_next_queued(self) -> Optional[str]:
        """Get and remove the next task ID from the queue"""

    @abstractmethod
    async def get_queue_length(self) -> int:
        """Get current queue length"""