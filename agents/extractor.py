"""
Agent 2 — Obligation Extractor
Model: Gemini 2.0 Flash (balanced speed + precision)
Role: Extract structured obligations from filtered regulatory documents.
      WHO must do WHAT by WHEN under WHAT conditions with WHAT penalties.
"""
import uuid
import structlog
import vertexai
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from agents.state import ComplianceWorkflowState, Obligation
from knowledge.vectors.qdrant_store import RegulatoryVectorStore
from config import settings

logger = structlog.get_logger()

vertexai.init(project=settings.vertex_project, location=settings.vertex_location)

EXTRACTOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a senior regulatory compliance analyst specializing in
obligation extraction from legal and regulatory texts.

Extract ALL obligations from the provided regulatory text.
For each obligation, extract:

{{
  "obligations": [
    {{
      "obligation_id": "unique id e.g. OBL-001",
      "text": "exact quote or close paraphrase from source",
      "who_must_comply": "entities required to comply (e.g., 'financial institutions', 'data controllers')",
      "what": "specific action or requirement",
      "deadline": "exact date or timeframe (null if not specified)",
      "conditions": "conditions under which obligation applies (null if always)",
      "penalty": "consequence of non-compliance (null if not specified)",
      "source_clause": "section/article reference e.g. 'Article 13(1)'"
    }}
  ],
  "extraction_confidence": 0.0-1.0
}}

Rules:
- Extract ONLY obligations explicitly stated in the text
- Do NOT infer or add obligations not present
- Include direct quotes where possible in 'text' field
- Set confidence based on text clarity (clear mandate = high, ambiguous = low)"""),
    ("human", """Regulatory Document: {regulation_id}
Jurisdiction: {jurisdiction}
Regulatory Body: {regulatory_body}

Full Text:
{text}

Extract all compliance obligations."""),
])


class ExtractorAgent:
    """Agent 2: Obligation extraction using Gemini 2.0 Flash."""

    def __init__(self):
        self._llm = ChatVertexAI(
            model_name=settings.gemini_flash_model,
            project=settings.vertex_project,
            location=settings.vertex_location,
            temperature=0.0,
            max_output_tokens=4096,
        )
        self._parser = JsonOutputParser()
        self._chain = EXTRACTOR_PROMPT | self._llm | self._parser
        self._vector_store = RegulatoryVectorStore()

    def run(self, state: ComplianceWorkflowState) -> ComplianceWorkflowState:
        logger.info("extractor_agent_start", document_id=state.document_id)

        try:
            # Split text into chunks to handle long documents
            text_chunks = self._split_for_extraction(state.raw_text)
            all_obligations = []
            total_confidence = 0.0

            for chunk in text_chunks:
                result = self._chain.invoke({
                    "regulation_id": state.document_id,
                    "jurisdiction": state.jurisdiction,
                    "regulatory_body": state.regulatory_body,
                    "text": chunk,
                })

                chunk_obligations = result.get("obligations", [])
                chunk_confidence = result.get("extraction_confidence", 0.5)
                total_confidence += chunk_confidence

                for obs_dict in chunk_obligations:
                    if not obs_dict.get("obligation_id"):
                        obs_dict["obligation_id"] = f"OBL-{uuid.uuid4().hex[:8].upper()}"
                    all_obligations.append(Obligation(**obs_dict))

            state.obligations = self._deduplicate_obligations(all_obligations)
            state.extraction_confidence = (
                total_confidence / len(text_chunks) if text_chunks else 0.0
            )

            logger.info(
                "extractor_agent_done",
                document_id=state.document_id,
                obligation_count=len(state.obligations),
                confidence=state.extraction_confidence,
            )

        except Exception as e:
            logger.error("extractor_agent_failed", error=str(e))
            state.error = f"Extractor failed: {str(e)}"

        return state

    def _split_for_extraction(self, text: str, chunk_size: int = 6000) -> list[str]:
        """Split long regulatory text into overlapping chunks for extraction."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        overlap = 500
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
        return chunks

    def _deduplicate_obligations(self, obligations: list[Obligation]) -> list[Obligation]:
        """Remove duplicate obligations by comparing 'what' field."""
        seen = set()
        unique = []
        for obs in obligations:
            key = obs.what.lower().strip()[:100]
            if key not in seen:
                seen.add(key)
                unique.append(obs)
        return unique


def extractor_node(state: ComplianceWorkflowState) -> ComplianceWorkflowState:
    """LangGraph node wrapper for the Extractor Agent."""
    agent = ExtractorAgent()
    return agent.run(state)
