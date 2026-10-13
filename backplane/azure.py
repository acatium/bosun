"""Thin wrappers over Microsoft's own CLIs. The backplane never holds credentials: `az` and `m365` use the
signed-in person's session."""
from __future__ import annotations

import json
import subprocess

GRAPH = "https://graph.microsoft.com/v1.0"
FABRIC = "https://api.fabric.microsoft.com/v1"


class CommandError(RuntimeError):
    pass


def _run(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise CommandError(f"{' '.join(args[:4])}...: {result.stderr.strip()[:500]}")
    return result.stdout


def az_rest(method: str, url: str, body: dict | None = None, resource: str | None = None) -> dict:
    args = ["az", "rest", "--method", method, "--url", url, "-o", "json"]
    if resource:
        args += ["--resource", resource]
    if body is not None:
        args += ["--headers", "Content-Type=application/json", "--body", json.dumps(body)]
    out = _run(args).strip()
    return json.loads(out) if out else {}


def graph(method: str, path: str, body: dict | None = None) -> dict:
    return az_rest(method, GRAPH + path, body)


def fabric(method: str, path: str, body: dict | None = None) -> dict:
    return az_rest(method, FABRIC + path, body, resource="https://api.fabric.microsoft.com")


def m365(*args: str, connection: str | None = None) -> dict | list | str:
    cmd = ["m365", *args, "--output", "json"]
    if connection:
        _run(["m365", "connection", "use", "--name", connection])
    out = _run(cmd).strip()
    try:
        return json.loads(out) if out else {}
    except json.JSONDecodeError:
        return out


def token(resource: str) -> str:
    return _run(["az", "account", "get-access-token", "--resource", resource, "--query", "accessToken", "-o", "tsv"]).strip()


def fabric_lro(method: str, path: str, body: dict | None = None, timeout: int = 300) -> dict:
    """Fabric calls that may answer 202 Accepted: follow the operation until it finishes and return its result."""
    import time
    import urllib.request

    def request(m: str, url: str, payload: dict | None = None):
        req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None, method=m,
                                     headers={"Authorization": f"Bearer {token('https://api.fabric.microsoft.com')}",
                                              "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as response:
            text = response.read().decode()
            return response.status, response.headers, (json.loads(text) if text.strip() else {})

    status, headers, data = request(method, FABRIC + path, body)
    if status != 202:
        return data
    operation = headers.get("x-ms-operation-id")
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(3)
        _, _, state = request("GET", f"{FABRIC}/operations/{operation}")
        if state.get("status") == "Succeeded":
            try:
                return request("GET", f"{FABRIC}/operations/{operation}/result")[2]
            except Exception:
                return {}
        if state.get("status") == "Failed":
            raise CommandError(f"Fabric operation failed: {json.dumps(state.get('error'))[:500]}")
    raise CommandError("Fabric operation timed out")
