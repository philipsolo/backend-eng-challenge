import time
import uuid

from fastapi import FastAPI
from fastapi import Request
from .api.endpoints import router
from .core import api_logger

app = FastAPI(
    title="Task Processing API",
    description="API for managing long-running tasks with support for pausing, resuming, and cancellation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    api_logger.info(f"Request {request_id} started: {request.method} {request.url.path}")
    start_time = time.time()

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        api_logger.info(
            f"Request {request_id} completed: {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Time: {process_time:.3f}s"
        )
        return response
    except Exception as e:
        api_logger.error(f"Request {request_id} failed: {str(e)}")
        raise

app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)