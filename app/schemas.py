from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class TaskRequest(BaseModel):
    prompt: str
    params: Dict[str, Any] = Field(default_factory=dict)


class TaskSubmissionResponse(BaseModel):
    task_id: Optional[str] = None
    status: TaskStatus
    cached: bool = False
    result: Optional[Dict[str, Any]] = None


class TaskDetailResponse(BaseModel):
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
