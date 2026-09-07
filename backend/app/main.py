from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import Base, engine
from .models import Job, Candidate, Screening, User, UserSession
from .api.routes import router
from .api.auth import router as auth_router

app=FastAPI(title="AI Hiring Assistant", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.app_cors_origins.split(",") if x.strip()], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
Base.metadata.create_all(bind=engine)
app.include_router(router)
app.include_router(auth_router)
