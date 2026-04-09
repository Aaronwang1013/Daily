"""
RSS ingestion + optional Claude summarization.
Called by APScheduler daily at 08:00 Asia/Taipei and by the manual trigger endpoint.
"""

import os
import re
import logging
from datetime import datetime, timezone, timedelta

import feedparser

from ..database import SessionLocal
from ..models import FinancialNews

logger = logging.getLogger(__name__)

TAIPEI_TZ = timezone(timedelta(hours=8))

RSS_SOURCES = [
    {
        "key": "cnyes_tw",
        "name": "鉅亨網台股",
        "url": "https://feeds.feedburner.com/cnyes/stock",
        "market": "tw",
    },
    {
        "key": "cnyes_us",
        "name": "鉅亨網美股",
        "url": "https://feeds.feedburner.com/cnyes/usstock",
        "market": "us",
    },
    {
        "key": "yahoo_tw",
        "name": "Yahoo Finance TW",
        "url": "https://tw.stock.yahoo.com/rss",
        "market": "tw",
    },
    {
        "key": "reuters_markets",
        "name": "Reuters",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "market": "global",
    },
    {
        "key": "ftchinese",
        "name": "FT中文網",
        "url": "https://www.ftchinese.com/rss/feed",
        "market": "global",
    },
]


def _parse_date(entry) -> str:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                utc_dt = datetime(*t[:6], tzinfo=timezone.utc)
                taipei_dt = utc_dt.astimezone(TAIPEI_TZ)
                return taipei_dt.strftime("%Y-%m-%d")
            except Exception:
                pass
    return datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d")


def _extract_text(entry) -> str:
    for attr in ("summary_detail", "content"):
        val = getattr(entry, attr, None)
        if val:
            if isinstance(val, list):
                val = val[0]
            text = getattr(val, "value", "") or ""
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 80:
                return text[:2000]
    return entry.get("title", "")


def _summarize_with_claude(articles_text: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.info("ANTHROPIC_API_KEY not set — skipping summarization")
        return ""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "你是一位財經分析師。以下是今日多個財經新聞標題與摘要，"
            "請用繁體中文寫出 3-5 個重點條列，每點 1-2 句，著重台股與美股市場影響。\n\n"
            + articles_text
        )
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        logger.warning(f"Claude summarization failed: {e}")
        return ""


def run_fetch_job():
    """Fetch all RSS sources, store new articles, optionally summarize."""
    db = SessionLocal()
    today = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d")
    new_articles = []

    try:
        for source in RSS_SOURCES:
            try:
                feed = feedparser.parse(source["url"])
                for entry in feed.entries[:15]:
                    url = entry.get("link", "")
                    if not url:
                        continue

                    exists = (
                        db.query(FinancialNews.id)
                        .filter(FinancialNews.url == url)
                        .first()
                    )
                    if exists:
                        continue

                    pub_date = _parse_date(entry)
                    raw = _extract_text(entry)
                    title = entry.get("title", "").strip()

                    tags = []
                    for t in getattr(entry, "tags", []):
                        label = getattr(t, "term", "") or getattr(t, "label", "")
                        if label:
                            tags.append(label[:50])

                    item = FinancialNews(
                        source=source["key"],
                        title=title,
                        url=url,
                        raw_content=raw,
                        summary=None,
                        published_date=pub_date,
                        market=source["market"],
                        tags=tags[:10],
                    )
                    db.add(item)
                    if pub_date == today:
                        new_articles.append(f"【{source['name']}】{title}\n{raw[:300]}")

            except Exception as e:
                logger.error(f"Failed to fetch {source['key']}: {e}")

        db.commit()

        if new_articles:
            combined = "\n\n---\n\n".join(new_articles[:20])
            digest = _summarize_with_claude(combined)
            if digest:
                first_today = (
                    db.query(FinancialNews)
                    .filter(FinancialNews.published_date == today)
                    .order_by(FinancialNews.created_at.asc())
                    .first()
                )
                if first_today and not first_today.summary:
                    first_today.summary = digest
                    db.commit()

        logger.info(f"RSS fetch complete. {len(new_articles)} new articles today.")

    except Exception as e:
        logger.error(f"run_fetch_job failed: {e}")
        db.rollback()
    finally:
        db.close()
