import logging
import structlog
import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.database import engine, Base
from app.api.v1 import auth, video, chat, notes, quiz, project, pdf, jobs
from app.config import settings

structlog.configure(
  processors=[
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.JSONRenderer(),
  ],
  logger_factory=structlog.stdlib.LoggerFactory(),
)
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = structlog.get_logger()
logger.info("Structlog initialized successfully.")

if settings.SENTRY_DSN.strip():
  logger.info("Initializing Sentry SDK for error tracking and tracing...")
  sentry_sdk.init(
    dsn=settings.SENTRY_DSN.strip(),
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
  )

def run_migrations():
  import sqlite3
  db_path = "workspace.db"
  if "sqlite" in str(engine.url):
    db_path = str(engine.url).replace("sqlite:///", "")
  try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(conversations)")
    columns = [col[1] for col in cursor.fetchall()]
    
    new_cols = {
      "notes_summary": "TEXT",
      "notes_detailed": "TEXT",
      "project_prompt": "TEXT",
      "project_content": "TEXT",
      "quiz_content": "TEXT"
    }
    
    for col_name, col_type in new_cols.items():
      if col_name not in columns:
        cursor.execute(f"ALTER TABLE conversations ADD COLUMN {col_name} {col_type}")
        logger.info(f"Migration: Added column '{col_name}' to conversations table.")
    conn.commit()
    conn.close()
  except Exception as e:
    logger.warning("Migration warning:", error=str(e))

try:
  Base.metadata.create_all(bind=engine)
  run_migrations()
  logger.info("Database tables initialized successfully.")
except Exception as e:
  logger.error("Error initializing database tables:", error=str(e))

app = FastAPI(
  title="YouTube AI Learning Workspace API",
  description="API backing the YouTube AI Chrome Extension, providing RAG context chat, summaries, notes, PDFs, and repository blueprints.",
  version="1.0.0"
)


app.add_middleware(
  CORSMiddleware,
  allow_origin_regex=r"chrome-extension://.*|http://localhost:.*",
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(video.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")
app.include_router(quiz.router, prefix="/api/v1")
app.include_router(project.router, prefix="/api/v1")
app.include_router(pdf.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")

Instrumentator().instrument(app).expose(app)

@app.get("/", tags=["Health Check"])
def read_root():
  return {
    "status": "healthy",
    "service": "YouTube AI Learning Workspace API",
    "version": "1.0.0"
  }
