from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from ..database import get_db
from ..models import ClaudeSummary

router = APIRouter(prefix="/api/summary", tags=["Summary"])


class SummaryCreate(BaseModel):
    content: str
    summary_date: str          # YYYY-MM-DD
    tags: List[str] = []


@router.get("/latest")
def get_latest(db: Session = Depends(get_db)):
    s = db.query(ClaudeSummary).order_by(ClaudeSummary.summary_date.desc()).first()
    if not s:
        return {"content": "", "summary_date": "", "tags": []}
    return s


@router.get("/history")
def get_history(limit: int = 7, db: Session = Depends(get_db)):
    return (
        db.query(ClaudeSummary)
        .order_by(ClaudeSummary.summary_date.desc())
        .limit(limit)
        .all()
    )


@router.post("", status_code=201)
def create_summary(body: SummaryCreate, db: Session = Depends(get_db)):
    s = ClaudeSummary(**body.dict())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{summary_id}", status_code=204)
def delete_summary(summary_id: int, db: Session = Depends(get_db)):
    s = db.query(ClaudeSummary).get(summary_id)
    if not s:
        raise HTTPException(404, "Not found")
    db.delete(s)
    db.commit()
