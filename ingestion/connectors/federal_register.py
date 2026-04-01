import aiohttp
import structlog
from datetime import datetime
from typing import AsyncIterator

from .base import BaseConnector, DocumentType, Jurisdiction, RawRegulatoryDocument

logger = structlog.get_logger()

FEDERAL_REGISTER_API = "https://www.federalregister.gov/api/v1"

DOCUMENT_TYPE_MAP = {
    "RULE": DocumentType.NEW_REGULATION,
    "PROPOSED_RULE": DocumentType.CONSULTATION,
    "NOTICE": DocumentType.GUIDANCE,
    "PRESIDENTIAL_DOCUMENT": DocumentType.NEW_REGULATION,
}


class FederalRegisterConnector(BaseConnector):
    """Connects to the US Federal Register API."""

    source_name = "Federal Register"
    jurisdiction = Jurisdiction.US_FEDERAL

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def fetch_recent(self, since: datetime) -> AsyncIterator[RawRegulatoryDocument]:
        session = await self._get_session()
        page = 1

        while True:
            params = {
                "fields[]": ["document_number", "title", "type", "publication_date",
                              "full_text_xml_url", "pdf_url", "html_url", "agencies"],
                "per_page": 20,
                "page": page,
                "conditions[publication_date][gte]": since.strftime("%Y-%m-%d"),
                "order": "newest",
            }
            if self._api_key:
                params["api_key"] = self._api_key

            async with session.get(f"{FEDERAL_REGISTER_API}/documents", params=params) as resp:
                if resp.status != 200:
                    logger.error("federal_register_fetch_failed", status=resp.status)
                    break

                data = await resp.json()
                results = data.get("results", [])
                if not results:
                    break

                for doc in results:
                    content, content_type = await self._fetch_content(session, doc)
                    if content is None:
                        continue

                    agencies = doc.get("agencies", [{}])
                    regulatory_body = agencies[0].get("name", "Unknown Agency") if agencies else "Unknown Agency"

                    yield RawRegulatoryDocument(
                        source_id=doc["document_number"],
                        source_url=doc.get("html_url", ""),
                        title=doc.get("title", "Untitled"),
                        jurisdiction=Jurisdiction.US_FEDERAL,
                        regulatory_body=regulatory_body,
                        document_type=DOCUMENT_TYPE_MAP.get(
                            doc.get("type", ""), DocumentType.GUIDANCE
                        ),
                        published_date=datetime.strptime(
                            doc["publication_date"], "%Y-%m-%d"
                        ),
                        raw_content=content,
                        content_type=content_type,
                        metadata={
                            "agencies": [a.get("name") for a in agencies],
                            "pdf_url": doc.get("pdf_url"),
                        },
                    )

                if page >= data.get("total_pages", 1):
                    break
                page += 1

    async def _fetch_content(
        self, session: aiohttp.ClientSession, doc: dict
    ) -> tuple[bytes | None, str]:
        # Prefer PDF, fall back to HTML
        pdf_url = doc.get("pdf_url")
        html_url = doc.get("html_url")

        if pdf_url:
            try:
                async with session.get(pdf_url) as r:
                    if r.status == 200:
                        return await r.read(), "application/pdf"
            except Exception as e:
                logger.warning("pdf_fetch_failed", url=pdf_url, error=str(e))

        if html_url:
            try:
                async with session.get(html_url) as r:
                    if r.status == 200:
                        return await r.read(), "text/html"
            except Exception as e:
                logger.warning("html_fetch_failed", url=html_url, error=str(e))

        return None, ""

    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(f"{FEDERAL_REGISTER_API}/documents?per_page=1") as r:
                return r.status == 200
        except Exception:
            return False
