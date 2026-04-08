from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from ..database import get_db
from ..models import CalendarEvent, EarningsEvent

router = APIRouter(prefix="/api/calendar", tags=["Calendar"])

# ── Seed 財報日期（首次啟動時寫入 DB）──
EARNINGS_SEED = [
    {"title": "JPMorgan (JPM) 財報",      "date": "2026-04-11", "color": "#ef4444", "market": "us", "ticker": "JPM"},
    {"title": "Goldman Sachs (GS) 財報",  "date": "2026-04-14", "color": "#ef4444", "market": "us", "ticker": "GS"},
    {"title": "Netflix (NFLX) 財報",      "date": "2026-04-16", "color": "#ef4444", "market": "us", "ticker": "NFLX"},
    {"title": "TSMC ADR (TSM) 財報",      "date": "2026-04-17", "color": "#f59e0b", "market": "tw", "ticker": "TSM"},
    {"title": "台積電法說會",              "date": "2026-04-17", "color": "#f59e0b", "market": "tw", "ticker": "2330"},
    {"title": "Alphabet (GOOGL) 財報",    "date": "2026-04-23", "color": "#ef4444", "market": "us", "ticker": "GOOGL"},
    {"title": "Meta (META) 財報",         "date": "2026-04-23", "color": "#ef4444", "market": "us", "ticker": "META"},
    {"title": "Microsoft (MSFT) 財報",    "date": "2026-04-24", "color": "#ef4444", "market": "us", "ticker": "MSFT"},
    {"title": "Amazon (AMZN) 財報",       "date": "2026-04-30", "color": "#ef4444", "market": "us", "ticker": "AMZN"},
    {"title": "Apple (AAPL) 財報",        "date": "2026-05-01", "color": "#ef4444", "market": "us", "ticker": "AAPL"},
    {"title": "NVIDIA (NVDA) 財報",       "date": "2026-05-28", "color": "#ef4444", "market": "us", "ticker": "NVDA"},
    {"title": "台股月營收截止 (3月)",      "date": "2026-04-10", "color": "#22c55e", "market": "tw", "ticker": None},
    {"title": "台股月營收截止 (4月)",      "date": "2026-05-10", "color": "#22c55e", "market": "tw", "ticker": None},
    {"title": "台股 Q1 季報截止日",        "date": "2026-05-15", "color": "#f59e0b", "market": "tw", "ticker": None},
]


def seed_earnings(db: Session):
    if db.query(EarningsEvent).count() == 0:
        for e in EARNINGS_SEED:
            db.add(EarningsEvent(**e))
        db.commit()


# ── Schemas ──
class EventCreate(BaseModel):
    title: str
    date: str           # YYYY-MM-DD
    time: Optional[str] = None
    color: str = "#7c5cfc"
    event_type: str = "personal"


class EarningsCreate(BaseModel):
    title: str
    date: str
    color: str = "#ef4444"
    market: str         # us / tw
    ticker: Optional[str] = None


# ── Endpoints ──
@router.get("/events")
def list_events(date: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(CalendarEvent)
    if date:
        q = q.filter(CalendarEvent.date == date)
    return q.order_by(CalendarEvent.date).all()


@router.post("/events", status_code=201)
def create_event(body: EventCreate, db: Session = Depends(get_db)):
    ev = CalendarEvent(**body.dict())
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    ev = db.query(CalendarEvent).get(event_id)
    if not ev:
        raise HTTPException(404, "Event not found")
    db.delete(ev)
    db.commit()


@router.get("/earnings")
def list_earnings(month: Optional[str] = None, db: Session = Depends(get_db)):
    seed_earnings(db)
    q = db.query(EarningsEvent)
    if month:          # e.g. "2026-04"
        q = q.filter(EarningsEvent.date.startswith(month))
    return q.order_by(EarningsEvent.date).all()


@router.post("/earnings", status_code=201)
def create_earnings(body: EarningsCreate, db: Session = Depends(get_db)):
    ev = EarningsEvent(**body.dict())
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


@router.delete("/earnings/{event_id}", status_code=204)
def delete_earnings(event_id: int, db: Session = Depends(get_db)):
    ev = db.query(EarningsEvent).get(event_id)
    if not ev:
        raise HTTPException(404, "Not found")
    db.delete(ev)
    db.commit()
