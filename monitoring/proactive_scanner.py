"""
Proactive CVE Scanner
Runs as a background asyncio task. Every N hours (configurable via SCAN_INTERVAL_HOURS):
  1. Loads all registered packages from tech_stack_packages table
  2. Queries OSV.dev for CVEs affecting each package+version
  3. Deduplicates against cve_alerts table (skips already-seen CVEs)
  4. For NEW critical/high CVEs:
     a. Maps to compliance obligations via cve_control_mapper
     b. Calculates blast radius (fine exposure)
     c. Sends Slack alert
     d. Creates Jira ticket
     e. Stores in cve_alerts table

Start from FastAPI lifespan:
    task = asyncio.create_task(proactive_scan_loop())
"""
import asyncio
import json
import structlog
import httpx
from datetime import datetime
from typing import Optional

from config import settings
from ingestion.connectors.osv import batch_query_packages
from knowledge.security.cve_control_mapper import map_cves_to_compliance
from knowledge.security.blast_radius import calculate_blast_radius
from org_context.models.database import (
    list_tech_stack_packages,
    upsert_cve_alert,
    mark_cve_alert_notified,
    list_cve_alerts,
)

logger = structlog.get_logger()

# How often to run the scan (override with SCAN_INTERVAL_HOURS env var)
DEFAULT_SCAN_INTERVAL_HOURS = 6
NOTIFY_SEVERITIES = {"CRITICAL", "HIGH"}


async def _send_slack_proactive(cve_data: dict, blast: dict) -> bool:
    """Send a Slack notification for a newly discovered CVE."""
    if not settings.slack_webhook_url:
        return False

    affected_pkgs = ", ".join(
        f"{p['name']}=={p.get('version', '?')}" for p in cve_data.get("affected_packages", [])[:3]
    )
    deadline_h = blast.get("earliest_deadline_hours", 72)
    exposure = blast.get("total_exposure_usd", 0)
    jurisdictions = ", ".join(blast.get("jurisdictions_triggered", []))

    payload = {
        "text": f"🚨 *Red Forge Proactive Alert — {cve_data['cve_id']}*",
        "attachments": [{
            "color": "#E5484D" if cve_data["severity"] == "CRITICAL" else "#F59E0B",
            "fields": [
                {"title": "Severity", "value": f"{cve_data['severity']} (CVSS {cve_data['cvss_score']:.1f})", "short": True},
                {"title": "Category", "value": cve_data.get("category", "Unknown"), "short": True},
                {"title": "Affected Packages", "value": affected_pkgs or "Unknown", "short": False},
                {"title": "Compliance Deadline", "value": f"⏰ {deadline_h}h from discovery", "short": True},
                {"title": "Fine Exposure", "value": f"${exposure:,.0f} USD across {jurisdictions}", "short": True},
                {"title": "Description", "value": (cve_data.get("description") or "")[:300], "short": False},
            ],
            "footer": "Red Forge Proactive Monitoring",
            "ts": int(datetime.utcnow().timestamp()),
        }]
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(settings.slack_webhook_url, json=payload)
            return resp.status_code == 200
    except Exception as e:
        logger.error("proactive_slack_failed", cve_id=cve_data["cve_id"], error=str(e))
        return False


async def _create_jira_proactive(cve_data: dict, blast: dict) -> Optional[str]:
    """Create a Jira ticket for a newly discovered CVE. Returns jira_key or None."""
    if not settings.jira_base_url or not settings.jira_api_token:
        return None

    project_key = settings.jira_project_key or "COMP"
    cve_id = cve_data["cve_id"]
    affected_pkgs = "\n".join(
        f"- {p['name']}=={p.get('version', '?')} (fix: {p.get('fixed_version', 'TBD')})"
        for p in cve_data.get("affected_packages", [])
    )
    remediation = "\n".join(f"- {s}" for s in cve_data.get("remediation_steps", []))
    compliance_lines = "\n".join(
        f"- {r['name']} ({r['regulator']}): deadline {r['deadline_hours']}h — {r['action']}"
        for r in cve_data.get("compliance_impact", [])[:5]
    )
    blast_summary = blast.get("summary", "")

    description_text = (
        f"[AUTO-DETECTED by Red Forge Proactive Scanner]\n\n"
        f"CVE: {cve_id}\nSeverity: {cve_data['severity']} (CVSS {cve_data['cvss_score']:.1f})\n"
        f"Category: {cve_data.get('category', 'Unknown')}\n\n"
        f"Description:\n{cve_data.get('description', '')}\n\n"
        f"Affected Packages:\n{affected_pkgs}\n\n"
        f"Compliance Blast Radius:\n{blast_summary}\n\n"
        f"Regulatory Obligations:\n{compliance_lines}\n\n"
        f"Remediation Steps:\n{remediation}"
    )

    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": f"[Proactive CVE] {cve_id} — {cve_data['severity']} — {cve_data.get('category', 'Security')}",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": description_text}
                ]}]
            },
            "issuetype": {"name": "Task"},
            "priority": {"name": "Highest" if cve_data["severity"] == "CRITICAL" else "High"},
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.jira_base_url}/rest/api/3/issue",
                json=payload,
                auth=(settings.jira_email, settings.jira_api_token),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
            if response.status_code == 201:
                return response.json().get("key")
            logger.warning("proactive_jira_failed", cve_id=cve_id, status=response.status_code)
    except Exception as e:
        logger.error("proactive_jira_error", cve_id=cve_id, error=str(e))
    return None


