from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings


connect_args = {}
pool_kwargs = {}

if settings.DATABASE_URL.startswith("sqlite"):
  connect_args = {"check_same_thread": False}
else:
  
  pool_kwargs = {
    "pool_size": 20,
    "max_overflow": 10,
    "pool_recycle": 1800,
    "pool_pre_ping": True
  }

engine = create_engine(
  settings.DATABASE_URL,
  connect_args=connect_args,
  **pool_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


read_engine = None
if settings.DATABASE_READ_URL.strip():
  read_engine = create_engine(
    settings.DATABASE_READ_URL.strip(),
    connect_args=connect_args,
    **pool_kwargs
  )
  ReadSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=read_engine)
else:
  ReadSessionLocal = SessionLocal

Base = declarative_base()

def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


def get_read_db():
  db = ReadSessionLocal()
  try:
    yield db
  finally:
    db.close()
