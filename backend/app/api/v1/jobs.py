from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult
from pydantic import BaseModel
from typing import Optional, Any

router = APIRouter(prefix="/jobs", tags=["Job Queue Services"])

class JobStatusResponse(BaseModel):
  job_id: str
  status: str
  progress: int
  message: Optional[str] = None
  result: Optional[Any] = None
  error: Optional[str] = None

@router.get("/status/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
  """
  Polls the state of a Celery background job and returns structured progress information.
  """
  res = AsyncResult(job_id)
  state = res.state
  
  progress = 0
  message = "Waiting in queue"
  result_data = None
  error_data = None
  
  if state == "SUCCESS":
    status_str = "success"
    progress = 100
    message = "Completed"
    result_data = res.result
  elif state == "FAILURE":
    status_str = "failure"
    progress = 100
    message = "Failed"
    error_data = str(res.result)
  elif state == "PROGRESS":
    status_str = "processing"
    meta = res.info or {}
    progress = meta.get("progress", 50)
    message = meta.get("message", "Processing")
  elif state == "STARTED":
    status_str = "processing"
    progress = 15
    message = "Starting job"
  elif state == "PENDING":
    status_str = "pending"
    progress = 0
    message = "Queued in background worker"
  else:
    status_str = state.lower()
    progress = 50
    message = "Executing"
    
  return JobStatusResponse(
    job_id=job_id,
    status=status_str,
    progress=progress,
    message=message,
    result=result_data,
    error=error_data
  )
