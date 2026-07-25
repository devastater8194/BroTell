import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db, get_read_db, SessionLocal
from app.models.models import Video, Conversation, Message, User
from app.schemas.schemas import ChatRequest, ConversationOut, MessageOut
from app.auth.auth_handler import get_current_user
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService

from app.services.semantic_cache import SemanticCache

router = APIRouter(prefix="/chat", tags=["Chat Services"])

@router.post("")
def chat_stream(
  payload: ChatRequest,
  user: Optional[User] = Depends(get_current_user),
  db: Session = Depends(get_db)
):
  youtube_video_id = payload.video_id.strip()
  if not youtube_video_id:
    raise HTTPException(status_code=400, detail="Invalid Video ID")

  # 1. Fetch the video from DB
  video = db.query(Video).filter(Video.youtube_video_id == youtube_video_id).first()
  if not video:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Video not ingested. Please trigger /video/ingest first."
    )

  # 2. Retrieve or create conversation
  user_id = user.id if user else None
  conversation = None

  if payload.conversation_id:
    conversation = db.query(Conversation).filter(
      Conversation.id == payload.conversation_id
    ).first()

  if not conversation:
    # Set conversation title to user's first message (truncated to 40 chars)
    msg_title = payload.message.strip()
    if len(msg_title) > 40:
      msg_title = msg_title[:37] + "..."
    elif not msg_title:
      msg_title = "New Chat"

    conversation = Conversation(
      user_id=user_id,
      video_id=video.id,
      title=msg_title,
      model=payload.model
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

  conversation_id = conversation.id

  # --- TABS COMMAND INTERCEPTION ---
  msg_lower = payload.message.strip().lower()
  is_notes_cmd = any(x in msg_lower for x in ["create notes", "generate notes", "create note", "generate note", "make notes", "make note", "get notes", "summary"])
  is_quiz_cmd = any(x in msg_lower for x in ["create quiz", "generate quiz", "make quiz", "get quiz", "test me", "quizz"])
  is_project_cmd = any(x in msg_lower for x in ["create project", "generate project", "make project", "build project"])

  if is_notes_cmd or is_quiz_cmd or is_project_cmd:
    from app.tasks import generate_notes_task, generate_quiz_task, generate_project_task
    
    # Save user message to database
    user_msg = Message(
      conversation_id=conversation_id,
      role="user",
      content=payload.message
    )
    db.add(user_msg)
    db.commit()

    if is_notes_cmd:
      task = generate_notes_task.apply(args=[user_id, youtube_video_id, 'detailed', conversation_id, False])
      tag = f"[notes_ready_download_pdf:{youtube_video_id}]"
      msg = "Your detailed notes are generated! Click below to view or download them."
    elif is_quiz_cmd:
      task = generate_quiz_task.apply(args=[user_id, youtube_video_id, conversation_id, False])
      tag = f"[quiz_ready:{youtube_video_id}]"
      msg = "Your quiz is ready! Click the button below to test your knowledge."
    else:
      task = generate_project_task.apply(args=[user_id, youtube_video_id, payload.message, conversation_id, False])
      tag = f"[project_ready_download_zip:{youtube_video_id}]"
      msg = "Your project blueprint is ready! You can view it in the Projects tab or download the workspace."

    async def sse_cmd_generator():
      yield f"data: {json.dumps({'conversation_id': conversation_id})}\n\n"
      yield f"data: {json.dumps({'text': msg + ' '})}\n\n"
      yield f"data: {json.dumps({'text': tag})}\n\n"
      
      try:
        db_session = SessionLocal()
        assistant_msg = Message(
          conversation_id=conversation_id,
          role="assistant",
          content=f"{msg} {tag}"
        )
        db_session.add(assistant_msg)
        db_session.commit()
        db_session.close()
      except Exception as save_err:
        print("Chat API: Error saving command response:", save_err)
        
    return StreamingResponse(sse_cmd_generator(), media_type="text/event-stream")

  # --- SEMANTIC CACHE LOOKUP ---
  # Temporarily bypassed because mock embeddings trigger 1.000 similarity false positives
  # cached_response = SemanticCache.lookup(youtube_video_id, payload.message)
  # if cached_response: ...

  # 3. Retrieve relevant chunks from RAG vector store
  retrieved_chunks = RAGService.retrieve_context(youtube_video_id, payload.message)
  context_blocks = []
  for chunk in retrieved_chunks:
    meta = chunk["metadata"]
    start = meta.get("timestamp_start", 0.0)
    end = meta.get("timestamp_end", 0.0)
    context_blocks.append(
      f"[Timestamp: {start:.1f}s - {end:.1f}s]\n{chunk['text']}"
    )
  
  context_text = "\n\n".join(context_blocks)

  # 4. Load past messages
  past_messages = db.query(Message).filter(
    Message.conversation_id == conversation_id
  ).order_by(Message.created_at.asc()).all()
  
  # Format history for LLM (limit to last 10 messages)
  history_text = ""
  for msg in past_messages[-10:]:
    history_text += f"{msg.role.capitalize()}: {msg.content}\n"

  # 5. Assemble prompt
  user_query_clean = payload.message.strip().lower().rstrip("!.,?")
  common_greetings = {
    "hey", "hi", "hello", "hey there", "hi there", "hello there", 
    "good morning", "good afternoon", "good evening", "greetings", 
    "whats up", "what's up", "yo", "sup", "help", "bro"
  }

  if user_query_clean in common_greetings:
    full_prompt = (
      "You are a hilarious, ultra-chill 'Big Bro' AI learning assistant.\n"
      "The user sent a simple greeting. Respond warmly, hilariously, and concisely in 1-2 sentences.\n"
      "Greet them like your favorite younger sibling or buddy (use chill big bro vibes like 'Yo bro!', 'What's good fam!', 'Aye what's crackin!').\n"
      "Tell them you've got their back and ask what they want to tackle in this video today.\n"
      "CRITICAL: Do NOT generate transcript summaries, notes, code blocks, or timestamp lists for simple greetings.\n\n"
      f"User: {payload.message}\n"
      f"Assistant:"
    )
  else:
    system_prompt = (
      "You are a hilarious, ultra-chill 'Big Bro' who happens to be a genius tech expert and master tutor for this video.\n"
      "Rules:\n"
      "1. Adopt a hilarious, laid-back, supportive 'big bro' persona ('bro', 'fam', 'dude', 'gotchu covered', 'no cap'). Keep it fun, witty, and engaging while delivering 100% accurate, crystal-clear information.\n"
      "2. Respond directly to the user's specific request or question without unnecessary waffle.\n"
      "3. Use the provided transcript context to answer video-related questions accurately.\n"
      "4. Cite starting timestamps (e.g., [Timestamp: 12.5s]) when referencing specific parts of the video.\n"
      "5. DO NOT dump full video summaries or notes unless the user explicitly asks for a summary or notes."
    )

    full_prompt = (
      f"{system_prompt}\n\n"
      f"--- VIDEO TRANSCRIPT CONTEXT ---\n"
      f"{context_text}\n\n"
      f"--- CONVERSATION HISTORY ---\n"
      f"{history_text}\n"
      f"User: {payload.message}\n"
      f"Assistant:"
    )

  # Save user message to database
  user_msg = Message(
    conversation_id=conversation_id,
    role="user",
    content=payload.message
  )
  db.add(user_msg)
  db.commit()

  # 6. Stream SSE Response
  async def sse_generator():
    import asyncio
    accumulated_content = ""
    
    # Broadcast initial token structure
    yield f"data: {json.dumps({'conversation_id': conversation_id})}\n\n"
    
    # Stream from LLM Service
    async for chunk in LLMService.stream_response(full_prompt, routing="cheap"):
      accumulated_content += chunk
      yield f"data: {json.dumps({'text': chunk})}\n\n"

    # Save the assistant response to database on completion
    try:
      db_session = SessionLocal()
      assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=accumulated_content
      )
      db_session.add(assistant_msg)
      db_session.commit()
      db_session.close()

      # Write to Semantic Cache on success
      SemanticCache.save(youtube_video_id, payload.message, accumulated_content)
    except Exception as save_err:
      print("Chat API: Error saving assistant response:", save_err)

  return StreamingResponse(sse_generator(), media_type="text/event-stream")

