"""Demo setup only: place the Project Atlas CIM email from Woodgrove Bank in the signed-in user's inbox.

Run as the partner persona through the short-lived contoso-demo-seeder app (Mail.ReadWrite, that user only):
    HOME=<seeder session dir> python tools/seed_cim_email.py <cim.pdf>
The message is created in the inbox with the "sent" flag set, so it reads as a received email rather than a draft.
"""
import base64
import datetime
import json
import pathlib
import subprocess
import sys
import urllib.request

GRAPH = "https://graph.microsoft.com/v1.0"
SUBJECT = "Project Atlas - Confidential Information Memorandum"
BODY = """<p>Dana,</p>
<p>Following our call, please find attached the Confidential Information Memorandum for Project Atlas
(Wide World Importers). First-round indications of interest are due on 14 November.</p>
<p>Please direct all questions to me rather than to the Company.</p>
<p>Best regards,<br>Elena Marsh<br>Managing Director, Capital Markets Advisory<br>Woodgrove Bank</p>"""


def token() -> str:
    out = subprocess.run(["m365", "util", "accesstoken", "get", "--resource", "https://graph.microsoft.com",
                          "--new", "--output", "text"], capture_output=True, text=True, check=True).stdout
    return out.strip().strip('"')


def call(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(GRAPH + path, data=data, method=method, headers={
        "Authorization": f"Bearer {token()}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode()
    return json.loads(text) if text else {}


def main(pdf: pathlib.Path) -> None:
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    me = call("GET", "/me?$select=displayName,userPrincipalName")
    sender = {"emailAddress": {"name": "Elena Marsh (Woodgrove Bank)", "address": "elena.marsh@woodgrovebank.example"}}
    message = call("POST", "/me/mailFolders/inbox/messages", {
        "subject": SUBJECT, "importance": "high",
        "body": {"contentType": "HTML", "content": BODY},
        "from": sender, "sender": sender,
        "toRecipients": [{"emailAddress": {"name": me["displayName"], "address": me["userPrincipalName"]}}],
        "attachments": [{"@odata.type": "#microsoft.graph.fileAttachment", "name": pdf.name,
                         "contentType": "application/pdf", "contentBytes": base64.b64encode(pdf.read_bytes()).decode()}],
        "singleValueExtendedProperties": [
            {"id": "Integer 0x0E07", "value": "1"},       # PR_MESSAGE_FLAGS: read, not a draft
            {"id": "SystemTime 0x0E06", "value": now},    # PR_MESSAGE_DELIVERY_TIME
            {"id": "SystemTime 0x0039", "value": now},    # PR_CLIENT_SUBMIT_TIME
        ],
    })
    call("PATCH", f"/me/messages/{message['id']}", {"isRead": False})
    print(f"placed '{SUBJECT}' with {pdf.name} in the inbox")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]))
