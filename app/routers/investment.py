from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from ..database import get_db
from ..models import WatchlistStock, ResearchTask, IndustrySignal, ValuationNote

router = APIRouter(prefix="/api/investment", tags=["Investment"])

TAIPEI_TZ = timezone(timedelta(hours=8))

# ─────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────

class StockOut(BaseModel):
    id: int
    ticker: str
    price: Optional[str]
    forward_pe: Optional[str]
    peg_ratio: Optional[str]
    analyst_target: Optional[str]
    week_change: Optional[str]
    price_override: Optional[str]
    forward_pe_override: Optional[str]
    peg_ratio_override: Optional[str]
    analyst_target_override: Optional[str]
    notes: Optional[str]
    last_fetched: Optional[datetime]

    class Config:
        from_attributes = True


class StockCreate(BaseModel):
    ticker: str


class StockOverride(BaseModel):
    price_override: Optional[str] = None
    forward_pe_override: Optional[str] = None
    peg_ratio_override: Optional[str] = None
    analyst_target_override: Optional[str] = None
    notes: Optional[str] = None


class TaskOut(BaseModel):
    id: int
    text: str
    ticker_tag: Optional[str]
    task_type: str
    done: int
    created_at: datetime

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    text: str
    ticker_tag: Optional[str] = None
    task_type: str = "daily"   # daily | weekly | monthly


class TaskToggle(BaseModel):
    done: int   # 0 or 1


class SignalOut(BaseModel):
    id: int
    note: str
    category: str
    sentiment: str
    created_at: datetime

    class Config:
        from_attributes = True


class SignalCreate(BaseModel):
    note: str
    category: str = "other"       # upstream_capex | supply_chain | earnings | other
    sentiment: str = "neutral"    # positive | negative | neutral


class ValuationNoteOut(BaseModel):
    id: int
    ticker: str
    price: Optional[str]
    forward_pe: Optional[str]
    peg_ratio: Optional[str]
    judgment: Optional[str]
    note_date: str
    created_at: datetime

    class Config:
        from_attributes = True


class ValuationNoteCreate(BaseModel):
    ticker: str
    price: Optional[str] = None
    forward_pe: Optional[str] = None
    peg_ratio: Optional[str] = None
    judgment: Optional[str] = None
    note_date: Optional[str] = None   # defaults to today if omitted


# ─────────────────────────────────────────
# Ticker Search (Yahoo Finance proxy)
# ─────────────────────────────────────────

@router.get("/search")
async def search_tickers(q: str = Query(..., min_length=1)):
    """Proxy to Yahoo Finance quote search. Returns list of {ticker, name, type}."""
    import httpx
    url = (
        "https://query2.finance.yahoo.com/v1/finance/search"
        f"?q={q}&quotes_count=10&news_count=0&enableFuzzyQuery=false"
    )
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            data = resp.json()
        quotes = data.get("quotes", [])
        return [
            {
                "ticker": item["symbol"],
                "name": item.get("shortname") or item.get("longname") or "",
                "type": item.get("quoteType", ""),
            }
            for item in quotes
            if item.get("symbol") and item.get("quoteType") in ("EQUITY", "ETF", "INDEX")
        ]
    except Exception:
        return []


# ─────────────────────────────────────────
# Watchlist Endpoints
# ─────────────────────────────────────────

@router.get("/stocks", response_model=List[StockOut])
def list_stocks(db: Session = Depends(get_db)):
    return db.query(WatchlistStock).order_by(WatchlistStock.created_at).all()


