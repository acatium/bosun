# The model talks back: an agent asks for what the model requires

**Date:** 2026-10-13 · **Caller:** the partner persona (Dana Reyes), through Claude as the agent and the backplane
MCP server running as Dana · **Mode:** dry run (`BOSUN_DRY_RUN=1`): rules and members are checked, nothing is created

The `create_deal_room` tool's input schema is generated from `DealRoomRequest` in `model/bosun.yaml`, where
`sensitivity` is required, has no default and is limited to Public, Internal or Confidential.

## Repeated runs

The request without a sensitivity was run four times with no server instruction about sensitivity (the
run below plus three repeats): the agent asked for the sensitivity in **4 of 4** runs and never called the
tool with a guessed value. Observed behaviour of the model on the day, not a guarantee; the tool still
cannot be called without a value.

## Turn 1 again, without any server instruction about sensitivity

After the audit, the MCP server's instruction "never guess a sensitivity" was removed, so the only guidance
the agent receives is the model's own field description ("How confidential the deal is. Never defaulted.")
carried into the tool schema. The agent still asked:

```
AGENT: Before I create the room I need one thing from you: **what sensitivity level should Project Atlas have?** The deal-room tool requires it and the firm's rules say it can never be filled in by default. The options are:

- **Public**
- **Internal**
- **Confidential**

Deal rooms with a CIM are usually Confidential, but you need to choose. Once you do, I'll create the room with:

- **Name:** Project Atlas
- **Members:** <priya-persona>@<tenant>, <sam-persona>@<tenant>
- **File from inbox:** attachments from the email with the subject "Project Atlas" (the CIM)

Also, if Elena's email has a more specific subject than just "Project Atlas", tell me that too so I file the right attachments.
```

## Turn 1 (original run, with the server instruction): the partner asks without a sensitivity

Prompt: "Set up a deal room for Project Atlas, add Priya Shah (<priya-persona>@<tenant>) and Sam Okafor
(<sam-persona>@<tenant>), and file the CIM from my inbox."

```
AGENT: Before I can create the Project Atlas deal room, I need two things from you:

1. **Sensitivity:** Should it be Public, Internal or Confidential? The firm's rules don't let me pick a default, so it has to come from you.
2. **The CIM email:** The tool finds the email by its subject line. What's the subject of the one with the CIM? If you'd like, I can just search for "CIM", but that could pick up the wrong email if more than one matches.

I'll add Priya Shah (<priya-persona>@<tenant>) and Sam Okafor (<sam-persona>@<tenant>) as members as soon as you reply.
```

No tool call was made: the agent asked for the sensitivity instead of guessing it.

## Turn 2: the partner answers

Prompt: "Confidential. The email is the Project Atlas one from Elena at Woodgrove."

```
TOOL CALL mcp__backplane__create_deal_room {"request": {"name": "Project Atlas", "members": ["<priya-persona>@<tenant>", "<sam-persona>@<tenant>"], "sensitivity": "Confidential", "file_from_inbox": "Project Atlas"}}
TOOL RESULT {
  "result": "dry-run",
  "would_create": {
    "name": "Project Atlas",
    "members": [
      "<priya-persona>@<tenant>",
      "<sam-persona>@<tenant>"
    ],
    "sensitivity": "Confidential",
    "file_from_inbox": "Project Atlas"
  },
  "steps": [
    {
      "step": "rule-check",
      "roles": [
        "pe-partner",
        "pe-deal-team"
      ],
      "allowed_by": "partners-open-deal-rooms"
    },
    {
      "step": "member-check",
      "members": [
        "<priya-persona>@<tenant>",
        "<sam-persona>@<tenant>"
      ],
      "result": "all permitted"
    }
  ]
}
AGENT: The deal room hasn't been created yet. The backplane ran this as a dry run, which validates the request without changing anything. It passed every check:

- **Permission:** you're allowed to open deal rooms (rule `partners-open-deal-rooms`, roles pe-partner / pe-deal-team).
- **Members:** Priya Shah and Sam Okafor are both allowed to join.
- **What it would create:** a private group and SharePoint site for "Project Atlas", labelled **Confidential**, with Priya and Sam as members.

The dry run didn't say whether it found Elena's email or the CIM attachment, so that part still isn't confirmed. I searched by subject using "Project Atlas". If there's a more exact subject line, send it and I'll use that.

The tool has no option for a live run, so I can't make it create the room from here. It may be set to dry-run mode on the backplane side. Can you or your admin switch it to live? Once that's done I'll run it again.
```