async def run_proactive_scan() -> dict:
    """
    Run a single proactive scan cycle. Returns a summary dict.
    Safe to call manually (e.g. from an API endpoint for on-demand scan).
    """
    logger.info("proactive_scan_start")
    start = datetime.utcnow()

    # 1. Load registered packages
    packages_rows = list_tech_stack_packages()
    if not packages_rows:
        logger.info("proactive_scan_skip", reason="no_packages_registered")
        return {"status": "skipped", "reason": "No packages registered. Upload a requirements.txt first."}

    packages = [
        {"name": p.package_name, "version": p.version, "ecosystem": p.ecosystem}
        for p in packages_rows
    ]

    logger.info("proactive_scan_querying_osv", packages_count=len(packages))

    # 2. Query OSV for all packages (concurrent)
    cves = await batch_query_packages(packages, cvss_min=7.0)
    if not cves:
        logger.info("proactive_scan_done", new_cves=0, elapsed_s=0)
        return {"status": "ok", "scanned_packages": len(packages), "new_cves": 0, "cves": []}

    # 3. Map to compliance
    mapped = map_cves_to_compliance(cves)
    mapped_by_id = {m["cve_id"]: m for m in mapped}

    new_cves_processed = []
    notifications = []

    for cve in cves:
        cve_id = cve["cve_id"]
        if not cve_id or cve_id.startswith("GHSA"):
            continue  # skip non-CVE OSV IDs for now

        mapped_adv = mapped_by_id.get(cve_id)
        if not mapped_adv:
            continue  # no compliance mapping — skip

        # 4. Compute blast radius
        blast = calculate_blast_radius(cve_id, mapped, org_annual_revenue_usd=None)

        # 5. Upsert into DB — is_new tells us if we need to notify
        affected_pkg_list = [{
            "name": cve.get("affected_package", ""),
            "version": cve.get("affected_version", ""),
            "ecosystem": next(
                (p.ecosystem for p in packages_rows if p.package_name == cve.get("affected_package")),
                "PyPI",
            ),
            "fixed_version": cve.get("fixed_version", ""),
        }]

        alert, is_new = upsert_cve_alert(
            cve_id=cve_id,
            cvss_score=cve.get("cvss_score", 0),
            severity=cve.get("severity", "HIGH"),
            category=mapped_adv.get("category", ""),
            description=cve.get("description", ""),
            affected_packages=affected_pkg_list,
            compliance_impact=mapped_adv.get("compliance_impact", []),
            blast_radius=blast,
            remediation_steps=mapped_adv.get("remediation_steps", []),
            is_kev=cve.get("is_kev", False),
        )

        cve_record = {
            "cve_id": cve_id,
            "severity": cve.get("severity", "HIGH"),
            "cvss_score": cve.get("cvss_score", 0),
            "category": mapped_adv.get("category", ""),
            "description": cve.get("description", ""),
            "affected_packages": affected_pkg_list,
            "compliance_impact": mapped_adv.get("compliance_impact", []),
            "remediation_steps": mapped_adv.get("remediation_steps", []),
            "blast_radius": blast,
            "is_new": is_new,
        }

        new_cves_processed.append(cve_record)

        # 6. Notify for new CRITICAL/HIGH CVEs
        if is_new and cve.get("severity", "HIGH") in NOTIFY_SEVERITIES:
            slack_sent = await _send_slack_proactive(cve_record, blast)
            jira_key = await _create_jira_proactive(cve_record, blast)
            mark_cve_alert_notified(cve_id, slack_sent=slack_sent, jira_key=jira_key)
            notifications.append({
                "cve_id": cve_id,
                "slack_sent": slack_sent,
                "jira_key": jira_key,
            })

    elapsed = (datetime.utcnow() - start).total_seconds()
    new_count = sum(1 for c in new_cves_processed if c["is_new"])

    logger.info(
        "proactive_scan_done",
        scanned_packages=len(packages),
        cves_found=len(new_cves_processed),
        new_cves=new_count,
        notified=len(notifications),
        elapsed_s=round(elapsed, 2),
    )

    return {
        "status": "ok",
        "scanned_packages": len(packages),
        "cves_found": len(new_cves_processed),
        "new_cves": new_count,
        "notifications_sent": len(notifications),
        "cves": new_cves_processed[:20],
        "notifications": notifications,
        "elapsed_seconds": round(elapsed, 2),
    }


async def proactive_scan_loop(interval_hours: int = DEFAULT_SCAN_INTERVAL_HOURS):
    """
    Infinite background loop. Runs run_proactive_scan() every interval_hours.
    Started via asyncio.create_task() in FastAPI lifespan.
    Runs the first scan after a short delay (30s) so the API is fully ready.
    """
    logger.info("proactive_scanner_started", interval_hours=interval_hours)
    await asyncio.sleep(30)  # let FastAPI finish startup

    while True:
        try:
            await run_proactive_scan()
        except Exception as e:
            logger.error("proactive_scan_error", error=str(e))

        await asyncio.sleep(interval_hours * 3600)
