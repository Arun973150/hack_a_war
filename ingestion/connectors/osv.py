"""
OSV.dev API Connector
Queries the Open Source Vulnerabilities (OSV) database for CVEs affecting specific
package versions. No API key required. Covers PyPI, npm, Maven, Go, RubyGems, etc.

OSV API: https://google.github.io/osv.dev/api/
"""
import asyncio
import httpx
import structlog
from typing import Optional

logger = structlog.get_logger()

OSV_API_BASE = "https://api.osv.dev/v1"
OSV_BATCH_ENDPOINT = f"{OSV_API_BASE}/querybatch"
OSV_QUERY_ENDPOINT = f"{OSV_API_BASE}/query"

# OSV ecosystem identifiers
ECOSYSTEM_MAP = {
    "pypi": "PyPI",
    "npm": "npm",
    "maven": "Maven",
    "go": "Go",
    "cargo": "crates.io",
    "rubygems": "RubyGems",
    "nuget": "NuGet",
    "packagist": "Packagist",
}

SEVERITY_TO_CVSS = {
    "CRITICAL": 9.5,
    "HIGH": 7.5,
    "MEDIUM": 5.0,
    "LOW": 2.0,
}


def _parse_cvss_from_severity(severity_list: list) -> float:
    """
    Extract a numeric CVSS score from OSV severity array.
    OSV severity entries can be CVSS vector strings or numeric strings.
    """
    for entry in severity_list:
        score_str = entry.get("score", "")
        if not score_str:
            continue
        # Some entries are plain numeric like "8.1"
        if not score_str.startswith("CVSS:"):
            try:
                return float(score_str)
            except ValueError:
                continue
        # CVSS vector — too complex to parse fully; use database_specific if available
    return 0.0


def _extract_cve_id(osv_id: str, aliases: list[str]) -> str:
    """Prefer CVE ID from aliases; fall back to OSV ID."""
    for alias in aliases:
        if alias.startswith("CVE-"):
            return alias
    return osv_id


def _extract_fixed_version(affected: list[dict]) -> Optional[str]:
    """Find the first fixed version from OSV affected ranges."""
    for pkg in affected:
        for rng in pkg.get("ranges", []):
            for event in rng.get("events", []):
                if "fixed" in event:
                    return event["fixed"]
    return None


def _parse_osv_vuln(vuln: dict, package_name: str, package_version: str) -> dict:
    """Convert an OSV vulnerability object to Red Forge CVE format."""
    osv_id = vuln.get("id", "")
    aliases = vuln.get("aliases", [])
    cve_id = _extract_cve_id(osv_id, aliases)

    severity_list = vuln.get("severity", [])
    cvss_score = _parse_cvss_from_severity(severity_list)

    # Try database_specific severity string as fallback
    db_specific = vuln.get("database_specific", {})
    if cvss_score == 0.0:
        sev_str = db_specific.get("severity", "").upper()
        cvss_score = SEVERITY_TO_CVSS.get(sev_str, 5.0)

    if cvss_score >= 9.0:
        severity = "CRITICAL"
    elif cvss_score >= 7.0:
        severity = "HIGH"
    elif cvss_score >= 4.0:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    # CWEs from database_specific or top-level
    cwes = db_specific.get("cwes", []) or vuln.get("cwes", [])

    fixed_version = _extract_fixed_version(vuln.get("affected", []))
    description = vuln.get("summary") or vuln.get("details", "")[:500]

    return {
        "cve_id": cve_id,
        "osv_id": osv_id,
        "description": description,
        "cvss_score": cvss_score,
        "severity": severity,
        "cwes": cwes,
        "affected_package": package_name,
        "affected_version": package_version,
        "fixed_version": fixed_version,
        "published": vuln.get("published", ""),
        "modified": vuln.get("modified", ""),
        "is_kev": False,  # OSV doesn't track KEV; handled by CISA feed
    }


