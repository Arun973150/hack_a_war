import aiohttp
import feedparser
import structlog
from datetime import datetime
from typing import AsyncIterator

from .base import BaseConnector, DocumentType, Jurisdiction, RawRegulatoryDocument

logger = structlog.get_logger()

EUR_LEX_RSS_FEEDS = {
    "regulations": "https://eur-lex.europa.eu/rss/legal-act-consolidated.xml",
    "decisions": "https://eur-lex.europa.eu/rss/legal-act-decisions.xml",
    "directives": "https://eur-lex.europa.eu/rss/legal-act-directives.xml",
}

EUR_LEX_SPARQL = "https://publications.europa.eu/webapi/rdf/sparql"


class EurLexConnector(BaseConnector):
    """Connects to EUR-Lex (EU Official Journal) via RSS and SPARQL."""

    source_name = "EUR-Lex"
    jurisdiction = Jurisdiction.EU

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def fetch_recent(self, since: datetime) -> AsyncIterator[RawRegulatoryDocument]:
        session = await self._get_session()

        for feed_type, feed_url in EUR_LEX_RSS_FEEDS.items():
            try:
                async with session.get(feed_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        logger.warning("eur_lex_feed_failed", feed=feed_type, status=resp.status)
                        continue
                    feed_content = await resp.text()

                feed = feedparser.parse(feed_content)

                for entry in feed.entries:
                    published = self._parse_date(entry.get("published", ""))
                    if published and published < since:
                        continue

                    content, content_type = await self._fetch_document(session, entry)
                    if content is None:
                        continue

                    yield RawRegulatoryDocument(
                        source_id=entry.get("id", entry.get("link", "")),
                        source_url=entry.get("link", ""),
                        title=entry.get("title", "Untitled EU Document"),
                        jurisdiction=Jurisdiction.EU,
                        regulatory_body="European Commission",
                        document_type=self._infer_type(feed_type),
                        published_date=published or datetime.utcnow(),
                        raw_content=content,
                        content_type=content_type,
                        metadata={"feed_type": feed_type, "summary": entry.get("summary", "")},
                    )

            except Exception as e:
                logger.error("eur_lex_feed_error", feed=feed_type, error=str(e))

    async def _fetch_document(
        self, session: aiohttp.ClientSession, entry: dict
    ) -> tuple[bytes | None, str]:
        link = entry.get("link", "")
        if not link:
            return None, ""
        try:
            async with session.get(link, timeout=aiohttp.ClientTimeout(total=30)) as r:
                if r.status == 200:
                    content_type = r.headers.get("Content-Type", "text/html")
                    if "pdf" in content_type:
                        return await r.read(), "application/pdf"
                    return await r.read(), "text/html"
        except Exception as e:
            logger.warning("eur_lex_doc_fetch_failed", url=link, error=str(e))
        return None, ""

    def _parse_date(self, date_str: str) -> datetime | None:
        formats = ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).replace(tzinfo=None)
            except ValueError:
                continue
        return None

    def _infer_type(self, feed_type: str) -> DocumentType:
        return {
            "regulations": DocumentType.NEW_REGULATION,
            "directives": DocumentType.NEW_REGULATION,
            "decisions": DocumentType.ENFORCEMENT_ACTION,
        }.get(feed_type, DocumentType.GUIDANCE)

    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(
                EUR_LEX_RSS_FEEDS["regulations"],
                timeout=aiohttp.ClientTimeout(total=10)
            ) as r:
                return r.status == 200
        except Exception:
            return False
