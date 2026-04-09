from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from ..database import get_db
from ..models import FinancialNews

router = APIRouter(prefix="/api/news", tags=["News"])

TAIPEI_TZ = timezone(timedelta(hours=8))


class NewsItem(BaseModel):
    id: int
    source: str
    title: str
    url: str
    summary: Optional[str] = None
    published_date: str
    market: Optional[str] = None
    tags: List[str] = []

    class Config:
        from_attributes = True


@router.get("/today", response_model=List[NewsItem])
def get_today(
    market: Optional[str] = Query(None),
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db),
):
    today = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d")
    q = db.query(FinancialNews).filter(FinancialNews.published_date == today)
    if market:
        q = q.filter(FinancialNews.market == market)
    return q.order_by(FinancialNews.created_at.desc()).limit(limit).all()


@router.get("/latest", response_model=List[NewsItem])
def get_latest(limit: int = Query(15, le=30), db: Session = Depends(get_db)):
    return (
        db.query(FinancialNews)
        .order_by(FinancialNews.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/date/{date_str}", response_model=List[NewsItem])
def get_by_date(
    date_str: str,
    market: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(FinancialNews).filter(FinancialNews.published_date == date_str)
    if market:
        q = q.filter(FinancialNews.market == market)
    return q.order_by(FinancialNews.created_at.desc()).all()


@router.post("/fetch", status_code=202)
def trigger_fetch():
    from ..services.news_fetcher import run_fetch_job
    import threading
    threading.Thread(target=run_fetch_job, daemon=True).start()
    return {"message": "RSS fetch job triggered"}


@router.delete("/{news_id}", status_code=204)
def delete_news(news_id: int, db: Session = Depends(get_db)):
    item = db.query(FinancialNews).filter(FinancialNews.id == news_id).first()
    if not item:
        raise HTTPException(404, "Not found")
    db.delete(item)
    db.commit()
