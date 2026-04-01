"""
CRUD layer for org_context SQLAlchemy models.
All operations use the Supabase PostgreSQL engine from storage/db.py.
"""
import uuid
import structlog
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from storage.db import get_engine, get_session
from org_context.models.schemas import (
    Base,
    OrganizationUnit,
    ComplianceControl,
    RegulationTracking,
    ActionItem,
    AuditFinding,
    ComplianceFramework,
    RiskLevel,
    TechStackPackage,
    CveAlert,
    RegulationSnapshot,
)

logger = structlog.get_logger()


def create_tables():
    """Create all org_context tables in Supabase PostgreSQL."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("org_context_tables_created")


# ─── OrganizationUnit CRUD ───────────────────────────────────────────────────

def create_org_unit(
    name: str,
    description: str = "",
    owner_email: str = "",
    jurisdictions: list[str] | None = None,
    parent_id: str | None = None,
    session: Session | None = None,
) -> OrganizationUnit:
    db = session or get_session()
    try:
        unit = OrganizationUnit(
            name=name,
            description=description,
            owner_email=owner_email,
            jurisdictions=jurisdictions or [],
            parent_id=uuid.UUID(parent_id) if parent_id else None,
        )
        db.add(unit)
        db.commit()
        db.refresh(unit)
        logger.info("org_unit_created", name=name, id=str(unit.id))
        return unit
    finally:
        if not session:
            db.close()


def get_org_unit(unit_id: str, session: Session | None = None) -> OrganizationUnit | None:
    db = session or get_session()
    try:
        return db.query(OrganizationUnit).filter(
            OrganizationUnit.id == uuid.UUID(unit_id)
        ).first()
    finally:
        if not session:
            db.close()


def list_org_units(session: Session | None = None) -> list[OrganizationUnit]:
    db = session or get_session()
    try:
        return db.query(OrganizationUnit).all()
    finally:
        if not session:
            db.close()


# ─── ComplianceControl CRUD ──────────────────────────────────────────────────

def create_control(
    control_id: str,
    name: str,
    description: str,
    framework: ComplianceFramework,
    owner_email: str = "",
    owner_unit_id: str | None = None,
    coverage_score: float = 0.0,
    is_automated: bool = False,
    evidence_location: str = "",
    session: Session | None = None,
) -> ComplianceControl:
    db = session or get_session()
    try:
        control = ComplianceControl(
            control_id=control_id,
            name=name,
            description=description,
            framework=framework,
            owner_email=owner_email,
            owner_unit_id=uuid.UUID(owner_unit_id) if owner_unit_id else None,
            coverage_score=coverage_score,
            is_automated=is_automated,
            evidence_location=evidence_location,
        )
        db.add(control)
        db.commit()
        db.refresh(control)
        logger.info("control_created", control_id=control_id)
        return control
    finally:
        if not session:
            db.close()


def get_control(control_id: str, session: Session | None = None) -> ComplianceControl | None:
    """Lookup by string control_id (e.g. 'CTL-001'), not UUID."""
    db = session or get_session()
    try:
        return db.query(ComplianceControl).filter(
            ComplianceControl.control_id == control_id
        ).first()
    finally:
        if not session:
            db.close()


def list_controls(
    framework: str | None = None,
    session: Session | None = None,
) -> list[ComplianceControl]:
    db = session or get_session()
    try:
        q = db.query(ComplianceControl)
        if framework:
            q = q.filter(ComplianceControl.framework == framework)
        return q.order_by(ComplianceControl.control_id).all()
    finally:
        if not session:
            db.close()


def update_control_coverage(
    control_id: str,
    coverage_score: float,
    session: Session | None = None,
) -> bool:
    db = session or get_session()
    try:
        rows = db.query(ComplianceControl).filter(
            ComplianceControl.control_id == control_id
        ).update({
            "coverage_score": coverage_score,
            "updated_at": datetime.utcnow(),
        })
        db.commit()
        return rows > 0
    finally:
        if not session:
            db.close()


# ─── RegulationTracking CRUD ─────────────────────────────────────────────────

def upsert_regulation_tracking(
    source_id: str,
    title: str,
    jurisdiction: str,
    regulatory_body: str,
    document_type: str,
    published_date: str,
    source_url: str,
    is_relevant: bool = False,
    relevance_score: float = 0.0,
    overall_risk_score: int = 0,
    impact_summary: str = "",
    processing_status: str = "pending",
    session: Session | None = None,
) -> RegulationTracking:
    db = session or get_session()
    try:
        existing = db.query(RegulationTracking).filter(
            RegulationTracking.source_id == source_id
        ).first()

        if existing:
            existing.is_relevant = is_relevant
            existing.relevance_score = relevance_score
            existing.overall_risk_score = overall_risk_score
            existing.impact_summary = impact_summary
            existing.processing_status = processing_status
            existing.processed_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing

        reg = RegulationTracking(
            source_id=source_id,
            title=title,
            jurisdiction=jurisdiction,
            regulatory_body=regulatory_body,
            document_type=document_type,
            published_date=datetime.fromisoformat(published_date) if published_date else None,
            source_url=source_url,
            is_relevant=is_relevant,
            relevance_score=relevance_score,
            overall_risk_score=overall_risk_score,
            impact_summary=impact_summary,
            processing_status=processing_status,
        )
        db.add(reg)
        db.commit()
        db.refresh(reg)
        logger.info("regulation_tracking_upserted", source_id=source_id)
        return reg
    finally:
        if not session:
            db.close()


def list_regulation_tracking(
    jurisdiction: str | None = None,
    is_relevant: bool | None = None,
    limit: int = 50,
    session: Session | None = None,
) -> list[RegulationTracking]:
    db = session or get_session()
    try:
        q = db.query(RegulationTracking)
        if jurisdiction:
            q = q.filter(RegulationTracking.jurisdiction == jurisdiction)
        if is_relevant is not None:
            q = q.filter(RegulationTracking.is_relevant == is_relevant)
        return q.order_by(RegulationTracking.created_at.desc()).limit(limit).all()
    finally:
        if not session:
            db.close()


# ─── ActionItem CRUD ─────────────────────────────────────────────────────────

def create_action_item(
    action_id: str,
    title: str,
    description: str,
    owner: str,
    deadline: str,
    priority: str,
    effort_days: int,
    compliance_risk_score: int,
    source_obligation_ids: list[str],
    source_clauses: list[str],
    regulation_db_id: str | None = None,
    session: Session | None = None,
) -> ActionItem:
    db = session or get_session()
    try:
        item = ActionItem(
            action_id=action_id,
            regulation_id=uuid.UUID(regulation_db_id) if regulation_db_id else None,
            title=title,
            description=description,
            owner=owner,
            deadline=deadline,
            priority=priority,
            effort_days=effort_days,
            compliance_risk_score=compliance_risk_score,
            source_obligation_ids=source_obligation_ids,
            source_clauses=source_clauses,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        logger.info("action_item_created", action_id=action_id)
        return item
    finally:
        if not session:
            db.close()


def list_action_items(
    priority: str | None = None,
    status: str | None = None,
    owner: str | None = None,
    limit: int = 50,
    session: Session | None = None,
) -> list[ActionItem]:
    db = session or get_session()
    try:
        q = db.query(ActionItem)
        if priority:
            q = q.filter(ActionItem.priority == priority.upper())
        if status:
            q = q.filter(ActionItem.status == status)
        if owner:
            q = q.filter(ActionItem.owner.ilike(f"%{owner}%"))
        return q.order_by(ActionItem.compliance_risk_score.desc()).limit(limit).all()
    finally:
        if not session:
            db.close()


def update_action_status(
    action_id: str,
    status: str,
    session: Session | None = None,
) -> bool:
    db = session or get_session()
    try:
        rows = db.query(ActionItem).filter(
            ActionItem.action_id == action_id
        ).update({
            "status": status,
            "updated_at": datetime.utcnow(),
        })
        db.commit()
        return rows > 0
    finally:
        if not session:
            db.close()


def update_action_jira_ticket(
    action_id: str,
    jira_ticket_id: str,
    session: Session | None = None,
) -> bool:
    db = session or get_session()
    try:
        rows = db.query(ActionItem).filter(
            ActionItem.action_id == action_id
        ).update({
            "jira_ticket_id": jira_ticket_id,
            "updated_at": datetime.utcnow(),
        })
        db.commit()
        return rows > 0
    finally:
        if not session:
            db.close()


# ─── AuditFinding CRUD ───────────────────────────────────────────────────────

def create_audit_finding(
    control_uuid: str,
    severity: RiskLevel,
    description: str,
    remediation: str,
    session: Session | None = None,
) -> AuditFinding:
    db = session or get_session()
    try:
        finding = AuditFinding(
            control_id=uuid.UUID(control_uuid),
            severity=severity,
            description=description,
            remediation=remediation,
        )
        db.add(finding)
        db.commit()
        db.refresh(finding)
        logger.info("audit_finding_created", control_id=control_uuid, severity=severity)
        return finding
    finally:
        if not session:
            db.close()


def list_audit_findings(
    control_id: str | None = None,
    severity: str | None = None,
    unresolved_only: bool = False,
    session: Session | None = None,
) -> list[AuditFinding]:
    db = session or get_session()
    try:
        q = db.query(AuditFinding)
        if control_id:
            q = q.filter(AuditFinding.control_id == uuid.UUID(control_id))
        if severity:
            q = q.filter(AuditFinding.severity == severity)
        if unresolved_only:
            q = q.filter(AuditFinding.resolved_at.is_(None))
        return q.order_by(AuditFinding.finding_date.desc()).all()
    finally:
        if not session:
            db.close()


# ─── TechStackPackage CRUD ────────────────────────────────────────────────────

def upsert_tech_stack_packages(
    packages: list[dict],
    source_file: str = "",
    session=None,
) -> list[TechStackPackage]:
    """
    Register packages for proactive CVE monitoring.
    Each dict must have: name, version, ecosystem.
    Silently skips duplicates (unique on ecosystem+name+version).
    """
    db = session or get_session()
    added = []
    try:
        for pkg in packages:
            name = pkg.get("name", "").strip()
            version = pkg.get("version", "").strip()
            ecosystem = pkg.get("ecosystem", "PyPI").strip()
            if not name:
                continue

            existing = db.query(TechStackPackage).filter(
                TechStackPackage.ecosystem == ecosystem,
                TechStackPackage.package_name == name,
                TechStackPackage.version == version,
            ).first()

            if existing:
                continue

            row = TechStackPackage(
                ecosystem=ecosystem,
                package_name=name,
                version=version,
                source_file=source_file,
            )
            db.add(row)
            added.append(row)

        db.commit()
        logger.info("tech_stack_packages_upserted", count=len(added), source=source_file)
        return added
    finally:
        if not session:
            db.close()


def list_tech_stack_packages(ecosystem: str | None = None, session=None) -> list[TechStackPackage]:
    db = session or get_session()
    try:
        q = db.query(TechStackPackage)
        if ecosystem:
            q = q.filter(TechStackPackage.ecosystem == ecosystem)
        return q.order_by(TechStackPackage.ecosystem, TechStackPackage.package_name).all()
    finally:
        if not session:
            db.close()


def delete_tech_stack_packages(session=None) -> int:
    """Clear all registered packages (for re-upload scenario)."""
    db = session or get_session()
    try:
        count = db.query(TechStackPackage).count()
        db.query(TechStackPackage).delete()
        db.commit()
        return count
    finally:
        if not session:
            db.close()


# ─── CveAlert CRUD ────────────────────────────────────────────────────────────

def upsert_cve_alert(
    cve_id: str,
    cvss_score: float,
    severity: str,
    category: str,
    description: str,
    affected_packages: list,
    compliance_impact: list,
    blast_radius: dict,
    remediation_steps: list,
    is_kev: bool = False,
    session=None,
) -> tuple[CveAlert, bool]:
    """
    Insert or update a CVE alert. Returns (alert, is_new).
    is_new=True means this CVE was not previously seen — triggers notifications.
    """
    db = session or get_session()
    try:
        existing = db.query(CveAlert).filter(CveAlert.cve_id == cve_id).first()
        if existing:
            existing.cvss_score = cvss_score
            existing.severity = severity
            existing.last_updated = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing, False

        alert = CveAlert(
            cve_id=cve_id,
            cvss_score=cvss_score,
            severity=severity,
            category=category,
            description=description,
            affected_packages=affected_packages,
            compliance_impact=compliance_impact,
            blast_radius=blast_radius,
            remediation_steps=remediation_steps,
            is_kev=is_kev,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        logger.info("cve_alert_created", cve_id=cve_id, severity=severity)
        return alert, True
    finally:
        if not session:
            db.close()


def mark_cve_alert_notified(
    cve_id: str,
    slack_sent: bool = False,
    jira_key: str | None = None,
    session=None,
) -> bool:
    db = session or get_session()
    try:
        rows = db.query(CveAlert).filter(CveAlert.cve_id == cve_id).update({
            "slack_sent": slack_sent,
            "jira_key": jira_key,
            "last_updated": datetime.utcnow(),
        })
        db.commit()
        return rows > 0
    finally:
        if not session:
            db.close()


def list_cve_alerts(
    severity: str | None = None,
    unnotified_only: bool = False,
    limit: int = 50,
    session=None,
) -> list[CveAlert]:
    db = session or get_session()
    try:
        q = db.query(CveAlert)
        if severity:
            q = q.filter(CveAlert.severity == severity.upper())
        if unnotified_only:
            q = q.filter(CveAlert.slack_sent == False)  # noqa: E712
        return q.order_by(CveAlert.cvss_score.desc(), CveAlert.first_seen.desc()).limit(limit).all()
    finally:
        if not session:
            db.close()


# ─── RegulationSnapshot CRUD ──────────────────────────────────────────────────

def save_regulation_snapshot(
    source_id: str,
    version_hash: str,
    obligations_snapshot: list,
    jurisdiction: str = "",
    regulatory_body: str = "",
    title: str = "",
    published_date=None,
    session=None,
) -> RegulationSnapshot:
    """Store a new regulation snapshot. Called each time a regulation is processed."""
    db = session or get_session()
    try:
        snap = RegulationSnapshot(
            source_id=source_id,
            version_hash=version_hash,
            obligations_snapshot=obligations_snapshot,
            obligations_count=len(obligations_snapshot),
            jurisdiction=jurisdiction,
            regulatory_body=regulatory_body,
            title=title,
            published_date=published_date,
        )
        db.add(snap)
        db.commit()
        db.refresh(snap)
        logger.info("regulation_snapshot_saved", source_id=source_id, hash=version_hash[:8])
        return snap
    finally:
        if not session:
            db.close()


def get_regulation_snapshots(
    source_id: str,
    limit: int = 10,
    session=None,
) -> list[RegulationSnapshot]:
    """Get all snapshots for a regulation, newest first."""
    db = session or get_session()
    try:
        return (
            db.query(RegulationSnapshot)
            .filter(RegulationSnapshot.source_id == source_id)
            .order_by(RegulationSnapshot.created_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        if not session:
            db.close()


def list_all_snapshotted_sources(limit: int = 100, session=None) -> list[str]:
    """Return distinct source_ids that have at least one snapshot."""
    db = session or get_session()
    try:
        rows = (
            db.query(RegulationSnapshot.source_id)
            .distinct()
            .limit(limit)
            .all()
        )
        return [r[0] for r in rows]
    finally:
        if not session:
            db.close()
