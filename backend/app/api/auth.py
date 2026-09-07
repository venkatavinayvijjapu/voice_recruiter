import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from ..db import get_db
from ..models import User, UserSession

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserSignup(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_current_user(authorization: str | None = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing Authorization header")
    token = authorization.split(" ")[1]
    
    session = db.scalar(select(UserSession).where(UserSession.session_token == token, UserSession.is_active == True))
    if not session or session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    return user, session

@router.post("/signup")
def signup(body: UserSignup, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    user = User(
        email=body.email,
        hashed_password=get_password_hash(body.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email}

@router.post("/login")
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    session = UserSession(
        user_id=user.id,
        session_token=token,
        expires_at=expires_at,
        is_active=True
    )
    db.add(session)
    db.commit()
    
    return {"token": token, "user": {"id": user.id, "email": user.email}}

@router.post("/logout")
def logout(current_data: tuple = Depends(get_current_user), db: Session = Depends(get_db)):
    user, session = current_data
    session.is_active = False
    db.add(session)
    db.commit()
    return {"message": "Logged out successfully"}

@router.get("/sessions")
def sessions(current_data: tuple = Depends(get_current_user), db: Session = Depends(get_db)):
    user, current_session = current_data
    user_sessions = db.scalars(select(UserSession).where(UserSession.user_id == user.id).order_by(UserSession.created_at.desc())).all()
    
    return [
        {
            "id": s.id,
            "created_at": s.created_at,
            "expires_at": s.expires_at,
            "is_active": s.is_active and s.expires_at > datetime.now(timezone.utc),
            "is_current": s.id == current_session.id
        }
        for s in user_sessions
    ]
