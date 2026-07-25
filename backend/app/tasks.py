import os
import json
import time
import math
import asyncio
import hashlib
from typing import Optional
from contextlib import contextmanager
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.models import Video, Notes, Conversation, User
from app.services.transcript_service import TranscriptService
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.services.redis_service import RedisService

@contextmanager
def get_db_session():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()

def safe_update_state(task, state, meta):
  try:
    task.update_state(state=state, meta=meta)
  except Exception as e:
    print(f"Celery update_state failed (non-blocking): {e}")

def run_async(coro):
  """Helper to run async coroutines in synchronous celery task context."""
  try:
    loop = asyncio.get_event_loop()
  except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop = asyncio.get_event_loop()
  return loop.run_until_complete(coro)

async def _collect_llm_response(prompt: str, routing: str = "cheap") -> str:
  result = ""
  async for token in LLMService.stream_response(prompt, routing=routing):
    result += token
  return result

@celery_app.task(bind=True)
def ingest_video_task(self, youtube_video_id: str):
  safe_update_state(self, state="PROGRESS", meta={"progress": 10, "message": "Initializing video ingestion"})
  try:
    with get_db_session() as db:
      # 1. Double check if video exists
      existing_video = db.query(Video).filter(Video.youtube_video_id == youtube_video_id).first()
      if existing_video:
        safe_update_state(self, state="PROGRESS", meta={"progress": 100, "message": "Already ingested"})
        return {
          "status": "success",
          "video_id": existing_video.id,
          "source": existing_video.transcript_source,
          "message": "Video already ingested"
        }
        
      safe_update_state(self, state="PROGRESS", meta={"progress": 30, "message": "Fetching and transcribing video"})
      
      try:
        segments, source = TranscriptService.get_transcript(youtube_video_id)
      except Exception as e:
        safe_update_state(self, state="FAILURE", meta={"error": str(e)})
        raise e

      safe_update_state(self, state="PROGRESS", meta={"progress": 60, "message": "Saving video metadata"})

      duration = 0
      if segments:
        duration = int(segments[-1]["end"])

      new_video = Video(
        youtube_video_id=youtube_video_id,
        title=f"YouTube Video {youtube_video_id}",
        language="en",
        transcript_source=source,
        duration_seconds=duration
      )
      db.add(new_video)
      db.commit()
      db.refresh(new_video)

      safe_update_state(self, state="PROGRESS", meta={"progress": 80, "message": "Indexing transcript in Vector DB"})

      try:
        RAGService.index_transcript(new_video.id, youtube_video_id, segments)
      except Exception as e:
        print(f"RAG Indexing error during task execution (non-blocking): {e}")

      safe_update_state(self, state="PROGRESS", meta={"progress": 100, "message": "Ingestion completed successfully"})
      
      # Store transcript in Redis cache for instant loading
      RedisService.set_video_cache(youtube_video_id, "transcript", segments, ttl=86400)
      
      return {
        "status": "success",
        "video_id": new_video.id,
        "source": source,
        "segments_count": len(segments)
      }
  finally:
    RedisService.release_task_lock(f"ingest:{youtube_video_id}")

