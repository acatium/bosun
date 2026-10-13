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
DOCUMENT = re.compile(r"\.(pdf|docx?|xlsx?|pptx?)$", re.IGNORECASE)


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

        member_ids = []
        for email in request.members:  # look everyone up, then check every member against the rules before acting
            quoted = email.replace("'", "''")
            found = call("GET", f"{GRAPH}/users?$filter=" + urllib.parse.quote(
                f"userPrincipalName eq '{quoted}' or mail eq '{quoted}'") + "&$select=id,userType")
            if not found.get("value"):
                raise Refused(f"Cannot add {email}: not found in the firm's directory.")
            user = found["value"][0]
            if user.get("userType") not in ("Member", "Guest"):
                raise Refused(f"Cannot add {email}: could not confirm whether they are inside the firm.")
            check_member(model, sensitivity, user["userType"], email)
            member_ids.append(user["id"])
        steps.append({"step": "member-check", "members": request.members, "result": "all permitted"})
        if os.environ.get("BOSUN_DRY_RUN"):
            record["result"] = "dry-run"
            return {"result": "dry-run", "would_create": request.model_dump(mode="json"), "steps": steps}

        nickname = f"deal-{slug(request.name)}"
        existing = call("GET", f"{GRAPH}/groups?$filter=" + urllib.parse.quote(f"mailNickname eq '{nickname}'")
                        + "&$select=id,assignedLabels").get("value", [])
        if existing:
            # Resume only the caller's own room, at the sensitivity it was created with.
            group = existing[0]
            owners = {o["id"] for o in call("GET", f"{GRAPH}/groups/{group['id']}/owners?$select=id").get("value", [])}
            if me["id"] not in owners:
                raise Refused(f"A deal room called {request.name} already exists and you do not own it.")
            labels = {l.get("labelId") for l in group.get("assignedLabels", [])}
            if label_id(sensitivity) and label_id(sensitivity) not in labels:
                raise Refused(f"{request.name} already exists with a different sensitivity; it was not changed.")
            steps.append({"step": "resume", "group_id": group["id"]})
        else:
            group_body = {
                "displayName": request.name, "mailNickname": nickname,
                "description": f"{model.name} deal room ({STORE}). Domain: {domain_name}. Sensitivity: {sensitivity}.",
                "groupTypes": ["Unified"], "mailEnabled": True, "securityEnabled": False,
                "visibility": "Private" if sensitivity != "Public" else "Public",
                "owners@odata.bind": [f"{GRAPH}/users/{me['id']}"],
                "members@odata.bind": [f"{GRAPH}/users/{i}" for i in [me["id"], *member_ids]],
            }
            if not label_id(sensitivity):
                raise Refused(f"No sensitivity label is configured for {sensitivity}; no room was created.")
            group_body["assignedLabels"] = [{"labelId": label_id(sensitivity)}]
            try:
                group = call("POST", f"{GRAPH}/groups", group_body)
            except urllib.error.HTTPError as error:
                if "is not assigned to current user" in str(error.reason):
                    # The label is the native control that keeps guests out; without it, do nothing.
                    raise Refused(f"The {sensitivity} label is not yet available to you, so no room was created. "
                                  "Newly published labels can take a few hours to reach people.") from None
                raise
            steps.append({"step": "create-group", "group_id": group["id"], "label": sensitivity})
        record["group_id"] = group["id"]

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
        have = {c["name"] for c in call("GET", f"{GRAPH}/sites/{site['id']}/lists/{library['id']}/columns?$select=name").get("value", [])}
        for column in columns:
            default = column.pop("defaultValue")["value"]
            if column["name"] not in have:
                call("POST", f"{GRAPH}/sites/{site['id']}/lists/{library['id']}/columns", column)
            # Graph accepts but does not store column defaults; SharePoint's own API does.
            call("POST", f"{fields_api}/getbyinternalnameortitle('{column['name']}')", {"DefaultValue": default},
                 resource=spo, headers={"X-HTTP-Method": "MERGE", "IF-MATCH": "*"})
        readback = call("GET", f"{fields_api}?$filter=startswith(InternalName,'Contoso')&$select=InternalName,DefaultValue", resource=spo)
        defaults = {f["InternalName"].removeprefix("Contoso"): f.get("DefaultValue") for f in readback.get("value", [])}
        steps.append({"step": "library-defaults", "verified": defaults})

        call("POST", f"{site['webUrl']}/_api/web/lists(guid'{library['id']}')",
             {"DefaultSensitivityLabelForLibrary": label_id(sensitivity)},
             resource=spo, headers={"X-HTTP-Method": "MERGE", "IF-MATCH": "*"})
        steps.append({"step": "library-default-label", "label": sensitivity})

        if request.file_from_inbox:
            # The most recent email whose subject contains the text; only document attachments are filed.
            found = call("GET", f"{GRAPH}/me/messages?$select=id,subject,hasAttachments,receivedDateTime"
                                "&$orderby=receivedDateTime desc&$top=50")
            wanted = request.file_from_inbox.lower()
            message = next((m for m in found.get("value", [])
                            if m.get("hasAttachments") and wanted in (m.get("subject") or "").lower()), None)
            if not message:
                steps.append({"step": "file-cim", "result": f"no email with attachments whose subject contains '{request.file_from_inbox}'"})
            else:
                attachments = call("GET", f"{GRAPH}/me/messages/{message['id']}/attachments?$select=id,name,contentType")
                for meta in attachments.get("value", []):
                    if meta.get("@odata.type") != "#microsoft.graph.fileAttachment" or not DOCUMENT.search(meta["name"]):
                        continue
                    attachment = call("GET", f"{GRAPH}/me/messages/{message['id']}/attachments/{meta['id']}")
                    content = base64.b64decode(attachment["contentBytes"])
                    path = urllib.parse.quote(attachment["name"])
                    item = call("PUT", f"{GRAPH}/drives/{drive['id']}/root:/{path}:/content", raw=content)
                    fields = call("GET", f"{GRAPH}/drives/{drive['id']}/items/{item['id']}/listItem/fields"
                                         "?$select=FileLeafRef,ContosoDomain,ContosoDeal,ContosoSensitivity")
                    steps.append({"step": "file-cim", "file": attachment["name"], "item_id": item.get("id"),
                                  "from_email": message["subject"], "received": message["receivedDateTime"],
                                  "tags_verified": {k: fields.get(f"Contoso{k}") for k in ("Domain", "Deal", "Sensitivity")}})

        record["result"] = "created"
        record["site"] = site["webUrl"]
        return {"result": "created", "deal_room": request.name, "site": site["webUrl"], "steps": steps}
    except Refused as refusal:
        record["result"] = "refused"
        record["reason"] = str(refusal)
        return {"result": "refused", "reason": str(refusal)}
    except Exception as error:
        # If the group exists, it stays (private, labelled); the same request resumes it.
        record["result"] = "incomplete" if record.get("group_id") else "error"
        record["reason"] = f"{type(error).__name__}: {error}"[:500]
        hint = " Ask again with the same request to finish setting it up." if record.get("group_id") else ""
        return {"result": record["result"], "reason": record["reason"] + hint, "steps": steps}
    finally:
        receipt(record)
