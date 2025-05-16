import asyncio

import pytest

from app.managers.task_manager import TaskManager
from app.models import TaskStatus


async def _wait_for_status(manager, task_id, desired, attempts=30, delay=0.05):
    for _ in range(attempts):
        if manager.tasks[task_id].status == desired:
            return True
        await asyncio.sleep(delay)
    return False

@pytest.mark.asyncio
async def test_multiple_add_tasks():
    manager = TaskManager(max_concurrent=2)
    # Use actual 'add' task
    task_ids = []
    for i in range(4):
        tid = await manager.submit_task("add", {"a": i, "b": i})
        task_ids.append(tid)

    # Check concurrency
    await asyncio.sleep(0.1)
    running = sum(t.status == TaskStatus.RUNNING for t in manager.tasks.values())
    queued = sum(t.status == TaskStatus.QUEUED for t in manager.tasks.values())
    assert running == 2
    assert queued == 2

    # Wait for all tasks to complete
    for tid in task_ids:
        assert await _wait_for_status(manager, tid, TaskStatus.COMPLETED)

@pytest.mark.asyncio
async def test_long_task_pause_resume():
    manager = TaskManager()
    tid = await manager.submit_task("long", {"duration": 1, "steps": 3})
    assert await _wait_for_status(manager, tid, TaskStatus.RUNNING)


    await manager.pause_task(tid)
    assert manager.tasks[tid].status == TaskStatus.PAUSED

    await manager.resume_task(tid)
    assert manager.tasks[tid].status == TaskStatus.RUNNING
    assert await _wait_for_status(manager, tid, TaskStatus.COMPLETED)


@pytest.mark.asyncio
async def test_fourth_task_queued():
    manager = TaskManager(max_concurrent=3)
    for i in range(4):
        await manager.submit_task("add", {"a": i, "b": i})

    await asyncio.sleep(0.1)  # Let tasks start
    running = sum(t.status == TaskStatus.RUNNING for t in manager.tasks.values())
    queued = sum(t.status == TaskStatus.QUEUED for t in manager.tasks.values())

    assert running == 3
    assert queued == 1