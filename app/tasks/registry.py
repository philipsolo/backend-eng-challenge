from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional



class AddTaskParams(BaseModel):
    a: int = Field(..., description="First number to add")
    b: int = Field(..., description="Second number to add")


class FibonacciTaskParams(BaseModel):
    n: int = Field(..., description="Calculate the nth Fibonacci number")


class LongTaskParams(BaseModel):
    duration: int = Field(default=30, description="Total duration in seconds")
    steps: int = Field(default=20, description="Number of steps to break work into")



TASK_SPECS = {
    "add": {
        "description": "Add two numbers together",
        "model": AddTaskParams,
        "example": {"a": 5, "b": 3}
    },
    "fib": {
        "description": "Calculate Fibonacci sequence value",
        "model": FibonacciTaskParams,
        "example": {"n": 10}
    },
    "long": {
        "description": "Long-running task with progress tracking",
        "model": LongTaskParams,
        "example": {"duration": 20, "steps": 10}
    }
}


def validate_task_parameters(task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    if task_type not in TASK_SPECS:
        raise ValueError(f"Unknown task type: {task_type}")

    validated = TASK_SPECS[task_type]["model"](**parameters)
    return validated.model_dump()


def get_available_task_types() -> List[str]:
    return list(TASK_SPECS.keys())


def get_task_spec(task_type: str) -> Optional[Dict[str, Any]]:
    return TASK_SPECS.get(task_type)