"""Deterministic guardrail checks. Any violation fails the build.

Checks:
  1. The firm profile is internally consistent (prefix valid, keys well-formed, owners and domains exist).
  2. Infrastructure declares only allowed Azure resource types and carries required tags.
  3. The bootstrap script requests only allowed Microsoft Graph permissions.
"""
import os
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
errors: list[str] = []

guardrails = yaml.safe_load((ROOT / "config/guardrails.yaml").read_text())
profile_name = os.environ.get("FIRM_PROFILE") or "contoso"
profile_path = ROOT / "config" / "profiles" / f"{profile_name}.yaml"
if not profile_path.exists():
    print(f"Guardrail check FAILED:\n  - firm profile {profile_path.relative_to(ROOT)} does not exist")
    sys.exit(1)
org = yaml.safe_load(profile_path.read_text())
where = profile_path.relative_to(ROOT)

# 1. Firm profile
prefix = str(org.get("firm", {}).get("prefix", ""))
if not re.match(guardrails["prefix_pattern"], prefix):
    errors.append(f"{where}: firm prefix '{prefix}' must match {guardrails['prefix_pattern']}")

key_pattern = re.compile(r"^[a-z][a-z0-9-]*$")
domains = {d["key"]: d for d in org.get("domains", [])}
personas = {p["key"]: p for p in org.get("personas", [])}

for kind, items in (("domain", domains), ("persona", personas)):
    for key in items:
        if not key_pattern.match(key):
            errors.append(f"{where}: {kind} key '{key}' must be lowercase letters, digits and hyphens")

for key, domain in domains.items():
    if domain.get("owner") not in personas:
        errors.append(f"{where}: domain '{key}' has owner '{domain.get('owner')}', which is not a defined persona")

for key, persona in personas.items():
    if persona.get("domain") not in domains:
        errors.append(f"{where}: persona '{key}' belongs to domain '{persona.get('domain')}', which is not defined")

# 2. Infrastructure
allowed_types = set(guardrails["allowed_azure_resource_types"])
resource_pattern = re.compile(r"^\s*resource\s+\w+\s+'([^'@]+)@", re.MULTILINE)
for bicep in sorted((ROOT / "infra").rglob("*.bicep")):
    text = bicep.read_text()
    rel = bicep.relative_to(ROOT)
    for resource_type in resource_pattern.findall(text):
        if resource_type not in allowed_types:
            errors.append(f"{rel}: resource type '{resource_type}' is not in the allowlist")
    for tag in guardrails["required_tags"]:
        if not re.search(rf"\b{re.escape(tag)}\s*:", text):
            errors.append(f"{rel}: required tag '{tag}' is missing")

# 3. Bootstrap Graph permissions
allowed_graph = set(guardrails["allowed_graph_application_permissions"])
bootstrap = (ROOT / "bootstrap/bootstrap.ps1").read_text()
match = re.search(r"\$GraphPermissions\s*=\s*@\(([^)]*)\)", bootstrap)
if not match:
    errors.append("bootstrap/bootstrap.ps1: could not find the $GraphPermissions list")
else:
    requested = set(re.findall(r"'([^']+)'", match.group(1)))
    for permission in sorted(requested - allowed_graph):
        errors.append(f"bootstrap/bootstrap.ps1: Graph permission '{permission}' is not in the allowlist")

if errors:
    print("Guardrail check FAILED:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
print(f"Guardrail check passed for profile '{profile_name}': {len(domains)} domains, {len(personas)} personas, infrastructure and bootstrap within allowlists.")
