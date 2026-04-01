from fastapi import APIRouter
from typing import Optional
import structlog

from knowledge.graph.neo4j_client import Neo4jClient
from org_context.models.database import (
    list_controls,
    list_action_items,
    list_regulation_tracking,
    list_cve_alerts,
)

logger = structlog.get_logger()
router = APIRouter()


def _calculate_compliance_score() -> dict:
    """
    Calculate an overall compliance health score (0-100) with breakdown.

    Formula:
        score = (control_coverage_pct * 0.4)
              + (action_completion_pct * 0.25)
              + (regulation_coverage_pct * 0.2)
              + (cve_resolved_pct * 0.15)
    """
    # ── Control coverage from Neo4j ──────────────────────────────────────
    control_coverage_pct = 0.0
    framework_breakdown = {}
    try:
        neo4j = Neo4jClient()
        rows = neo4j.run_cypher(
            """
            MATCH (c:ComplianceControl)
            RETURN c.framework AS framework,
                   avg(c.coverage_score) AS avg_coverage,
                   count(c) AS cnt
            """
        )
        total_controls = 0
        weighted_sum = 0.0
        for row in rows:
            fw = row.get("framework") or "Unknown"
            avg_cov = float(row.get("avg_coverage") or 0)
            cnt = int(row.get("cnt") or 0)
            framework_breakdown[fw] = {
                "avg_coverage": round(avg_cov * 100, 1),
                "control_count": cnt,
            }
            weighted_sum += avg_cov * cnt
            total_controls += cnt
        if total_controls > 0:
            control_coverage_pct = (weighted_sum / total_controls) * 100
    except Exception as e:
        logger.error("compliance_score_neo4j_failed", error=str(e))

    # ── Action items from PostgreSQL ─────────────────────────────────────
    action_completion_pct = 0.0
    open_actions = 0
    completed_actions = 0
    total_actions = 0
    try:
        all_actions = list_action_items(limit=10000)
        total_actions = len(all_actions)
        completed_actions = sum(
            1 for a in all_actions if (a.status or "").lower() in ("completed", "waived")
        )
        open_actions = total_actions - completed_actions
        if total_actions > 0:
            action_completion_pct = (completed_actions / total_actions) * 100
    except Exception as e:
        logger.error("compliance_score_actions_failed", error=str(e))

    # ── Regulation tracking from PostgreSQL ──────────────────────────────
    regulation_coverage_pct = 0.0
    total_regulations = 0
    relevant_regulations = 0
    avg_risk_score = 0.0
    try:
        all_regs = list_regulation_tracking(limit=10000)
        total_regulations = len(all_regs)
        relevant_regulations = sum(1 for r in all_regs if r.is_relevant)
        risk_scores = [r.overall_risk_score for r in all_regs if r.overall_risk_score is not None]
        if risk_scores:
            avg_risk_score = sum(risk_scores) / len(risk_scores)
        # Regulation coverage = percentage of relevant regulations that have been processed
        processed = sum(
            1 for r in all_regs
            if r.is_relevant and (r.processing_status or "").lower() == "processed"
        )
        if relevant_regulations > 0:
            regulation_coverage_pct = (processed / relevant_regulations) * 100
    except Exception as e:
        logger.error("compliance_score_regulations_failed", error=str(e))

    # ── CVE alerts from PostgreSQL ───────────────────────────────────────
    cve_resolved_pct = 0.0
    total_cves = 0
    unresolved_cves = 0
    try:
        all_cves = list_cve_alerts(limit=10000)
        total_cves = len(all_cves)
        # Unresolved = no jira_key assigned and still active
        unresolved_cves = sum(1 for c in all_cves if not c.jira_key)
        resolved_cves = total_cves - unresolved_cves
        if total_cves > 0:
            cve_resolved_pct = (resolved_cves / total_cves) * 100
        else:
            # No CVEs means no vulnerability exposure — full score
            cve_resolved_pct = 100.0
    except Exception as e:
        logger.error("compliance_score_cves_failed", error=str(e))

    # ── Final score ──────────────────────────────────────────────────────
    score = (
        (control_coverage_pct * 0.4)
        + (action_completion_pct * 0.25)
        + (regulation_coverage_pct * 0.2)
        + (cve_resolved_pct * 0.15)
    )
    score = round(min(max(score, 0), 100), 1)

    if score < 40:
        risk_level = "CRITICAL"
    elif score < 60:
        risk_level = "HIGH"
    elif score < 80:
        risk_level = "MEDIUM"
    else:
        risk_level = "GOOD"

    return {
        "score": score,
        "risk_level": risk_level,
        "breakdown": {
            "control_coverage": {
                "pct": round(control_coverage_pct, 1),
                "weight": 0.4,
                "weighted_score": round(control_coverage_pct * 0.4, 1),
            },
            "action_completion": {
                "pct": round(action_completion_pct, 1),
                "weight": 0.25,
                "weighted_score": round(action_completion_pct * 0.25, 1),
                "open": open_actions,
                "completed": completed_actions,
                "total": total_actions,
            },
            "regulation_coverage": {
                "pct": round(regulation_coverage_pct, 1),
                "weight": 0.2,
                "weighted_score": round(regulation_coverage_pct * 0.2, 1),
                "total_regulations": total_regulations,
                "relevant_regulations": relevant_regulations,
                "avg_risk_score": round(avg_risk_score, 1),
            },
            "cve_resolved": {
                "pct": round(cve_resolved_pct, 1),
                "weight": 0.15,
                "weighted_score": round(cve_resolved_pct * 0.15, 1),
                "total_cves": total_cves,
                "unresolved_cves": unresolved_cves,
            },
        },
        "framework_breakdown": framework_breakdown,
    }


