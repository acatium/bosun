"""Bosun gateway: the orchestrator's only route to store agents.

Runs locally as a stdio MCP server, as the signed-in user. It holds no keys: each call carries the user's own
Entra token, so the store decides who may invoke its agent. On top of that, it applies one deterministic
rule before an answer reaches the model: every figure must be tied to a business glossary term, and the
answer must state an as-of month. Answers that break the rule are blocked with the reason. Every call is
logged, whatever the outcome.
"""
import base64
import json
import os
import pathlib
import re
import subprocess
import time
import urllib.error
import urllib.request

import yaml
from mcp.server.mcpserver import MCPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
STORES = yaml.safe_load((ROOT / "config/stores.yaml").read_text())["stores"]
GLOSSARY = yaml.safe_load((ROOT / "config/glossary.yaml").read_text())["terms"]
TERMS = sorted({t["term"].lower() for t in GLOSSARY} | {t["measure"].lower() for t in GLOSSARY}, key=len, reverse=True)
LOG = pathlib.Path(os.environ.get("BOSUN_ACTION_LOG", ROOT / "local/agent-actions.jsonl"))

MONTH = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}\b|\b\d{4}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b",
    re.IGNORECASE,
)
FIGURE = re.compile(r"[-−+]?\$?\d[\d,]*(\.\d+)?\s*(%|x\b|k\b|m\b|bn\b)?", re.IGNORECASE)
LIST_MARKER = re.compile(r"^\s*(\d+[.)]|[-*•])\s+")


def user_token() -> str:
    """The signed-in user's Fabric token from their own Azure CLI session. Never stored."""
    return subprocess.run(
        ["az", "account", "get-access-token", "--resource", "https://api.fabric.microsoft.com",
         "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def caller(token: str) -> str:
    payload = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    return claims.get("upn") or claims.get("unique_name") or claims.get("oid", "unknown")


def figures_in(line: str) -> list[str]:
    """Numbers that state a quantity, ignoring list markers and dates."""
    text = MONTH.sub(" ", LIST_MARKER.sub("", line))
    return [m.group(0).strip() for m in FIGURE.finditer(text)]


def check(answer: str) -> list[str]:
    """The deterministic rule. Returns the reasons to block; an empty list means the answer passes."""
    reasons = []
    if not MONTH.search(answer):
        reasons.append("the answer does not state an as-of month")
    for line in answer.splitlines():
        if figures_in(line) and not any(term in line.lower() for term in TERMS):
            reasons.append(f"figure without a glossary term: {line.strip()[:160]}")
    return reasons


def ask_store(store: dict, question: str) -> str:
    agent = store["agent"]
    url = (f"https://api.fabric.microsoft.com/v1/mcp/workspaces/{os.environ[agent['workspace_id_env']]}"
           f"/dataagents/{os.environ[agent['agent_id_env']]}/agent")
    started, record = time.time(), {"store": store["key"], "question": question}
    try:
        token = user_token()
        record["user"] = caller(token)
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "DataAgent_" + store["name"].replace(" ", "_") + "_Agent",
            "arguments": {"userQuestion": question}}}).encode()
        request = urllib.request.Request(url, data=body, method="POST", headers={
            "Authorization": f"Bearer {token}", "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"})
        try:
            with urllib.request.urlopen(request, timeout=280) as response:
                reply = json.loads(response.read())
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                record.update(verdict="refused", reason=f"store returned HTTP {error.code}")
                return (f"REFUSED by {store['name']}: you are not on this store's access list "
                        f"({store['access_group']}). Ask the {store['domain']} domain owner for access.")
            raise
        if reply.get("error", {}).get("data", {}).get("errorCode") == "Unauthorized":
            record.update(verdict="refused", reason=reply["error"].get("message"))
            return (f"REFUSED by {store['name']}: you are not on this store's access list "
                    f"({store['access_group']}). Ask the {store['domain']} domain owner for access.")
        if "error" in reply:
            record.update(verdict="error", reason=json.dumps(reply["error"])[:300])
            return f"ERROR from {store['name']}: {reply['error'].get('message')}"
        answer = "\n".join(c.get("text", "") for c in reply["result"]["content"])
        reasons = check(answer)
        if reasons:
            record.update(verdict="blocked", reason=reasons)
            return "BLOCKED by the Bosun guardrail. The store's answer was withheld because:\n- " + "\n- ".join(reasons)
        record.update(verdict="passed")
        return answer
    except Exception as error:  # fail closed: nothing unchecked reaches the model
        record.update(verdict="error", reason=repr(error)[:300])
        return f"ERROR: the gateway could not complete the call ({type(error).__name__}). Nothing was returned."
    finally:
        record.update(ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), seconds=round(time.time() - started, 1))
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as handle:
            handle.write(json.dumps(record) + "\n")


server = MCPServer("bosun-gateway", instructions="Route questions to Contoso Capital store agents. Answers are checked against the business glossary.")

for _store in STORES:
    def _tool(question: str, store=_store) -> str:
        return ask_store(store, question)
    server.add_tool(_tool, name="ask_" + _store["key"].replace("-", "_"),
                    description=f"Ask the {_store['name']} store agent. {_store['description']}")

if __name__ == "__main__":
    server.run("stdio")
