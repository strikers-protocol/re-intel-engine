"""
Database models for STRIKERS_PROTOCOL RE::INTEL
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id          = Column(Integer, primary_key=True, index=True)
    username    = Column(String(50), unique=True, index=True, nullable=False)
    email       = Column(String(120), unique=True, index=True, nullable=False)
    hashed_pw   = Column(String(256), nullable=False)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    analyses    = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    title         = Column(String(200), default="Untitled Analysis")
    target_type   = Column(String(50), nullable=False)   # software/firmware/hardware/code/network
    analysis_mode = Column(String(50), nullable=False)   # full/components/logic/security/bugs
    language      = Column(String(20), default="hinglish")
    input_text    = Column(Text, default="")
    file_name     = Column(String(256), default="")
    file_path     = Column(String(512), default="")
    file_size     = Column(Integer, default=0)
    file_type     = Column(String(100), default="")
    result_md     = Column(Text, default="")
    report_path   = Column(String(512), default="")
    risk_level    = Column(String(20), default="Unknown")
    complexity    = Column(String(20), default="Unknown")
    confidence    = Column(Float, default=0.0)
    tokens_used   = Column(Integer, default=0)
    duration_ms   = Column(Integer, default=0)
    created_at    = Column(DateTime, default=datetime.utcnow)
    status        = Column(String(20), default="pending")  # pending/running/done/error

    user          = relationship("User", back_populates="analyses")
