"""
Regulatory Horizon Scanner
Runs as a background asyncio task. Every N hours (configurable via HORIZON_SCAN_INTERVAL_HOURS):
  1. Fetches latest regulations from Federal Register, EUR-Lex, SEBI feeds
  2. Checks against regulation_tracking table — skips already-seen source_ids
  3. For truly new regulations, upserts into regulation_tracking with status="discovered"
  4. Optionally auto-triggers Slack alert for high-relevance regulations

Start from FastAPI lifespan:
    task = asyncio.create_task(horizon_scan_loop())
"""
import asyncio
import os
import hashlib
import structlog
import httpx
import feedparser
from datetime import datetime
from typing import Optional

from config import settings
from org_context.models.database import upsert_regulation_tracking

logger = structlog.get_logger()

# How often to run the scan (override with HORIZON_SCAN_INTERVAL_HOURS env var)
DEFAULT_HORIZON_SCAN_INTERVAL_HOURS = 12

# Keywords that indicate high relevance (trigger Slack alerts)
HIGH_RELEVANCE_KEYWORDS = ["payment", "cyber", "data protection", "ai", "fintech"]

# Feed URLs
FEDERAL_REGISTER_URL = (
    "https://www.federalregister.gov/api/v1/documents.json"
    "?conditions[agencies][]=consumer-financial-protection-bureau"
    "&conditions[agencies][]=securities-and-exchange-commission"
    "&per_page=10&order=newest"
)
EUR_LEX_RSS_URL = "https://www.ecb.europa.eu/rss/press.html"
SEBI_RSS_URL = (
    "https://www.sebi.gov.in/sebiweb/home/HomeAction.do"
    "?doListing=yes&sid=1&ssid=1&smid=0"
)


def _is_high_relevance(title: str, summary: str = "") -> bool:
    """Check if a regulation matches high-relevance keywords."""
    text = f"{title} {summary}".lower()
    return any(kw in text for kw in HIGH_RELEVANCE_KEYWORDS)


