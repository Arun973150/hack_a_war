from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import AsyncIterator


class Jurisdiction(str, Enum):
    US_FEDERAL = "US_FEDERAL"
    EU = "EU"
    UK = "UK"
    INDIA = "INDIA"
    UNKNOWN = "UNKNOWN"


class DocumentType(str, Enum):
    NEW_REGULATION = "NEW_REGULATION"
    AMENDMENT = "AMENDMENT"
    ENFORCEMENT_ACTION = "ENFORCEMENT_ACTION"
    GUIDANCE = "GUIDANCE"
    CONSULTATION = "CONSULTATION"
    CIRCULAR = "CIRCULAR"
    NOTIFICATION = "NOTIFICATION"


@dataclass
class RawRegulatoryDocument:
    source_id: str                          # unique ID from source
    source_url: str
    title: str
    jurisdiction: Jurisdiction
    regulatory_body: str
    document_type: DocumentType
    published_date: datetime
    raw_content: bytes                      # raw PDF/HTML bytes
    content_type: str                       # "application/pdf" | "text/html"
    metadata: dict = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.utcnow)


class BaseConnector(ABC):
    """Base class for all regulatory source connectors."""

    @property
    @abstractmethod
    def source_name(self) -> str: ...

    @property
    @abstractmethod
    def jurisdiction(self) -> Jurisdiction: ...

    @abstractmethod
    async def fetch_recent(self, since: datetime) -> AsyncIterator[RawRegulatoryDocument]:
        """Yield documents published since the given datetime."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the source is reachable."""
        ...
