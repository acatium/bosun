"""Ask the portfolio data agent the reviewed questions, as whoever is signed in to `az`, and check the answers.

    python evals/run_golden.py                  # the signed-in person should be answered
    python evals/run_golden.py --expect-denied  # the signed-in person should be refused by Fabric

Expected values live in golden-questions.yaml and come from DAX against the semantic model, never from the
agent. A figure passes when its expected text appears in the answer; a ranking also needs the companies in
the expected order; a refusal passes when the answer says the term is not defined and gives no figures.
Prints a Markdown report and exits non-zero on any failure.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backplane.azure import token  # noqa: E402

TOOL = "DataAgent_Contoso_Portfolio_Agent"


def ask(question: str) -> tuple[int, str]:
    url = (f"https://api.fabric.microsoft.com/v1/mcp/workspaces/{os.environ['BOSUN_FABRIC_WORKSPACE_ID']}"
           f"/dataagents/{os.environ['BOSUN_DATA_AGENT_ID']}/agent")
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": TOOL, "arguments": {"userQuestion": question}}}
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {token('https://api.fabric.microsoft.com')}",
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            reply = json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode(errors="replace")[:500]
    if "result" in reply:
        return 200, reply["result"]["content"][0]["text"]
    return 200, json.dumps(reply.get("error", reply))[:500]


def check(case: dict, answer: str) -> list[str]:
    expected, problems = case["expected"], []
    answer = answer.replace("\u2212", "-")  # agents sometimes write a typographic minus
    if "refusal" in expected:
        if "not a defined" not in answer.lower():
            problems.append("does not say the term is undefined")
        if re.search(r"\d+(\.\d+)?\s?%", answer) or re.search(r":\s*-?[\d,.]+\b", answer):
            problems.append("gives figures instead of naming terms")
        return problems
    positions = []
    for company, value in expected.items():
        if company not in answer:
            problems.append(f"{company} missing")
            continue
        if value not in answer and value.lstrip("+") not in answer:
            problems.append(f"{company}: expected {value}")
        positions.append(answer.index(company))
    if len(expected) > 1 and positions != sorted(positions):
        problems.append("ranking out of order")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect-denied", action="store_true")
    args = parser.parse_args()
    suite = yaml.safe_load((Path(__file__).parent / "golden-questions.yaml").read_text())
    failures = 0
    print(f"| Question | Result | Detail |\n|---|---|---|")
    transcripts = []
    for case in suite["questions"]:
        status, answer = ask(case["question"])
        if args.expect_denied:
            denied = status in (401, 403) or "not authorized" in answer.lower() or "unauthorized" in answer.lower()
            problems = [] if denied else ["answered someone who should be refused"]
        else:
            problems = [f"HTTP {status}"] if status != 200 else check(case, answer)
        failures += bool(problems)
        print(f"| {case['id']} | {'Fail' if problems else 'Pass'} | {'; '.join(problems) or '-'} |")
        transcripts.append(f"### {case['question']}\n\n{answer.strip()}\n")
    print("\n## Answers\n\n" + "\n".join(transcripts))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
