import asyncio
import time
from typing import Dict, Any, Callable

from app.core.logger import task_logger
from app.tasks import AddTaskParams, FibonacciTaskParams, LongTaskParams, register_task

TaskProgressCallback = Callable[[int, int, str], None]


@register_task(
    name="add",
    model=AddTaskParams,
    example={"a": 5, "b": 3},
    description="Add two numbers together"
)
async def add_task(params: Dict[str, Any],
                   progress_callback: TaskProgressCallback,
                   is_cancelled: Callable[[], bool],
                   _is_paused: Callable[[], bool]) -> Any:
    """Add two numbers together"""
    a = params["a"]
    b = params["b"]

    # Report start
    progress_callback(0, 2, "Starting addition task")
    await asyncio.sleep(0.5)  # Small delay to simulate work

    # Check if cancelled
    if is_cancelled():
        task_logger.info("Addition task cancelled")
        return None

    # Report progress
    progress_callback(1, 2, "Processing numbers")
    await asyncio.sleep(0.5)  # Small delay to simulate work

    # Check if cancelled again
    if is_cancelled():
        task_logger.info("Addition task cancelled")
        return None

    # Report completion
    progress_callback(2, 2, "Addition complete")

    return a + b


@register_task(
    name="fib",
    model=FibonacciTaskParams,
    example={"n": 10},
    description="Calculate nth Fibonacci number"
)
async def fibonacci_task(params: Dict[str, Any],
                         progress_callback: TaskProgressCallback,
                         is_cancelled: Callable[[], bool],
                         _is_paused: Callable[[], bool]) -> Any:
    """Calculate nth Fibonacci number"""
    n = params["n"]

    # Report start
    progress_callback(0, n, "Starting Fibonacci calculation")

    if n <= 0:
        return 0
    if n == 1:
        return 1

    a, b = 0, 1
    for i in range(2, n + 1):
        # Support for pausing
        while _is_paused() and not is_cancelled():
            await asyncio.sleep(0.1)

        if is_cancelled():
            task_logger.info(f"Fibonacci task cancelled at step {i}/{n}")
            return None

        a, b = b, a + b
        progress_callback(i, n, f"Calculated F({i})")
        await asyncio.sleep(0.1)  # Small delay to simulate work

    return b


@register_task(
    name="long",
    model=LongTaskParams,
    example={"duration": 30, "steps": 20},
    description="Long-running task with progress reporting"
)
async def long_task(params: Dict[str, Any],
                    progress_callback: TaskProgressCallback,
                    is_cancelled: Callable[[], bool],
                    _is_paused: Callable[[], bool]) -> Any:
    """Long-running task with progress reporting"""
    duration = params.get("duration", 30)
    steps = params.get("steps", 20)

    step_duration = duration / steps

    progress = 0
    result_data = {"steps_completed": 0}

    for step in range(steps):
        # Support for pausing
        while _is_paused() and not is_cancelled():
            await asyncio.sleep(0.1)

        if is_cancelled():
            task_logger.info(f"Long task cancelled at step {step}/{steps}")
            return {"status": "cancelled", "progress": f"{progress}/{duration} seconds"}

        # Simulate work for this step
        step_start = time.time()
        await asyncio.sleep(step_duration)
        actual_step_time = time.time() - step_start

        progress += actual_step_time
        result_data["steps_completed"] = step + 1

        # Report progress to match original implementation
        percentage = (step + 1) / steps * 100
        message = f"Task progress: {percentage:.1f}% ({progress:.1f}/{duration} seconds)"
        progress_callback(step + 1, steps, message)

        if is_cancelled():
            return {"status": "cancelled", "progress": f"{progress}/{duration} seconds"}

    result_data.update({
        "status": "completed",
        "duration_requested": duration,
        "actual_duration": progress,
        "steps_completed": steps
    })

    return result_data