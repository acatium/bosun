"""Fails if environment-specific values are hard-coded anywhere in the repository.

Tenant IDs, subscription IDs, client IDs, the tenant's email domain, its SharePoint host and the GitHub owner belong in .env (local, gitignored)
and GitHub repository variables, never in tracked files. This keeps the repository portable:
any firm can adopt it as a template without inheriting another firm's identifiers.
"""
import os
import re
import subprocess
import sys

GUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
WELL_KNOWN_GUIDS = {
    "00000003-0000-0000-c000-000000000000",  # Microsoft Graph's public application ID
}
# Files that legitimately name the current owner. Both are listed in PORTING.md as files to update.
EXEMPT = {"LICENSE", ".github/CODEOWNERS"}

values = {
    name: os.environ.get(name, "").strip().lower()
    for name in ("AZURE_TENANT_ID", "AZURE_SUBSCRIPTION_ID", "AZURE_CLIENT_ID", "GITHUB_OWNER", "TENANT_DOMAIN", "SHAREPOINT_HOST")
}

tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.splitlines()
findings: list[str] = []
for path in tracked:
    if path in EXEMPT:
        continue
    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            text = handle.read().lower()
    except (IsADirectoryError, FileNotFoundError):
        continue
    for guid in sorted(set(GUID.findall(text)) - WELL_KNOWN_GUIDS):
        findings.append(f"{path}: hard-coded GUID {guid[:8]}... (move it to .env or a repository variable)")
    for name, value in values.items():
        if value and value in text:
            findings.append(f"{path}: contains the value of {name}")

if findings:
    for finding in findings:
        print(f"::error::{finding}")
    sys.exit(1)
print(f"Portability check passed: {len(tracked)} tracked files contain no environment-specific identifiers.")
