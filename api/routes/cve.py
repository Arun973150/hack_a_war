"""
CVE Intelligence API
Exposes Red Forge as a developer API for security+compliance intelligence.

Endpoints:
  POST /api/v1/cve/suggest-fix        — Research a CVE: get patch, compliance obligations, deadlines
  POST /api/v1/cve/blast-radius       — Calculate regulatory fine exposure for a CVE
  POST /api/v1/cve/scan-stack         — Register tech stack packages for proactive monitoring
  GET  /api/v1/cve/alerts             — List all proactively detected CVE alerts
  POST /api/v1/cve/scan-now           — Trigger an immediate proactive scan
  GET  /api/v1/cve/regulation-diffs   — List all regulations with version diffs
  GET  /api/v1/cve/regulation-diff/{source_id} — Get diff for a specific regulation
"""
import asyncio
import structlog
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional

from ingestion.connectors.nvd import fetch_nvd_cves, fetch_nvd_cve_by_id
import json as _json

from ingestion.connectors.osv import (
    query_package_vulns,
    batch_query_packages,
    parse_requirements_txt,
    parse_package_json,
)
from knowledge.security.cve_control_mapper import map_cves_to_compliance
from knowledge.security.blast_radius import calculate_blast_radius
from org_context.models.database import (
    upsert_tech_stack_packages,
    list_tech_stack_packages,
    delete_tech_stack_packages,
    list_cve_alerts,
    list_all_snapshotted_sources,
)
from monitoring.regulation_differ import get_latest_diff
from monitoring.proactive_scanner import run_proactive_scan

logger = structlog.get_logger()
router = APIRouter()


# ─── Request / Response Models ────────────────────────────────────────────────

class SuggestFixRequest(BaseModel):
    cve_id: str
    package_name: Optional[str] = None
    package_version: Optional[str] = None
    ecosystem: Optional[str] = "PyPI"
    jurisdiction: Optional[str] = None
    org_annual_revenue_usd: Optional[float] = None


class BlastRadiusRequest(BaseModel):
    cve_id: str
    cwes: Optional[list[str]] = None
    description: Optional[str] = None
    cvss_score: Optional[float] = None
    org_annual_revenue_usd: Optional[float] = None


class RegisterStackRequest(BaseModel):
    packages: list[dict]  # [{name, version, ecosystem}]
    replace_existing: bool = False


# ─── Suggest Fix ─────────────────────────────────────────────────────────────

@router.post("/suggest-fix")
async def suggest_fix(request: SuggestFixRequest):
    """
    Given a CVE ID (+ optional package info), return:
    - Patch version (from OSV)
    - Exact remediation steps
    - All compliance obligations triggered
    - Regulatory deadlines per jurisdiction
    - Blast radius (fine exposure)
    - Priority level

    This is the core developer API — callable without running the full 5-agent pipeline.
    """
    cve_id = request.cve_id.strip().upper()

    # 1. Fetch CVE details from OSV (if package provided) or NVD keyword search
    cve_data: Optional[dict] = None
    fixed_version: Optional[str] = None

    if request.package_name and request.package_version:
        osv_cves = await query_package_vulns(
            request.package_name,
            request.package_version,
            ecosystem=request.ecosystem or "PyPI",
            cvss_min=0.0,
        )
        # Find the matching CVE
        for c in osv_cves:
            if c["cve_id"] == cve_id or c["osv_id"] == cve_id:
                cve_data = c
                fixed_version = c.get("fixed_version")
                break

    # Fallback: direct NVD lookup by CVE ID
    if not cve_data:
        cve_data = await fetch_nvd_cve_by_id(cve_id)

    # If still not found, construct minimal from request context
    if not cve_data:
        cve_data = {
            "cve_id": cve_id,
            "description": f"CVE details not found for {cve_id}. Using CWE-based compliance mapping.",
            "cvss_score": request.cvss_score or 7.0,
            "severity": "HIGH",
            "cwes": [],
        }

    # 2. Map to compliance
    mapped = map_cves_to_compliance([cve_data])
    if not mapped:
        raise HTTPException(
            404,
            f"{cve_id} could not be mapped to any compliance framework. "
            "Try providing cwes or check that the CVE is in NVD."
        )

    advisory = mapped[0]

    # 3. Filter by jurisdiction if requested
    compliance_impact = advisory.get("compliance_impact", [])
    if request.jurisdiction:
        jur_lower = request.jurisdiction.lower()
        compliance_impact = [
            r for r in compliance_impact
            if jur_lower in r.get("name", "").lower()
            or jur_lower in r.get("regulator", "").lower()
        ] or compliance_impact  # fall back to all if filter yields nothing

    # 4. Calculate blast radius
    blast = calculate_blast_radius(
        cve_id,
        mapped,
        org_annual_revenue_usd=request.org_annual_revenue_usd,
    )

    # 5. Build patch guidance
    patch_guidance = {}
    if request.package_name:
        if fixed_version:
            patch_guidance = {
                "action": "upgrade",
                "command": f"pip install {request.package_name}>={fixed_version}",
                "fixed_version": fixed_version,
                "current_version": request.package_version,
            }
        else:
            patch_guidance = {
                "action": "monitor",
                "message": f"No fixed version found in OSV for {request.package_name}. "
                           "Check vendor advisory and consider alternative packages.",
                "current_version": request.package_version,
            }

    return {
        "cve_id": cve_id,
        "priority": advisory.get("priority", "HIGH"),
        "severity": cve_data.get("severity", "HIGH"),
        "cvss_score": cve_data.get("cvss_score", 7.0),
        "category": advisory.get("category", ""),
        "description": cve_data.get("description", ""),
        "cwes": advisory.get("cwes", []),
        "patch": patch_guidance,
        "remediation_steps": advisory.get("remediation_steps", []),
        "compliance_obligations": compliance_impact,
        "compliance_controls_affected": advisory.get("compliance_controls", []),
        "blast_radius": blast,
        "is_kev": cve_data.get("is_kev", False),
    }


