# Bosun

A governed AI foundation on the Microsoft stack, demonstrated on **Contoso Capital**, a fictional
alternative investment firm. (Contoso and its portfolio companies are Microsoft's standard fictional
names. Everything else here is built from scratch.)

Bosun's claim is that people can use AI agents freely when a few governed primitives sit underneath them
and the rules are enforced by the platform, not by prompts. It is built almost entirely from native
Microsoft components; the one custom piece is a small, auditable gateway.

## The model

**Four primitives**, each with an owner:

| Primitive | Native component here | Source of truth |
|---|---|---|
| Identity | Entra ID users and security groups | Entra (HR-driven in production) |
| Org domains | Fabric Domains (Private Equity, Finance & Operations, Technology) | [`config/profiles/contoso.yaml`](config/profiles/contoso.yaml) |
| Closed business glossary | Each term bound to exactly one semantic model measure | [`config/glossary.yaml`](config/glossary.yaml) |
| Ontology | Tables and relationships in the semantic model; Fabric IQ ontology (preview) is the native next step | [`semantic-model/`](semantic-model/) |

**Two agent layers**:

- **Store agents are domain-scoped and keyed.** Each store (here, a Fabric workspace) has one agent. The
  agent reads data through the store's own identity (the workspace identity), not the caller's, so its
  reach is one store and nothing else. Only people on the store's access list can invoke it.
- **The orchestrator is user-scoped and holds no keys.** Claude Code here, Microsoft 365 Copilot in a
  licensed tenant. It acts as the person using it and can only reach stores that person can already reach.

**One deterministic rule on top**: every figure in an answer must name a glossary term and an as-of month,
or the answer is blocked with the reason. This is the only custom code ([`gateway/`](gateway/)), and it is
small enough to read in a few minutes.

```
Person ──► Orchestrator (Claude Code, runs as the person, no keys)
              │  MCP
              ▼
           bosun-gateway (local, no keys: forwards the person's token, checks every answer, logs every call)
              │  MCP, person's Entra token
              ▼
           Store agent (Fabric data agent)  ◄── invocation gate: store access group
              │  store key: workspace identity
              ▼
           Semantic model (glossary-bound measures) ──► Lakehouse (OneLake)
```

## What was proved

Evidence from real runs is in [`results/`](results/). Each claim has a pass/fail test.

| # | Claim | Result |
|---|---|---|
| 1 | A person on the store's access list can ask its agent and get a governed answer | Pass |
| 2 | A person not on the list is refused by the platform, with no Bosun code involved | See results |
| 3 | The orchestrator reaches stores only as the person using it | Pass |
| 4 | Answers match the authoritative calculation (golden questions vs DAX) | Pass, 3 of 3 |
| 5 | An undefined term (IRR) is refused, not estimated | Pass |
| 6 | A figure without a glossary term or as-of month is blocked, with the reason | Pass, on real agent output |
| 7 | Every orchestrator call is logged with caller, store, question and verdict | Pass |

Not yet built: deal room provisioning and teardown, `Sites.Selected` keys for SharePoint stores, label
inheritance and the Microsoft 365 Copilot surface. These are described as the next steps in the results.

## Repository layout

| Path | Purpose |
|---|---|
| `config/profiles/` | Firm profile: domains, personas and owners. `contoso.yaml` is the example |
| `config/glossary.yaml` | The closed business glossary and each term's measure |
| `config/stores.yaml` | Store registry: one entry per keyed store and its agent |
| `data/portfolio/` | Sample operating data: four portfolio companies, actuals vs plan, value creation initiatives |
| `semantic-model/` | The Direct Lake semantic model as TMDL (Microsoft's text format for models) |
| `data-agent/` | The Fabric data agent definition |
| `gateway/` | bosun-gateway, the one custom component |
| `evals/` | Reviewed test questions with expected values |
| `results/` | Captured evidence |
| `tools/`, `.github/` | Repository hygiene checks run in CI |
| `bootstrap/`, `infra/` | GitHub-to-Azure federation and pipeline foundation (not used in the 2026-10-12 run) |

## Replicating it

See [`REPLICATE.md`](REPLICATE.md). Everything needed is in this repository; nothing depends on the
original tenant. The run costs a few dollars if torn down the same day.

## Environment notes

- Microsoft 365 E3. Fabric on a paid F2 capacity (data agents do not run on trial capacity). Users need a
  Power BI licence or trial to query a semantic model on capacities below F64.
- All Azure resources live in one resource group and are deleted after validation.
