# Bosun

A governed AI platform, demonstrated on **Contoso Capital**, a fictional alternative investment firm.
(Contoso is Microsoft's standard fictional company. Everything else here is built from scratch.)

Bosun shows how an investment firm can let people use AI agents freely, because the rules that keep
it safe are enforced in code rather than in prompts or policy documents.

## The idea in one paragraph

A small set of governed primitives (identity, organizational domains, a closed business glossary and
an ontology) sits underneath everything. People work through a **user-scoped orchestrator** that runs
as them and holds no keys. Behind it, **store-scoped agents** each hold one key to one data store,
limited to specific actions, and can be invoked only by people who can already access that store.
A **deterministic harness** checks every call and output: untraced figures are blocked, outputs
inherit the strictest label of their sources, and every agent action is logged.

## How changes flow

Nothing in this environment is changed by hand.

1. Agents (Claude in chat or Claude Code) propose changes as pull requests.
2. CI runs deterministic guardrail checks and an Azure what-if preview.
3. A human owner approves. Merges to `main` deploy through the `production` environment.
4. GitHub Actions signs in to Azure with workload identity federation. There are no stored secrets
   for Azure anywhere in this repo or its settings.

## Validation

Each claim the architecture makes has a pass/fail test. Results are captured in [`results/`](results/).

| # | Test | What passing proves | Status |
|---|------|---------------------|--------|
| 1 | Keyed store | An agent can read the one store it holds a key to, and is denied every other | Pending |
| 2 | Invocation gate | A person outside a store's access group cannot make its agent act | Pending |
| 3 | Orchestrator runs as the user | Two people asking the same question see only what each can access | Pending |
| 4 | Provision and teardown | A deal room appears in minutes and its agent's key is revoked on retirement | Pending |
| 5 | Label inheritance | A saved output carries the strictest label among its sources | Pending |
| 6 | Citation guardrail | An answer containing an untraced figure is blocked, with the reason shown | Pending |
| 7 | Ontology contracts | A malformed tool output is rejected deterministically | Pending |
| 8 | Audit trail | Every action in tests 1-7 appears in the agent action log | Pending |

## Repository layout

| Path | Purpose |
|------|---------|
| `config/profiles/` | Firm profiles: domains, personas and owners, the org primitives as data. `contoso.yaml` is the example |
| `config/guardrails.yaml` | Firm-agnostic rules: prefix format, allowed Azure resource types, allowed Graph permissions |
| `tools/` | Deterministic checks run in CI: guardrails, portability and deny-list |
| `infra/` | Azure infrastructure (Bicep) |
| `bootstrap/` | The one manual step: creating the trust between GitHub and Entra ID |
| `results/` | Captured validation results |
| `.env.example` | Every environment-specific setting, named and documented. None of them are secrets |

## Adopting it

Bosun is built to be adopted, not just demonstrated. A firm creates its own copy from this template,
adds its profile, fills in `.env` and runs bootstrap once. CI then refuses any change that hard-codes a
tenant, subscription or organization identifier, so the repository stays portable as it grows.
See [PORTING.md](PORTING.md).

## Environment notes

- Runs on Microsoft 365 E3. Features that need E5 (default library labels, access reviews, lifecycle
  workflows) are implemented by the harness instead, which keeps the guardrails under the platform's
  own control on any licence tier.
- All Azure resources live in one resource group, named with the firm profile's prefix, and are torn
  down after validation.
