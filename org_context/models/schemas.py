from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, String, Float, Integer, Boolean,
    DateTime, Text, ARRAY, JSON, ForeignKey, Enum as SAEnum,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid


class Base(DeclarativeBase):
    pass


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ComplianceFramework(str, Enum):
    GDPR = "GDPR"
    SOC2 = "SOC2"
    ISO27001 = "ISO27001"
    PCI_DSS = "PCI_DSS"
    HIPAA = "HIPAA"
    EU_AI_ACT = "EU_AI_ACT"
    DORA = "DORA"
    SEBI = "SEBI"
    RBI = "RBI"
    CUSTOM = "CUSTOM"


class OrganizationUnit(Base):
    __tablename__ = "organization_units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("organization_units.id"), nullable=True)
    owner_email = Column(String(200))
    jurisdictions = Column(ARRAY(String))
    created_at = Column(DateTime, default=datetime.utcnow)

    controls = relationship("ComplianceControl", back_populates="owner_unit")


class ComplianceControl(Base):
    __tablename__ = "compliance_controls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    control_id = Column(String(50), unique=True, nullable=False)   # e.g. "CTL-001"
    name = Column(String(500), nullable=False)
    description = Column(Text)
    framework = Column(SAEnum(ComplianceFramework))
    owner_unit_id = Column(UUID(as_uuid=True), ForeignKey("organization_units.id"))
    owner_email = Column(String(200))
    coverage_score = Column(Float, default=0.0)   # 0.0 - 1.0
    is_automated = Column(Boolean, default=False)
    evidence_location = Column(Text)
    last_tested_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner_unit = relationship("OrganizationUnit", back_populates="controls")
    audit_findings = relationship("AuditFinding", back_populates="control")


class RegulationTracking(Base):
    __tablename__ = "regulation_tracking"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(String(500), unique=True, nullable=False)
    title = Column(Text)
    jurisdiction = Column(String(50))
    regulatory_body = Column(String(200))
    document_type = Column(String(100))
    published_date = Column(DateTime)
    effective_date = Column(DateTime, nullable=True)
    source_url = Column(Text)
    is_relevant = Column(Boolean, default=False)
    relevance_score = Column(Float, default=0.0)
    overall_risk_score = Column(Integer, default=0)
    impact_summary = Column(Text)
    processing_status = Column(String(50), default="pending")
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    action_items = relationship("ActionItem", back_populates="regulation")


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_id = Column(String(50), unique=True, nullable=False)
    regulation_id = Column(UUID(as_uuid=True), ForeignKey("regulation_tracking.id"))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    owner = Column(String(200))
    deadline = Column(String(200))
    priority = Column(String(20))
    effort_days = Column(Integer)
    compliance_risk_score = Column(Integer)
    source_obligation_ids = Column(ARRAY(String))
    source_clauses = Column(ARRAY(String))
    status = Column(String(50), default="open")
    jira_ticket_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    regulation = relationship("RegulationTracking", back_populates="action_items")


class AuditFinding(Base):
    __tablename__ = "audit_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    control_id = Column(UUID(as_uuid=True), ForeignKey("compliance_controls.id"))
    finding_date = Column(DateTime, default=datetime.utcnow)
    severity = Column(SAEnum(RiskLevel))
    description = Column(Text)
    remediation = Column(Text)
    resolved_at = Column(DateTime, nullable=True)

    control = relationship("ComplianceControl", back_populates="audit_findings")


# ─── Tech Stack Package ───────────────────────────────────────────────────────

class TechStackPackage(Base):
    """Registered software packages to monitor for CVEs proactively."""
    __tablename__ = "tech_stack_packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ecosystem = Column(String(50), nullable=False)   # PyPI, npm, Maven, Go
    package_name = Column(String(255), nullable=False)
    version = Column(String(100), default="")
    source_file = Column(String(100))                # e.g. "requirements.txt"
    registered_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("ecosystem", "package_name", "version",
                         name="uq_tech_stack_package_version"),
    )


# ─── CVE Alert ────────────────────────────────────────────────────────────────

class CveAlert(Base):
    """Proactively detected CVEs affecting the registered tech stack."""
    __tablename__ = "cve_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cve_id = Column(String(50), unique=True, nullable=False)
    cvss_score = Column(Float, default=0.0)
    severity = Column(String(20))
    category = Column(String(100))
    description = Column(Text)
    affected_packages = Column(JSON)    # [{name, version, ecosystem, fixed_version}]
    compliance_impact = Column(JSON)    # from cve_control_mapper
    blast_radius = Column(JSON)         # from blast_radius calculator
    remediation_steps = Column(JSON)
    is_kev = Column(Boolean, default=False)
    slack_sent = Column(Boolean, default=False)
    jira_key = Column(String(100))
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Regulation Snapshot ─────────────────────────────────────────────────────

class RegulationSnapshot(Base):
    """Immutable point-in-time snapshot of a regulation's extracted obligations.
    Used for diff computation when a regulation is updated."""
    __tablename__ = "regulation_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(String(500), nullable=False, index=True)
    version_hash = Column(String(64), nullable=False)     # SHA256 of obligations JSON
    obligations_snapshot = Column(JSON)                   # [{id, text, deadline, penalty}]
    obligations_count = Column(Integer, default=0)
    jurisdiction = Column(String(50))
    regulatory_body = Column(String(200))
    title = Column(Text)
    published_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_reg_snapshot_source_created", "source_id", "created_at"),
    )
