from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Notes, Video, Conversation, User
from app.schemas.schemas import NotesRequest, NotesOut
from app.services.redis_service import RedisService
from app.tasks import generate_notes_task
from app.auth.auth_handler import get_current_user
from app.auth.rate_limiter import rate_limit
from typing import Optional

router = APIRouter(prefix="/notes", tags=["Notes Services"])

def is_legacy_format(content: Optional[str]) -> bool:
  """Returns True if notes format is legacy (lacks screenshots or contains raw markdown headings/bolds)."""
  if not content:
    return True
  
  # Check if there is any markdown heading (e.g., a line starting with "#", "##", or "###" followed by a space)
  has_markdown_headings = False
  for line in content.split("\n"):
    stripped = line.strip()
    if stripped.startswith("#") and any(stripped.startswith(h + " ") for h in ["#", "##", "###", "####"]):
      has_markdown_headings = True
      break
      
  # Check if there is any markdown bold pattern (**text**)
  has_markdown_bold = "**" in content
  
  # Check if it lacks the screenshot pattern "ss_"
  lacks_screenshots = "ss_" not in content
  
  return has_markdown_headings or has_markdown_bold or lacks_screenshots

@router.post("", response_model=NotesOut, dependencies=[Depends(rate_limit(limit_override=20))])
def generate_notes(
  payload: NotesRequest,
  user: Optional[User] = Depends(get_current_user),
  db: Session = Depends(get_db)
):
  youtube_video_id = payload.video_id.strip()
  
  # Check if video exists
  video = db.query(Video).filter(Video.youtube_video_id == youtube_video_id).first()
  if not video:
    raise HTTPException(status_code=404, detail="Video metadata not found. Please ingest first.")

  user_id = user.id if user else None
  conversation = None

  if payload.conversation_id:
    conversation = db.query(Conversation).filter(Conversation.id == payload.conversation_id).first()

  # 1. Check Redis Cache First (Only if force_new is False)
  if not payload.force_new:
    redis_notes = RedisService.get_video_cache(youtube_video_id, f"notes:{payload.format}")
    if redis_notes and not is_legacy_format(redis_notes):
      # If conversation available, sync cache to database conversation record
      if conversation:
        if payload.format == "detailed":
          if conversation.notes_detailed != redis_notes:
            conversation.notes_detailed = redis_notes
            db.commit()
        else:
          if conversation.notes_summary != redis_notes:
            conversation.notes_summary = redis_notes
            db.commit()
      return NotesOut(notes=redis_notes, conversation_id=conversation.id if conversation else None)

  # 2. Check Database Conversation Cache
  if conversation and not payload.force_new:
    cached_content = conversation.notes_detailed if payload.format == "detailed" else conversation.notes_summary
    if cached_content and not is_legacy_format(cached_content):
      # Write to Redis cache so subsequent requests hit Redis
      RedisService.set_video_cache(youtube_video_id, f"notes:{payload.format}", cached_content, ttl=86400)
      return NotesOut(notes=cached_content, conversation_id=conversation.id)

  # 3. Check Database Global Notes Cache
  if not payload.force_new:
    existing_note = db.query(Notes).filter(
      Notes.video_id == video.id,
      Notes.user_id == user_id,
      Notes.note_type == payload.format
    ).first()

    if existing_note and not is_legacy_format(existing_note.content):
      content = existing_note.content
      # Write to Redis cache and sync to active conversation
      RedisService.set_video_cache(youtube_video_id, f"notes:{payload.format}", content, ttl=86400)
      if conversation:
        if payload.format == "detailed":
          conversation.notes_detailed = content
        else:
          conversation.notes_summary = content
        db.commit()
      return NotesOut(notes=content, conversation_id=conversation.id if conversation else None)

  # Check active task lock
  lock_name = f"notes:{youtube_video_id}:{payload.format}"
  existing_job_id = RedisService.get_task_lock(lock_name)
  if existing_job_id:
    return NotesOut(
      status="processing",
      job_id=existing_job_id,
      conversation_id=conversation.id if conversation else None
    )

  # 4. Cache Miss -> Dispatch Background task synchronously
  task = generate_notes_task.apply(kwargs={
    "user_id": user_id,
    "youtube_video_id": youtube_video_id,
    "note_format": payload.format,
    "conversation_id": conversation.id if conversation else None,
    "force_new": payload.force_new
  })
  
  result = task.result

  return NotesOut(
    status="success",
    notes=result.get("notes", ""),
    conversation_id=result.get("conversation_id")
  )
