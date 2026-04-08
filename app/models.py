from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from .database import Base


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    id        = Column(Integer, primary_key=True, index=True)
    title     = Column(String(200), nullable=False)
    date      = Column(String(10), nullable=False, index=True)   # YYYY-MM-DD
    time      = Column(String(5), nullable=True)                  # HH:MM
    color     = Column(String(20), default="#4f8ef7")
    event_type = Column(String(20), default="personal")          # personal / us / tw
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EarningsEvent(Base):
    __tablename__ = "earnings_events"
    id      = Column(Integer, primary_key=True, index=True)
    title   = Column(String(200), nullable=False)
    date    = Column(String(10), nullable=False, index=True)
    color   = Column(String(20), default="#ef4444")
    market  = Column(String(5), nullable=False)                  # us / tw
    ticker  = Column(String(20), nullable=True)


class ClaudeSummary(Base):
    __tablename__ = "claude_summaries"
    id         = Column(Integer, primary_key=True, index=True)
    content    = Column(Text, nullable=False)
    summary_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    tags       = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AWSProgress(Base):
    __tablename__ = "aws_progress"
    id             = Column(Integer, primary_key=True, index=True)
    done           = Column(Integer, default=0)
    total          = Column(Integer, default=18)
    current_lesson = Column(String(200), default="")
    resume_url     = Column(Text, default="")
    lessons        = Column(JSON, default=list)
    updated_at     = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
