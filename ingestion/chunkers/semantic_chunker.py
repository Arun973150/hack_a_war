import hashlib
import re
import structlog
from dataclasses import dataclass, field
from typing import Callable

from langchain.text_splitter import RecursiveCharacterTextSplitter
from ingestion.parsers.document_parser import ParsedDocument

logger = structlog.get_logger()

# Regulatory clause boundary patterns
REGULATORY_SEPARATORS = [
    r"\n#{1,4}\s",            # markdown headings
    r"\n(?:Section|SECTION|Article|ARTICLE|Chapter|CHAPTER)\s+\d+",
    r"\n\(\d+\)\s",           # numbered clauses (1), (2)
    r"\n\d+\.\d+\s",          # section numbers like 3.2
    r"\n\d+\.\s[A-Z]",        # numbered items like "1. The..."
    r"\n\n",                   # double newline (paragraph break)
    r"\n",                     # single newline
    r"\s",                     # space
]


@dataclass
class RegulatoryChunk:
    chunk_id: str              # SHA256 of content for deduplication
    text: str
    section_title: str
    chunk_index: int
    total_chunks: int
    word_count: int
    metadata: dict = field(default_factory=dict)


class SemanticChunker:
    """
    Semantic chunker for regulatory documents.
    Preserves clause boundaries, cross-references, and regulatory structure.
    Uses LangChain's RecursiveCharacterTextSplitter with regulatory-aware separators.
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        min_chunk_size: int = 100,
    ):
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._min_chunk_size = min_chunk_size

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=REGULATORY_SEPARATORS,
            is_separator_regex=True,
            length_function=self._word_count,
        )

    def chunk(self, document: ParsedDocument, doc_metadata: dict) -> list[RegulatoryChunk]:
        """
        Chunk a parsed regulatory document into semantically meaningful pieces.
        Sections are chunked individually to preserve regulatory clause boundaries.
        """
        chunks: list[RegulatoryChunk] = []

        if document.sections:
            for section in document.sections:
                section_text = f"{section['title']}\n\n{section['content']}" \
                    if section.get("content") else section.get("title", "")
                section_chunks = self._chunk_text(
                    section_text,
                    section_title=section.get("title", ""),
                    base_metadata={**doc_metadata, "section": section.get("title", ""),
                                   "page_num": section.get("page_num", 1)},
                )
                chunks.extend(section_chunks)
        else:
            # No sections — chunk the full text
            chunks = self._chunk_text(
                document.text,
                section_title="Full Document",
                base_metadata=doc_metadata,
            )

        # Remove duplicates by chunk_id
        seen = set()
        deduped = []
        for chunk in chunks:
            if chunk.chunk_id not in seen:
                seen.add(chunk.chunk_id)
                deduped.append(chunk)

        # Re-index after dedup
        total = len(deduped)
        for i, chunk in enumerate(deduped):
            chunk.chunk_index = i
            chunk.total_chunks = total

        logger.info("chunking_complete", total_chunks=total, sections=len(document.sections))
        return deduped

    def _chunk_text(
        self, text: str, section_title: str, base_metadata: dict
    ) -> list[RegulatoryChunk]:
        if not text or not text.strip():
            return []

        # Pre-process: normalize whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

        raw_chunks = self._splitter.split_text(text)
        result = []

        for i, chunk_text in enumerate(raw_chunks):
            chunk_text = chunk_text.strip()
            if self._word_count(chunk_text) < self._min_chunk_size:
                continue

            chunk_id = hashlib.sha256(chunk_text.encode()).hexdigest()

            result.append(RegulatoryChunk(
                chunk_id=chunk_id,
                text=chunk_text,
                section_title=section_title,
                chunk_index=i,
                total_chunks=len(raw_chunks),
                word_count=self._word_count(chunk_text),
                metadata={
                    **base_metadata,
                    "cross_references": self._extract_cross_references(chunk_text),
                    "has_deadline": self._has_deadline(chunk_text),
                    "has_monetary_value": self._has_monetary_value(chunk_text),
                },
            ))

        return result

    def _word_count(self, text: str) -> int:
        return len(text.split())

    def _extract_cross_references(self, text: str) -> list[str]:
        """Extract references to other regulations/sections within the chunk."""
        patterns = [
            r"(?:Section|Article|Regulation|Rule|Clause)\s+[\d.]+(?:\([a-z]\))?",
            r"(?:pursuant to|under|as per|in accordance with)\s+[A-Z][a-z]+\s+(?:Act|Regulation|Rule)",
            r"\b(?:CFR|USC|EU)\s+[\d.]+",
        ]
        refs = []
        for pattern in patterns:
            refs.extend(re.findall(pattern, text, re.IGNORECASE))
        return list(set(refs))

    def _has_deadline(self, text: str) -> bool:
        deadline_patterns = [
            r"\bby\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)",
            r"\bwithin\s+\d+\s+(?:days|months|years)",
            r"\beffective\s+(?:date|January|February)",
            r"\bdeadline\b",
            r"\bdue\s+(?:by|date)\b",
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in deadline_patterns)

    def _has_monetary_value(self, text: str) -> bool:
        return bool(re.search(
            r"\$[\d,]+|\bEUR\s*[\d,]+|\bUSD\s*[\d,]+|\b[\d,]+\s*(?:million|billion|crore)",
            text, re.IGNORECASE
        ))
