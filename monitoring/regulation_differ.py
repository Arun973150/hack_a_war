"""
Regulation Diff Engine
When a regulation is processed, snapshot its obligations. On subsequent versions
of the same regulation (same source_id), diff the obligation sets to surface:
  - New obligations added
  - Obligations removed
  - Deadline changes (tightened / relaxed)
  - Penalty changes

Usage (called from regulations.py pipeline after agent run):
    from monitoring.regulation_differ import snapshot_and_diff
    diff = snapshot_and_diff(source_id, state.obligations, jurisdiction, ...)
"""
import hashlib
import json
import structlog
from datetime import datetime
from typing import Optional

from org_context.models.database import (
    save_regulation_snapshot,
    get_regulation_snapshots,
)

logger = structlog.get_logger()


def _obligations_to_snapshot(obligations: list) -> list[dict]:
    """
    Normalize obligation objects to a consistent dict for snapshotting.
    Works with both Pydantic Obligation objects and plain dicts.
    """
    normalized = []
    for ob in obligations:
        if hasattr(ob, "model_dump"):
            d = ob.model_dump()
        elif hasattr(ob, "__dict__"):
            d = vars(ob)
        else:
            d = dict(ob)

        normalized.append({
            "obligation_id": str(d.get("obligation_id", "")),
            "text": str(d.get("text", "") or d.get("what", ""))[:500],
            "deadline": str(d.get("deadline", "") or ""),
            "penalty": str(d.get("penalty", "") or ""),
            "who_must_comply": str(d.get("who_must_comply", "") or ""),
        })
    return normalized


