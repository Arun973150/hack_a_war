"""
Agent 4 — Action Plan Generator
Model: Gemini 2.0 Flash
Role: Translate impact analysis into concrete, prioritized action items
      with deadlines, owners, effort estimates, and risk scores.
"""
import uuid
import structlog
import vertexai
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from agents.state import ActionItem, ComplianceWorkflowState, Priority
from config import settings

logger = structlog.get_logger()

vertexai.init(project=settings.vertex_project, location=settings.vertex_location)

ACTION_PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a compliance program manager and security response lead generating a prioritized action plan.

Convert compliance gaps AND security vulnerability obligations into actionable tasks.
Each action item must:
- Have a specific, measurable title
- Be assigned to the correct team/role
- Have a realistic deadline — for security CVEs use the regulatory deadline from the advisory
- Have effort estimate and risk score

For security advisory tasks specifically:
- Title must reference the CVE ID (e.g. "Patch CVE-2024-XXXX — Encryption Weakness")
- Description must include: what the vulnerability is, which compliance obligation it triggers, specific regulatory deadline
- Owner must be Security Engineering or DevSecOps for CVE tasks
- Deadline must match the regulatory requirement (e.g. "48 hours — RBI PA Guidelines Annex 2")

Return JSON:
{{
  "action_items": [
    {{
      "action_id": "ACT-xxx",
      "title": "specific action title",
      "description": "2-3 sentence description including regulation citation and specific deadline",
      "owner": "team or role responsible",
      "deadline": "YYYY-MM-DD or deadline like '48 hours — RBI PA Guidelines Annex 2'",
      "priority": "CRITICAL|HIGH|MEDIUM|LOW",
      "effort_days": estimated working days,
      "compliance_risk_score": 1-10,
      "source_obligation_ids": ["OBL-xxx or CVE-2024-xxx"],
      "source_clauses": ["Article 13", "RBI Annex 2", "PCI-DSS Req 6.3"]
    }}
  ]
}}

Priority rules:
- CRITICAL: CISA KEV (actively exploited) or fines > $1M or criminal liability or CVSS ≥ 9.0
- HIGH: CVSS ≥ 7.0 or significant fines or regulatory audit finding expected
- MEDIUM: Operational compliance risk
- LOW: Best practice / documentation
"""),
    ("human", """REGULATION: {regulation_id} ({jurisdiction})
REGULATORY BODY: {regulatory_body}
IMPACT SUMMARY: {impact_summary}
OVERALL RISK SCORE: {overall_risk_score}/10
AFFECTED BUSINESS UNITS: {affected_business_units}

COMPLIANCE GAPS:
{gaps}

OBLIGATIONS:
{obligations}

ACTIVE SECURITY ADVISORIES REQUIRING COMPLIANCE ACTION:
{security_advisories}

Generate a complete action plan covering BOTH regulatory compliance gaps AND security vulnerability remediation.
Security tasks must include the specific regulatory deadline from the advisory."""),
])


class ActionPlannerAgent:
    """Agent 4: Action plan generation using Gemini 2.0 Flash."""

    def __init__(self):
        self._llm = ChatVertexAI(
            model_name=settings.gemini_flash_model,
            project=settings.vertex_project,
            location=settings.vertex_location,
            temperature=0.2,
            max_output_tokens=4096,
        )
        self._parser = JsonOutputParser()
        self._chain = ACTION_PLANNER_PROMPT | self._llm | self._parser

    def run(self, state: ComplianceWorkflowState) -> ComplianceWorkflowState:
        logger.info("action_planner_start", document_id=state.document_id)

        try:
            gaps_text = "\n".join([
                f"Gap [{g.obligation_id}]: {g.gap_description} "
                f"(coverage: {g.coverage_pct:.0f}%, risk: {g.risk_score}/10, "
                f"controls: {', '.join(g.existing_controls) or 'none'})"
                for g in state.gaps
            ])

            obligations_text = "\n".join([
                f"[{o.obligation_id}] {o.what} | Deadline: {o.deadline or 'TBD'} "
                f"| Clause: {o.source_clause or 'N/A'}"
                for o in state.obligations
            ])

            # Format security advisories for the prompt
            security_text = self._format_security_advisories(state)

            result = self._chain.invoke({
                "regulation_id": state.document_id,
                "jurisdiction": state.jurisdiction,
                "regulatory_body": state.regulatory_body,
                "impact_summary": state.impact_summary,
                "overall_risk_score": state.overall_risk_score,
                "affected_business_units": ", ".join(state.affected_business_units),
                "gaps": gaps_text or "No specific gaps identified — full compliance review recommended.",
                "obligations": obligations_text,
                "security_advisories": security_text,
            })

            action_items = []
            for item_dict in result.get("action_items", []):
                if not item_dict.get("action_id"):
                    item_dict["action_id"] = f"ACT-{uuid.uuid4().hex[:8].upper()}"
                if not item_dict.get("source_obligation_ids"):
                    item_dict["source_obligation_ids"] = []
                if not item_dict.get("source_clauses"):
                    item_dict["source_clauses"] = []
                action_items.append(ActionItem(**item_dict))

            # Sort by risk score descending
            state.action_items = sorted(
                action_items, key=lambda x: x.compliance_risk_score, reverse=True
            )

            logger.info(
                "action_planner_done",
                document_id=state.document_id,
                action_count=len(state.action_items),
            )

        except Exception as e:
            logger.error("action_planner_failed", error=str(e))
            state.error = f"Action planning failed: {str(e)}"

        return state


    def _format_security_advisories(self, state: ComplianceWorkflowState) -> str:
        advisories = getattr(state, "security_advisories", [])
        if not advisories:
            return "No active security advisories fetched for this sector."

        lines = []
        for adv in advisories[:5]:
            is_dict = isinstance(adv, dict)
            cve_id = adv.get("cve_id") if is_dict else adv.cve_id
            cvss = adv.get("cvss_score") if is_dict else adv.cvss_score
            category = adv.get("category") if is_dict else adv.category
            desc = adv.get("description") if is_dict else adv.description
            impacts = adv.get("compliance_impact", []) if is_dict else adv.compliance_impact
            is_kev = adv.get("is_kev", False) if is_dict else adv.is_kev

            kev_label = " ⚠️ CISA KNOWN EXPLOITED" if is_kev else ""
            lines.append(f"[{cve_id}] CVSS {cvss} — {category}{kev_label}")
            lines.append(f"  {desc[:200]}")
            for imp in impacts[:2]:
                lines.append(
                    f"  → {imp.get('name', '')} ({imp.get('regulator', '')}): "
                    f"{imp.get('requirement', '')[:120]} [Deadline: {imp.get('deadline_hours', '?')}h]"
                )
            lines.append("")
        return "\n".join(lines)


def action_planner_node(state: ComplianceWorkflowState) -> ComplianceWorkflowState:
    """LangGraph node wrapper for the Action Planner Agent."""
    agent = ActionPlannerAgent()
    return agent.run(state)
