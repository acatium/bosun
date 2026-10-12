"""Fails the build if any denied term appears in tracked files, commit messages or history.

The terms come only from the DENYLIST Actions secret (one term per line or comma-separated).
They are never stored in this repository, and matches are reported by file and term number,
never by the term itself. If the secret is unavailable (for example on pull requests from forks),
the check fails closed.
"""
import os
import re
import subprocess
import sys

raw = os.environ.get("DENYLIST", "")
terms = [t.strip().lower() for t in re.split(r"[\n,]", raw) if t.strip()]
if not terms:
    print("::error::DENYLIST secret is not available. Failing closed.")
    sys.exit(1)

def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout

findings: list[str] = []

# Current tracked files
for path in git("ls-files").splitlines():
    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            text = handle.read().lower()
    except (IsADirectoryError, FileNotFoundError):
        continue
    for number, term in enumerate(terms, start=1):
        if term in text:
            findings.append(f"file {path}: denied term #{number}")

# Full history: every patch, commit message and author name ever committed
history = git("log", "--all", "-p", "--format=%H%n%an%n%B").lower()
for number, term in enumerate(terms, start=1):
    if term in history:
        findings.append(f"git history: denied term #{number} (a past commit contains it)")

if findings:
    for finding in findings:
        print(f"::error::{finding}")
    sys.exit(1)
print(f"Deny-list scan passed: {len(terms)} terms checked across files and full history.")