async def query_package_vulns(
    package_name: str,
    version: str,
    ecosystem: str = "PyPI",
    cvss_min: float = 4.0,
) -> list[dict]:
    """
    Query OSV.dev for vulnerabilities affecting a specific package version.

    Args:
        package_name: e.g. "requests", "fastapi"
        version: e.g. "2.28.0"
        ecosystem: e.g. "PyPI", "npm", "Maven"
        cvss_min: Minimum CVSS score to return (default 4.0 = medium+)

    Returns:
        List of CVE dicts in Red Forge format
    """
    ecosystem = ECOSYSTEM_MAP.get(ecosystem.lower(), ecosystem)
    payload = {
        "version": version,
        "package": {
            "name": package_name,
            "ecosystem": ecosystem,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(OSV_QUERY_ENDPOINT, json=payload)
            if response.status_code != 200:
                logger.warning("osv_query_failed", package=package_name, status=response.status_code)
                return []

            data = response.json()
            vulns = data.get("vulns", [])

            results = []
            for vuln in vulns:
                parsed = _parse_osv_vuln(vuln, package_name, version)
                if parsed["cvss_score"] >= cvss_min:
                    results.append(parsed)

            logger.info("osv_query_complete", package=package_name, version=version,
                        found=len(results))
            return results

    except Exception as e:
        logger.error("osv_query_error", package=package_name, version=version, error=str(e))
        return []


async def batch_query_packages(
    packages: list[dict],
    cvss_min: float = 4.0,
    batch_size: int = 5,
    batch_delay_seconds: float = 6.0,
) -> list[dict]:
    """
    Query OSV.dev for multiple packages in rate-limited batches.
    OSV.dev has no official rate limit but NVD (called for CVSS enrichment) is 5 req/30s.
    We process in batches of 5 with a 6s delay between batches to stay safe.

    Args:
        packages: List of {"name": str, "version": str, "ecosystem": str}
        cvss_min: Minimum CVSS to include
        batch_size: Packages per concurrent batch (default 5)
        batch_delay_seconds: Seconds to wait between batches (default 6s)
    """
    valid_packages = [p for p in packages if p.get("name")]
    if not valid_packages:
        return []

    all_cves: list[dict] = []

    # Process in batches to respect rate limits
    for i in range(0, len(valid_packages), batch_size):
        batch = valid_packages[i:i + batch_size]
        tasks = [
            query_package_vulns(
                pkg["name"],
                pkg.get("version", ""),
                pkg.get("ecosystem", "PyPI"),
                cvss_min=cvss_min,
            )
            for pkg in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                all_cves.extend(res)

        # Wait between batches if more remain
        if i + batch_size < len(valid_packages):
            await asyncio.sleep(batch_delay_seconds)

    # Deduplicate by CVE ID (keep highest CVSS instance)
    seen: dict[str, dict] = {}
    for cve in all_cves:
        cid = cve["cve_id"]
        if cid not in seen or cve["cvss_score"] > seen[cid]["cvss_score"]:
            seen[cid] = cve

    return sorted(seen.values(), key=lambda x: x["cvss_score"], reverse=True)


def parse_requirements_txt(content: str) -> list[dict]:
    """
    Parse a requirements.txt file into package list for OSV querying.
    Handles: package==1.0.0, package>=1.0.0 (uses lower bound), package (no version)
    """
    packages = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue

        # Strip extras like package[extra]==1.0
        name = line.split("[")[0].split("=")[0].split(">")[0].split("<")[0].split("~")[0].strip()
        version = ""

        if "==" in line:
            version = line.split("==")[1].split(";")[0].split(" ")[0].strip()
        elif ">=" in line:
            # Use the minimum version for OSV query (worst case)
            version = line.split(">=")[1].split(",")[0].split(";")[0].strip()

        if name:
            packages.append({"name": name, "version": version, "ecosystem": "PyPI"})

    return packages


def parse_package_json(content: str) -> list[dict]:
    """Parse package.json dependencies into package list for OSV querying."""
    import json
    try:
        data = json.loads(content)
    except Exception:
        return []

    packages = []
    for section in ["dependencies", "devDependencies"]:
        for name, version_spec in data.get(section, {}).items():
            # Strip semver operators: ^1.0.0 → 1.0.0
            version = version_spec.lstrip("^~>=<").split(" ")[0].strip()
            packages.append({"name": name, "version": version, "ecosystem": "npm"})

    return packages
