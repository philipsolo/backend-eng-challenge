import asyncio
import time
from enum import Enum
from typing import Dict, Any

from pydantic import BaseModel


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    CANCELLING = "cancelling"

class TaskRequest(BaseModel):
    parameters: Dict[str, Any]


class Task:
    def __init__(self, task_id: str, task_type: str, parameters: Dict[str, Any]):
        self.task_id = task_id
        self.task_type = task_type
        self.parameters = parameters
        self.status = TaskStatus.QUEUED
        self.result = None
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.pause_event = asyncio.Event()
        self.pause_event.set()
        self.cancel_requested = False

    def to_dict(self, include_result=False):
        response = {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }

        if hasattr(self, 'progress') and self.progress:
            response["progress"] = self.progress

        if include_result and self.status == TaskStatus.COMPLETED:
            response["result"] = self.result
            if self.started_at and self.completed_at:
                response["execution_time"] = self.completed_at - self.started_at

        return response