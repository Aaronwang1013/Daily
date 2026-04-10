"""
yfinance stock data refresh.
Called by APScheduler and by POST /api/investment/stocks/refresh.
"""
import logging
from datetime import datetime, timezone, timedelta

from ..database import SessionLocal
from ..models import WatchlistStock

logger = logging.getLogger(__name__)

TAIPEI_TZ = timezone(timedelta(hours=8))
DEFAULT_TICKERS = ["LITE", "COHR", "CIEN", "AAOI"]


def _safe_str(val) -> str | None:
    """Convert yfinance numeric to 2-decimal string; return None for NaN/inf/None."""
    if val is None:
        return None
    try:
        f = float(val)
        if f != f or f in (float("inf"), float("-inf")):
            return None
        return f"{f:.2f}"
    except (TypeError, ValueError):
        return None


def fetch_ticker_data(ticker: str) -> dict:
    """
    Fetch live metrics for a single ticker via yfinance.
    Returns dict with: price, forward_pe, peg_ratio, analyst_target, week_change.
    All values are strings ("12.34") or None.
    """
    import yfinance as yf

    try:
        t = yf.Ticker(ticker)
        info = t.info

        price = _safe_str(
            info.get("currentPrice") or info.get("regularMarketPrice")
        )
        forward_pe = _safe_str(info.get("forwardPE"))
        peg_ratio = _safe_str(
            info.get("trailingPegRatio") or info.get("pegRatio")
        )
        analyst_target = _safe_str(info.get("targetMeanPrice"))

        # Weekly % change: compare last close to close 5 trading days ago
        week_change = None
        try:
            hist = t.history(period="5d")
            if len(hist) >= 2:
                close_now = hist["Close"].iloc[-1]
                close_prev = hist["Close"].iloc[0]
                if close_prev and close_prev != 0:
                    pct = (close_now - close_prev) / close_prev * 100
                    week_change = f"{pct:+.2f}"
        except Exception:
            pass

        return {
            "price": price,
            "forward_pe": forward_pe,
            "peg_ratio": peg_ratio,
            "analyst_target": analyst_target,
            "week_change": week_change,
        }
    except Exception as e:
        logger.warning(f"yfinance fetch failed for {ticker}: {e}")
        return {
            "price": None,
            "forward_pe": None,
            "peg_ratio": None,
            "analyst_target": None,
            "week_change": None,
        }


def run_stock_refresh():
    """Refresh all WatchlistStock rows with live yfinance data."""
    db = SessionLocal()
    try:
        stocks = db.query(WatchlistStock).all()
        if not stocks:
            logger.info("No stocks in watchlist, skipping refresh.")
            return
        for stock in stocks:
            data = fetch_ticker_data(stock.ticker)
            stock.price          = data["price"]
            stock.forward_pe     = data["forward_pe"]
            stock.peg_ratio      = data["peg_ratio"]
            stock.analyst_target = data["analyst_target"]
            stock.week_change    = data["week_change"]
            stock.last_fetched   = datetime.now(TAIPEI_TZ)
        db.commit()
        logger.info(f"Stock refresh complete for {len(stocks)} tickers.")
    except Exception as e:
        logger.error(f"run_stock_refresh failed: {e}")
        db.rollback()
    finally:
        db.close()


def seed_default_watchlist():
    """Seed the 4 default tickers on first startup if the table is empty."""
    db = SessionLocal()
    try:
        if db.query(WatchlistStock).count() == 0:
            for t in DEFAULT_TICKERS:
                db.add(WatchlistStock(ticker=t))
            db.commit()
            logger.info(f"Seeded default watchlist: {DEFAULT_TICKERS}")
    except Exception as e:
        logger.error(f"seed_default_watchlist failed: {e}")
        db.rollback()
    finally:
        db.close()
