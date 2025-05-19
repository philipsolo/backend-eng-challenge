import asyncio
import time
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from app.main import app
from app.tasks.registry import TASK_REGISTRY, TaskSpec

client = TestClient(app)


class AddParams(BaseModel):
    a: int
    b: int


class LongParams(BaseModel):
    duration: float = 1.0
    steps: int = 5


@pytest.fixture
def mock_add_task():
    async def mock_handler(params, progress_callback, is_cancelled, is_paused):
        progress_callback(0, 2, "Starting")
        await asyncio.sleep(0.1)
        progress_callback(2, 2, "Completed")
        return params["a"] + params["b"]

    mock_spec = TaskSpec(
        name="add",
        model=AddParams,
        func=mock_handler,
        example={"a": 1, "b": 2},
        description="Add two numbers"
    )

    with patch.dict(TASK_REGISTRY, {"add": mock_spec}):
        yield


@pytest.fixture
def mock_long_task():
    async def mock_handler(params, progress_callback, is_cancelled, is_paused):
        progress_callback(0, 5, "Starting")
        for i in range(5):
            while is_paused() and not is_cancelled():
                await asyncio.sleep(0.05)
            if is_cancelled():
                return {"status": "cancelled", "step": i}
            await asyncio.sleep(0.1)
            progress_callback(i + 1, 5, f"Step {i + 1}")
        return {"status": "completed", "steps": 5}

    mock_spec = TaskSpec(
        name="long",
        model=LongParams,
        func=mock_handler,
        example={"duration": 1.0, "steps": 5},
        description="Long-running task"
    )

    with patch.dict(TASK_REGISTRY, {"long": mock_spec}):
        yield

def wait_for_status(task_id, target_status, max_attempts=20):
    """Wait for a task to reach a specific status"""
    for _ in range(max_attempts):
        response = client.get(f"/api/task/{task_id}/status")
        if response.status_code == 200 and response.json()["status"] == target_status:

            time.sleep(0.2)
            return True
        time.sleep(0.1)
    return False


def test_submit_task(mock_add_task):
    response = client.post("/api/run/add", json={"parameters": {"a": 5, "b": 3}})
    assert response.status_code == 200
    assert "task_id" in response.json()
    assert "message" in response.json()


def test_task_status(mock_add_task):
    response = client.post("/api/run/add", json={"parameters": {"a": 5, "b": 3}})
    task_id = response.json()["task_id"]

    response = client.get(f"/api/task/{task_id}/status")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["task_id"] == task_id



def test_pause_resume_task(mock_long_task):
    response = client.post("/api/run/long", json={"parameters": {"duration": 1}})
    task_id = response.json()["task_id"]

    assert wait_for_status(task_id, "running")

    response = client.post(f"/api/task/{task_id}/pause")
    assert response.status_code == 200

    response = client.get(f"/api/task/{task_id}/status")
    assert response.json()["status"] == "paused"

    response = client.post(f"/api/task/{task_id}/resume")
    assert response.status_code == 200

    response = client.get(f"/api/task/{task_id}/status")
    assert response.json()["status"] == "running"


def test_cancel_task(mock_long_task):
    response = client.post("/api/run/long", json={"parameters": {"duration": 2}})
    task_id = response.json()["task_id"]

    assert wait_for_status(task_id, "running")

    response = client.delete(f"/api/task/{task_id}")
    assert response.status_code == 200

    response = client.get(f"/api/task/{task_id}/status")
    assert response.json()["status"] in ["cancelling", "cancelled"]

    wait_for_status(task_id, "cancelled")


def test_error_cases():
    response = client.post("/api/run/long", json={"parameters": {"duration": 1}})
    task_id = response.json()["task_id"]

    response = client.get(f"/api/task/{task_id}/result")
    assert response.status_code == 400

    response = client.get("/api/task/nonexistent-id/status")
    assert response.status_code == 404

    response = client.post("/api/run/invalid_type", json={"parameters": {}})
    assert response.status_code == 404


def test_task_progress(mock_long_task):
    response = client.post("/api/run/long", json={"parameters": {"duration": 1, "steps": 3}})
    task_id = response.json()["task_id"]

    time.sleep(0.2)

    response = client.get(f"/api/task/{task_id}/status")
    assert response.status_code == 200
    assert "progress" in response.json()
    progress = response.json()["progress"]

    assert "current" in progress
    assert "total" in progress
    assert "message" in progress

