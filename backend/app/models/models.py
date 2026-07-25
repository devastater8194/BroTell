import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float, Boolean, Text
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
  return str(uuid.uuid4())

class User(Base):
  __tablename__ = "users"

  id = Column(String, primary_key=True, default=generate_uuid)
  email = Column(String, unique=True, index=True, nullable=False)
  password_hash = Column(String, nullable=True)
  google_id = Column(String, unique=True, index=True, nullable=True)
  display_name = Column(String, nullable=True)
  created_at = Column(DateTime, default=datetime.utcnow)
  updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

  conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
  notes = relationship("Notes", back_populates="user", cascade="all, delete-orphan")

class Video(Base):
  __tablename__ = "videos"

  id = Column(String, primary_key=True, default=generate_uuid)
  youtube_video_id = Column(String, unique=True, index=True, nullable=False)
  title = Column(String, nullable=True)
  language = Column(String, default="en")
  transcript_source = Column(String, default="official") # official, whisper, ocr
  duration_seconds = Column(Integer, default=0)
  created_at = Column(DateTime, default=datetime.utcnow)

  conversations = relationship("Conversation", back_populates="video", cascade="all, delete-orphan")

class Conversation(Base):
  __tablename__ = "conversations"

  id = Column(String, primary_key=True, default=generate_uuid)
  user_id = Column(String, ForeignKey("users.id"), nullable=True) # Nullable for guest chats
  video_id = Column(String, ForeignKey("videos.id"), nullable=False)
  title = Column(String, nullable=True)
  model = Column(String, default="gemini")
  created_at = Column(DateTime, default=datetime.utcnow)

  # Conversational memory for notes, projects, and quizzes
  notes_summary = Column(Text, nullable=True)
  notes_detailed = Column(Text, nullable=True)
  project_prompt = Column(Text, nullable=True)
  project_content = Column(Text, nullable=True)
  quiz_content = Column(Text, nullable=True)

  user = relationship("User", back_populates="conversations")
  video = relationship("Video", back_populates="conversations")
  messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
  __tablename__ = "messages"

  id = Column(String, primary_key=True, default=generate_uuid)
  conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
  role = Column(String, nullable=False) # user or assistant
  content = Column(Text, nullable=False)
  token_count = Column(Integer, default=0)
  created_at = Column(DateTime, default=datetime.utcnow)

  conversation = relationship("Conversation", back_populates="messages")

class Notes(Base):
  __tablename__ = "notes"

  id = Column(String, primary_key=True, default=generate_uuid)
  user_id = Column(String, ForeignKey("users.id"), nullable=True)
  video_id = Column(String, ForeignKey("videos.id"), nullable=False)
  content = Column(Text, nullable=False)
  note_type = Column(String, default="summary") # summary, detailed, flashcards, quiz
  created_at = Column(DateTime, default=datetime.utcnow)

  user = relationship("User", back_populates="notes")

class Usage(Base):
  __tablename__ = "usage"

  id = Column(String, primary_key=True, default=generate_uuid)
  user_id = Column(String, nullable=False, index=True)
  date = Column(String, nullable=False) # YYYY-MM-DD
  chats_today = Column(Integer, default=0)
  whisper_minutes = Column(Float, default=0.0)
  ocr_requests = Column(Integer, default=0)
  vision_requests = Column(Integer, default=0)
  pdf_exports = Column(Integer, default=0)