@router.get("/history/{video_id}", response_model=ConversationOut)
def get_chat_history(
  video_id: str,
  user: Optional[User] = Depends(get_current_user),
  db: Session = Depends(get_read_db)
):
  # Find video
  video = db.query(Video).filter(Video.youtube_video_id == video_id).first()
  if not video:
    raise HTTPException(status_code=404, detail="Video not found")

  # Find latest conversation for this user and video
  user_id = user.id if user else None
  conversation = db.query(Conversation).filter(
    Conversation.video_id == video.id,
    Conversation.user_id == user_id
  ).order_by(Conversation.created_at.desc()).first()

  if not conversation:
    return ConversationOut(id="new-chat", video_id=video_id, title="New Conversation", messages=[])

  messages = db.query(Message).filter(
    Message.conversation_id == conversation.id
  ).order_by(Message.created_at.asc()).all()

  message_outs = [
    MessageOut(
      id=m.id,
      role=m.role,
      content=m.content,
      created_at=m.created_at
    ) for m in messages
  ]

  return ConversationOut(
    id=conversation.id,
    video_id=video_id,
    title=conversation.title,
    messages=message_outs,
    notes_summary=conversation.notes_summary,
    notes_detailed=conversation.notes_detailed,
    project_prompt=conversation.project_prompt,
    project_content=conversation.project_content,
    quiz_content=conversation.quiz_content
  )

