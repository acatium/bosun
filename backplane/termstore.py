"""Business terms in SharePoint's term store: the same vocabulary the semantic model's measures use.

One term group per firm, with a term set for domains and one for business terms. Term descriptions
carry the model's definitions, so a person reading the term store reads the agreed meaning.
"""
from __future__ import annotations

from .azure import m365
from .model import Model

SETS = ("Domains", "Business terms")


def stored_name(name: str) -> str:
    """SharePoint stores '&' in term names as the full-width '\uff06'."""
    return name.replace("&", "\uff06")


def desired(model: Model) -> dict[str, dict[str, str]]:
    return {
        "Domains": {d["name"]: d.get("description", "") for d in model.domains.values()},
        "Business terms": {t["name"]: t["definition"] for t in model.terms.values()},
    }


def plan(model: Model) -> list[dict]:
    group = model.name
    steps = []
    groups = {g["Name"] for g in m365("spo", "term", "group", "list")}
    if group not in groups:
        steps.append({"op": "create-group", "group": group})
    for set_name, terms in desired(model).items():
        existing = {}
        if group in groups:
            sets = {s["Name"] for s in m365("spo", "term", "set", "list", "--termGroupName", group)}
            if set_name in sets:
                existing = {t["Name"]: t.get("Description", "")
                            for t in m365("spo", "term", "list", "--termGroupName", group, "--termSetName", set_name)}
            else:
                steps.append({"op": "create-set", "group": group, "set": set_name})
        else:
            steps.append({"op": "create-set", "group": group, "set": set_name})
        for name, description in terms.items():
            if stored_name(name) not in existing:
                steps.append({"op": "create-term", "group": group, "set": set_name, "term": name, "description": description})
            elif existing[stored_name(name)] != description:
                steps.append({"op": "drift", "group": group, "set": set_name, "term": name,
                              "detail": "description differs from the model"})
    return steps


def apply(steps: list[dict]) -> list[str]:
    done = []
    for step in steps:
        if step["op"] == "create-group":
            m365("spo", "term", "group", "add", "--name", step["group"],
                 "--description", "Compiled from the Bosun model. Do not edit by hand.")
        elif step["op"] == "create-set":
            m365("spo", "term", "set", "add", "--name", step["set"], "--termGroupName", step["group"])
        elif step["op"] == "create-term":
            m365("spo", "term", "add", "--name", step["term"], "--termSetName", step["set"],
                 "--termGroupName", step["group"], "--description", step["description"])
        else:
            continue
        done.append(f"{step['op']} {step.get('term') or step.get('set') or step.get('group')}")
    return done