@router.post("/stocks", response_model=StockOut, status_code=201)
def add_stock(body: StockCreate, db: Session = Depends(get_db)):
    ticker = body.ticker.upper().strip()
    if db.query(WatchlistStock).filter(WatchlistStock.ticker == ticker).first():
        raise HTTPException(400, f"{ticker} is already in the watchlist")
    from ..services.stock_fetcher import fetch_ticker_data
    data = fetch_ticker_data(ticker)
    stock = WatchlistStock(
        ticker=ticker,
        price=data["price"],
        forward_pe=data["forward_pe"],
        peg_ratio=data["peg_ratio"],
        analyst_target=data["analyst_target"],
        week_change=data["week_change"],
        last_fetched=datetime.now(TAIPEI_TZ),
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock


@router.patch("/stocks/{stock_id}", response_model=StockOut)
def update_stock(stock_id: int, body: StockOverride, db: Session = Depends(get_db)):
    stock = db.get(WatchlistStock, stock_id)
    if not stock:
        raise HTTPException(404, "Stock not found")
    for field in body.model_fields_set:
        setattr(stock, field, getattr(body, field))
    db.commit()
    db.refresh(stock)
    return stock


@router.delete("/stocks/{stock_id}", status_code=204)
def remove_stock(stock_id: int, db: Session = Depends(get_db)):
    stock = db.get(WatchlistStock, stock_id)
    if not stock:
        raise HTTPException(404, "Stock not found")
    db.delete(stock)
    db.commit()


@router.post("/stocks/refresh", status_code=202)
def trigger_refresh(background_tasks: BackgroundTasks):
    from ..services.stock_fetcher import run_stock_refresh
    background_tasks.add_task(run_stock_refresh)
    return {"message": "Stock refresh triggered"}


# ─────────────────────────────────────────
# Research Task Endpoints
# ─────────────────────────────────────────

@router.get("/tasks", response_model=List[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(ResearchTask).order_by(ResearchTask.created_at).all()


@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(body: TaskCreate, db: Session = Depends(get_db)):
    valid_types = {"daily", "weekly", "monthly"}
    if body.task_type not in valid_types:
        raise HTTPException(400, f"task_type must be one of {valid_types}")
    ticker = body.ticker_tag.upper().strip() if body.ticker_tag else None
    task = ResearchTask(text=body.text, ticker_tag=ticker, task_type=body.task_type)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def toggle_task(task_id: int, body: TaskToggle, db: Session = Depends(get_db)):
    task = db.get(ResearchTask, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    task.done = body.done
    db.commit()
    db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(ResearchTask, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    db.delete(task)
    db.commit()


# ─────────────────────────────────────────
# Industry Signal Endpoints
# ─────────────────────────────────────────

@router.get("/signals", response_model=List[SignalOut])
def list_signals(db: Session = Depends(get_db)):
    return db.query(IndustrySignal).order_by(IndustrySignal.created_at.desc()).all()


@router.post("/signals", response_model=SignalOut, status_code=201)
def create_signal(body: SignalCreate, db: Session = Depends(get_db)):
    valid_cats = {"upstream_capex", "supply_chain", "earnings", "other"}
    valid_sents = {"positive", "negative", "neutral"}
    if body.category not in valid_cats:
        raise HTTPException(400, f"category must be one of {valid_cats}")
    if body.sentiment not in valid_sents:
        raise HTTPException(400, f"sentiment must be one of {valid_sents}")
    signal = IndustrySignal(note=body.note, category=body.category, sentiment=body.sentiment)
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


@router.delete("/signals/{signal_id}", status_code=204)
def delete_signal(signal_id: int, db: Session = Depends(get_db)):
    signal = db.get(IndustrySignal, signal_id)
    if not signal:
        raise HTTPException(404, "Signal not found")
    db.delete(signal)
    db.commit()


# ─────────────────────────────────────────
# Valuation Note Endpoints
# ─────────────────────────────────────────

@router.get("/valuation", response_model=List[ValuationNoteOut])
def list_valuation_notes(
    ticker: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(ValuationNote)
    if ticker:
        q = q.filter(ValuationNote.ticker == ticker.upper())
    return q.order_by(ValuationNote.note_date.desc(), ValuationNote.created_at.desc()).all()


@router.post("/valuation", response_model=ValuationNoteOut, status_code=201)
def create_valuation_note(body: ValuationNoteCreate, db: Session = Depends(get_db)):
    note_date = body.note_date or datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d")
    note = ValuationNote(
        ticker=body.ticker.upper().strip(),
        price=body.price,
        forward_pe=body.forward_pe,
        peg_ratio=body.peg_ratio,
        judgment=body.judgment,
        note_date=note_date,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/valuation/{note_id}", status_code=204)
def delete_valuation_note(note_id: int, db: Session = Depends(get_db)):
    note = db.get(ValuationNote, note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    db.delete(note)
    db.commit()
