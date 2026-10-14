# Deal-room retry after the label policy, 2026-10-14

**Caller:** the partner persona, calling `deal_room.create` directly (the same code the MCP tool runs), signed in as
the partner · Addresses redacted to `<persona>@<tenant>`.

The label policy `contoso-labels` was created at 17:44 UTC. "Project Dryrun" (Confidential, two members, CIM from
the inbox) was retried at 18:18 and 20:01 UTC. Receipt from 20:01:

```
{"ts": "2026-10-14T20:01:47Z", "tool": "create_deal_room",
 "request": {"name": "Project Dryrun", "members": ["<priya>@<tenant>", "<sam>@<tenant>"], "sensitivity": "Confidential", "file_from_inbox": "Atlas"},
 "steps": [{"step": "rule-check", "roles": ["pe-partner", "pe-deal-team"], "allowed_by": "partners-open-deal-rooms"},
           {"step": "member-check", "members": ["<priya>@<tenant>", "<sam>@<tenant>"], "result": "all permitted"}],
 "caller": "<partner>@<tenant>", "result": "refused",
 "reason": "The Confidential label is not yet available to you, so no room was created. Newly published labels can take a few hours to reach people."}
```

Microsoft Graph rejected the group because the label is not yet assigned to the partner. Directory query for the
group afterwards:

```
GET /v1.0/groups?$filter=displayName eq 'Project Dryrun'
{"value": []}
```

Result: the rule and member checks passed; the label had not reached the partner; no group was created.
