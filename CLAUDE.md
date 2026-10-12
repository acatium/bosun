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
| Orchestration | Azure AI Foundry agent using a Claude deployment |
| Structured Q&A | Fabric data agent over the lakehouse and semantic model, called as a Foundry tool |
| Semantic layer | Fabric semantic model (Direct Lake), with a small set of documented measures bound to glossary terms |
| Retrieval over documents | Azure AI Search |
| Prompt injection, content safety | Azure AI Content Safety (Prompt Shields). Verify which Foundry filters apply to Claude deployments |
| Answer quality | Foundry evaluations (groundedness) on a small test set |
| Audit and tracing | Application Insights / Log Analytics, plus the Microsoft 365 audit log |
| Resource rules | Azure Policy on the resource group |

Known custom pieces, kept small enough to explain line by line: the runtime citation check that blocks
untraced figures, and output label inheritance (an E3 licensing gap).

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

Done: repository scaffold, CI guardrails, portability layer, bootstrap script (not yet run).

Next, in order:
1. Run bootstrap; create the F2 Fabric capacity.
2. Value management: lakehouse, portfolio company data, semantic model with glossary-bound measures,
   Fabric data agent.
3. Deal flow: deal-room SharePoint site, managed identity with `Sites.Selected`, Azure AI Search index,
   Foundry agent with Content Safety.
4. The bridge, the citation check and evaluations.
5. Capture results in `results/`, tear down, then prepare the repository to go public.
