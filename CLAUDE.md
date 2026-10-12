# Working on Bosun

Read this before doing anything in this repository. If `local/BRIEF.md` exists, read it too: it holds
private context and must never be copied into a tracked file.

## Purpose

Demonstrate an enterprise-grade agent harness on the Microsoft stack, solving representative investment
problems end to end. The value is fluency with real enterprise tools and sound security, not custom
software. Portability to another tenant is a bonus, not the goal.

## Scope: two workflows, one harness

1. **Expedited deal flow (unstructured).** A deal team asks questions of a SharePoint data room and gets
   cited answers. Only that deal team can ask; only that deal's documents can be read.
2. **Value management (structured).** A portfolio company's operating data lands in Fabric. Partners ask
   how the company is tracking against plan and get answers from the governed semantic model.
3. **The bridge.** Diligence figures become the baseline for the value creation plan in Fabric, under the
   same glossary terms.

Anything outside this scope needs an explicit decision from the owner before work starts.

## Use native Microsoft components first

Write custom code only where Microsoft has no equivalent. If you are about to build something, first
check whether one of these already does it:

| Concern | Native component |
|---|---|
| Who can ask | Entra group, plus an app registration with assignment required |
| What an agent can read | Managed identity; Graph `Sites.Selected` on one SharePoint site |
| Orchestration | User-scoped, holds no keys: Microsoft 365 Copilot where licensed; Claude Code (optionally on a Foundry Claude deployment) otherwise. Foundry Agent Service does not support Claude models |
| Structured Q&A (store agent) | Fabric data agent over the semantic model, published as an MCP server; reads data through the workspace identity (the store key) |
| Org domains | Fabric Domains, created from the firm profile |
| Semantic layer | Fabric semantic model (Direct Lake, kept as TMDL in git), with a small set of measures bound to glossary terms |
| Ontology | Fabric IQ ontology (preview) when adopted; until then, the semantic model's tables and relationships |
| Retrieval over documents | Azure AI Search |
| Prompt injection, content safety | Azure AI Content Safety (Prompt Shields) for Azure OpenAI models. Foundry applies no built-in content filtering to Claude deployments; Claude relies on Anthropic's safeguards |
| Answer quality | Foundry evaluations (groundedness) on a small test set |
| Audit and tracing | Application Insights / Log Analytics, plus the Microsoft 365 audit log |
| Resource rules | Azure Policy on the resource group |

Known custom pieces, kept small enough to explain line by line: `gateway/bosun_gateway.py` (the runtime
check that blocks figures without a glossary term or as-of month, plus the call log), and output label
inheritance (an E3 licensing gap, not yet built).

## Environment facts

- Microsoft 365 E3, not E5: no default library labels, access reviews or lifecycle workflows.
- Fabric runs on a paid F2 capacity. Fabric data agents do not work on trial capacity. **Pause the
  capacity when a session ends.**
- One resource group holds every Azure resource. Everything is tagged per `config/guardrails.yaml`.
- Scripts a human runs on Windows target PowerShell 5.1 (no `&&` or `||`). Claude Code runs in bash.
- The owner prefers one consolidated, single-paste command block over step-by-step sequences.

## Working rules

- **Sandbox shortcuts stay out of git.** Exploratory or elevated-permission scripts go in `local/`
  (gitignored). Anything worth keeping is rewritten properly and arrives through a pull request.
- **No secrets in chat, code, commits or logs.** Prefer managed identity and federation. Any client
  secret needs a written justification in the pull request.
- **Least privilege.** Never use Owner on the subscription, `Directory.ReadWrite.All` or
  `Sites.FullControl.All` at runtime, and nothing that only works because the operator is a Global
  Administrator.
- **Never name a real firm, employer or project** other than Contoso Capital, the fictional example.
  CI enforces a deny-list over files and full history.
- **Tear down what you create** when it is no longer needed, and say what you removed.
- **Teach as you go.** The owner is an enterprise architect learning Fabric and Foundry hands-on. When
  you configure something in a portal or CLI, explain what it is and why, briefly.

## The bar for every component

Before anything merges, the pull request description answers six questions:

1. What identity does it run as?
2. What can that identity access?
3. How is that access revoked?
4. Where is its activity logged?
5. What happens when it fails?
6. What does it cost?

If any answer is unknown, the component is not done.

## Own-goals to avoid

Secrets anywhere. Over-privileged identities. An agent that can read more than the person asking it.
Ignoring prompt injection from documents. An audit trail nobody can query. Personal email, tenant IDs
or live public endpoints exposed through the public repository. Claims of "production-ready", tests that
do not test, or results without evidence. Resources left running.

## Current state and next steps

Done (2026-10-12 run, see `results/`): value management store end to end: sample data, lakehouse, TMDL
semantic model with glossary-bound measures, data agent keyed by the workspace identity, Fabric Domains,
access group, bosun-gateway, golden-question evals and access proofs. Bootstrap and the deploy pipeline
exist but were not used.

Next, in order:
1. Deal flow as a second keyed store: deal-room SharePoint site, an agent identity granted `Sites.Selected`
   on that one site, registered in `config/stores.yaml`.
2. Deal room provisioning and teardown as one workflow (Power Automate or Logic Apps), logging every action.
3. The bridge: diligence figures become the value creation plan baseline under the same glossary terms.
4. Tighten the gateway check from per line to per figure; send its log to Log Analytics.
5. Prepare the repository to go public (commit author emails, deny-list, branch protection).
