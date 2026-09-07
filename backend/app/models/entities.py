from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    session_token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    questions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now
    )


class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    phone: Mapped[str] = mapped_column(String(50))
    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    experience_years: Mapped[float] = mapped_column(
        Float,
        default=0
    )
    current_company: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    current_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    skills: Mapped[str] = mapped_column(
        Text,
        default=""
    )


class Screening(Base):
    __tablename__ = "screenings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"),
        index=True
    )

    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.candidate_id"),
        index=True
    )

    hunar_call_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        index=True
    )

    lifecycle_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    raw_call: Mapped[dict] = mapped_column(
        JSON,
        default=dict
    )

    transcript: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    recording_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    evaluation: Mapped[dict] = mapped_column(
        JSON,
        default=dict
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        onupdate=now
    )