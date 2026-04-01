"""
LangGraph Orchestrator — The compliance workflow state machine.

Graph topology:
    START
      │
      ▼
   scanner ──── irrelevant ──▶ END
      │
    relevant
      │
      ▼
  extractor
      │
      ▼
 impact_analyst
      │
      ▼
 action_planner
      │
      ▼
  validator ──── valid ──────▶ END
      │
    invalid + retry_count < max_retries
      │
      ▼
  extractor (retry with refined context)
"""
import structlog
from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg

from agents.state import ComplianceWorkflowState
from agents.scanner import scanner_node
from agents.extractor import extractor_node
from agents.impact_analyst import impact_analyst_node
from agents.action_planner import action_planner_node
from agents.validator import validator_node
from config import settings

logger = structlog.get_logger()


# ─── Routing Functions ────────────────────────────────────────────────────────

def route_after_scanner(
    state: ComplianceWorkflowState,
) -> Literal["extractor", "__end__"]:
    """Route: relevant documents proceed, irrelevant go to END."""
    if state.error:
        logger.warning("scanner_error_routing_to_end", error=state.error)
        return END
    if state.is_relevant and state.relevance_score >= 0.4:
        return "extractor"
    logger.info("document_filtered_as_irrelevant", score=state.relevance_score)
    return END


def route_after_validator(
    state: ComplianceWorkflowState,
) -> Literal["extractor", "__end__"]:
    """
    Route: Valid output → END.
    Invalid + retries remaining → back to extractor (agentic self-correction loop).
    """
    if state.error:
        return END
    if state.validation and state.validation.valid:
        return END
    if state.retry_count < state.max_retries:
        state.retry_count += 1
        logger.info(
            "validation_failed_retrying",
            retry=state.retry_count,
            issues=state.validation.issues if state.validation else [],
        )
        return "extractor"
    logger.warning("max_retries_reached", document_id=state.document_id)
    return END


# ─── Graph Builder ────────────────────────────────────────────────────────────

def build_compliance_graph(use_checkpointer: bool = True) -> StateGraph:
    """Build and compile the LangGraph compliance workflow."""

    graph = StateGraph(ComplianceWorkflowState)

    # Add nodes (each is an agent)
    graph.add_node("scanner", scanner_node)
    graph.add_node("extractor", extractor_node)
    graph.add_node("impact_analyst", impact_analyst_node)
    graph.add_node("action_planner", action_planner_node)
    graph.add_node("validator", validator_node)

    # Entry point
    graph.set_entry_point("scanner")

    # Edges
    graph.add_conditional_edges(
        "scanner",
        route_after_scanner,
        {"extractor": "extractor", END: END},
    )
    graph.add_edge("extractor", "impact_analyst")
    graph.add_edge("impact_analyst", "action_planner")
    graph.add_edge("action_planner", "validator")
    graph.add_conditional_edges(
        "validator",
        route_after_validator,
        {"extractor": "extractor", END: END},
    )

    # Compile with PostgreSQL checkpointer for persistent state
    if use_checkpointer:
        try:
            conn = psycopg.connect(settings.database_url, autocommit=True)
            checkpointer = PostgresSaver(conn)
            checkpointer.setup()
            return graph.compile(checkpointer=checkpointer)
        except Exception as e:
            logger.warning("checkpointer_init_failed", error=str(e))

    return graph.compile()


# ─── Public API ───────────────────────────────────────────────────────────────

class ComplianceOrchestrator:
    """
    High-level interface for running the compliance workflow.
    Wraps LangGraph with thread management and result extraction.
    """

    def __init__(self):
        self._graph = build_compliance_graph()

    def process_document(
        self,
        document_id: str,
        raw_text: str,
        source_url: str,
        jurisdiction: str,
        regulatory_body: str,
        document_type: str,
        published_date: str,
        thread_id: str | None = None,
    ) -> ComplianceWorkflowState:
        """
        Process a regulatory document through the full 5-agent pipeline.
        Returns the final state with action items and validation results.
        """
        initial_state = ComplianceWorkflowState(
            document_id=document_id,
            raw_text=raw_text,
            source_url=source_url,
            jurisdiction=jurisdiction,
            regulatory_body=regulatory_body,
            document_type=document_type,
            published_date=published_date,
        )

        config = {"configurable": {"thread_id": thread_id or document_id}}

        logger.info("workflow_start", document_id=document_id, thread_id=config["configurable"]["thread_id"])

        final_state = self._graph.invoke(initial_state, config=config)

        state = ComplianceWorkflowState(**final_state) if isinstance(final_state, dict) else final_state

        logger.info(
            "workflow_complete",
            document_id=document_id,
            is_relevant=state.is_relevant,
            obligations=len(state.obligations),
            action_items=len(state.action_items),
            valid=state.validation.valid if state.validation else None,
        )

        return state

    def get_graph_diagram(self) -> str:
        """Returns ASCII diagram of the graph for debugging."""
        return self._graph.get_graph().draw_ascii()