def _hash_obligations(obligations: list[dict]) -> str:
    """Deterministic SHA-256 of the obligation set (sorted by obligation_id)."""
    sorted_obs = sorted(obligations, key=lambda x: x.get("obligation_id", ""))
    canonical = json.dumps(sorted_obs, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _diff_obligation_sets(
    previous: list[dict],
    current: list[dict],
) -> dict:
    """
    Compare two obligation snapshots. Returns a structured diff.
    """
    prev_by_id = {ob["obligation_id"]: ob for ob in previous}
    curr_by_id = {ob["obligation_id"]: ob for ob in current}

    prev_ids = set(prev_by_id.keys())
    curr_ids = set(curr_by_id.keys())

    new_ids = curr_ids - prev_ids
    removed_ids = prev_ids - curr_ids
    common_ids = prev_ids & curr_ids

    new_obligations = [curr_by_id[i] for i in new_ids]
    removed_obligations = [prev_by_id[i] for i in removed_ids]

    changed_obligations = []
    for ob_id in common_ids:
        prev_ob = prev_by_id[ob_id]
        curr_ob = curr_by_id[ob_id]

        changes = {}
        for field in ["text", "deadline", "penalty", "who_must_comply"]:
            if prev_ob.get(field) != curr_ob.get(field):
                changes[field] = {
                    "from": prev_ob.get(field),
                    "to": curr_ob.get(field),
                }

        if changes:
            changed_obligations.append({
                "obligation_id": ob_id,
                "changes": changes,
            })

    # Classify severity of the diff
    severity = "none"
    if new_obligations or removed_obligations:
        severity = "major"
    elif changed_obligations:
        # Check if any deadline was shortened
        deadline_tightened = any(
            "deadline" in ch["changes"]
            for ch in changed_obligations
        )
        severity = "critical" if deadline_tightened else "minor"

    return {
        "has_changes": bool(new_obligations or removed_obligations or changed_obligations),
        "severity": severity,
        "new_obligations": new_obligations,
        "removed_obligations": removed_obligations,
        "changed_obligations": changed_obligations,
        "summary": _build_diff_summary(new_obligations, removed_obligations, changed_obligations),
    }


def _build_diff_summary(new_obs, removed_obs, changed_obs) -> str:
    parts = []
    if new_obs:
        parts.append(f"{len(new_obs)} new obligation(s) added")
    if removed_obs:
        parts.append(f"{len(removed_obs)} obligation(s) removed")
    if changed_obs:
        deadline_changes = sum(1 for c in changed_obs if "deadline" in c["changes"])
        if deadline_changes:
            parts.append(f"{deadline_changes} deadline(s) changed")
        other = len(changed_obs) - deadline_changes
        if other:
            parts.append(f"{other} obligation text(s) updated")
    return "; ".join(parts) if parts else "No changes detected"


def snapshot_and_diff(
    source_id: str,
    obligations: list,
    jurisdiction: str = "",
    regulatory_body: str = "",
    title: str = "",
    published_date: Optional[datetime] = None,
) -> dict:
    """
    Main entry point: snapshot current obligations and compute diff vs previous version.

    Returns a diff dict. If no previous snapshot exists, returns diff with no changes
    (just records the baseline). Caller should check diff["has_changes"].
    """
    if not obligations:
        return {"has_changes": False, "severity": "none", "summary": "No obligations extracted"}

    normalized = _obligations_to_snapshot(obligations)
    current_hash = _hash_obligations(normalized)

    # Get previous snapshots
    previous_snapshots = get_regulation_snapshots(source_id, limit=2)

    is_new_regulation = len(previous_snapshots) == 0
    diff = {"has_changes": False, "severity": "none", "summary": "No changes detected"}

    if not is_new_regulation:
        latest = previous_snapshots[0]
        if latest.version_hash != current_hash:
            prev_obligations = latest.obligations_snapshot or []
            diff = _diff_obligation_sets(prev_obligations, normalized)
            logger.info(
                "regulation_diff_computed",
                source_id=source_id,
                severity=diff["severity"],
                new=len(diff.get("new_obligations", [])),
                removed=len(diff.get("removed_obligations", [])),
                changed=len(diff.get("changed_obligations", [])),
            )
        else:
            logger.info("regulation_unchanged", source_id=source_id, hash=current_hash[:8])

    # Always save the new snapshot (even if unchanged — tracks last seen date)
    save_regulation_snapshot(
        source_id=source_id,
        version_hash=current_hash,
        obligations_snapshot=normalized,
        jurisdiction=jurisdiction,
        regulatory_body=regulatory_body,
        title=title,
        published_date=published_date,
    )

    diff["source_id"] = source_id
    diff["is_new_regulation"] = is_new_regulation
    diff["obligations_count"] = len(normalized)
    diff["version_hash"] = current_hash[:12]
    return diff


def get_latest_diff(source_id: str) -> dict:
    """
    Compute a diff between the two most recent snapshots for a given regulation.
    Used by the API to serve diffs on demand.
    """
    snapshots = get_regulation_snapshots(source_id, limit=2)
    if len(snapshots) < 2:
        return {
            "source_id": source_id,
            "has_changes": False,
            "severity": "none",
            "summary": "Only one version available — no diff yet",
            "snapshots_available": len(snapshots),
        }

    current = snapshots[0]
    previous = snapshots[1]

    if current.version_hash == previous.version_hash:
        return {
            "source_id": source_id,
            "has_changes": False,
            "severity": "none",
            "summary": "No changes between latest two versions",
            "current_version": current.version_hash[:12],
            "previous_version": previous.version_hash[:12],
            "current_date": current.created_at.isoformat() if current.created_at else None,
            "previous_date": previous.created_at.isoformat() if previous.created_at else None,
        }

    diff = _diff_obligation_sets(
        previous.obligations_snapshot or [],
        current.obligations_snapshot or [],
    )
    diff.update({
        "source_id": source_id,
        "title": current.title or "",
        "jurisdiction": current.jurisdiction or "",
        "regulatory_body": current.regulatory_body or "",
        "current_version": current.version_hash[:12],
        "previous_version": previous.version_hash[:12],
        "current_date": current.created_at.isoformat() if current.created_at else None,
        "previous_date": previous.created_at.isoformat() if previous.created_at else None,
        "obligations_count": current.obligations_count or 0,
    })
    return diff