# ─── Blast Radius ────────────────────────────────────────────────────────────

@router.post("/blast-radius")
async def blast_radius(request: BlastRadiusRequest):
    """
    Calculate regulatory fine exposure for a CVE across all triggered jurisdictions.
    Pass CVE ID + optional CVSS score and CWEs for precise mapping.
    """
    cve_data = {
        "cve_id": request.cve_id.upper(),
        "description": request.description or "",
        "cvss_score": request.cvss_score or 7.0,
        "severity": "CRITICAL" if (request.cvss_score or 0) >= 9.0 else "HIGH",
        "cwes": request.cwes or [],
    }

    mapped = map_cves_to_compliance([cve_data])
    if not mapped:
        raise HTTPException(
            404,
            f"Cannot map {request.cve_id} to compliance frameworks. "
            "Provide cwes or description for keyword matching."
        )

    blast = calculate_blast_radius(
        request.cve_id.upper(),
        mapped,
        org_annual_revenue_usd=request.org_annual_revenue_usd,
    )

    # Enrich with compliance mapping details
    blast["compliance_category"] = mapped[0].get("category", "")
    blast["compliance_controls"] = mapped[0].get("compliance_controls", [])
    blast["remediation_steps"] = mapped[0].get("remediation_steps", [])

    return blast


# ─── Stack JSON Parser ───────────────────────────────────────────────────────

def _parse_stack_json(content: str) -> list[dict]:
    """
    Parse a custom stack JSON file. Supports three formats:

    Format 1 — flat array (most common):
      [{"name": "fastapi", "version": "0.115.0", "ecosystem": "PyPI"}, ...]

    Format 2 — named key:
      {"packages": [{"name": "...", "version": "...", "ecosystem": "..."}]}
      {"stack": [...]}
      {"dependencies": [...]}

    Format 3 — poetry/pipenv lock style:
      {"default": {"fastapi": {"version": "==0.115.0"}}}

    Ecosystem defaults to PyPI if not specified.
    """
    try:
        data = _json.loads(content)
    except Exception:
        return []

    packages = []

    # Format 1: top-level array
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("name"):
                packages.append({
                    "name": item["name"].strip(),
                    "version": str(item.get("version", "")).strip().lstrip("=^~>< "),
                    "ecosystem": item.get("ecosystem", "PyPI"),
                })
        return packages

    if not isinstance(data, dict):
        return []

    # Format 2: named key containing array
    for key in ("packages", "stack", "dependencies", "items"):
        if key in data and isinstance(data[key], list):
            for item in data[key]:
                if isinstance(item, dict) and item.get("name"):
                    packages.append({
                        "name": item["name"].strip(),
                        "version": str(item.get("version", "")).strip().lstrip("=^~>< "),
                        "ecosystem": item.get("ecosystem", "PyPI"),
                    })
            return packages

    # Format 3: Pipenv/Poetry lock — {"default": {"fastapi": {"version": "==0.115.0"}}}
    for section in ("default", "develop", "packages"):
        if section in data and isinstance(data[section], dict):
            for pkg_name, meta in data[section].items():
                if isinstance(meta, dict):
                    version = str(meta.get("version", "")).lstrip("=^~>< ")
                elif isinstance(meta, str):
                    version = meta.lstrip("=^~>< ")
                else:
                    version = ""
                packages.append({"name": pkg_name, "version": version, "ecosystem": "PyPI"})
            return packages

    return packages


