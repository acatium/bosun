"""Identity and group membership: one dynamic group per domain and per titled role.

Membership is never managed by hand: it follows the directory attributes the HR system sets
(company, department, job title).
"""
from __future__ import annotations

from .azure import graph
from .model import Model


def prefix(model: Model) -> str:
    return model.name.split()[0].lower()


def domain_group(model: Model, domain_id: str) -> str:
    return f"{prefix(model)}-domain-{domain_id}"


def role_group(model: Model, role_id: str) -> str:
    return f"{prefix(model)}-role-{role_id}"


def desired(model: Model) -> dict[str, dict]:
    company = f'(user.companyName -eq "{model.name}")'
    groups = {}
    for domain_id, domain in model.domains.items():
        departments = model.departments(domain_id)
        if not departments:
            continue
        in_list = ", ".join(f'"{d}"' for d in departments)
        groups[domain_group(model, domain_id)] = {
            "rule": f"{company} -and (user.department -in [{in_list}])",
            "description": f"{model.name}: members of the {domain['name']} domain. Compiled from the model; do not edit.",
        }
    for role_id, role in model.roles.items():
        if role.get("job_title"):
            groups[role_group(model, role_id)] = {
                "rule": f'{company} -and (user.department -eq "{role["department"]}") -and (user.jobTitle -eq "{role["job_title"]}")',
                "description": f"{model.name}: people in the {role['name']} role. Compiled from the model; do not edit.",
            }
    return groups


def actual(model: Model) -> dict[str, dict]:
    found = graph("GET", f"/groups?$filter=startswith(displayName,'{prefix(model)}-')"
                         f"&$select=id,displayName,groupTypes,membershipRule&$top=999")
    return {g["displayName"]: g for g in found.get("value", [])}


def plan(model: Model) -> list[dict]:
    want, have = desired(model), actual(model)
    steps = []
    for name, spec in want.items():
        current = have.get(name)
        if current is None:
            steps.append({"op": "create", "group": name, **spec})
        elif "DynamicMembership" not in current.get("groupTypes", []) or current.get("membershipRule") != spec["rule"]:
            steps.append({"op": "update", "group": name, "id": current["id"], **spec})
    managed_prefixes = (f"{prefix(model)}-domain-", f"{prefix(model)}-role-")
    for name in have:
        if name.startswith(managed_prefixes) and name not in want:
            steps.append({"op": "drift", "group": name, "detail": "group not in the model"})
    return steps


def apply(steps: list[dict]) -> list[str]:
    done = []
    for step in [s for s in steps if s["op"] != "drift"]:
        body = {"groupTypes": ["DynamicMembership"], "membershipRule": step["rule"],
                "membershipRuleProcessingState": "On", "description": step["description"]}
        if step["op"] == "create":
            graph("POST", "/groups", {**body, "displayName": step["group"], "mailEnabled": False,
                                      "mailNickname": step["group"], "securityEnabled": True})
        else:
            graph("PATCH", f"/groups/{step['id']}", body)
        done.append(f"{step['op']} group {step['group']}")
    return done


def ids(model: Model) -> dict[str, str]:
    return {name: g["id"] for name, g in actual(model).items()}
