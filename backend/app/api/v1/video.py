from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Video
from app.schemas.schemas import VideoIngest, VideoStatus
from app.tasks import ingest_video_task
from app.auth.rate_limiter import rate_limit
from app.services.redis_service import RedisService
from celery.result import AsyncResult

router = APIRouter(prefix="/video", tags=["Video Services"])

@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(rate_limit(limit_override=10))])
def ingest_video(payload: VideoIngest, db: Session = Depends(get_db)):
  """
  Starts the background ingestion process (fetch transcript, chunk, and RAG index).
  Returns immediately with a job ID and 'processing' status.
  """
  youtube_video_id = payload.video_id.strip()
  if not youtube_video_id:
    raise HTTPException(status_code=400, detail="Invalid YouTube Video ID")

  # 1. Check if video already exists in the database
  existing_video = db.query(Video).filter(Video.youtube_video_id == youtube_video_id).first()
  if existing_video:
    return {
      "status": "success",
      "message": "Video already ingested",
      "video_id": existing_video.id,
      "source": existing_video.transcript_source,
      "progress": 100
    }

  # Check active task lock
  lock_name = f"ingest:{youtube_video_id}"
  existing_job_id = RedisService.get_task_lock(lock_name)
  if existing_job_id:
    return {
      "status": "processing",
      "job_id": existing_job_id,
      "progress": 0,
      "message": "Queued transcription and indexing background task (resumed from active lock)"
    }

  # 2. Execute ingestion synchronously to bypass the need for a separate Celery worker
  try:
    task = ingest_video_task.apply(args=[youtube_video_id])
    task_result = task.get() if hasattr(task, 'get') else task.result
    
    # We clear the lock just in case, though apply is synchronous
    RedisService.release_task_lock(lock_name)

    if isinstance(task_result, dict) and task_result.get("status") == "success":
      return {
        "status": "success",
        "video_id": task_result.get("video_id"),
        "message": "Video successfully ingested"
      }
    else:
      return {
        "status": "error",
        "message": str(task_result) if task_result else "Ingestion failed"
      }
  except Exception as e:
    RedisService.release_task_lock(lock_name)
    raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")

@router.get("/status/{job_id}")
def get_ingestion_status(job_id: str):
  """
  Queries the status of the Celery ingestion task.
  """
  res = AsyncResult(job_id)
  state = res.state
  
  if state == "SUCCESS":
    task_result = res.result or {}
    return {
      "status": "success",
      "job_id": job_id,
      "progress": 100,
      "video_id": task_result.get("video_id"),
      "source": task_result.get("source")
    }
  elif state == "FAILURE":
    return {
      "status": "failure",
      "job_id": job_id,
      "progress": 100,
      "error": str(res.result)
    }
  elif state == "PROGRESS":
    meta = res.info or {}
    return {
      "status": "processing",
      "job_id": job_id,
      "progress": meta.get("progress", 50),
      "message": meta.get("message", "Processing")
    }
  elif state == "PENDING":
    return {
      "status": "pending",
      "job_id": job_id,
      "progress": 0,
      "message": "Waiting for worker to pick up task"
    }
  else:
    return {
      "status": "processing",
      "job_id": job_id,
      "progress": 50,
      "message": "Processing"
    }