# ─── Tech Stack Registration ──────────────────────────────────────────────────

@router.post("/scan-stack")
async def register_stack(request: RegisterStackRequest):
    """Register packages for proactive CVE monitoring."""
    if request.replace_existing:
        deleted = delete_tech_stack_packages()
        logger.info("tech_stack_cleared", deleted=deleted)

    added = upsert_tech_stack_packages(request.packages)
    all_packages = list_tech_stack_packages()

    return {
        "registered": len(added),
        "total_monitored": len(all_packages),
        "packages": [
            {"name": p.package_name, "version": p.version, "ecosystem": p.ecosystem}
            for p in all_packages
        ],
    }


@router.post("/upload-stack")
async def upload_stack_file(
    file: UploadFile = File(...),
    replace_existing: bool = False,
):
    """
    Upload a requirements.txt or package.json to register packages for monitoring.
    Supports: requirements.txt (PyPI), package.json (npm)
    """
    content = (await file.read()).decode("utf-8", errors="ignore")
    filename = (file.filename or "").lower()

    if "requirements" in filename or filename.endswith(".txt"):
        packages = parse_requirements_txt(content)
        source_file = "requirements.txt"
    elif "package.json" in filename:
        packages = parse_package_json(content)
        source_file = "package.json"
    elif filename.endswith(".json"):
        packages = _parse_stack_json(content)
        source_file = file.filename or "stack.json"
    else:
        raise HTTPException(400, "Unsupported file type. Upload requirements.txt, package.json, or a stack JSON file")

    if not packages:
        raise HTTPException(400, "No packages found in the uploaded file")

    if replace_existing:
        delete_tech_stack_packages()

    added = upsert_tech_stack_packages(packages, source_file=source_file)
    all_packages = list_tech_stack_packages()

    return {
        "filename": file.filename,
        "parsed_packages": len(packages),
        "newly_registered": len(added),
        "total_monitored": len(all_packages),
    }


# ─── CVE Alerts ───────────────────────────────────────────────────────────────

@router.get("/alerts")
async def get_cve_alerts(
    severity: Optional[str] = None,
    unnotified_only: bool = False,
    limit: int = 50,
):
    """List all proactively detected CVE alerts."""
    alerts = list_cve_alerts(severity=severity, unnotified_only=unnotified_only, limit=limit)
    return {
        "alerts": [
            {
                "cve_id": a.cve_id,
                "severity": a.severity,
                "cvss_score": a.cvss_score,
                "category": a.category,
                "description": a.description,
                "affected_packages": a.affected_packages,
                "compliance_impact": a.compliance_impact,
                "blast_radius": a.blast_radius,
                "remediation_steps": a.remediation_steps,
                "is_kev": a.is_kev,
                "slack_sent": a.slack_sent,
                "jira_key": a.jira_key,
                "first_seen": a.first_seen.isoformat() if a.first_seen else None,
            }
            for a in alerts
        ],
        "total": len(alerts),
    }


# ─── On-Demand Scan ──────────────────────────────────────────────────────────

@router.post("/scan-now")
async def trigger_scan_now():
    """Trigger an immediate proactive CVE scan (don't wait for scheduled run)."""
    result = await run_proactive_scan()
    return result


# ─── Regulation Diffs ────────────────────────────────────────────────────────

@router.get("/regulation-diffs")
async def list_regulation_diffs(limit: int = 20):
    """List all regulations that have been snapshotted and may have diffs."""
    sources = list_all_snapshotted_sources(limit=limit)
    diffs = []
    for source_id in sources:
        diff = get_latest_diff(source_id)
        if diff.get("has_changes"):
            diffs.append(diff)

    return {
        "diffs": diffs,
        "total": len(diffs),
        "sources_tracked": len(sources),
    }


@router.get("/regulation-diff/{source_id:path}")
async def get_regulation_diff(source_id: str):
    """Get the diff between the two most recent versions of a specific regulation."""
    diff = get_latest_diff(source_id)
    if not diff:
        raise HTTPException(404, f"No snapshots found for source_id: {source_id}")
    return diff
