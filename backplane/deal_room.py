"""Open a deal room for the person asking, as that person.

Order of work: check the model's rules, then create the Microsoft 365 group with its sensitivity label,
add the team, set the library's default tags, file the CIM, and write a receipt. Every effect uses the
caller's own delegated token, so nothing here can do more than the caller could do by hand.
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

from .generated import DealRoomRequest
from .model import ROOT, Model

GRAPH = "https://graph.microsoft.com/v1.0"
RECEIPTS = pathlib.Path(os.environ.get("BOSUN_RECEIPTS", ROOT / "local" / "receipts" / "deal-rooms.jsonl"))
STORE = "deal-room"


class Refused(Exception):
    """A rule in the model said no. The message names the rule."""


def token(resource: str) -> str:
    out = subprocess.run(["m365", "util", "accesstoken", "get", "--resource", resource, "--new", "--output", "text"],
                         capture_output=True, text=True, check=True).stdout.strip()
    return out.strip('"')


def call(method: str, url: str, body=None, resource: str = "https://graph.microsoft.com",
         raw: bytes | None = None, headers: dict | None = None) -> dict:
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    request = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token(resource)}", "Accept": "application/json",
        "Content-Type": "application/octet-stream" if raw is not None else "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            text = response.read().decode() or "{}"
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:300]
        raise urllib.error.HTTPError(error.url, error.code, f"{error.reason}: {detail}", error.headers, None) from None
    return json.loads(text) if text.strip().startswith(("{", "[")) else {}


def caller_roles(model: Model, me: dict) -> list[str]:
    return [role_id for role_id, role in model.roles.items()
            if role.get("department") == me.get("department")
            and role.get("job_title") in (None, me.get("jobTitle"))]


def check_open(model: Model, roles: list[str]) -> str:
    """Return the id of the rule that allows opening a deal room, or raise Refused."""
    rules = model.rules_for("open", STORE)
    for rule in rules:
        if rule["effect"] == "deny" and rule.get("role") in (None, *roles):
            raise Refused(f"{rule['description']} (rule: {rule['id']})")
    for rule in rules:
        if rule["effect"] == "allow" and rule.get("role") in (None, *roles):
            return rule["id"]
    raise Refused("No rule lets your role open a deal room.")


def check_member(model: Model, sensitivity: str, member_kind: str, who: str) -> None:
    for rule in model.rules_for("add_member", STORE):
        if (rule["effect"] == "deny" and rule.get("sensitivity") in (None, sensitivity)
                and rule.get("member_kind") in (None, member_kind)):
            raise Refused(f"Cannot add {who}: {rule['description']} (rule: {rule['id']})")


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def label_id(sensitivity: str) -> str | None:
    return os.environ.get(f"BOSUN_LABEL_{sensitivity.upper()}")


def receipt(record: dict) -> None:
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with RECEIPTS.open("a") as handle:
        handle.write(json.dumps(record) + "\n")


def create(model: Model, request: DealRoomRequest) -> dict:
    sensitivity = request.sensitivity.value if hasattr(request.sensitivity, "value") else str(request.sensitivity)
    store = model.stores[STORE]
    domain_name = model.domains[store["domain"]]["name"]
    steps: list[dict] = []
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tool": "create_deal_room",
              "request": request.model_dump(mode="json"), "steps": steps}
    try:
        me = call("GET", f"{GRAPH}/me?$select=id,userPrincipalName,displayName,department,jobTitle")
        record["caller"] = me["userPrincipalName"]
        roles = caller_roles(model, me)
        steps.append({"step": "rule-check", "roles": roles, "allowed_by": check_open(model, roles)})

        tenant_domain = me["userPrincipalName"].split("@", 1)[1].lower()
        for email in request.members:  # every member is checked against the rules before anything else happens
            kind = "Member" if email.lower().endswith("@" + tenant_domain) else "Guest"
            check_member(model, sensitivity, kind, email)
        member_ids = [call("GET", f"{GRAPH}/users/{urllib.parse.quote(email)}?$select=id")["id"]
                      for email in request.members]
        steps.append({"step": "member-check", "members": request.members, "result": "all permitted"})

        group_body = {
            "displayName": request.name, "mailNickname": f"deal-{slug(request.name)}",
            "description": f"{model.name} deal room ({STORE}). Domain: {domain_name}. Sensitivity: {sensitivity}.",
            "groupTypes": ["Unified"], "mailEnabled": True, "securityEnabled": False,
            "visibility": "Private" if sensitivity != "Public" else "Public",
            "owners@odata.bind": [f"{GRAPH}/users/{me['id']}"],
            "members@odata.bind": [f"{GRAPH}/users/{i}" for i in [me["id"], *member_ids]],
        }
        if label_id(sensitivity):
            group_body["assignedLabels"] = [{"labelId": label_id(sensitivity)}]
        try:
            group = call("POST", f"{GRAPH}/groups", group_body)
            steps.append({"step": "create-group", "group_id": group["id"], "label": sensitivity if label_id(sensitivity) else None})
        except urllib.error.HTTPError as error:
            if "is not assigned to current user" not in str(error.reason):
                raise
            # Newly published labels take hours to reach users. Create the room private and unlabelled, and say so.
            group_body.pop("assignedLabels")
            group = call("POST", f"{GRAPH}/groups", group_body)
            steps.append({"step": "create-group", "group_id": group["id"], "label": None,
                          "label_pending": f"{sensitivity} label not yet available to this user; room created Private"})

        site = None
        for _ in range(40):
            try:
                site = call("GET", f"{GRAPH}/groups/{group['id']}/sites/root?$select=id,webUrl")
                break
            except urllib.error.HTTPError:
                time.sleep(6)
        if not site:
            raise RuntimeError("The SharePoint site was not ready after four minutes.")
        drive = call("GET", f"{GRAPH}/sites/{site['id']}/drive?$select=id")
        library = call("GET", f"{GRAPH}/drives/{drive['id']}/list?$select=id")
        steps.append({"step": "site-ready", "site": site["webUrl"]})

        columns = [
            {"name": "ContosoDomain", "displayName": "Domain", "choice": {"choices": [d["name"] for d in model.domains.values()]},
             "defaultValue": {"value": domain_name}},
            {"name": "ContosoDeal", "displayName": "Deal", "text": {}, "defaultValue": {"value": request.name}},
            {"name": "ContosoSensitivity", "displayName": "Sensitivity",
             "choice": {"choices": ["Public", "Internal", "Confidential"]}, "defaultValue": {"value": sensitivity}},
        ]
        spo = f"https://{urllib.parse.urlparse(site['webUrl']).netloc}"
        fields_api = f"{site['webUrl']}/_api/web/lists(guid'{library['id']}')/fields"
        for column in columns:
            default = column.pop("defaultValue")["value"]
            call("POST", f"{GRAPH}/sites/{site['id']}/lists/{library['id']}/columns", column)
            # Graph accepts but does not store column defaults; SharePoint's own API does.
            call("POST", f"{fields_api}/getbyinternalnameortitle('{column['name']}')", {"DefaultValue": default},
                 resource=spo, headers={"X-HTTP-Method": "MERGE", "IF-MATCH": "*"})
        readback = call("GET", f"{fields_api}?$filter=startswith(InternalName,'Contoso')&$select=InternalName,DefaultValue", resource=spo)
        defaults = {f["InternalName"].removeprefix("Contoso"): f.get("DefaultValue") for f in readback.get("value", [])}
        steps.append({"step": "library-defaults", "verified": defaults})

        if label_id(sensitivity):
            try:
                call("POST", f"{site['webUrl']}/_api/web/lists(guid'{library['id']}')", {"DefaultSensitivityLabelForLibrary": label_id(sensitivity)},
                     resource=spo, headers={"X-HTTP-Method": "MERGE", "IF-MATCH": "*"})
                steps.append({"step": "library-default-label", "label": sensitivity})
            except urllib.error.HTTPError as error:
                steps.append({"step": "library-default-label", "skipped": f"HTTP {error.code}"})

        if request.file_from_inbox:
            query = urllib.parse.quote(f'"{request.file_from_inbox}"')
            found = call("GET", f"{GRAPH}/me/messages?$search={query}&$select=id,subject,hasAttachments&$top=5")
            message = next((m for m in found.get("value", []) if m.get("hasAttachments")), None)
            if not message:
                steps.append({"step": "file-cim", "skipped": "no matching email with attachments"})
            else:
                attachments = call("GET", f"{GRAPH}/me/messages/{message['id']}/attachments")
                for attachment in attachments.get("value", []):
                    if attachment.get("@odata.type") != "#microsoft.graph.fileAttachment":
                        continue
                    content = base64.b64decode(attachment["contentBytes"])
                    path = urllib.parse.quote(attachment["name"])
                    item = call("PUT", f"{GRAPH}/drives/{drive['id']}/root:/{path}:/content", raw=content)
                    fields = call("GET", f"{GRAPH}/drives/{drive['id']}/items/{item['id']}/listItem/fields"
                                         "?$select=FileLeafRef,ContosoDomain,ContosoDeal,ContosoSensitivity")
                    steps.append({"step": "file-cim", "file": attachment["name"], "item_id": item.get("id"),
                                  "from_email": message["subject"],
                                  "tags_verified": {k: fields.get(f"Contoso{k}") for k in ("Domain", "Deal", "Sensitivity")}})

        record["result"] = "created"
        record["site"] = site["webUrl"]
        record["group_id"] = group["id"]
        return {"result": "created", "deal_room": request.name, "site": site["webUrl"], "steps": steps}
    except Refused as refusal:
        record["result"] = "refused"
        record["reason"] = str(refusal)
        return {"result": "refused", "reason": str(refusal)}
    except Exception as error:  # fail closed and say what happened
        record["result"] = "error"
        record["reason"] = f"{type(error).__name__}: {error}"[:500]
        return {"result": "error", "reason": record["reason"], "steps": steps}
    finally:
        receipt(record)
