# Bosun

A proof of concept on Microsoft 365, Entra and Fabric for **Contoso Capital**, a fictional private markets firm.

**The idea:** one model of the firm's governance (domains, roles, business terms, data stores, access rules) is
compiled into Microsoft's native controls, and agents act through deterministic tools that obey it. Governance
happens automatically instead of by tickets between teams.

## What you're looking at

| Part | In one line |
|---|---|
| **Model** ([`model/contoso.yaml`](model/contoso.yaml)) | The firm in LinkML: 3 domains, 4 roles, 10 business terms, 5 stores, 5 rules. Start here |
| **Compiler** ([`backplane/`](backplane/)) | Applies the model to the tenant: Entra groups, Fabric domains and roles, term store, semantic model measures, data agent instructions. Plans before it applies; reports drift. Run by the platform owner through a Claude Code Skill ([`.claude/skills/backplane/`](.claude/skills/backplane/SKILL.md)) |
| **MCP tool** ([`backplane/deal_room.py`](backplane/deal_room.py)) | `create_deal_room`: an agent opens a labelled, private deal room as the person asking. Input schema generated from the model; refuses what the rules forbid; writes a receipt |
| **Portfolio store** ([`semantic-model/`](semantic-model/), [`data-agent/`](data-agent/)) | Fabric semantic model and data agent over fictional portfolio data, using the model's terms |

Design choices and rejected alternatives: [`docs/decisions.md`](docs/decisions.md). All names are Microsoft's
standard fictional ones. Built with Claude Code.

## What was shown

| Result | Evidence |
|---|---|
| The compiler converges: re-planning after apply shows zero changes; the conformance report is clean | [rerun](results/2026-10-13/rerun.md) |
| Portfolio access follows the compiled groups: the partner is answered, an outsider is refused by Fabric | [rerun](results/2026-10-13/rerun.md) |
| The data agent's answers match DAX run against the model (EBITDA variance, leverage); it refuses IRR while IRR is undefined | [golden questions](results/2026-10-13/golden-questions.md) |
| An agent asked for the sensitivity the user omitted, prompted only by the model-generated schema (4 of 4 runs) | [model talks back](results/2026-10-13/model-talks-back.md) |
| `create_deal_room` refuses guests on Confidential rooms, unknown people, a missing label and a changed sensitivity, naming the rule | [refusals](results/2026-10-13/refusals.md) |
| It fails closed live: with the label not yet published to the partner, nothing was created | [retry](results/2026-10-14/deal-room-retry.md) |
| One model change adds Gross IRR end to end (data, measure, term, agent instructions); the measure matches an independent XIRR | [IRR rehearsal](results/2026-10-13/irr-rehearsal.md) |
| Model validation, generated-code check and 14 offline tests run in CI | [`ci.yml`](.github/workflows/ci.yml), [`tests/`](tests/) |

## Known gaps

- **No deal room has been created end to end yet.** The label policy was published on 2026-10-14 and had not
  reached the partner when last retried ([retry](results/2026-10-14/deal-room-retry.md)).
- **IRR answers are unreliable.** After the IRR change the data agent answered correctly 2 of 5 times, with no
  wrong figures; the measure itself is correct ([IRR retest](results/2026-10-14/irr-hidden-keys.md)).
- Data agent answers are generated queries, not deterministic.
- The MCP server runs on the partner's machine; its rule checks guard the agent's path. The sensitivity label is
  the native control for everyone else.
- Access is per store, not per table.
- Sensitivity labels are created by an admin script outside the repository.
- No Microsoft 365 audit log evidence captured. Copilot Studio as the front end was not built.

## Layout

| Path | Purpose |
|---|---|
| `model/` | LinkML schema and the Contoso model |
| `backplane/` | Compiler (`python -m backplane validate\|plan\|apply\|report`) and MCP server |
| `semantic-model/`, `data-agent/`, `data/` | Portfolio store definitions and fictional data |
| `results/` | Evidence from runs |
| `docs/`, `evals/`, `tests/`, `tools/` | Decisions, golden questions, tests, repository checks |

[`REPLICATE.md`](REPLICATE.md) describes rebuilding it in another tenant.
