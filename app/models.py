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


class FinancialNews(Base):
    __tablename__ = "financial_news"
    id             = Column(Integer, primary_key=True, index=True)
    source         = Column(String(100), nullable=False)
    title          = Column(String(500), nullable=False)
    url            = Column(String(1000), nullable=False, unique=True)
    raw_content    = Column(Text, nullable=True)
    summary        = Column(Text, nullable=True)
    published_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    market         = Column(String(5), nullable=True)                # "tw" | "us" | "global"
    tags           = Column(JSON, default=list)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())


# ── Investment Research Models ──

class WatchlistStock(Base):
    __tablename__ = "watchlist_stocks"
    id                      = Column(Integer, primary_key=True, index=True)
    ticker                  = Column(String(20), nullable=False, unique=True)
    # Auto-fetched fields (refreshed by scheduler)
    price                   = Column(String(20), nullable=True)
    forward_pe              = Column(String(20), nullable=True)
    peg_ratio               = Column(String(20), nullable=True)
    analyst_target          = Column(String(20), nullable=True)
    week_change             = Column(String(20), nullable=True)   # e.g. "+3.21" (%)
    # Manual overrides (NULL = use auto value)
    price_override          = Column(String(20), nullable=True)
    forward_pe_override     = Column(String(20), nullable=True)
    peg_ratio_override      = Column(String(20), nullable=True)
    analyst_target_override = Column(String(20), nullable=True)
    notes                   = Column(Text, nullable=True)
    last_fetched            = Column(DateTime(timezone=True), nullable=True)
    created_at              = Column(DateTime(timezone=True), server_default=func.now())


class ResearchTask(Base):
    __tablename__ = "research_tasks"
    id         = Column(Integer, primary_key=True, index=True)
    text       = Column(String(500), nullable=False)
    ticker_tag = Column(String(20), nullable=True)
    task_type  = Column(String(10), nullable=False, default="daily")  # daily | weekly | monthly
    done       = Column(Integer, default=0)   # 0/1
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IndustrySignal(Base):
    __tablename__ = "industry_signals"
    id         = Column(Integer, primary_key=True, index=True)
    note       = Column(String(1000), nullable=False)
    category   = Column(String(30), nullable=False, default="other")
    # upstream_capex | supply_chain | earnings | other
    sentiment  = Column(String(10), nullable=False, default="neutral")
    # positive | negative | neutral
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ValuationNote(Base):
    __tablename__ = "valuation_notes"
    id         = Column(Integer, primary_key=True, index=True)
    ticker     = Column(String(20), nullable=False, index=True)
    price      = Column(String(20), nullable=True)
    forward_pe = Column(String(20), nullable=True)
    peg_ratio  = Column(String(20), nullable=True)
    judgment   = Column(Text, nullable=True)   # personal analysis
    note_date  = Column(String(10), nullable=False)  # YYYY-MM-DD
    created_at = Column(DateTime(timezone=True), server_default=func.now())
