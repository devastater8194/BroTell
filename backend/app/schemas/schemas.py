from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# --- Authentication Schemas ---
class UserCreate(BaseModel):
  email: EmailStr
  password: str
  display_name: Optional[str] = None

class UserLogin(BaseModel):
  email: EmailStr
  password: str

class UserOut(BaseModel):
  id: str
  email: EmailStr
  display_name: Optional[str] = None
  created_at: datetime

  class Config:
    from_attributes = True

class Token(BaseModel):
  access_token: str
  token_type: str
  user: Optional[UserOut] = None

class TokenData(BaseModel):
  email: Optional[str] = None
  user_id: Optional[str] = None

# --- Video Ingestion Schemas ---
class VideoIngest(BaseModel):
  video_id: str

class VideoStatus(BaseModel):
  status: str
  job_id: str
  progress: Optional[int] = 0

class VideoOut(BaseModel):
  id: str
  youtube_video_id: str
  title: Optional[str] = None
  language: str
  duration_seconds: int

  class Config:
    from_attributes = True

# --- Chat & Messaging Schemas ---
class ChatRequest(BaseModel):
  video_id: str
  conversation_id: Optional[str] = None
  message: str
  model: Optional[str] = "gemini"

class MessageOut(BaseModel):
  id: str
  role: str
  content: str
  created_at: datetime

  class Config:
    from_attributes = True

class ConversationOut(BaseModel):
  id: str
  video_id: str
  title: Optional[str] = None
  messages: List[MessageOut] = []
  notes_summary: Optional[str] = None
  notes_detailed: Optional[str] = None
  project_prompt: Optional[str] = None
  project_content: Optional[str] = None
  quiz_content: Optional[str] = None

  class Config:
    from_attributes = True

# --- Notes, Quiz & Exports ---
class NotesRequest(BaseModel):
  video_id: str
  conversation_id: Optional[str] = None
  format: Optional[str] = "summary" # summary, detailed
  force_new: Optional[bool] = False

class NotesOut(BaseModel):
  notes: Optional[str] = None
  conversation_id: Optional[str] = None
  job_id: Optional[str] = None
  status: Optional[str] = "success"

class QuizRequest(BaseModel):
  video_id: str
  conversation_id: Optional[str] = None
  force_new: Optional[bool] = False

class QuizSubmitRequest(BaseModel):
  video_id: str
  conversation_id: str
  quiz_id: str
  answers: dict
  score: str

class QuizOut(BaseModel):
  quiz: Optional[str] = None
  conversation_id: Optional[str] = None
  job_id: Optional[str] = None
  status: Optional[str] = "success"

class ProjectRequest(BaseModel):
  video_id: str
  conversation_id: Optional[str] = None
  prompt: Optional[str] = "Build the project shown in this video."

class ProjectOut(BaseModel):
  project_files: Optional[str] = None
  conversation_id: Optional[str] = None
  job_id: Optional[str] = None
  status: Optional[str] = "success"
