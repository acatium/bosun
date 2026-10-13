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

from .azure import az_rest, fabric, fabric_lro, token
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
            "For every figure, state the term and its exact as-of date. Unless the question names a period, report "
            "monthly terms for the latest month in the data only, never summed across months, and report any other term "
            "as of the latest date its data covers. If a question uses a term that is not in "
            "this list, say it is not a defined term and name the closest defined terms, without figures, instead of guessing. "
            "Amounts are in USD thousands unless the term says otherwise.")


def datasource_instructions(model: Model) -> str:
    measures = ", ".join(t["measure"] for t in model.terms.values() if t.get("measure"))
    return f"Answer with the model's measures ({measures}). Filter companies by companies[company_name]."


def measures_in(parts: dict[str, str]) -> set[str]:
    found = set()
    for text in parts.values():
        for match in re.finditer(r"^\s*measure\s+('([^']+)'|([^\s=]+))\s*=", text, re.MULTILINE):
            found.add(match.group(2) or match.group(3))
    return found


def normalise(expression: str) -> str:
    return re.sub(r"\s+", "", expression)


def measure_expressions(parts: dict[str, str]) -> dict[str, str]:
    """Single-line measure expressions by name (multi-line measures are compared as their first line)."""
    found = {}
    for text in parts.values():
        for match in re.finditer(r"^\s*measure\s+('([^']+)'|([^\s=]+))\s*=\s*(.*)$", text, re.MULTILINE):
            found[match.group(2) or match.group(3)] = match.group(4)
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
    expressions = measure_expressions(parts)
    for term_id, term in model.terms.items():
        if term.get("measure") in present and term.get("calculation"):
            if normalise(expressions.get(term["measure"], "")) != normalise(term["calculation"]):
                steps.append({"op": "drift", "term": term["name"],
                              "detail": f"measure '{term['measure']}' differs from the model's calculation"})
        if term.get("measure") and term["measure"] not in present:
            if term.get("calculation") and term.get("source"):
                steps.append({"op": "add-measure", "term": term["name"], "measure": term["measure"],
                              "table": model.stores[term["source"]]["table"], "calculation": term["calculation"],
                              "definition": term["definition"], "format": term.get("format_string") or "#,0.00"})
            else:
                steps.append({"op": "drift", "term": term["name"],
                              "detail": f"measure '{term['measure']}' is missing and the term has no calculation"})
    agent = agent_definition()
    for path, text in agent.items():
        if path.endswith("datasource.json"):
            selected = {e["display_name"] for e in json.loads(text).get("elements", []) if e.get("is_selected")}
            for ds in datasets(model):
                if ds["table"] not in selected:
                    steps.append({"op": "agent-add-table", "table": ds["table"], "path": path})
    current = json.loads(agent.get("Files/Config/published/stage_config.json", "{}")).get("aiInstructions", "")
    sources = [json.loads(text).get("dataSourceInstructions") for path, text in agent.items() if path.endswith("datasource.json")]
    if current != agent_instructions(model) or any(s != datasource_instructions(model) for s in sources):
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
                       f"\t\tformatString: {step['format']}\n\n")
            header_end = text.index("\n\n", text.index(f"table {step['table']}")) + 2
            parts[path] = text[:header_end] + measure + text[header_end:]
            done.append(f"added measure '{step['measure']}' for term {step['term']}")
        # The SQL endpoint must see new tables before Direct Lake can read them.
        fabric_lro("POST", f"/workspaces/{env('BOSUN_FABRIC_WORKSPACE_ID')}/sqlEndpoints/"
                           f"{env('BOSUN_SQL_ENDPOINT_ID')}/refreshMetadata", {})
        fabric_lro("POST", f"/workspaces/{env('BOSUN_FABRIC_WORKSPACE_ID')}/semanticModels/"
                           f"{env('BOSUN_SEMANTIC_MODEL_ID')}/updateDefinition",
                   {"definition": {"parts": [{"path": k, "payload": base64.b64encode(v.encode()).decode(),
                                              "payloadType": "InlineBase64"} for k, v in parts.items()]}})

    if model_steps:
        az_rest("POST", f"https://api.powerbi.com/v1.0/myorg/groups/{env('BOSUN_FABRIC_WORKSPACE_ID')}/datasets/"
                        f"{env('BOSUN_SEMANTIC_MODEL_ID')}/refreshes", {"type": "full"},
                resource="https://analysis.windows.net/powerbi/api")
        done.append("refreshed the semantic model so the new table and measure are queryable")

    agent_steps = [s for s in steps if s["op"] in ("agent-add-table", "update-agent-vocabulary")]
    if agent_steps:
        parts = agent_definition()
        for step in [s for s in agent_steps if s["op"] == "agent-add-table"]:
            source = json.loads(parts[step["path"]])
            source.setdefault("elements", []).append({"id": None, "is_selected": True, "display_name": step["table"],
                                                      "type": "semantic_model.table", "description": None, "children": []})
            parts[step["path"]] = json.dumps(source, indent=2)
            done.append(f"let the data agent see table {step['table']} ({step['path'].split('/')[2]})")
        for path in [p for p in parts if p.endswith("datasource.json")]:
            source = json.loads(parts[path])
            source["dataSourceInstructions"] = datasource_instructions(model)
            parts[path] = json.dumps(source, indent=2)
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
        if any(s["op"] == "update-agent-vocabulary" for s in agent_steps):
            done.append("regenerated the data agent's vocabulary from the model")
    return done
