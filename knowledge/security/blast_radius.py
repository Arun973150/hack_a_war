"""
Cross-CVE Blast Radius Calculator
Given a CVE (mapped to compliance obligations), computes total regulatory fine exposure
across all triggered jurisdictions. Fine schedules loaded from fine_schedules.json — not hardcoded.
"""
import json
from pathlib import Path
from typing import Optional

_FINE_SCHEDULES: dict | None = None


def _load_fine_schedules() -> dict:
    global _FINE_SCHEDULES
    if _FINE_SCHEDULES is None:
        path = Path(__file__).parent.parent / "regulatory" / "fine_schedules.json"
        with open(path, encoding="utf-8") as f:
            _FINE_SCHEDULES = json.load(f)
    return _FINE_SCHEDULES


# Maps regulation name fragments → fine_schedule keys
_REGULATION_TO_SCHEDULE = {
    "gdpr": "GDPR",
    "dpdp": "DPDP",
    "rbi": "RBI_PA",
    "pci": "PCI_DSS",
    "pci-dss": "PCI_DSS",
    "dora": "DORA",
    "nis2": "NIS2",
    "sec": "SEC_CYBER",
    "sebi": "SEBI_CSCRF",
    "hipaa": "HIPAA",
    "iso 27001": "ISO_27001",
    "iso27001": "ISO_27001",
}


def _to_usd(amount: float, currency: str, rates: dict) -> float:
    """Convert any currency to USD using conversion rates from fine_schedules.json."""
    rate = rates.get(currency.upper(), 1.0)
    return amount * rate


def _get_schedule_for_regulation(reg_name: str, schedules: dict) -> tuple[str, dict] | tuple[None, None]:
    """Find the matching fine schedule for a regulation name."""
    name_lower = reg_name.lower()
    for key_fragment, schedule_key in _REGULATION_TO_SCHEDULE.items():
        if key_fragment in name_lower:
            if schedule_key in schedules:
                return schedule_key, schedules[schedule_key]
    return None, None


