"""
Agent 1 — Regulatory Scanner
Model: Gemini 2.0 Flash-Lite (fast, cheap — built for high-volume triage)
Role: First-pass classification and relevance filtering.
      90% of documents are irrelevant — this agent catches that cheap.
"""
import json
import structlog
import vertexai
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from agents.state import ComplianceWorkflowState
from config import settings

logger = structlog.get_logger()

vertexai.init(project=settings.vertex_project, location=settings.vertex_location)

SCANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a regulatory compliance triage specialist.
Your job is to quickly classify incoming regulatory documents and determine
if they are relevant to an organization's compliance requirements.

Classify the document and return JSON only:
{{
  "is_relevant": true/false,
  "relevance_score": 0.0-1.0,
  "jurisdiction": "US_FEDERAL|EU|UK|INDIA|UNKNOWN",
  "sector": "Finance|Healthcare|Technology|Energy|General|Multiple",
  "document_type": "NEW_REGULATION|AMENDMENT|ENFORCEMENT|GUIDANCE|CONSULTATION",
  "regulatory_body": "name of the issuing body",
  "key_topics": ["list", "of", "main", "topics"],
  "reasoning": "one sentence explaining relevance decision"
}}

Mark as relevant if it involves: data privacy, financial compliance,
cybersecurity, AI regulation, environmental, healthcare, or employment law."""),
    ("human", """Document Title: {title}
Jurisdiction: {jurisdiction}
Regulatory Body: {regulatory_body}
Document Type: {document_type}
Published: {published_date}

Content (first 2000 chars):
{content}

Classify this document."""),
])


class ScannerAgent:
    """Agent 1: Fast triage using Gemini 2.0 Flash-Lite."""

    def __init__(self):
        self._llm = ChatVertexAI(
            model_name=settings.gemini_flash_lite_model,
            project=settings.vertex_project,
            location=settings.vertex_location,
            temperature=0.0,
            max_output_tokens=512,
        )
        self._parser = JsonOutputParser()
        self._chain = SCANNER_PROMPT | self._llm | self._parser

    def run(self, state: ComplianceWorkflowState) -> ComplianceWorkflowState:
        """Classify the regulatory document and update state."""
        logger.info("scanner_agent_start", document_id=state.document_id)

        try:
            result = self._chain.invoke({
                "title": state.document_id,
                "jurisdiction": state.jurisdiction,
                "regulatory_body": state.regulatory_body,
                "document_type": state.document_type,
                "published_date": state.published_date,
                "content": state.raw_text[:2000],
            })

            state.is_relevant = result.get("is_relevant", False)
            state.relevance_score = result.get("relevance_score", 0.0)
            state.jurisdiction = result.get("jurisdiction", state.jurisdiction)
            state.sector = result.get("sector", "General")
            state.document_type = result.get("document_type", state.document_type)
            state.regulatory_body = result.get("regulatory_body", state.regulatory_body)
            state.scan_reasoning = result.get("reasoning", "")

            logger.info(
                "scanner_agent_done",
                document_id=state.document_id,
                is_relevant=state.is_relevant,
                relevance_score=state.relevance_score,
                sector=state.sector,
            )

        except Exception as e:
            logger.error("scanner_agent_failed", error=str(e))
            state.error = f"Scanner failed: {str(e)}"
            state.is_relevant = False

        return state


def scanner_node(state: ComplianceWorkflowState) -> ComplianceWorkflowState:
    """LangGraph node wrapper for the Scanner Agent."""
    agent = ScannerAgent()
    return agent.run(state)