@celery_app.task(bind=True)
def generate_notes_task(self, user_id: Optional[str], youtube_video_id: str, note_format: str, conversation_id: Optional[str], force_new: bool):
  safe_update_state(self, state="PROGRESS", meta={"progress": 15, "message": "Retrieving video context"})
  try:
    with get_db_session() as db:
      video = db.query(Video).filter(Video.youtube_video_id == youtube_video_id).first()
      if not video:
        raise ValueError("Video metadata not found. Please ingest first.")

      # Sort and process transcript segments
      safe_update_state(self, state="PROGRESS", meta={"progress": 30, "message": "Downsampling and formatting transcript"})
      
      # Fetch chronological transcript annotated with timestamps
      try:
        from app.services.rag_service import chroma_client
        collection = chroma_client.get_collection(name=f"video_{youtube_video_id}")
        results = collection.get()
        documents = results.get("documents", []) or []
        metadatas = results.get("metadatas", []) or []
        
        chunks_with_time = []
        for doc, meta in zip(documents, metadatas):
          t_start = meta.get("timestamp_start", 0.0)
          chunks_with_time.append((t_start, doc))
        chunks_with_time.sort(key=lambda x: x[0])
      except Exception as rag_err:
        print("tasks.py: Failed to load chronological transcript, falling back to retrieve_context:", rag_err)
        retrieved_chunks = RAGService.retrieve_context(youtube_video_id, query="*", k=100)
        chunks_with_time = []
        for c in retrieved_chunks:
          t_start = c["metadata"].get("timestamp_start", 0.0)
          chunks_with_time.append((t_start, c["text"]))
        chunks_with_time.sort(key=lambda x: x[0])
        
      # Downsample if total length exceeds safe limit (e.g. 24000 characters)
      max_chars = 24000
      total_len = sum(len(doc) for _, doc in chunks_with_time)
      
      if total_len > max_chars:
        step = math.ceil(total_len / max_chars)
        selected_chunks = chunks_with_time[::step]
      else:
        selected_chunks = chunks_with_time
        
      transcript_lines = []
      for t_start, doc in selected_chunks:
        minutes = int(t_start // 60)
        seconds = int(t_start % 60)
        timestamp_str = f"[{minutes:02d}:{seconds:02d}]"
        transcript_lines.append(f"{timestamp_str} {doc}")
        
      full_transcript = "\n\n".join(transcript_lines)

      safe_update_state(self, state="PROGRESS", meta={"progress": 50, "message": "Generating study guide via LLM"})

      # Dynamic Note Format parameters
      if note_format == "summary":
        prompt = (
          f"You are a hilarious, ultra-chill Big Bro who is also a genius tech expert. Analyze the following YouTube transcript with timestamps:\n\n"
          f"--- START OF TRANSCRIPT ---\n{full_transcript}\n--- END OF TRANSCRIPT ---\n\n"
          f"Create a concise, hilarious, and deeply informative study summary of the key concepts and milestones. Format: SUMMARY.\n\n"
          f"CRITICAL INSTRUCTIONS FOR TONE AND FORMAT:\n"
          f"1. Adopt a hilarious, laid-back, supportive 'big bro' persona ('bro', 'fam', 'dude', 'gotchu covered', 'no cap'). Keep it fun and witty while delivering 100% accurate, crystal-clear knowledge. DO NOT use hesitant phrases like 'appears to be' or 'the author explains'.\n"
          f"2. Do NOT use `#` characters for headings/titles, and do NOT use `*` or `**` characters for list items, bolding, or emphasis. "
          f"Instead, use ALL CAPS followed by a colon for headings (e.g. 'THE GAME PLAN:'). For lists, use standard dashes '- list item'.\n"
          f"3. Include video screenshot markdown tags at the exact locations where a milestone starts. "
          f"To do this, convert the [MM:SS] timestamp from the transcript into seconds (e.g. [01:15] is 75 seconds), and insert the screenshot markdown: "
          f"![Milestone Screenshot](ss_TIMESTAMP_IN_SECONDS) (replace TIMESTAMP_IN_SECONDS with the integer number of seconds, e.g. ss_75).\n"
          f"Ensure the output has absolutely no asterisks (*) or hash symbols (#) in the text."
        )
      else:
        prompt = (
          f"You are a hilarious, ultra-chill Big Bro who is also a genius tech expert. Analyze the following YouTube transcript with timestamps:\n\n"
          f"--- START OF TRANSCRIPT ---\n{full_transcript}\n--- END OF TRANSCRIPT ---\n\n"
          f"Create a highly detailed, hilarious, and comprehensive study guide covering the entire video. Format: DETAILED.\n\n"
          f"CRITICAL INSTRUCTIONS FOR TONE AND FORMAT:\n"
          f"1. Adopt a hilarious, laid-back, supportive 'big bro' persona ('bro', 'fam', 'dude', 'gotchu covered', 'no cap'). Keep it fun and witty while delivering 100% accurate, crystal-clear knowledge. DO NOT use hesitant phrases like 'appears to be' or 'the author explains'.\n"
          f"2. GO TOPIC-BY-TOPIC chronologically. Make sure EVERY SINGLE part of the transcript is fully covered in depth. Do not skip any section, method, concept, or code implementation mentioned.\n"
          f"3. Do NOT use `#` characters for headings/titles, and do NOT use `*` or `**` characters for list items, bolding, or emphasis. "
          f"Instead, use ALL CAPS followed by a colon for headings (e.g. 'DEEP DIVE:'). For lists, use standard dashes '- list item'.\n"
          f"4. Include video screenshot markdown tags at the exact locations where a topic starts or is explained. "
          f"To do this, convert the [MM:SS] timestamp from the transcript into seconds (e.g. [01:15] is 75 seconds), and insert the screenshot markdown: "
          f"![Topic Screenshot Description](ss_TIMESTAMP_IN_SECONDS) (replace TIMESTAMP_IN_SECONDS with the integer number of seconds, e.g. ss_75). "
          f"Include multiple screenshots throughout the guide so there is a screenshot for every major concept or slide.\n"
          f"5. Combine the explanations with the actual code snippets from the transcript enclosed in triple backticks (```) containing inline comments explaining the logic.\n"
          f"Ensure the output has absolutely no asterisks (*) or hash symbols (#) in the text."
        )

      routing = "complex" # Use complex routing to generate high quality detailed study guides
      generated_notes = run_async(_collect_llm_response(prompt, routing=routing))
      
      safe_update_state(self, state="PROGRESS", meta={"progress": 85, "message": "Saving notes to database"})

      conversation = None
      if conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

      if not conversation:
        convo_title = f"Notes: {video.title or video.youtube_video_id}"
        if len(convo_title) > 40:
          convo_title = convo_title[:37] + "..."
        conversation = Conversation(
          user_id=user_id,
          video_id=video.id,
          title=convo_title
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

      # Save to conversation record
      if note_format == "detailed":
        conversation.notes_detailed = generated_notes
      else:
        conversation.notes_summary = generated_notes
      
      # Save globally in Notes table
      new_note = Notes(
        user_id=user_id,
        video_id=video.id,
        content=generated_notes,
        note_type=note_format
      )
      db.add(new_note)
      db.commit()
      db.refresh(conversation)

      # Save to Redis Cache
      RedisService.set_video_cache(youtube_video_id, f"notes:{note_format}", generated_notes, ttl=86400)
      
      safe_update_state(self, state="PROGRESS", meta={"progress": 100, "message": "Notes ready"})
      return {"notes": generated_notes, "conversation_id": conversation.id}
  finally:
    RedisService.release_task_lock(f"notes:{youtube_video_id}:{note_format}")

@celery_app.task(bind=True)
def generate_quiz_task(self, user_id: Optional[str], youtube_video_id: str, conversation_id: Optional[str], force_new: bool):
  safe_update_state(self, state="PROGRESS", meta={"progress": 20, "message": "Formatting video context"})
  try:
    with get_db_session() as db:
      video = db.query(Video).filter(Video.youtube_video_id == youtube_video_id).first()
      if not video:
        raise ValueError("Video not ingested yet.")

      context_text = RAGService.get_condensed_context(youtube_video_id)

      prompt = (
        f"You are a professional educational assessor. Based on this transcript material:\n\n"
        f"--- MATERIAL ---\n{context_text}\n\n"
        f"Create a multiple choice quiz with exactly 5 questions.\n"
        f"You MUST respond with ONLY a valid JSON array. No markdown, no explanation, no code fences.\n"
        f"Each element must be an object with these exact keys:\n"
        f'  "question": the question text,\n'
        f'  "options": an object with keys "A", "B", "C", "D" and their text values,\n'
        f'  "answer": the correct option letter (A, B, C, or D),\n'
        f'  "explanation": a brief 1-2 sentence explanation of why the correct answer is right\n\n'
        f"Example format:\n"
        f'[{{"question":"What is X?","options":{{"A":"Option 1","B":"Option 2","C":"Option 3","D":"Option 4"}},"answer":"B","explanation":"Option 2 is correct because..."}}]\n\n'
        f"Respond with ONLY the JSON array, nothing else."
      )

      safe_update_state(self, state="PROGRESS", meta={"progress": 55, "message": "Synthesizing questions via LLM"})
      
      generated_quiz_raw = run_async(_collect_llm_response(prompt, routing="cheap"))
      
      quiz_clean = generated_quiz_raw.replace("```json", "").replace("```", "").strip()

      
      try:
        parsed_quiz = json.loads(quiz_clean)
        if not isinstance(parsed_quiz, list):
          raise ValueError("LLM returned non-list format")
      except Exception as e:
        print(f"Celery Quiz Task: JSON parse failed. Retrying fallback JSON wrap.")
        parsed_quiz = [{"question": "Failed to parse generated quiz. Please try again.", "options": {"A": "N/A", "B": "N/A", "C": "N/A", "D": "N/A"}, "answer": "A", "explanation": "System error"}]
        quiz_clean = json.dumps(parsed_quiz)

      
      new_quiz_entry = {
        "id": f"quiz_{int(time.time())}",
        "questions": parsed_quiz,
        "score": None,
        "answers": {},
        "submitted": False
      }

      safe_update_state(self, state="PROGRESS", meta={"progress": 85, "message": "Saving quiz to database"})

      conversation = None
      if conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

      if not conversation:
        convo_title = f"Quiz: {video.title or video.youtube_video_id}"
        if len(convo_title) > 40:
          convo_title = convo_title[:37] + "..."
        conversation = Conversation(
          user_id=user_id,
          video_id=video.id,
          title=convo_title
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

      
      try:
        existing_quizzes = json.loads(conversation.quiz_content or "[]")
        if not isinstance(existing_quizzes, list):
          existing_quizzes = []
        
        if existing_quizzes and "question" in existing_quizzes[0]:
          existing_quizzes = [{
            "id": "quiz_1",
            "questions": existing_quizzes,
            "score": None,
            "answers": {},
            "submitted": False
          }]
      except Exception:
        existing_quizzes = []

      merged_quizzes = existing_quizzes + [new_quiz_entry]
      merged_quiz_str = json.dumps(merged_quizzes)

      conversation.quiz_content = merged_quiz_str

      
      existing_note = db.query(Notes).filter(
        Notes.video_id == video.id,
        Notes.user_id == user_id,
        Notes.note_type == "quiz"
      ).first()
      if existing_note:
        existing_note.content = merged_quiz_str
      else:
        db.add(Notes(
          user_id=user_id,
          video_id=video.id,
          content=merged_quiz_str,
          note_type="quiz"
        ))
      db.commit()
      db.refresh(conversation)

      
      RedisService.set_video_cache(youtube_video_id, "quiz", merged_quiz_str, ttl=86400)

      safe_update_state(self, state="PROGRESS", meta={"progress": 100, "message": "Quiz generated successfully"})
      return {"quiz": merged_quiz_str, "conversation_id": conversation.id}
  finally:
    RedisService.release_task_lock(f"quiz:{youtube_video_id}")

@celery_app.task(bind=True)
def generate_project_task(self, user_id: Optional[str], youtube_video_id: str, prompt_text: str, conversation_id: Optional[str]):
  safe_update_state(self, state="PROGRESS", meta={"progress": 20, "message": "Retrieving video segment indexes"})
  try:
    with get_db_session() as db:
      video = db.query(Video).filter(Video.youtube_video_id == youtube_video_id).first()
      if not video:
        raise ValueError("Video metadata not ingested yet.")

      context_text = RAGService.get_condensed_context(youtube_video_id)

      prompt = (
        f"You are a Senior Principal Software Architect. Analyze this tutorial transcript:\n\n"
        f"--- TUTORIAL TRANSCRIPT ---\n{context_text}\n\n"
        f"Based on the concepts demonstrated in this tutorial, generate a complete software project blueprint. "
        f"Detail the project file layout structure, build configuration files (e.g. package.json/requirements.txt), "
        f"Docker configurations, basic source code files, unit tests, and a README detailing instructions to run the app. "
        f"Specific User Request: {prompt_text}\n"
        f"Write the outputs in clear markdown notation."
      )

      safe_update_state(self, state="PROGRESS", meta={"progress": 50, "message": "Generating repository files via LLM"})
      
      generated_project = run_async(_collect_llm_response(prompt, routing="cheap"))

      safe_update_state(self, state="PROGRESS", meta={"progress": 85, "message": "Saving project configuration"})

      conversation = None
      if conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

      if not conversation:
        convo_title = f"Project: {video.title or video.youtube_video_id}"
        if len(convo_title) > 40:
          convo_title = convo_title[:37] + "..."
        conversation = Conversation(
          user_id=user_id,
          video_id=video.id,
          title=convo_title
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

      conversation.project_prompt = prompt_text
      conversation.project_content = generated_project

      new_project_note = Notes(
        user_id=user_id,
        video_id=video.id,
        content=generated_project,
        note_type="project"
      )
      db.add(new_project_note)
      db.commit()
      db.refresh(conversation)

      # Save to Redis Cache
      prompt_hash = hashlib.md5(prompt_text.encode('utf-8')).hexdigest()
      RedisService.set_video_cache(youtube_video_id, f"project:{prompt_hash}", generated_project, ttl=86400)
      
      safe_update_state(self, state="PROGRESS", meta={"progress": 100, "message": "Project blueprint generated"})
      return {"project_files": generated_project, "conversation_id": conversation.id}
  finally:
    RedisService.release_task_lock(f"project:{youtube_video_id}")
