"""
NVD (National Vulnerability Database) CVE Connector
Fetches security advisories relevant to fintech/financial sector.
Free public API — no key required (rate limit: 5 req/30s).

Used by ImpactAnalyst to enrich compliance analysis with active CVEs.
"""
import httpx
import structlog
from typing import Any

logger = structlog.get_logger()

NVD_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

# Sector → keyword mapping for NVD keyword search
SECTOR_KEYWORDS: dict[str, str] = {
    "financial services": "payment banking fintech authentication encryption",
    "banking": "banking payment swift authentication encryption token",
    "technology": "authentication encryption software application api",
    "capital markets": "trading securities authentication encryption",
    "insurance": "insurance authentication data encryption",
    "healthcare": "healthcare medical authentication encryption",
    "all": "payment fintech authentication encryption tls",
}


async def fetch_nvd_cves(sector: str, cvss_min: float = 7.0, limit: int = 8) -> list[dict[str, Any]]:
    """
    Fetch recent high-severity CVEs from NVD relevant to a given sector.
    Returns list of {cve_id, description, cvss_score, severity, cwes, published_date}.
    """
    sector_lower = sector.lower()
    keywords = next(
        (v for k, v in SECTOR_KEYWORDS.items() if k in sector_lower),
        SECTOR_KEYWORDS["all"],
    )

    params = {
        "keywordSearch": keywords,
        "resultsPerPage": min(limit * 3, 30),  # fetch more, filter by CVSS
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(NVD_BASE, params=params)
            if resp.status_code == 403:
                logger.warning("nvd_rate_limited")
                return []
            if resp.status_code != 200:
                logger.warning("nvd_fetch_failed", status=resp.status_code)
                return []

            data = resp.json()
            cves = []

            for vuln in data.get("vulnerabilities", []):
                cve_obj = vuln.get("cve", {})
                cve_id = cve_obj.get("id", "")

                # Extract English description
                descriptions = cve_obj.get("descriptions", [])
                desc = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")

                # Extract CVSS score (v3.1 preferred, fallback v3.0, v2)
                metrics = cve_obj.get("metrics", {})
                cvss_score = 0.0
                severity = "MEDIUM"
                for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                    if key in metrics and metrics[key]:
                        m = metrics[key][0]
                        cvss_data = m.get("cvssData", {})
                        cvss_score = float(cvss_data.get("baseScore", 0.0))
                        severity = str(cvss_data.get("baseSeverity", "MEDIUM")).upper()
                        break

                if cvss_score < cvss_min:
                    continue

                # Extract CWEs
                weaknesses = cve_obj.get("weaknesses", [])
                cwes = []
                for w in weaknesses:
                    for d in w.get("description", []):
                        val = d.get("value", "")
                        if val.startswith("CWE-") and val not in cwes:
                            cwes.append(val)

                published = cve_obj.get("published", "")[:10]

                cves.append({
                    "cve_id": cve_id,
                    "description": desc[:400],
                    "cvss_score": cvss_score,
                    "severity": severity,
                    "cwes": cwes,
                    "published_date": published,
                })

                if len(cves) >= limit:
                    break

            logger.info("nvd_cves_fetched", sector=sector, count=len(cves))
            return cves

    except Exception as e:
        logger.error("nvd_fetch_error", error=str(e))
        return []


async def fetch_nvd_cve_by_id(cve_id: str) -> dict | None:
    """
    Look up a specific CVE by its exact ID from NVD.
    Uses ?cveId= parameter — NVD's correct way to fetch a single CVE.
    """
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(NVD_BASE, params={"cveId": cve_id})
            if resp.status_code != 200:
                logger.warning("nvd_cve_lookup_failed", cve_id=cve_id, status=resp.status_code)
                return None

            data = resp.json()
            vulns = data.get("vulnerabilities", [])
            if not vulns:
                return None

            cve_obj = vulns[0].get("cve", {})
            descriptions = cve_obj.get("descriptions", [])
            desc = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")

            metrics = cve_obj.get("metrics", {})
            cvss_score = 0.0
            severity = "MEDIUM"
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                if key in metrics and metrics[key]:
                    m = metrics[key][0]
                    cvss_data = m.get("cvssData", {})
                    cvss_score = float(cvss_data.get("baseScore", 0.0))
                    severity = str(cvss_data.get("baseSeverity", "MEDIUM")).upper()
                    break

            weaknesses = cve_obj.get("weaknesses", [])
            cwes = []
            for w in weaknesses:
                for d in w.get("description", []):
                    val = d.get("value", "")
                    if val.startswith("CWE-") and val not in cwes:
                        cwes.append(val)

            return {
                "cve_id": cve_obj.get("id", cve_id),
                "description": desc[:500],
                "cvss_score": cvss_score,
                "severity": severity,
                "cwes": cwes,
                "published_date": cve_obj.get("published", "")[:10],
            }

    except Exception as e:
        logger.error("nvd_cve_lookup_error", cve_id=cve_id, error=str(e))
        return None


async def fetch_cisa_kev(limit: int = 5) -> list[dict[str, Any]]:
    """
    Fetch CISA Known Exploited Vulnerabilities catalog.
    These are CVEs actively being exploited in the wild — highest priority.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(CISA_KEV_URL)
            if resp.status_code != 200:
                logger.warning("cisa_kev_fetch_failed", status=resp.status_code)
                return []

            data = resp.json()
            vulns = data.get("vulnerabilities", [])

            # Return most recently added KEVs
            recent = sorted(
                vulns,
                key=lambda v: v.get("dateAdded", ""),
                reverse=True,
            )[:limit]

            return [
                {
                    "cve_id": v.get("cveID", ""),
                    "description": f"{v.get('vendorProject', '')} {v.get('product', '')}: {v.get('shortDescription', '')}",
                    "cvss_score": 9.0,          # KEV = actively exploited = treat as critical
                    "severity": "CRITICAL",
                    "cwes": [],
                    "published_date": v.get("dateAdded", ""),
                    "is_kev": True,
                    "required_action": v.get("requiredAction", ""),
                    "due_date": v.get("dueDate", ""),
                }
                for v in recent
            ]

    except Exception as e:
        logger.error("cisa_kev_error", error=str(e))
        return []
