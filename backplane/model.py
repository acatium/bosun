"""Load the LinkML model and check what LinkML's validators do not: that every reference resolves.

LinkML validation (run in CI and by `backplane validate`) checks types, enums, required fields and patterns.
It does not check that a rule's role or a term's owner actually exists, so that check lives here.
"""
from __future__ import annotations

import pathlib
import subprocess
from dataclasses import dataclass, field

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "model" / "bosun.yaml"
DEFAULT_MODEL = ROOT / "model" / "contoso.yaml"

# Which collection each reference slot points into.
REFERENCES = {
    "domains": {"parent": "domains", "owner": "roles"},
    "roles": {"domain": "domains"},
    "terms": {"domain": "domains", "owner": "roles", "source": "stores"},
    "stores": {"domain": "domains", "within": "stores"},
    "rules": {"role": "roles", "store": "stores"},
}


@dataclass
class Model:
    name: str
    domains: dict[str, dict] = field(default_factory=dict)
    roles: dict[str, dict] = field(default_factory=dict)
    terms: dict[str, dict] = field(default_factory=dict)
    stores: dict[str, dict] = field(default_factory=dict)
    rules: dict[str, dict] = field(default_factory=dict)

    def departments(self, domain_id: str) -> list[str]:
        return sorted({r["department"] for r in self.roles.values() if r["domain"] == domain_id})

    def rules_for(self, action: str, store_id: str | None = None) -> list[dict]:
        return [r for r in self.rules.values()
                if r["action"] == action and r.get("store") in (None, store_id)]


def linkml_validate(path: pathlib.Path) -> tuple[bool, str]:
    """Run LinkML's own validator against the schema."""
    exe = ROOT / "model" / ".venv" / "bin" / "linkml"
    result = subprocess.run([str(exe), "validate", "--schema", str(SCHEMA), "--target-class", "Firm", str(path)],
                            capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0 and "No issues found" in output, output


def load(path: pathlib.Path = DEFAULT_MODEL) -> Model:
    data = yaml.safe_load(path.read_text())
    model = Model(name=data["name"])
    for collection in REFERENCES:
        setattr(model, collection, {item["id"]: item for item in data.get(collection, [])})
    return model


def reference_errors(model: Model) -> list[str]:
    errors = []
    for collection, slots in REFERENCES.items():
        for item_id, item in getattr(model, collection).items():
            for slot, target in slots.items():
                value = item.get(slot)
                if value is not None and value not in getattr(model, target):
                    errors.append(f"{collection}/{item_id}: {slot} '{value}' is not a defined {target[:-1]}")
    return errors
