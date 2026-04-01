import json
import structlog
import vertexai
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from config import settings

logger = structlog.get_logger()

vertexai.init(project=settings.vertex_project, location=settings.vertex_location)


class SPOTriplet(BaseModel):
    subject: str = Field(description="The entity (regulation, body, obligation)")
    predicate: str = Field(description="The relationship verb (REQUIRES, AMENDS, APPLIES_TO, etc.)")
    object: str = Field(description="The target entity")
    confidence: float = Field(default=1.0, description="Confidence score 0.0-1.0", ge=0.0, le=1.0)


class TripletExtractionResult(BaseModel):
    triplets: list[SPOTriplet]
    regulation_id: str
    amendment_refs: list[str] = Field(default_factory=list)


TRIPLET_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a regulatory knowledge graph expert.
Extract Subject-Predicate-Object triplets from regulatory text.

Allowed predicates:
- REQUIRES (obligation)
- AMENDS (modifies another regulation)
- SUPERSEDES (replaces another regulation)
- APPLIES_TO (jurisdiction/sector/entity type)
- ENFORCED_BY (regulatory body)
- DEADLINE_OF (date/timeframe obligation)
- PROHIBITS (forbidden action)
- DEFINES (definition of a term)
- REFERENCES (cites another regulation)
- EXEMPTS (excludes from obligation)

Rules:
- Subject must be a named entity (regulation, body, organization type)
- Object must be a named entity or action
- Extract only high-confidence facts explicitly stated in text
- Do NOT infer or hallucinate

Return JSON: {{"triplets": [...], "regulation_id": "...", "amendment_refs": [...]}}"""),
    ("human", """Regulation ID: {regulation_id}
Text:
{text}

Extract SPO triplets. Focus on obligations, amendments, deadlines, and applicability."""),
])


class TripletExtractor:
    """
    Extracts SPO triplets from regulatory text using Gemini 2.0 Flash.
    Cheaper model appropriate for structured extraction (not deep reasoning).
    """

    def __init__(self):
        self._llm = ChatVertexAI(
            model_name=settings.gemini_flash_model,
            project=settings.vertex_project,
            location=settings.vertex_location,
            temperature=0.0,   # deterministic for extraction
            max_output_tokens=2048,
        )
        self._parser = JsonOutputParser(pydantic_object=TripletExtractionResult)
        self._chain = TRIPLET_PROMPT | self._llm | self._parser

    def extract(self, text: str, regulation_id: str) -> TripletExtractionResult:
        """Extract SPO triplets from a regulatory text chunk."""
        try:
            result = self._chain.invoke({
                "text": text[:4000],
                "regulation_id": regulation_id,
            })
            if isinstance(result, dict):
                # Normalize capitalized keys from Gemini (Subject → subject, etc.)
                if "triplets" in result:
                    normalized = []
                    for t in result["triplets"]:
                        normalized.append({k.lower(): v for k, v in t.items()})
                    result["triplets"] = normalized
                return TripletExtractionResult(**result)
            return result
        except Exception as e:
            logger.error("triplet_extraction_failed", error=str(e), regulation_id=regulation_id)
            return TripletExtractionResult(triplets=[], regulation_id=regulation_id)

    def extract_batch(
        self, chunks: list[str], regulation_id: str
    ) -> list[SPOTriplet]:
        """Extract triplets from multiple chunks and deduplicate."""
        all_triplets: list[SPOTriplet] = []
        seen = set()

        for chunk in chunks:
            result = self.extract(chunk, regulation_id)
            for triplet in result.triplets:
                key = (triplet.subject.lower(), triplet.predicate, triplet.object.lower())
                if key not in seen and triplet.confidence >= 0.7:
                    seen.add(key)
                    all_triplets.append(triplet)

        logger.info(
            "batch_extraction_complete",
            total_triplets=len(all_triplets),
            chunks=len(chunks),
        )
        return all_triplets
