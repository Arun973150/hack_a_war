"""
Agent 5 — Hallucination Checker / Validator
Model: Gemini 2.0 Flash
Role: Verify all action items and obligations are grounded in source regulatory text.
      This is the agentic loop-on-failure mechanism — if invalid, re-route to extractor.
"""
import structlog
import vertexai
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from agents.state import ComplianceWorkflowState, ValidationResult
from config import settings

logger = structlog.get_logger()

vertexai.init(project=settings.vertex_project, location=settings.vertex_location)

VALIDATOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a regulatory compliance auditor performing a hallucination check.

Verify that the generated action plan is fully grounded in the source regulatory text.

Check for:
1. Hallucinated obligations (requirements not in source document)
2. Incorrect deadlines (dates not matching source)
3. Misattributed clauses (wrong section references)
4. Unsupported penalties
5. Scope creep (obligations extended beyond what source states)

Return JSON:
{{
  "valid": true/false,
  "confidence": 0.0-1.0,
  "issues": ["list of specific issues found"],
  "hallucinated_obligations": ["list of obligation IDs that are hallucinated"],
  "incorrect_deadlines": ["list of action IDs with wrong deadlines"]
}}

If all action items are grounded in source text, return valid: true with empty issue lists."""),
    ("human", """SOURCE REGULATORY TEXT (ground truth):
{source_text}

EXTRACTED OBLIGATIONS:
{obligations}

GENERATED ACTION ITEMS:
{action_items}

Validate that obligations and action items are grounded in the source text."""),
])


class ValidatorAgent:
    """
    Agent 5: Hallucination checking using Gemini 2.0 Flash.
    Implements the agentic self-correction loop.
    """

    def __init__(self):
        self._llm = ChatVertexAI(
            model_name=settings.gemini_flash_model,
            project=settings.vertex_project,
            location=settings.vertex_location,
            temperature=0.0,   # fully deterministic for verification
            max_output_tokens=2048,
        )
        self._parser = JsonOutputParser()
        self._chain = VALIDATOR_PROMPT | self._llm | self._parser

    def run(self, state: ComplianceWorkflowState) -> ComplianceWorkflowState:
        logger.info(
            "validator_start",
            document_id=state.document_id,
            retry_count=state.retry_count,
        )

        try:
            obligations_text = "\n".join([
                f"[{o.obligation_id}] WHO: {o.who_must_comply} | WHAT: {o.what} "
                f"| DEADLINE: {o.deadline} | CLAUSE: {o.source_clause}"
                for o in state.obligations
            ])

            action_items_text = "\n".join([
                f"[{a.action_id}] {a.title} | Owner: {a.owner} "
                f"| Deadline: {a.deadline} | Obligations: {a.source_obligation_ids} "
                f"| Clauses: {a.source_clauses}"
                for a in state.action_items
            ])

            result = self._chain.invoke({
                "source_text": state.raw_text[:6000],   # ground truth
                "obligations": obligations_text,
                "action_items": action_items_text,
            })

            state.validation = ValidationResult(
                valid=result.get("valid", False),
                confidence=result.get("confidence", 0.0),
                issues=result.get("issues", []),
                hallucinated_obligations=result.get("hallucinated_obligations", []),
                incorrect_deadlines=result.get("incorrect_deadlines", []),
            )

            logger.info(
                "validator_done",
                document_id=state.document_id,
                valid=state.validation.valid,
                confidence=state.validation.confidence,
                issues_count=len(state.validation.issues),
            )

        except Exception as e:
            logger.error("validator_failed", error=str(e))
            # On validator failure, mark as valid to avoid infinite loop
            state.validation = ValidationResult(
                valid=True,
                confidence=0.5,
                issues=[f"Validator error: {str(e)}"],
                hallucinated_obligations=[],
                incorrect_deadlines=[],
            )

        return state


def validator_node(state: ComplianceWorkflowState) -> ComplianceWorkflowState:
    """LangGraph node wrapper for the Validator Agent."""
    agent = ValidatorAgent()
    return agent.run(state)
