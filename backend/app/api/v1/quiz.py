from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Notes, Video, User, Conversation
from app.schemas.schemas import QuizRequest, QuizOut, QuizSubmitRequest
from app.services.redis_service import RedisService
from app.tasks import generate_quiz_task
from app.auth.auth_handler import get_current_user
from app.auth.rate_limiter import rate_limit
from typing import Optional
import json

router = APIRouter(prefix="/quiz", tags=["Quiz Services"])

def ensure_quiz_list_format(content: str) -> str:
  if not content:
    return "[]"
  try:
    parsed = json.loads(content)
    if isinstance(parsed, list):
      if len(parsed) == 0:
        return "[]"
      if "questions" in parsed[0] and "id" in parsed[0]:
        return content
      if "question" in parsed[0] and "options" in parsed[0]:
        migrated = [{
          "id": "quiz_1",
          "questions": parsed,
          "score": None,
          "answers": {},
          "submitted": False
        }]
        return json.dumps(migrated)
  except Exception:
    pass
  return "[]"

@router.post("", response_model=QuizOut, dependencies=[Depends(rate_limit(limit_override=20))])
def generate_quiz(
  payload: QuizRequest,
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

  # 1. Check Redis Cache First (Only if force_new is False)
  if not payload.force_new:
    redis_quiz = RedisService.get_video_cache(youtube_video_id, "quiz")
    if redis_quiz:
      redis_quiz_formatted = ensure_quiz_list_format(redis_quiz)
      if redis_quiz_formatted != "[]":
        # Sync database conversation record if needed
        if conversation:
          if conversation.quiz_content != redis_quiz_formatted:
            conversation.quiz_content = redis_quiz_formatted
            db.commit()
        return QuizOut(quiz=redis_quiz_formatted, conversation_id=conversation.id if conversation else None)

  # 2. Check Database Conversation Cache
  if conversation and not payload.force_new:
    if conversation.quiz_content:
      cached_content = ensure_quiz_list_format(conversation.quiz_content)
      if cached_content != "[]":
        RedisService.set_video_cache(youtube_video_id, "quiz", cached_content, ttl=86400)
        return QuizOut(quiz=cached_content, conversation_id=conversation.id)

  # 3. Check Database Global Notes Cache
  if not payload.force_new:
    existing_quiz = db.query(Notes).filter(
      Notes.video_id == video.id,
      Notes.user_id == user_id,
      Notes.note_type == "quiz"
    ).first()

    if existing_quiz:
      cached_content = ensure_quiz_list_format(existing_quiz.content)
      if cached_content != "[]":
        RedisService.set_video_cache(youtube_video_id, "quiz", cached_content, ttl=86400)
        if conversation:
          conversation.quiz_content = cached_content
          db.commit()
        return QuizOut(quiz=cached_content, conversation_id=conversation.id if conversation else None)

  # Check active task lock
  lock_name = f"quiz:{youtube_video_id}"
  existing_job_id = RedisService.get_task_lock(lock_name)
  if existing_job_id:
    return QuizOut(
      status="processing",
      job_id=existing_job_id,
      conversation_id=conversation.id if conversation else None
    )

  # 4. Cache Miss -> Dispatch Celery task synchronously
  task = generate_quiz_task.apply(kwargs={
    "user_id": user_id,
    "youtube_video_id": youtube_video_id,
    "conversation_id": conversation.id if conversation else None,
    "force_new": payload.force_new
  })
  
  # Celery's .apply() returns an EagerResult, so we extract .result
  result = task.result

  return QuizOut(
    status="success",
    quiz=result.get("quiz", "[]"),
    conversation_id=result.get("conversation_id")
  )

@router.post("/submit", response_model=QuizOut)
def submit_quiz_endpoint(
  payload: QuizSubmitRequest,
  user: Optional[User] = Depends(get_current_user),
  db: Session = Depends(get_db)
):
  conversation = db.query(Conversation).filter(Conversation.id == payload.conversation_id).first()
  if not conversation:
    raise HTTPException(status_code=404, detail="Conversation not found.")

  user_id = user.id if user else None

  # Load existing list of quizzes
  content = ensure_quiz_list_format(conversation.quiz_content)
  try:
    quizzes = json.loads(content)
  except Exception:
    quizzes = []

  # Find the specific quiz and update its score and answers
  found = False
  for q in quizzes:
    if q.get("id") == payload.quiz_id:
      q["score"] = payload.score
      q["answers"] = payload.answers
      q["submitted"] = True
      found = True
      break

  if not found:
    raise HTTPException(status_code=404, detail=f"Quiz with ID {payload.quiz_id} not found in conversation.")

  updated_content = json.dumps(quizzes)
  conversation.quiz_content = updated_content

  # Upsert Notes cache table with updated quiz list (preserving score on submit)
  video_for_note = db.query(Video).filter(Video.youtube_video_id == payload.video_id).first()
  video_id_for_note = video_for_note.id if video_for_note else payload.video_id
  existing_quiz = db.query(Notes).filter(
    Notes.video_id == video_id_for_note,
    Notes.user_id == user_id,
    Notes.note_type == "quiz"
  ).first()

  if existing_quiz:
    existing_quiz.content = updated_content
  else:
    new_quiz = Notes(
      user_id=user_id,
      video_id=video_id_for_note,
      content=updated_content,
      note_type="quiz"
    )
    db.add(new_quiz)

  db.commit()
  db.refresh(conversation)

  # Update Redis cache
  RedisService.set_video_cache(conversation.video.youtube_video_id if conversation.video else payload.video_id, "quiz", updated_content, ttl=86400)

  return QuizOut(quiz=updated_content, conversation_id=conversation.id)
