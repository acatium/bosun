"""Conformance report: does the tenant match the model? Read-only.

Covers what the compiler emits (groups, Fabric roles and tags, term store) and discovers deal rooms that
people have opened, checking each one against the model: label, privacy, guests and library tags.
"""
from __future__ import annotations

import json
import os

from . import entra, fabric, semantic, termstore
from .azure import graph
from .model import Model

LABELS = {"BOSUN_LABEL_PUBLIC": "Public", "BOSUN_LABEL_INTERNAL": "Internal", "BOSUN_LABEL_CONFIDENTIAL": "Confidential"}


def receipt_defaults(group_id: str) -> dict:
    from .deal_room import RECEIPTS
    if not RECEIPTS.exists():
        return {}
    for line in reversed(RECEIPTS.read_text().splitlines()):
        record = json.loads(line)
        if record.get("group_id") == group_id:
            for step in record.get("steps", []):
                if step.get("step") == "library-defaults":
                    return step.get("verified", {})
    return {}


def deal_rooms(model: Model) -> list[dict]:
    rooms = []
    label_names = {os.environ.get(k): v for k, v in LABELS.items() if os.environ.get(k)}
    found = graph("GET", "/groups?$filter=groupTypes/any(g:g eq 'Unified') and startswith(mailNickname,'deal-')"
                         "&$select=id,displayName,description,visibility,assignedLabels,createdDateTime")
    for group in found.get("value", []):
        if f"deal room (deal-room)" not in (group.get("description") or ""):
            continue
        labels = [label_names.get(l.get("labelId"), l.get("displayName")) for l in group.get("assignedLabels", [])]
        sensitivity = labels[0] if labels else None
        members = graph("GET", f"/groups/{group['id']}/members?$select=userPrincipalName,userType").get("value", [])
        guests = [m["userPrincipalName"] for m in members if m.get("userType") == "Guest"]
        issues = []
        if not sensitivity:
            issues.append("no sensitivity label")
        if sensitivity in ("Confidential", "Internal") and group.get("visibility") != "Private":
            issues.append("not private")
        for rule in model.rules_for("add_member", "deal-room"):
            if rule["effect"] == "deny" and rule.get("member_kind") == "Guest" and rule.get("sensitivity") in (None, sensitivity) and guests:
                issues.append(f"guests present, violating {rule['id']}")
        # The platform owner is not a member, so cannot read the room's content (by design). Content-side facts
        # come from the receipt the backplane wrote, as the partner, when it created and verified the room.
        columns = receipt_defaults(group["id"])
        if not columns:
            issues.append("no receipt with verified library tags")
        for needed in ("Domain", "Deal", "Sensitivity"):
            if columns and not columns.get(needed):
                issues.append(f"library default for {needed} missing")
        rooms.append({"deal_room": group["displayName"], "created": group["createdDateTime"], "sensitivity": sensitivity,
                      "visibility": group.get("visibility"), "members": len(members), "guests": guests,
                      "library_defaults": columns, "conformant": not issues, "issues": issues})
    return rooms


def build(model: Model) -> dict:
    sections = {
        "groups": entra.plan(model),
        "fabric": fabric.plan(model),
        "term_store": termstore.plan(model),
        "data": semantic.plan(model),
    }
    rooms = deal_rooms(model)
    drift = {name: steps for name, steps in sections.items() if steps}
    return {
        "model": model.name,
        "compiled_objects": {
            "groups": sorted(entra.desired(model)),
            "term_sets": {k: sorted(v) for k, v in termstore.desired(model).items()},
            "stores": {sid: {"kind": s["kind"], "domain": s["domain"], "sensitivity": s.get("sensitivity")}
                       for sid, s in model.stores.items()},
        },
        "drift": drift,
        "deal_rooms": rooms,
        "conformant": not drift and all(r["conformant"] for r in rooms),
    }


def render(report: dict) -> str:
    lines = [f"Conformance report: {report['model']}", ""]
    lines.append("Model-level objects: " + ("match the model" if not report["drift"] else "DRIFT"))
    for area, steps in report["drift"].items():
        for step in steps:
            lines.append(f"  - {area}: {step['op']} {step.get('group') or step.get('term') or step.get('item_name') or step.get('table') or step.get('name') or ''}")
    lines.append(f"Groups: {', '.join(report['compiled_objects']['groups'])}")
    lines.append(f"Business terms: {len(report['compiled_objects']['term_sets']['Business terms'])} in the term store")
    lines.append("")
    lines.append(f"Deal rooms found: {len(report['deal_rooms'])}")
    for room in report["deal_rooms"]:
        status = "conformant" if room["conformant"] else "NOT CONFORMANT: " + "; ".join(room["issues"])
        defaults = ", ".join(f"{k}={v}" for k, v in room["library_defaults"].items())
        lines.append(f"  - {room['deal_room']}: label {room['sensitivity'] or 'none'}, {room['visibility']}, {room['members']} members, "
                     f"guests: {len(room['guests'])}; tags (verified by the backplane as the owner): {defaults or 'none'} -> {status}")
    if report["deal_rooms"]:
        lines.append("  (Room content is not readable by the platform owner: deal team membership is the barrier.)")
    lines.append("")
    lines.append("Overall: " + ("CONFORMANT" if report["conformant"] else "NOT CONFORMANT"))
    return "\n".join(lines)
