# Bosun

**One model of the firm's primitives, compiled into Microsoft's native controls and called through MCP from
where people already work, so governance happens automatically instead of by coordination.**

Demonstrated on **Contoso Capital**, a fictional private markets firm. (Contoso, Fabrikam, Northwind,
Tailspin, Adventure Works, Wide World Importers and Woodgrove Bank are Microsoft's standard fictional names.)
Built with Claude Code; commits from the redesign onward carry a Claude co-author line.

## The idea

In a large firm, identity, groups, data, catalog, collaboration and records are each owned and configured by
a different team, so any change is a chain of tickets. Bosun holds the primitives as one small model and
compiles it into the platform:

| Primitive | In the model | Compiled into |
|---|---|---|
| Identity | Roles defined by directory attributes | Entra dynamic groups (membership follows department and title) |
| Group membership | Domains | Entra domain groups, Fabric domains |
| Business terms | A closed glossary with owners and calculations | SharePoint term store, semantic model measures, the data agent's vocabulary |
| Entitlements | Rules over roles, stores and tags | Fabric workspace roles; the deal-room tool's checks; sensitivity labels (one-time admin step) |
| Observability | Every compiled object traces to the model | Conformance report (drift both ways), receipts, Microsoft 365 audit log |

Users never tag anything and never raise a ticket. Agents propose; deterministic code applies; a person
approves. See [`docs/decisions.md`](docs/decisions.md) for every choice, what was rejected and why, and the
six questions (identity, access, revocation, logging, failure, cost) for each component.

## What it does

- **A partner opens a deal room by asking their agent.** The tool's input schema comes from the model, which
  marks sensitivity as required and never defaulted, so the agent asks for it. The tool checks the model's
  rules, then, as the partner, creates a private, labelled Microsoft 365 group and site, sets the library's
  default tags, and files the CIM from the partner's inbox. A banker who is a guest is refused under the
  rule `confidential-no-guests`.
- **Portfolio questions are answered in the glossary's terms** by a Fabric data agent over a Direct Lake
  semantic model, reading through the workspace's own identity.
- **The glossary owner defines a new term** (e.g. Gross IRR) and one model change is compiled into a
  loaded dataset, a measure, the term store and the agent's vocabulary.

## Evidence

| Claim | Evidence | Status |
|---|---|---|
| The agent asks for a sensitivity the person omitted, with no instruction from the server | [`results/2026-10-13/model-talks-back.md`](results/2026-10-13/model-talks-back.md) | Shown (dry run) |
| Guests are refused on Confidential rooms, including a guest addressed by internal UPN; unknown people and missing labels are refused | [`results/2026-10-13/refusals.md`](results/2026-10-13/refusals.md); rules unit-tested in [`tests/`](tests/) | Shown |
| A new term compiles end to end and matches an independent calculation | [`results/2026-10-13/irr-rehearsal.md`](results/2026-10-13/irr-rehearsal.md) | Shown |
| Portfolio answers match DAX ground truth; an undefined term is refused (by the agent's generated instructions) | [`results/2026-10-13/golden-questions.md`](results/2026-10-13/golden-questions.md) | Shown |
| Access to the portfolio store follows the model's rules (compiled groups); an outsider is refused | [`results/2026-10-13/golden-questions.md`](results/2026-10-13/golden-questions.md) (partner); [`results/2026-10-12/access-and-guardrail.md`](results/2026-10-12/access-and-guardrail.md) (outsider, before the compiler) | Shown |
| A deal room created from the agent, with the CIM tagged by nobody | Rehearsed; the live run waits for the Confidential label to reach the partner | Pending |
| Deal room activity corroborated by the Microsoft 365 audit log | To be captured after the live run | Pending |

## Limits, stated

- The MCP server runs on the partner's machine in this demo, so its checks guard the agent's path; the label
  and group membership are the controls that also stop a person. Hosting the server removes that gap.
- Access is per store. Tags carry domain and sensitivity for discovery and audit, but Microsoft does not
  enforce on them, so the rules are compiled into groups and roles.
- Sensitivity labels are created once by an admin and not checked by the conformance report.
- Deal-room content is not readable by the platform owner, so its tags are attested at creation, not re-read.

## Layout

| Path | Purpose |
|---|---|
| `model/` | The LinkML schema and the Contoso model |
| `backplane/` | Compiler (`python -m backplane validate|plan|apply|report`) and the MCP server |
| `.claude/skills/backplane/` | How Claude Code operates the backplane |
| `semantic-model/`, `data-agent/` | The portfolio store's semantic model (TMDL) and data agent definition |
| `data/` | Fictional portfolio data, fund cash flows and the Project Atlas CIM |
| `docs/` | Decisions, the demo change, research notes |
| `results/` | Evidence from real runs |
| `tests/`, `tools/`, `.github/` | Offline tests, content and repository checks, CI |

See [`REPLICATE.md`](REPLICATE.md) to rebuild it in another tenant.
