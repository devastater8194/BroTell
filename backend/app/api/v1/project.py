from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Notes, Video, User, Conversation
from app.schemas.schemas import ProjectRequest, ProjectOut
from app.services.redis_service import RedisService
from app.tasks import generate_project_task
from app.auth.auth_handler import get_current_user
from app.auth.rate_limiter import rate_limit
from typing import Optional
import hashlib

router = APIRouter(prefix="/project", tags=["Project Services"])

@router.post("", response_model=ProjectOut, dependencies=[Depends(rate_limit(limit_override=10))])
def generate_project(
  payload: ProjectRequest,
  user: Optional[User] = Depends(get_current_user),
  db: Session = Depends(get_db)
):
  youtube_video_id = payload.video_id.strip()

  video = db.query(Video).filter(Video.youtube_video_id == youtube_video_id).first()
  if not video:
    raise HTTPException(status_code=404, detail="Video not ingested yet.")

  user_id = user.id if user else None
  conversation = None

  if payload.conversation_id:
    conversation = db.query(Conversation).filter(Conversation.id == payload.conversation_id).first()

  # Create a hash of the prompt for custom cache keying
  prompt_hash = hashlib.md5(payload.prompt.encode('utf-8')).hexdigest()

  # 1. Check Redis Cache First
  redis_project = RedisService.get_video_cache(youtube_video_id, f"project:{prompt_hash}")
  if redis_project:
    # Sync with active conversation if available
    if conversation:
      if conversation.project_content != redis_project:
        conversation.project_prompt = payload.prompt
        conversation.project_content = redis_project
        db.commit()
    return ProjectOut(project_files=redis_project, conversation_id=conversation.id if conversation else None)

  # 2. Check Database Conversation Cache
  if conversation:
    if conversation.project_content and conversation.project_prompt == payload.prompt:
      # Write to Redis cache
      RedisService.set_video_cache(youtube_video_id, f"project:{prompt_hash}", conversation.project_content, ttl=86400)
      return ProjectOut(project_files=conversation.project_content, conversation_id=conversation.id)

  # 3. Check Database Global Cache (Notes table fallback)
  existing_project = db.query(Notes).filter(
    Notes.video_id == video.id,
    Notes.user_id == user_id,
    Notes.note_type == "project"
  ).first()

  if existing_project:
    content = existing_project.content
    # Write to Redis Cache
    RedisService.set_video_cache(youtube_video_id, f"project:{prompt_hash}", content, ttl=86400)
    # Sync conversation
    if conversation:
      conversation.project_prompt = payload.prompt
      conversation.project_content = content
      db.commit()
    return ProjectOut(project_files=content, conversation_id=conversation.id if conversation else None)

  # Check active task lock
  lock_name = f"project:{youtube_video_id}"
  existing_job_id = RedisService.get_task_lock(lock_name)
  if existing_job_id:
    return ProjectOut(
      status="processing",
      job_id=existing_job_id,
      conversation_id=conversation.id if conversation else None
    )

  # 4. Cache Miss -> Dispatch Celery task synchronously
  task = generate_project_task.apply(kwargs={
    "user_id": user_id,
    "youtube_video_id": youtube_video_id,
    "prompt_text": payload.prompt,
    "conversation_id": conversation.id if conversation else None
  })
  
  result = task.result

  return ProjectOut(
    status="success",
    project_files=result.get("project", ""),
    conversation_id=result.get("conversation_id")
  )
