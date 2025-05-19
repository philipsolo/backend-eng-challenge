from typing import Dict, Any, Callable, Type
from typing import List, Optional

from pydantic import BaseModel
from pydantic import Field

class AddTaskParams(BaseModel):
    a: int = Field(..., description="First number to add")
    b: int = Field(..., description="Second number to add")


class FibonacciTaskParams(BaseModel):
    n: int = Field(..., description="Calculate the nth Fibonacci number")


class LongTaskParams(BaseModel):
    duration: int = Field(default=30, description="Total duration in seconds")
    steps: int = Field(default=20, description="Number of steps to break work into")

class TaskRegistration(BaseModel):
    name: str = Field(..., description="Unique name for the task")
    model: Type[BaseModel] = Field(..., description="Pydantic model for parameter validation")
    example: Dict[str, Any] = Field(..., description="Example parameters")
    description: str = Field(..., description="Task description")


class TaskSpec:
    def __init__(
            self,
            name: str,
            model: Type[BaseModel],
            func: Callable,
            example: Dict[str, Any],
            description: str
    ):
        self.name = name
        self.model = model
        self.func = func
        self.example = example
        self.description = description

    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.model(**parameters)
        return validated.model_dump()

TASK_REGISTRY: Dict[str, TaskSpec] = {}


def register_task(
        name: str,
        model: Type[BaseModel],
        example: Dict[str, Any],
        description: str
) -> Callable:

    TaskRegistration(name=name, model=model, example=example, description=description)

    if name in TASK_REGISTRY:
        raise ValueError(f"Task '{name}' is already registered.")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        TASK_REGISTRY[name] = TaskSpec(
            name=name,
            model=model,
            func=func,
            example=example,
            description=description
        )
        return func

    return decorator


def get_available_task_types() -> List[str]:
    return list(TASK_REGISTRY.keys())

def get_task_spec(task_type: str) -> Optional[TaskSpec]:
    return TASK_REGISTRY.get(task_type)

def validate_task_parameters(task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    if task_type not in TASK_REGISTRY:
        raise ValueError(f"Unknown task type: {task_type}")
    return TASK_REGISTRY[task_type].validate_parameters(parameters)