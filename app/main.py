from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.schemas import TaskDetailResponse, TaskRequest, TaskSubmissionResponse
from app.services import task_service

app = FastAPI(title="FastAPI Redis Mini")


@app.post("/tasks", response_model=TaskSubmissionResponse, status_code=202)
async def submit_task_endpoint(request: TaskRequest):
    response = await task_service.submit_task(request)
    status_code = 200 if response.cached else 202
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(),
    )


@app.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task_endpoint(task_id: str):
    detail = await task_service.get_task(task_id)
    return detail
