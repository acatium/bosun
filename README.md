# Bosun

A proof of concept on Microsoft 365, Entra and Fabric for **Contoso Capital**, a fictional private markets firm.
One LinkML model holds the firm's domains, roles, business terms, stores and access rules. A compiler applies
it to the tenant, and an MCP server gives an agent one governed action: opening a deal room as the person
asking.

All names are Microsoft's standard fictional names (Contoso, Fabrikam, Northwind, Tailspin, Adventure Works,
Wide World Importers, Woodgrove Bank). Built with Claude Code; commits from the redesign onward carry a
Claude co-author line.

## What was built

| Part | What it does |
|---|---|
| Model ([`model/`](model/)) | LinkML schema and the Contoso instance: 3 domains, 4 roles, 10 business terms, 5 stores, 5 rules |
| Compiler ([`backplane/`](backplane/)) | `validate`, `plan`, `apply`, `report`. Emits Entra dynamic groups (from department and job title), Fabric domains, tags and workspace roles, SharePoint term store terms, dataset loads, semantic model tables and measures, and the Fabric data agent's instructions. Runs as the platform owner through a Claude Code Skill ([`.claude/skills/backplane/`](.claude/skills/backplane/SKILL.md)) |
| Conformance report | Lists compiled objects against the model, drift in both directions, and deal rooms (label, privacy, members, guests) |
| MCP server ([`backplane/mcp_server.py`](backplane/mcp_server.py)) | One tool, `create_deal_room`. Input schema generated from the model. Checks the model's rules, then creates a labelled private Microsoft 365 group and site as the calling user, sets library default tags and label, adds members, files a CIM from the caller's inbox, and writes a receipt |
| Portfolio store | Fabric lakehouse, Direct Lake semantic model ([`semantic-model/`](semantic-model/)) and data agent ([`data-agent/`](data-agent/)) over fictional portfolio data ([`data/`](data/)) |
| Checks | Offline tests ([`tests/`](tests/)), golden questions ([`evals/`](evals/)), CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)): model validation, generated-code diff, tests, portability and deny-list scans |

Choices made and alternatives not taken: [`docs/decisions.md`](docs/decisions.md).

## What was shown

| Result | Evidence |
|---|---|
| The model validates; generated classes match the schema; 12 offline tests pass | [`results/2026-10-13/rerun.md`](results/2026-10-13/rerun.md) |
| The compiler converges: a plan after apply shows zero changes; the conformance report is conformant | [`results/2026-10-13/rerun.md`](results/2026-10-13/rerun.md) |
| Portfolio access follows the compiled groups: the partner is answered, an outsider is refused by Fabric | [`results/2026-10-13/rerun.md`](results/2026-10-13/rerun.md) |
| Golden questions (EBITDA variance ranking, Northwind leverage, IRR refused as undefined) match DAX run against the model | [`results/2026-10-13/rerun.md`](results/2026-10-13/rerun.md), [`results/2026-10-13/golden-questions.md`](results/2026-10-13/golden-questions.md) |
| An agent asked for the sensitivity the person omitted, with no instruction from the server (4 of 4 runs, tool in dry-run mode) | [`results/2026-10-13/model-talks-back.md`](results/2026-10-13/model-talks-back.md) |
| `create_deal_room` refuses a guest on a Confidential room (including by internal UPN), an unknown person, a missing label, and a resume at a different sensitivity | [`results/2026-10-13/refusals.md`](results/2026-10-13/refusals.md) |
| One model change adds Gross IRR end to end (dataset, table, measure, term, agent instructions); the measure matches an independent XIRR | [`results/2026-10-13/irr-rehearsal.md`](results/2026-10-13/irr-rehearsal.md) |

## Known gaps

- No deal room has yet been created end to end. Until 2026-10-14 no label policy published the labels, so
  `create_deal_room` refused ([`results/2026-10-13/rerun.md`](results/2026-10-13/rerun.md)). The policy now
  exists and is propagating.
- After the Gross IRR change, the data agent answered the IRR question correctly once (rehearsal) and
  failed in four later runs: no query generated, an access error, and one wrong figure (7.38% for every
  company) ([`results/2026-10-13/rerun.md`](results/2026-10-13/rerun.md)). The measure itself is correct.
  With relationship columns hidden (2026-10-14): 2 of 5 correct, 0 wrong figures, 3 without an answer
  ([`results/2026-10-14/irr-hidden-keys.md`](results/2026-10-14/irr-hidden-keys.md)).
- Data agent answers are generated queries, not deterministic; golden questions cover three questions.
- The MCP server runs on the partner's machine; its rule checks apply to the agent's path only.
- Access is per store, not per table.
- Sensitivity labels are created by an admin script outside the repository; the report does not check
  their settings. The Internal and Public labels refuse guests; the model's rule refuses guests only on
  Confidential.
- Deal-room library tags are reported as recorded at creation, not re-read.
- No Microsoft 365 audit log evidence has been captured.
- Option A (Copilot Studio calling a hosted MCP server) was not built.

## Layout

| Path | Purpose |
|---|---|
| `model/` | LinkML schema and the Contoso model |
| `backplane/` | Compiler (`python -m backplane validate|plan|apply|report`) and MCP server |
| `.claude/skills/backplane/` | How Claude Code operates the compiler |
| `semantic-model/`, `data-agent/` | Portfolio semantic model (TMDL) and data agent definition |
| `data/` | Fictional portfolio data, fund cash flows, Project Atlas CIM |
| `docs/` | Decisions; the Gross IRR model change |
| `evals/` | Golden questions and their runner |
| `results/` | Evidence from runs |
| `tests/`, `tools/`, `.github/` | Offline tests, content and repository checks, CI |

[`REPLICATE.md`](REPLICATE.md) describes rebuilding it in another tenant.
