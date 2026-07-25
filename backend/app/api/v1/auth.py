from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User
from app.schemas.schemas import UserCreate, UserLogin, Token, UserOut
from app.auth.auth_handler import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
  # Check if email already exists
  existing_user = db.query(User).filter(User.email == user_data.email).first()
  if existing_user:
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="Email address already registered"
    )

  hashed_password = get_password_hash(user_data.password)
  new_user = User(
    email=user_data.email,
    password_hash=hashed_password,
    display_name=user_data.display_name or user_data.email.split("@")[0]
  )
  db.add(new_user)
  db.commit()
  db.refresh(new_user)

  # Generate access token
  access_token = create_access_token(data={"sub": new_user.email, "user_id": new_user.id})
  user_out = UserOut.from_orm(new_user)
  return Token(access_token=access_token, token_type="bearer", user=user_out)

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
  user = db.query(User).filter(User.email == login_data.email).first()
  if not user or not user.password_hash:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid email or password"
    )

  if not verify_password(login_data.password, user.password_hash):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid email or password"
    )

  access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
  user_out = UserOut.from_orm(user)
  return Token(access_token=access_token, token_type="bearer", user=user_out)