@router.get("/conversations/{video_id}")
def get_conversations(
  video_id: str,
  user: Optional[User] = Depends(get_current_user),
  db: Session = Depends(get_read_db)
):
  video = db.query(Video).filter(Video.youtube_video_id == video_id).first()
  if not video:
    return []

  user_id = user.id if user else None
  conversations = db.query(Conversation).filter(
    Conversation.video_id == video.id,
    Conversation.user_id == user_id
  ).order_by(Conversation.created_at.desc()).all()

  return [
    {
      "id": c.id,
      "title": c.title or f"Chat session on {video_id}",
      "created_at": c.created_at.isoformat()
    }
    for c in conversations
  ]

@router.get("/conversation/{conversation_id}", response_model=ConversationOut)
def get_conversation_by_id(
  conversation_id: str,
  db: Session = Depends(get_read_db)
):
  conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
  if not conversation:
    raise HTTPException(status_code=404, detail="Conversation not found")

  messages = db.query(Message).filter(
    Message.conversation_id == conversation.id
  ).order_by(Message.created_at.asc()).all()

  message_outs = [
    MessageOut(
      id=m.id,
      role=m.role,
      content=m.content,
      created_at=m.created_at
    ) for m in messages
  ]

  # Get the video's youtube id
  video = db.query(Video).filter(Video.id == conversation.video_id).first()
  youtube_video_id = video.youtube_video_id if video else ""

  return ConversationOut(
    id=conversation.id,
    video_id=youtube_video_id,
    title=conversation.title,
    messages=message_outs,
    notes_summary=conversation.notes_summary,
    notes_detailed=conversation.notes_detailed,
    project_prompt=conversation.project_prompt,
    project_content=conversation.project_content,
    quiz_content=conversation.quiz_content
  )

@router.delete("/conversation/{conversation_id}")
def delete_conversation(
  conversation_id: str,
  db: Session = Depends(get_db)
):
  conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
  if not conversation:
    raise HTTPException(status_code=404, detail="Conversation not found")

  db.delete(conversation)
  db.commit()
  return {"status": "success", "message": "Conversation deleted successfully"}
  return {"status": "success", "message": "Conversation deleted successfully"}
  return {"status": "success", "message": "Conversation deleted successfully"}
