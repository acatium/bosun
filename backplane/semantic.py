"""The portfolio store's data path: datasets in the lakehouse, the semantic model, and the data agent.

- A Dataset store whose table is missing is loaded from its file in the repository.
- A Dataset store whose table is missing from the semantic model is added to it (Direct Lake).
- A term with a calculation whose measure is missing is added as a measure, described by the term.
- The data agent's vocabulary is generated from the model's terms, so new terms reach it automatically.
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.request

from .azure import fabric, fabric_lro, token
from .model import ROOT, Model

ONELAKE = "https://onelake.dfs.fabric.microsoft.com"
DAX_TYPES = {"string": "string", "date": "dateTime", "timestamp": "dateTime", "double": "double",
             "integer": "int64", "long": "int64", "boolean": "boolean"}


def env(name: str) -> str:
    return os.environ[name]


def datasets(model: Model) -> list[dict]:
    return [{"id": sid, **s} for sid, s in model.stores.items()
            if s["kind"] == "Dataset" and s.get("within") == "portfolio" and s.get("file") and s.get("table")]


def lakehouse_tables() -> set[str]:
    data = fabric("GET", f"/workspaces/{env('BOSUN_FABRIC_WORKSPACE_ID')}/lakehouses/{env('BOSUN_LAKEHOUSE_ID')}/tables")
    return {t["name"] for t in data.get("data", [])}


def _onelake(method: str, path: str, data: bytes | None = None, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(f"{ONELAKE}/{env('BOSUN_FABRIC_WORKSPACE_ID')}/{env('BOSUN_LAKEHOUSE_ID')}/{path}",
                                 data=data, method=method, headers={
                                     "Authorization": f"Bearer {token('https://storage.azure.com')}",
                                     "x-ms-version": "2023-11-03", **(headers or {})})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


def table_schema(table: str) -> list[tuple[str, str]]:
    log = _onelake("GET", f"Tables/{table}/_delta_log/00000000000000000000.json").decode()
    for line in log.splitlines():
        entry = json.loads(line)
        if "metaData" in entry:
            return [(f["name"], f["type"]) for f in json.loads(entry["metaData"]["schemaString"])["fields"]]
    raise RuntimeError(f"No schema found for {table}")


def semantic_definition() -> dict[str, str]:
    result = fabric_lro("POST", f"/workspaces/{env('BOSUN_FABRIC_WORKSPACE_ID')}/semanticModels/"
                                f"{env('BOSUN_SEMANTIC_MODEL_ID')}/getDefinition?format=TMDL")
    return {p["path"]: base64.b64decode(p["payload"]).decode() for p in result["definition"]["parts"]}


def agent_definition() -> dict[str, str]:
    result = fabric_lro("POST", f"/workspaces/{env('BOSUN_FABRIC_WORKSPACE_ID')}/dataAgents/"
                                f"{env('BOSUN_DATA_AGENT_ID')}/getDefinition")
    return {p["path"]: base64.b64decode(p["payload"]).decode() for p in result["definition"]["parts"]}


def agent_instructions(model: Model) -> str:
    terms = "\n".join(f"- {t['name']}: {t['definition']} (measure: {t['measure']})"
                      for t in model.terms.values() if t.get("measure"))
    return (f"You answer questions about {model.name} portfolio companies using only the measures in the "
            "semantic model. Never compute figures yourself from raw columns.\n"
            "These are the only defined business terms:\n" + terms + "\n"
            "For every figure, state the term and the as-of period. If a question uses a term that is not in "
            "this list, say it is not a defined term and name the closest defined terms instead of guessing. "
            "Amounts are in USD thousands unless the term says otherwise.")


def measures_in(parts: dict[str, str]) -> set[str]:
    found = set()
    for text in parts.values():
        for match in re.finditer(r"^\s*measure\s+('([^']+)'|([^\s=]+))\s*=", text, re.MULTILINE):
            found.add(match.group(2) or match.group(3))
    return found


def plan(model: Model) -> list[dict]:
    steps = []
    loaded = lakehouse_tables()
    for ds in datasets(model):
        if ds["table"] not in loaded:
            steps.append({"op": "load-dataset", "store": ds["id"], "file": ds["file"], "table": ds["table"]})
    parts = semantic_definition()
    tables = {re.sub(r"^definition/tables/|\.tmdl$", "", p) for p in parts if p.startswith("definition/tables/")}
    for ds in datasets(model):
        if ds["table"] not in tables:
            steps.append({"op": "add-table", "store": ds["id"], "table": ds["table"]})
    present = measures_in(parts)
    for term_id, term in model.terms.items():
        if term.get("measure") and term["measure"] not in present:
            if term.get("calculation") and term.get("source"):
                steps.append({"op": "add-measure", "term": term["name"], "measure": term["measure"],
                              "table": model.stores[term["source"]]["table"], "calculation": term["calculation"],
                              "definition": term["definition"]})
            else:
                steps.append({"op": "drift", "term": term["name"],
                              "detail": f"measure '{term['measure']}' is missing and the term has no calculation"})
    current = json.loads(agent_definition().get("Files/Config/published/stage_config.json", "{}")).get("aiInstructions", "")
    if current != agent_instructions(model):
        steps.append({"op": "update-agent-vocabulary", "terms": len([t for t in model.terms.values() if t.get("measure")])})
    return steps


def _load(step: dict) -> None:
    data = (ROOT / step["file"]).read_bytes()
    name = os.path.basename(step["file"])
    path = f"Files/portfolio/{name}"
    _onelake("PUT", f"{path}?resource=file&overwrite=true", b"", {"Content-Length": "0"})
    _onelake("PATCH", f"{path}?action=append&position=0", data, {"Content-Type": "application/octet-stream"})
    _onelake("PATCH", f"{path}?action=flush&position={len(data)}", b"", {"Content-Length": "0"})
    fabric_lro("POST", f"/workspaces/{env('BOSUN_FABRIC_WORKSPACE_ID')}/lakehouses/{env('BOSUN_LAKEHOUSE_ID')}/tables/"
                       f"{step['table']}/load",
               {"relativePath": path, "pathType": "File", "mode": "Overwrite", "recursive": False,
                "formatOptions": {"format": "Csv", "header": True, "delimiter": ","}})


def _table_tmdl(table: str, description: str) -> str:
    lines = [f"/// {description}", f"table {table}", ""]
    for name, dtype in table_schema(table):
        lines += [f"\tcolumn {name}", f"\t\tdataType: {DAX_TYPES.get(dtype, 'string')}",
                  f"\t\tsourceColumn: {name}", "\t\tsummarizeBy: none", ""]
    lines += [f"\tpartition {table} = entity", "\t\tmode: directLake", "\t\tsource",
              f"\t\t\tentityName: {table}", "\t\t\tschemaName: dbo", "\t\t\texpressionSource: DatabaseQuery", ""]
    return "\n".join(lines)


def apply(model: Model, steps: list[dict]) -> list[str]:
    done = []
    for step in [s for s in steps if s["op"] == "load-dataset"]:
        _load(step)
        done.append(f"loaded {step['file']} into {step['table']}")

    model_steps = [s for s in steps if s["op"] in ("add-table", "add-measure")]
    if model_steps:
        parts = semantic_definition()
        for step in [s for s in model_steps if s["op"] == "add-table"]:
            store = model.stores[step["store"]]
            parts[f"definition/tables/{step['table']}.tmdl"] = _table_tmdl(step["table"], store["name"])
            parts["definition/model.tmdl"] = parts["definition/model.tmdl"].rstrip("\n") + f"\nref table {step['table']}\n"
            columns = {c for c, _ in table_schema(step["table"])}
            if "company_id" in columns and "definition/tables/companies.tmdl" in parts:
                parts["definition/relationships.tmdl"] = parts.get("definition/relationships.tmdl", "").rstrip("\n") + (
                    f"\n\nrelationship {step['table']}_company\n\tfromColumn: {step['table']}.company_id\n"
                    f"\ttoColumn: companies.company_id\n")
            done.append(f"added table {step['table']} to the semantic model")
        for step in [s for s in model_steps if s["op"] == "add-measure"]:
            path = f"definition/tables/{step['table']}.tmdl"
            text = parts[path]
            measure = (f"\t/// {step['definition']}\n\tmeasure '{step['measure']}' = {step['calculation']}\n"
                       f"\t\tformatString: 0.0%\n\n")
            header_end = text.index("\n\n", text.index(f"table {step['table']}")) + 2
            parts[path] = text[:header_end] + measure + text[header_end:]
            done.append(f"added measure '{step['measure']}' for term {step['term']}")
        fabric_lro("POST", f"/workspaces/{env('BOSUN_FABRIC_WORKSPACE_ID')}/semanticModels/"
                           f"{env('BOSUN_SEMANTIC_MODEL_ID')}/updateDefinition",
                   {"definition": {"parts": [{"path": k, "payload": base64.b64encode(v.encode()).decode(),
                                              "payloadType": "InlineBase64"} for k, v in parts.items()]}})

    if any(s["op"] == "update-agent-vocabulary" for s in steps):
        parts = agent_definition()
        for stage in ("draft", "published"):
            key = f"Files/Config/{stage}/stage_config.json"
            config = json.loads(parts.get(key, "{}"))
            config["aiInstructions"] = agent_instructions(model)
            config.setdefault("$schema", "1.0.0")
            parts[key] = json.dumps(config, indent=2)
        fabric_lro("POST", f"/workspaces/{env('BOSUN_FABRIC_WORKSPACE_ID')}/dataAgents/"
                           f"{env('BOSUN_DATA_AGENT_ID')}/updateDefinition",
                   {"definition": {"parts": [{"path": k, "payload": base64.b64encode(v.encode()).decode(),
                                              "payloadType": "InlineBase64"} for k, v in parts.items()]}})
        done.append("regenerated the data agent's vocabulary from the model")
    return done
