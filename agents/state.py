from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Annotated, Any
from langgraph.graph.message import add_messages
from pydantic import BaseModel


class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ValidationStatus(str, Enum):
    PENDING = "PENDING"
    VALID = "VALID"
    INVALID = "INVALID"
    RETRY = "RETRY"


class Obligation(BaseModel):
    obligation_id: str
    text: str
    who_must_comply: str
    what: str
    deadline: str | None = None
    conditions: str | None = None
    penalty: str | None = None
    source_clause: str | None = None


class ImpactGap(BaseModel):
    obligation_id: str
    gap_description: str
    existing_controls: list[str]
    coverage_pct: float
    risk_score: int                  # 1-10


class ActionItem(BaseModel):
    action_id: str
    title: str
    description: str
    owner: str
    deadline: str
    priority: Priority
    effort_days: int
    compliance_risk_score: int       # 1-10
    source_obligation_ids: list[str]
    source_clauses: list[str]


class ValidationResult(BaseModel):
    valid: bool
    confidence: float
    issues: list[str]
    hallucinated_obligations: list[str]
    incorrect_deadlines: list[str]


class SecurityAdvisory(BaseModel):
    """A CVE or security advisory mapped to compliance obligations."""
    cve_id: str
    cvss_score: float
    severity: str                          # CRITICAL / HIGH / MEDIUM
    description: str
    category: str                          # e.g. "Encryption Weakness"
    cwes: list[str] = []
    compliance_controls: list[str] = []
    compliance_impact: list[dict] = []     # [{name, regulator, requirement, deadline_hours}]
    remediation_steps: list[str] = []
    priority: str = "HIGH"
    is_kev: bool = False                   # CISA Known Exploited Vulnerability


# ─── LangGraph Shared State ──────────────────────────────────────────────────

class ComplianceWorkflowState(BaseModel):
    """
    The single state object flowing through the LangGraph.
    Each agent reads from and writes to this state.
    """

    # Input
    document_id: str = ""
    raw_text: str = ""
    source_url: str = ""
    jurisdiction: str = ""
    regulatory_body: str = ""
    document_type: str = ""
    published_date: str = ""

    # Agent 1 — Scanner output
    is_relevant: bool = False
    relevance_score: float = 0.0
    sector: str = ""
    scan_reasoning: str = ""

    # Agent 2 — Extractor output
    obligations: list[Obligation] = field(default_factory=list)
    extraction_confidence: float = 0.0

    # Agent 3 — Impact Analyst output
    affected_business_units: list[str] = field(default_factory=list)
    gaps: list[ImpactGap] = field(default_factory=list)
    overall_risk_score: int = 0
    jurisdiction_conflicts: list[str] = field(default_factory=list)
    impact_summary: str = ""

    # Security context (fetched during impact analysis from NVD + CISA)
    security_advisories: list[SecurityAdvisory] = field(default_factory=list)

    # Agent 4 — Action Planner output
    action_items: list[ActionItem] = field(default_factory=list)

    # Agent 5 — Validator output
    validation: ValidationResult | None = None
    retry_count: int = 0
    max_retries: int = 3

    # Routing
    error: str | None = None

    class Config:
        arbitrary_types_allowed = True