def calculate_blast_radius(
    cve_id: str,
    mapped_advisories: list[dict],
    org_annual_revenue_usd: Optional[float] = None,
) -> dict:
    """
    Calculate the total regulatory fine exposure for a CVE across all triggered jurisdictions.

    Args:
        cve_id: The CVE identifier (e.g. "CVE-2024-3094")
        mapped_advisories: Output from map_cves_to_compliance() — list of compliance-enriched advisories
        org_annual_revenue_usd: Annual revenue in USD for revenue-based fine calculations.
                                 If None, uses tier maximums only (conservative lower bound).

    Returns:
        dict with: total_exposure_usd, jurisdictions_triggered, obligations_count,
                   breakdown (per regulation), worst_case_usd, timeline_hours
    """
    schedules_data = _load_fine_schedules()
    usd_rates = schedules_data["_meta"]["usd_conversion_rates"]

    triggered_schedules: dict[str, dict] = {}   # schedule_key → {schedule, regulation_name, deadline_hours}
    total_obligations = 0
    earliest_deadline_hours: Optional[int] = None

    # Collect all triggered regulations from all advisories for this CVE
    target_advisories = [a for a in mapped_advisories if a.get("cve_id") == cve_id]
    if not target_advisories:
        # If no match by CVE ID, use all advisories (single-CVE context)
        target_advisories = mapped_advisories

    for advisory in target_advisories:
        for regulation in advisory.get("compliance_impact", []):
            reg_name = regulation.get("name", "")
            deadline_h = regulation.get("deadline_hours", 72)

            schedule_key, schedule = _get_schedule_for_regulation(reg_name, schedules_data)
            if not schedule_key:
                continue

            total_obligations += 1

            if schedule_key not in triggered_schedules:
                triggered_schedules[schedule_key] = {
                    "schedule": schedule,
                    "regulation_names": [],
                    "deadline_hours": deadline_h,
                }
            triggered_schedules[schedule_key]["regulation_names"].append(reg_name)
            # Keep the shortest (most urgent) deadline per framework
            if deadline_h < triggered_schedules[schedule_key]["deadline_hours"]:
                triggered_schedules[schedule_key]["deadline_hours"] = deadline_h

            if earliest_deadline_hours is None or deadline_h < earliest_deadline_hours:
                earliest_deadline_hours = deadline_h

    breakdown = []
    total_exposure_usd = 0.0
    worst_case_usd = 0.0
    jurisdictions: set[str] = set()

    for schedule_key, entry in triggered_schedules.items():
        schedule = entry["schedule"]
        currency = schedule.get("currency", "USD")
        jurisdiction = schedule.get("jurisdiction", "Unknown")
        jurisdictions.add(jurisdiction)

        # Calculate fine in native currency then convert to USD
        fine_native = 0.0
        fine_label = ""

        if "tier_2_max" in schedule:
            # GDPR-style: revenue-based with hard cap
            cap = schedule["tier_2_max"]
            if org_annual_revenue_usd:
                revenue_native = org_annual_revenue_usd / usd_rates.get(currency, 1.0)
                revenue_fine = revenue_native * (schedule["tier_2_revenue_pct"] / 100)
                fine_native = min(max(revenue_fine, schedule.get("tier_1_max", 0)), cap)
                fine_label = f"{schedule['tier_2_revenue_pct']}% revenue capped at {currency} {cap:,.0f}"
            else:
                fine_native = cap
                fine_label = f"Max {currency} {cap:,.0f} (no revenue provided)"

        elif "tier_1_revenue_pct" in schedule and org_annual_revenue_usd:
            cap = schedule.get("tier_1_max", 0)
            revenue_native = org_annual_revenue_usd / usd_rates.get(currency, 1.0)
            revenue_fine = revenue_native * (schedule["tier_1_revenue_pct"] / 100)
            fine_native = min(revenue_fine, cap) if cap else revenue_fine
            fine_label = f"{schedule['tier_1_revenue_pct']}% revenue capped at {currency} {cap:,.0f}"

        elif "monthly_max" in schedule:
            # PCI-DSS: monthly fine, assume 3-month exposure
            fine_native = schedule["monthly_max"] * 3
            fine_label = f"{currency} {schedule['monthly_max']:,.0f}/month × 3 months"

        elif "per_violation" in schedule:
            fine_native = schedule["per_violation"]
            fine_label = f"{currency} {fine_native:,.0f} per violation"

        elif "willful_max" in schedule:
            fine_native = schedule["willful_max"]
            fine_label = f"Up to {currency} {fine_native:,.0f}"

        elif "estimated_business_loss" in schedule:
            fine_native = schedule["estimated_business_loss"]
            fine_label = f"Estimated business loss {currency} {fine_native:,.0f}"

        else:
            fine_native = schedule.get("tier_1_max", 0)
            fine_label = f"Max {currency} {fine_native:,.0f}"

        fine_usd = _to_usd(fine_native, currency, usd_rates)
        total_exposure_usd += fine_usd
        worst_case_usd = max(worst_case_usd, fine_usd)

        breakdown.append({
            "framework": schedule_key,
            "full_name": schedule.get("full_name", schedule_key),
            "jurisdiction": jurisdiction,
            "regulator": schedule.get("regulator", ""),
            "fine_native_currency": currency,
            "fine_native_amount": round(fine_native, 2),
            "fine_usd": round(fine_usd, 2),
            "fine_label": fine_label,
            "deadline_hours": entry["deadline_hours"],
            "regulations_triggered": entry["regulation_names"],
        })

    # Sort breakdown by fine USD descending
    breakdown.sort(key=lambda x: x["fine_usd"], reverse=True)

    return {
        "cve_id": cve_id,
        "total_exposure_usd": round(total_exposure_usd, 2),
        "worst_single_fine_usd": round(worst_case_usd, 2),
        "obligations_triggered": total_obligations,
        "jurisdictions_triggered": sorted(jurisdictions),
        "jurisdictions_count": len(jurisdictions),
        "earliest_deadline_hours": earliest_deadline_hours or 72,
        "revenue_based": org_annual_revenue_usd is not None,
        "breakdown": breakdown,
        "summary": (
            f"{cve_id} triggers {total_obligations} regulatory obligations across "
            f"{len(jurisdictions)} jurisdiction(s) with up to "
            f"${total_exposure_usd:,.0f} USD in potential fines. "
            f"Earliest mandatory action: {earliest_deadline_hours or 72} hours."
        ),
    }
