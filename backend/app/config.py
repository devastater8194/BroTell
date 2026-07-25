import os
from pathlib import Path

# Load local .env file manually if present (dependency-free loader)
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

class Settings:
 
  JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
  JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
  ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

  DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./workspace.db")
  DATABASE_READ_URL: str = os.getenv("DATABASE_READ_URL", "")

 
  REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

  
  QDRANT_URL: str = os.getenv("QDRANT_URL", "")
  QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")

  
  SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")

  
  RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))

 
  GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
  
  
  GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
  OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
  CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")

 
  WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "small")
  WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
  MAX_VIDEO_LENGTH: int = int(os.getenv("MAX_VIDEO_LENGTH", "7200"))
  CACHE_TTL_DAYS: int = int(os.getenv("CACHE_TTL_DAYS", "30"))

settings = Settings()
