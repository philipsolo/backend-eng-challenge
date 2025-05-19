import asyncio
from typing import Dict, List, Optional

from app.models import Task, TaskStatus
from ..repositories import TaskRepository


class InMemoryTaskRepository(TaskRepository):
    """In-memory implementation of TaskRepository"""

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.queue: List[str] = []
        self.lock = asyncio.Lock()

    async def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    async def store_task(self, task: Task) -> None:
        self.tasks[task.task_id] = task

    async def update_task(self, task: Task) -> None:
        self.tasks[task.task_id] = task

    async def get_all_tasks(self) -> Dict[str, Task]:
        return self.tasks

    async def get_running_count(self) -> int:
        return sum(1 for task in self.tasks.values()
                   if task.status == TaskStatus.RUNNING)

    async def add_to_queue(self, task_id: str) -> None:
        self.queue.append(task_id)

    async def get_next_queued(self) -> Optional[str]:
        if not self.queue:
            return None
        return self.queue.pop(0)

    async def get_queue_length(self) -> int:
        return len(self.queue)