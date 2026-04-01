"""
Compliance Control Registry.

Central registry for managing an organization's compliance controls:
- Register controls mapped to frameworks (GDPR, HIPAA, SOC2, etc.)
- Link controls to specific regulatory obligations
- Calculate coverage scores and gap analysis
- Framework-level summary reporting
"""
import structlog
from dataclasses import dataclass, field
from typing import Optional

from knowledge.graph.neo4j_client import Neo4jClient
from org_context.models.database import (
    create_control,
    get_control,
    list_controls,
    update_control_coverage,
    list_action_items,
)
from org_context.models.schemas import ComplianceControl, ComplianceFramework

logger = structlog.get_logger()


@dataclass
class CoverageGap:
    control_id: str
    control_name: str
    framework: str
    coverage_score: float
    owner_email: str
    gap_pct: float          # 1.0 - coverage_score


@dataclass
class FrameworkSummary:
    framework: str
    total_controls: int
    avg_coverage: float
    fully_covered: int      # coverage >= 0.8
    gaps: int               # coverage < 0.8
    automated_count: int


class ControlRegistry:
    """
    Single source of truth for the organization's compliance control landscape.

    Usage:
        registry = ControlRegistry()
        registry.register_control(control_id="CTL-001", name="...", framework="GDPR", ...)
        registry.link_to_obligation("CTL-001", "OBL-abc123", coverage_pct=0.85)
        gaps = registry.get_gaps(threshold=0.8)
        summary = registry.get_framework_summary("GDPR")
    """

    def __init__(self):
        self._neo4j = Neo4jClient()

    # ─── Registration ────────────────────────────────────────────────────────

    def register_control(
        self,
        control_id: str,
        name: str,
        description: str,
        framework: str,
        owner_email: str = "",
        owner_unit_id: Optional[str] = None,
        is_automated: bool = False,
        evidence_location: str = "",
        coverage_score: float = 0.0,
    ) -> ComplianceControl:
        """
        Register a compliance control in both PostgreSQL and Neo4j KG.
        Idempotent — returns existing control if already registered.
        """
        existing = get_control(control_id)
        if existing:
            logger.info("control_already_registered", control_id=control_id)
            return existing

        # Normalize framework string
        try:
            fw = ComplianceFramework(framework.upper())
        except ValueError:
            fw = ComplianceFramework.CUSTOM

        # Persist to Supabase PostgreSQL
        control = create_control(
            control_id=control_id,
            name=name,
            description=description,
            framework=fw,
            owner_email=owner_email,
            owner_unit_id=owner_unit_id,
            coverage_score=coverage_score,
            is_automated=is_automated,
            evidence_location=evidence_location,
        )

        # Persist to Neo4j Knowledge Graph for graph traversal
        self._neo4j.upsert_control({
            "id": control_id,
            "name": name,
            "description": description,
            "framework": framework,
            "owner": owner_email,
            "coverage_score": coverage_score,
        })

        logger.info("control_registered", control_id=control_id, framework=framework)
        return control

    # ─── Linking ─────────────────────────────────────────────────────────────

    def link_to_obligation(
        self,
        control_id: str,
        obligation_id: str,
        coverage_pct: float,
    ) -> None:
        """
        Link a control to a regulatory obligation with a coverage percentage.
        Also updates the control's overall coverage_score as the average
        across all its obligation links.
        """
        # Link in Neo4j
        self._neo4j.link_control_to_obligation(control_id, obligation_id, coverage_pct)

        # Recalculate and persist average coverage for this control
        avg_coverage = self._compute_avg_coverage(control_id)
        update_control_coverage(control_id, avg_coverage)

        logger.info(
            "control_linked_to_obligation",
            control_id=control_id,
            obligation_id=obligation_id,
            coverage_pct=coverage_pct,
            new_avg_coverage=avg_coverage,
        )

    def _compute_avg_coverage(self, control_id: str) -> float:
        """Query Neo4j for all obligation links and return average coverage."""
        query = """
        MATCH (c:ComplianceControl {id: $control_id})-[r:ADDRESSES]->(o:Obligation)
        RETURN avg(r.coverage_pct) AS avg_cov
        """
        result = self._neo4j.run_cypher(query, {"control_id": control_id})
        if result and result[0].get("avg_cov") is not None:
            return round(result[0]["avg_cov"] / 100.0, 4)  # normalize to 0-1
        return 0.0

    # ─── Gap Analysis ────────────────────────────────────────────────────────

    def get_gaps(self, threshold: float = 0.8) -> list[CoverageGap]:
        """
        Return all controls with coverage_score below threshold.
        Sorted by gap descending (worst first).
        """
        controls = list_controls()
        gaps = []
        for c in controls:
            if c.coverage_score < threshold:
                gaps.append(CoverageGap(
                    control_id=c.control_id,
                    control_name=c.name,
                    framework=c.framework.value if c.framework else "CUSTOM",
                    coverage_score=c.coverage_score,
                    owner_email=c.owner_email or "",
                    gap_pct=round(threshold - c.coverage_score, 4),
                ))
        gaps.sort(key=lambda g: g.gap_pct, reverse=True)
        return gaps

    def get_obligation_gaps(self) -> list[dict]:
        """
        Query Neo4j for obligations with no or low-coverage controls.
        Returns top 20 uncovered obligations.
        """
        query = """
        MATCH (o:Obligation)
        OPTIONAL MATCH (c:ComplianceControl)-[r:ADDRESSES]->(o)
        WITH o, avg(r.coverage_pct) AS avg_coverage
        WHERE avg_coverage IS NULL OR avg_coverage < 80
        RETURN o.id AS obligation_id,
               o.what AS requirement,
               o.regulation_id AS regulation_id,
               coalesce(avg_coverage, 0.0) AS coverage_pct
        ORDER BY coverage_pct ASC
        LIMIT 20
        """
        return self._neo4j.run_cypher(query)

    # ─── Coverage Queries ────────────────────────────────────────────────────

    def get_control_obligations(self, control_id: str) -> list[dict]:
        """Return all obligations this control addresses, with coverage %."""
        query = """
        MATCH (c:ComplianceControl {id: $control_id})-[r:ADDRESSES]->(o:Obligation)
        RETURN o.id AS obligation_id,
               o.what AS requirement,
               r.coverage_pct AS coverage_pct
        ORDER BY r.coverage_pct DESC
        """
        return self._neo4j.run_cypher(query, {"control_id": control_id})

    def get_controls_for_obligation(self, obligation_id: str) -> list[dict]:
        """Return all controls covering a given obligation."""
        query = """
        MATCH (c:ComplianceControl)-[r:ADDRESSES]->(o:Obligation {id: $obligation_id})
        RETURN c.id AS control_id,
               c.name AS control_name,
               c.framework AS framework,
               r.coverage_pct AS coverage_pct
        ORDER BY r.coverage_pct DESC
        """
        return self._neo4j.run_cypher(query, {"obligation_id": obligation_id})

    # ─── Reporting ───────────────────────────────────────────────────────────

    def get_framework_summary(self, framework: Optional[str] = None) -> list[FrameworkSummary]:
        """
        Return coverage summary per framework.
        If framework is given, returns a single-item list for that framework.
        """
        frameworks_to_check = (
            [framework] if framework
            else [fw.value for fw in ComplianceFramework]
        )

        summaries = []
        for fw in frameworks_to_check:
            controls = list_controls(framework=fw)
            if not controls:
                continue
            avg_cov = sum(c.coverage_score for c in controls) / len(controls)
            summaries.append(FrameworkSummary(
                framework=fw,
                total_controls=len(controls),
                avg_coverage=round(avg_cov, 4),
                fully_covered=sum(1 for c in controls if c.coverage_score >= 0.8),
                gaps=sum(1 for c in controls if c.coverage_score < 0.8),
                automated_count=sum(1 for c in controls if c.is_automated),
            ))

        summaries.sort(key=lambda s: s.avg_coverage)
        return summaries

    def get_open_action_items(
        self,
        priority: Optional[str] = None,
        owner: Optional[str] = None,
        limit: int = 50,
    ) -> list:
        """Fetch open action items from PostgreSQL."""
        return list_action_items(
            priority=priority,
            status="open",
            owner=owner,
            limit=limit,
        )

    def get_registry_health(self) -> dict:
        """
        Returns a high-level health snapshot of the org's compliance posture.
        """
        all_controls = list_controls()
        if not all_controls:
            return {"status": "no_controls", "total": 0}

        total = len(all_controls)
        avg_coverage = sum(c.coverage_score for c in all_controls) / total
        gaps = [c for c in all_controls if c.coverage_score < 0.8]
        critical_gaps = [c for c in gaps if c.coverage_score < 0.3]
        automated = [c for c in all_controls if c.is_automated]

        return {
            "total_controls": total,
            "avg_coverage_score": round(avg_coverage, 4),
            "controls_with_gaps": len(gaps),
            "critical_gaps": len(critical_gaps),
            "automated_controls": len(automated),
            "automation_rate": round(len(automated) / total, 4),
            "overall_posture": (
                "HEALTHY" if avg_coverage >= 0.8 else
                "AT_RISK" if avg_coverage >= 0.5 else
                "CRITICAL"
            ),
        }
