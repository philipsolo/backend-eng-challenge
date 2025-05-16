from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Path, Body

from app.managers import TaskManager
from app.models import TaskRequest
from app.tasks import (
    get_available_task_types,
    get_task_spec,
    validate_task_parameters,
    TASK_SPECS
)

router = APIRouter(tags=["Tasks"])
task_manager = TaskManager(max_concurrent=3)


@router.get("/tasks", response_model=Dict[str, Any])
async def get_available_tasks():
    task_details = {}
    for task_type, spec in TASK_SPECS.items():
        task_details[task_type] = {
            "description": spec["description"],
            "parameters": spec["model"].model_json_schema(),
            "example": spec["example"]
        }

    return {
        "available_tasks": get_available_task_types(),
        "task_details": task_details
    }

@router.get("/tasks/{task_type}", response_model=Dict[str, Any])
async def get_task_info(
    task_type: str = Path(..., description="Task type to get information about")
):
    """Get information about a specific task type including required parameters"""
    spec = get_task_spec(task_type)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Task type '{task_type}' not found")

    return {
        "description": spec["description"],
        "parameters": spec["model"].model_json_schema(),
        "example": spec["example"]
    }

@router.post("/run/{task_type}", response_model=Dict[str, Any])
async def run_task(
        task_type: str = Path(..., description="Type of task to run"),
        request: TaskRequest = Body(...)
):
    if task_type not in get_available_task_types():
        raise HTTPException(status_code=404, detail=f"Task type '{task_type}' not found")

    try:
        validated_params = validate_task_parameters(task_type, request.parameters)
        task_id = await task_manager.submit_task(task_type, validated_params)
        return {"task_id": task_id, "message": f"Task {task_id} submitted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}/status")
async def get_task_status(task_id: str):
    try:

        task = task_manager.tasks[task_id]
        return task.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@router.get("/task/{task_id}/result")
async def get_task_result(task_id: str):
    try:
        task = task_manager.get_task_result(task_id)
        return task.to_dict(include_result=True)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/task/{task_id}/pause")
async def pause_task(task_id: str):
    try:
        await task_manager.pause_task(task_id)
        return {"message": f"Task {task_id} paused successfully"}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/task/{task_id}/resume")
async def resume_task(task_id: str):
    try:
        await task_manager.resume_task(task_id)
        return {"message": f"Task {task_id} resumed successfully"}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/task/{task_id}")
async def cancel_task(task_id: str):
    try:
        await task_manager.cancel_task(task_id)
        return {"message": f"Task {task_id} cancelled successfully"}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))