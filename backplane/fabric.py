"""Fabric: domains, the domain each workspace belongs to, who may read it, and the tags on its items.

Fabric tags and domains do not grant access; workspace roles do. So read rules compile into workspace
roles for the model's groups, and tags carry the domain and sensitivity for discovery and audit.
"""
from __future__ import annotations

import os

from . import entra
from .azure import fabric
from .model import Model


def fabric_domain_name(model: Model, domain_id: str) -> str:
    return f"{model.name.split()[0]} - {model.domains[domain_id]['name']}"


def tag_names(model: Model, store: dict) -> list[str]:
    """Fabric tag names allow letters, digits and spaces only, so '&' becomes 'and'."""
    tags = [f"Domain {model.domains[store['domain']]['name'].replace('&', 'and')}"]
    if store.get("sensitivity"):
        tags.append(f"Sensitivity {store['sensitivity']}")
    return tags


def workspace_id(store_id: str) -> str | None:
    """Environment-specific ids live in local/bosun.env, never in the model."""
    return os.environ.get("BOSUN_FABRIC_WORKSPACE_ID") if store_id == "portfolio" else None


def readers(model: Model, store_id: str, groups: dict[str, str]) -> dict[str, str]:
    """Group name -> id for everyone the model's read rules let into this store."""
    store = model.stores[store_id]
    wanted = {}
    for rule in model.rules_for("read", store_id):
        if rule["effect"] != "allow":
            continue
        if rule.get("audience") == "DomainMembers":
            wanted[entra.domain_group(model, store["domain"])] = None
        if rule.get("role"):
            wanted[entra.role_group(model, rule["role"])] = None
    return {name: groups.get(name) for name in wanted}


def plan(model: Model) -> list[dict]:
    steps = []
    prefix = entra.prefix(model)
    domains = {d["displayName"]: d["id"] for d in fabric("GET", "/admin/domains").get("domains", [])}
    for domain_id in model.domains:
        name = fabric_domain_name(model, domain_id)
        if name not in domains:
            steps.append({"op": "create-domain", "name": name})

    tags = {t["displayName"]: t["id"] for t in fabric("GET", "/admin/tags").get("value", [])}
    groups = entra.ids(model)
    for store_id, store in model.stores.items():
        if store["kind"] != "Workspace" or not workspace_id(store_id):
            continue
        ws = workspace_id(store_id)
        info = fabric("GET", f"/workspaces/{ws}")
        want_domain = fabric_domain_name(model, store["domain"])
        if domains.get(want_domain) != info.get("domainId"):
            steps.append({"op": "assign-domain", "workspace": ws, "domain": want_domain, "store": store_id})

        current = fabric("GET", f"/workspaces/{ws}/roleAssignments").get("value", [])
        managed = {a["principal"].get("displayName"): a for a in current
                   if a["principal"]["type"] == "Group" and a["principal"].get("displayName", "").startswith(prefix + "-")}
        want = readers(model, store_id, groups)
        for name, gid in want.items():
            if name not in managed:
                steps.append({"op": "grant", "workspace": ws, "group": name, "group_id": gid, "role": "Viewer", "store": store_id})
        for name, assignment in managed.items():
            if name not in want:
                steps.append({"op": "revoke", "workspace": ws, "group": name, "assignment": assignment["id"], "store": store_id})

        for tag in tag_names(model, store):
            if tag not in tags:
                steps.append({"op": "create-tag", "tag": tag})
        items = fabric("GET", f"/workspaces/{ws}/items").get("value", [])
        for item in items:
            have = {t.get("displayName") for t in item.get("tags", []) or []}
            missing = [t for t in tag_names(model, store) if t not in have]
            if missing:
                steps.append({"op": "tag-item", "workspace": ws, "item": item["id"], "item_name": item["displayName"],
                              "tags": missing, "store": store_id})
    return steps


def apply(steps: list[dict]) -> list[str]:
    done = []
    created_tags = sorted({s["tag"] for s in steps if s["op"] == "create-tag"})
    if created_tags:
        fabric("POST", "/admin/tags/bulkCreateTags", {"createTagsRequest": [{"displayName": t} for t in created_tags]})
        done.append(f"create tags {', '.join(created_tags)}")
    tags = {t["displayName"]: t["id"] for t in fabric("GET", "/admin/tags").get("value", [])}
    domains = {d["displayName"]: d["id"] for d in fabric("GET", "/admin/domains").get("domains", [])}
    for step in steps:
        op = step["op"]
        if op == "create-domain":
            fabric("POST", "/admin/domains", {"displayName": step["name"], "description": "Compiled from the Bosun model."})
        elif op == "assign-domain":
            domains = {d["displayName"]: d["id"] for d in fabric("GET", "/admin/domains").get("domains", [])}
            fabric("POST", f"/admin/domains/{domains[step['domain']]}/assignWorkspaces", {"workspacesIds": [step["workspace"]]})
        elif op == "grant":
            fabric("POST", f"/workspaces/{step['workspace']}/roleAssignments",
                   {"principal": {"id": step["group_id"], "type": "Group"}, "role": step["role"]})
        elif op == "revoke":
            fabric("DELETE", f"/workspaces/{step['workspace']}/roleAssignments/{step['assignment']}")
        elif op == "tag-item":
            fabric("POST", f"/workspaces/{step['workspace']}/items/{step['item']}/applyTags",
                   {"tags": [tags[t] for t in step["tags"]]})
        else:
            continue
        done.append(f"{op} {step.get('group') or step.get('item_name') or step.get('domain') or step.get('name')}")
    return done
