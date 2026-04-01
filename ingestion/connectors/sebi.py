import aiohttp
import structlog
from bs4 import BeautifulSoup
from datetime import datetime
from typing import AsyncIterator

from .base import BaseConnector, DocumentType, Jurisdiction, RawRegulatoryDocument

logger = structlog.get_logger()

SEBI_CIRCULARS_URL = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&smid=0"
RBI_CIRCULARS_URL = "https://www.rbi.org.in/scripts/BS_CircularIndexDisplay.aspx"


class SEBIConnector(BaseConnector):
    """Scrapes SEBI (Securities and Exchange Board of India) circulars."""

    source_name = "SEBI"
    jurisdiction = Jurisdiction.INDIA

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; RedForgeBot/1.0; regulatory compliance research)"
            }
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def fetch_recent(self, since: datetime) -> AsyncIterator[RawRegulatoryDocument]:
        session = await self._get_session()

        try:
            async with session.get(
                SEBI_CIRCULARS_URL, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    logger.error("sebi_fetch_failed", status=resp.status)
                    return
                html = await resp.text()

            soup = BeautifulSoup(html, "lxml")
            circular_rows = soup.select("table.table tbody tr")

            for row in circular_rows:
                cols = row.find_all("td")
                if len(cols) < 3:
                    continue

                date_text = cols[0].get_text(strip=True)
                published = self._parse_indian_date(date_text)
                if published and published < since:
                    continue

                link_tag = cols[1].find("a")
                if not link_tag:
                    continue

                doc_url = link_tag.get("href", "")
                if not doc_url.startswith("http"):
                    doc_url = f"https://www.sebi.gov.in{doc_url}"

                title = link_tag.get_text(strip=True)
                content, content_type = await self._fetch_document(session, doc_url)
                if content is None:
                    continue

                circular_ref = cols[2].get_text(strip=True) if len(cols) > 2 else ""

                yield RawRegulatoryDocument(
                    source_id=circular_ref or doc_url,
                    source_url=doc_url,
                    title=title,
                    jurisdiction=Jurisdiction.INDIA,
                    regulatory_body="SEBI",
                    document_type=DocumentType.CIRCULAR,
                    published_date=published or datetime.utcnow(),
                    raw_content=content,
                    content_type=content_type,
                    metadata={"circular_ref": circular_ref},
                )

        except Exception as e:
            logger.error("sebi_connector_error", error=str(e))

    async def _fetch_document(
        self, session: aiohttp.ClientSession, url: str
    ) -> tuple[bytes | None, str]:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
                if r.status == 200:
                    content_type = r.headers.get("Content-Type", "text/html")
                    if "pdf" in content_type or url.endswith(".pdf"):
                        return await r.read(), "application/pdf"
                    return await r.read(), "text/html"
        except Exception as e:
            logger.warning("sebi_doc_fetch_failed", url=url, error=str(e))
        return None, ""

    def _parse_indian_date(self, date_str: str) -> datetime | None:
        formats = ["%b %d, %Y", "%d %b %Y", "%d-%m-%Y", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None

    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(
                "https://www.sebi.gov.in", timeout=aiohttp.ClientTimeout(total=10)
            ) as r:
                return r.status == 200
        except Exception:
            return False