def _generate_source_id(source: str, identifier: str) -> str:
    """Generate a deterministic source_id from source name and identifier."""
    raw = f"{source}:{identifier}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def _send_slack_horizon_alert(regulation: dict) -> bool:
    """Send a Slack notification for a newly discovered high-relevance regulation."""
    if not settings.slack_webhook_url:
        return False

    payload = {
        "text": f"*Red Forge Horizon Scanner — New Regulation Discovered*",
        "attachments": [{
            "color": "#3B82F6",
            "fields": [
                {"title": "Title", "value": regulation.get("title", "Unknown"), "short": False},
                {"title": "Jurisdiction", "value": regulation.get("jurisdiction", "Unknown"), "short": True},
                {"title": "Source", "value": regulation.get("regulatory_body", "Unknown"), "short": True},
                {"title": "Published", "value": regulation.get("published_date", "Unknown"), "short": True},
                {"title": "URL", "value": regulation.get("source_url", "N/A"), "short": False},
            ],
            "footer": "Red Forge Horizon Scanner",
            "ts": int(datetime.utcnow().timestamp()),
        }]
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(settings.slack_webhook_url, json=payload)
            return resp.status_code == 200
    except Exception as e:
        logger.error("horizon_slack_failed", title=regulation.get("title"), error=str(e))
        return False


async def _fetch_federal_register_feed() -> list[dict]:
    """Fetch recent financial regulations from Federal Register API."""
    results = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(FEDERAL_REGISTER_URL)
            resp.raise_for_status()
            data = resp.json()

        for doc in data.get("results", []):
            doc_number = doc.get("document_number", "")
            if not doc_number:
                continue
            results.append({
                "source_id": _generate_source_id("federal_register", doc_number),
                "title": doc.get("title", "Untitled"),
                "jurisdiction": "US",
                "regulatory_body": ", ".join(
                    a.get("name", "") for a in doc.get("agencies", [])
                ) or "Federal Register",
                "document_type": doc.get("type", "Rule"),
                "published_date": doc.get("publication_date", ""),
                "source_url": doc.get("html_url", doc.get("pdf_url", "")),
                "summary": doc.get("abstract", ""),
            })

        logger.info("horizon_federal_register_fetched", count=len(results))

    except Exception as e:
        logger.error("horizon_federal_register_error", error=str(e))

    return results


async def _fetch_eur_lex_feed() -> list[dict]:
    """Fetch recent EU regulations from EUR-Lex RSS feed."""
    results = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(EUR_LEX_RSS_URL)
            resp.raise_for_status()

        feed = feedparser.parse(resp.text)

        for entry in feed.entries[:10]:
            entry_id = entry.get("id", entry.get("link", ""))
            if not entry_id:
                continue
            results.append({
                "source_id": _generate_source_id("ecb", entry_id),
                "title": entry.get("title", "Untitled"),
                "jurisdiction": "EU",
                "regulatory_body": "European Central Bank",
                "document_type": "Regulation",
                "published_date": entry.get("published", entry.get("updated", "")),
                "source_url": entry.get("link", ""),
                "summary": entry.get("summary", ""),
            })

        logger.info("horizon_eur_lex_fetched", count=len(results))

    except Exception as e:
        logger.error("horizon_eur_lex_error", error=str(e))

    return results


async def _fetch_sebi_feed() -> list[dict]:
    """Fetch recent SEBI circulars from RSS feed."""
    results = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(SEBI_RSS_URL)
            resp.raise_for_status()

        feed = feedparser.parse(resp.text)

        for entry in feed.entries[:10]:
            entry_id = entry.get("id", entry.get("link", ""))
            if not entry_id:
                continue
            results.append({
                "source_id": _generate_source_id("sebi", entry_id),
                "title": entry.get("title", "Untitled"),
                "jurisdiction": "India",
                "regulatory_body": "SEBI",
                "document_type": "Circular",
                "published_date": entry.get("published", entry.get("updated", "")),
                "source_url": entry.get("link", ""),
                "summary": entry.get("summary", ""),
            })

        logger.info("horizon_sebi_fetched", count=len(results))

    except Exception as e:
        logger.error("horizon_sebi_error", error=str(e))

    return results


async def run_horizon_scan() -> dict:
    """
    Run a single horizon scan cycle. Returns a summary dict.
    Safe to call manually (e.g. from an API endpoint for on-demand scan).
    """
    logger.info("horizon_scan_start")
    start = datetime.utcnow()

    # 1. Fetch from all feeds concurrently (each wrapped in try/except internally)
    fed_items, eur_items, sebi_items = await asyncio.gather(
        _fetch_federal_register_feed(),
        _fetch_eur_lex_feed(),
        _fetch_sebi_feed(),
    )

    all_items = fed_items + eur_items + sebi_items
    logger.info("horizon_scan_fetched", total_items=len(all_items))

    new_count = 0
    skipped_count = 0
    slack_alerts_sent = 0
    discovered = []

    # 2. Process each regulation
    for item in all_items:
        source_id = item["source_id"]
        title = item["title"]
        summary = item.get("summary", "")

        try:
            # Upsert into regulation_tracking — the function returns existing
            # record if source_id already exists, so we check processing_status
            reg = upsert_regulation_tracking(
                source_id=source_id,
                title=title,
                jurisdiction=item["jurisdiction"],
                regulatory_body=item["regulatory_body"],
                document_type=item["document_type"],
                published_date=item["published_date"] or datetime.utcnow().isoformat(),
                source_url=item["source_url"],
                processing_status="discovered",
            )

            # If the record was just created (discovered), it's new
            # We detect this by checking if processed_at is None (new records
            # don't get processed_at set when status is "discovered")
            if reg.processing_status == "discovered" and reg.processed_at is None:
                new_count += 1
                discovered.append({
                    "source_id": source_id,
                    "title": title,
                    "jurisdiction": item["jurisdiction"],
                    "regulatory_body": item["regulatory_body"],
                    "source_url": item["source_url"],
                    "high_relevance": _is_high_relevance(title, summary),
                })

                # 3. Slack alert for high-relevance regulations
                if _is_high_relevance(title, summary):
                    sent = await _send_slack_horizon_alert(item)
                    if sent:
                        slack_alerts_sent += 1
            else:
                skipped_count += 1

        except Exception as e:
            logger.error(
                "horizon_scan_upsert_error",
                source_id=source_id,
                title=title,
                error=str(e),
            )

    elapsed = (datetime.utcnow() - start).total_seconds()

    logger.info(
        "horizon_scan_done",
        total_fetched=len(all_items),
        new_discovered=new_count,
        skipped_existing=skipped_count,
        slack_alerts=slack_alerts_sent,
        elapsed_s=round(elapsed, 2),
    )

    return {
        "status": "ok",
        "total_fetched": len(all_items),
        "new_discovered": new_count,
        "skipped_existing": skipped_count,
        "slack_alerts_sent": slack_alerts_sent,
        "discovered": discovered[:50],
        "elapsed_seconds": round(elapsed, 2),
    }


async def horizon_scan_loop(interval_hours: int | None = None):
    """
    Infinite background loop. Runs run_horizon_scan() every interval_hours.
    Started via asyncio.create_task() in FastAPI lifespan.
    Runs the first scan after a short delay (60s) so the API is fully ready.
    """
    if interval_hours is None:
        interval_hours = int(
            os.environ.get("HORIZON_SCAN_INTERVAL_HOURS", DEFAULT_HORIZON_SCAN_INTERVAL_HOURS)
        )

    logger.info("horizon_scanner_started", interval_hours=interval_hours)
    await asyncio.sleep(60)  # let FastAPI finish startup

    while True:
        try:
            await run_horizon_scan()
        except Exception as e:
            logger.error("horizon_scan_error", error=str(e))

        await asyncio.sleep(interval_hours * 3600)