@router.get("/")
async def get_compliance_score():
    """Return overall compliance score (0-100) with breakdown by framework, jurisdiction, and risk areas."""
    try:
        result = _calculate_compliance_score()
        return result
    except Exception as e:
        logger.error("compliance_score_failed", error=str(e))
        return {
            "score": 0,
            "risk_level": "CRITICAL",
            "breakdown": {},
            "framework_breakdown": {},
            "error": str(e),
        }


@router.get("/summary")
async def get_compliance_summary():
    """Executive summary with key compliance stats."""
    try:
        score_data = _calculate_compliance_score()
        breakdown = score_data.get("breakdown", {})

        # Build concise executive summary
        summary_parts = []
        summary_parts.append(
            f"Overall compliance score: {score_data['score']}/100 ({score_data['risk_level']})."
        )

        action_info = breakdown.get("action_completion", {})
        if action_info.get("total", 0) > 0:
            summary_parts.append(
                f"{action_info['open']} open action items out of {action_info['total']} total "
                f"({action_info['pct']}% completion rate)."
            )

        reg_info = breakdown.get("regulation_coverage", {})
        if reg_info.get("total_regulations", 0) > 0:
            summary_parts.append(
                f"Tracking {reg_info['total_regulations']} regulations, "
                f"{reg_info['relevant_regulations']} relevant. "
                f"Avg risk score: {reg_info['avg_risk_score']}."
            )

        cve_info = breakdown.get("cve_resolved", {})
        if cve_info.get("total_cves", 0) > 0:
            summary_parts.append(
                f"{cve_info['unresolved_cves']} unresolved CVEs out of {cve_info['total_cves']}."
            )

        frameworks = list(score_data.get("framework_breakdown", {}).keys())

        return {
            "score": score_data["score"],
            "risk_level": score_data["risk_level"],
            "summary": " ".join(summary_parts),
            "frameworks_covered": frameworks,
            "key_metrics": {
                "open_action_items": action_info.get("open", 0),
                "total_regulations": reg_info.get("total_regulations", 0),
                "unresolved_cves": cve_info.get("unresolved_cves", 0),
                "control_coverage_pct": breakdown.get("control_coverage", {}).get("pct", 0),
            },
        }
    except Exception as e:
        logger.error("compliance_summary_failed", error=str(e))
        return {
            "score": 0,
            "risk_level": "CRITICAL",
            "summary": "Unable to generate compliance summary.",
            "frameworks_covered": [],
            "key_metrics": {},
            "error": str(e),
        }
