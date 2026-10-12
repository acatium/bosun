# Working on Bosun

Read this before doing anything in this repository. If `local/BRIEF.md` exists, read it too: it holds
private context and must never be copied into a tracked file.

## Purpose

Show that a small set of governed primitives lets people, agents and systems use AI safely and
seamlessly, demonstrated on the Microsoft stack for **Contoso Capital**, a fictional private markets firm.

The primitives:

1. **Identity**: people, agents and systems as Entra principals.
2. **Group membership**: the org as hierarchical domains, and who belongs where.
3. **Business terms**: a closed glossary whose terms tag both data and documents.
4. **Entitlements**: bounded access, written as rules over tags and compiled into what Microsoft enforces.
5. **Observability**: every object traceable to its domain, terms and access, with drift reported.

The thesis: in a large firm every one of these components is owned and configured by a different team
(identity, groups, data platform, catalog, collaboration, records), so any change is a chain of tickets
between them: the "coordination tax". When one owner holds the primitives as a single model and compiles
it into the platform, that tax disappears. Users never tag anything and never raise a ticket.

This is a first-round interview demo, not an enterprise build. Prove each primitive once, from the user's
seat. Describe everything else. The repository is the proof and must survive an antagonistic audit.

## Design

- **The model** (`model/`) is LinkML: about five classes (Domain, Role, StoreTemplate, Term, Rule) and
  three access-driving tag axes (domain, deal, sensitivity). It holds only what changes slowly. Keep it
  small enough to read in a minute.
- **Native Microsoft owns what changes fast**: deal room instances, team membership, documents, sharing.
  The model never manages who is on a deal team.
- **The compiler** is a Claude Code Skill that drives Microsoft's own tooling (CLI for Microsoft 365 and
  `az`). It runs at change time as the platform owner, never in a user's request path. It emits native
  objects, then runs **discover → remediate → report** over deal rooms that users create themselves.
  If it is switched off, the tenant keeps working; only automation and drift checks stop.
- **Tags are the source of truth for access.** Microsoft grants data access almost entirely through
  groups and roles (Fabric tags and domains do not affect access), so the compiler turns tag rules into
  Entra groups, team and site permissions, Fabric workspace roles and label settings.

Decisions already taken (rationale in `docs/decisions.md`):

| Decision | Choice | Rejected |
|---|---|---|
| Source of truth | LinkML model in git | Terraform (infrastructure layer, wrong owner); hand-configured tenant |
| Applying the model | Claude Code Skill + CLI for Microsoft 365 + `az` | Terraform providers; custom service |
| Deal rooms | Teams template, created by users; compiler applies site template and tags on discovery | Approval workflow and Logic Apps provisioning (described only) |
| Confidential vs public | Private teams with a sensitivity label vs a firm-wide research site; normal permission trimming | Restricted Content Discovery (hides from members too), Restricted SharePoint Search (retiring) |
| Metric interchange | Apache Ossie named as the future emit target for term-to-measure bindings; not built | Building on a 0.2 draft with no access constructs |
| AI over documents | SharePoint agent via Copilot Chat pay-as-you-go | Per-user Microsoft 365 Copilot licences |
| AI over portfolio data | Fabric data agent over the governed semantic model | Copilot Studio connected agent (needs a Copilot licence) |

## The five-minute demo (this is the scope)

Every beat starts from a business event, and names where the firm's own systems would plug in. Anything not
needed for these beats is out of scope unless the owner agrees otherwise.

1. **A CIM arrives for Project Atlas** (0:00). As the partner, in Teams: new team from the "Deal Room"
   template, Confidential label, add the associate, drop in the CIM. *Plug-in: in practice the CIM arrives
   from a banker's virtual data room or an inbox; that intake would trigger this step.*
2. **The backplane does the rest** (0:45). Run the compiler from Claude Code. Show why it knew what to do:
   the model (domains, roles, terms, rules in one file). It finds Atlas, applies the site template and the
   domain, deal and sensitivity tags. Open the CIM's properties: tagged, by nobody. The conformance report
   shows Atlas conformant.
3. **Research and contextualisation** (1:45). The partner asks the Atlas agent for the CIM's key risks and
   how the business compares with similar portfolio companies; it answers with citations. *Plug-in: this is
   where licensed research, prior IC memos and sector theses join as further stores, each declared in the
   model with its domain and tags, so the agent only ever sees what the asker can.*
4. **A new joiner, and an information barrier** (2:30). Switch to the analyst, who joined another deal team
   last week: their department was set and the right groups, Teams and sites followed. The research site is
   there; Atlas is not, in search or from the agent. *Plug-in: the HR system sets the department.*
5. **The month-end portfolio pack lands** (3:00). The partner asks the portfolio data agent which companies
   are behind plan on EBITDA; the answer uses the same glossary terms that tag the documents. *Plug-in: the
   firm's warehouse, semantic models or portfolio monitoring tool sit here; terms bind to whatever
   calculation finance already treats as authoritative.*
6. **The firm licenses a new data source** (4:00). In Claude Code: "Onboard a new data source to Private
   Equity". One model change, compiled, confirmed in the conformance report, the git diff as the audit
   trail. Today that is a ticket to each team that owns a piece of it.
7. **Close** (4:45). Every object traces to its domain, terms and access. Switch the compiler off and
   everything still works; only automation and drift checks stop.

Slow steps (agent answers take 20-60 seconds) are started early and talked over. The analyst's department
is set well before the call, because dynamic group updates take minutes.

Demo content (all fictional, in the repo): a CIM for Project Atlas, a few public-style research notes for
the research site, and the existing portfolio data.

## Definition of done

**Tenant**
- [ ] New Microsoft 365 E5 trial tenant (with Teams), auto-renew off, self-service trials and purchases off
- [ ] Licences assigned to a group; three personas (partner, analyst on another deal, ops lead who owns
      the glossary), each used from its own browser profile
- [ ] Pay-as-you-go Azure subscription in the tenant; F2 capacity, paused when idle
- [ ] Copilot Chat pay-as-you-go billing policy scoped to the personas group

**Model and compiler**
- [ ] LinkML schema and Contoso instance data, validated in CI; `gen-doc` output in `docs/`
- [ ] Compiler Skill emits: dynamic domain groups (from the user's department), term store sets and
      terms, content type and per-domain site templates, the Teams "Deal Room" template, Fabric domain,
      tags and workspace roles; the portfolio store redeployed from the repo
- [ ] Discover → remediate → report over deal rooms; the conformance report shows every store's domain,
      terms and access group, and drift

**One proof per primitive, from the user's seat**
- [ ] Identity: setting a persona's department places them in the right domain group, nothing else done
- [ ] Group membership: the partner creates "Project Atlas" from the Teams template and adds the team
- [ ] Business terms: Atlas files carry domain, deal and sensitivity tags no user applied; portfolio
      measures carry the same glossary terms
- [ ] Entitlements: research visible to all; Atlas only to its team; portfolio only to its domain; an AI
      answer per persona (SharePoint agent on Atlas, Fabric data agent on the portfolio)
- [ ] Observability: conformance report, model history in git, Microsoft 365 audit log entries

**The live moment**
- [ ] In Claude Code: "Onboard a new data source to Private Equity": one model change, compiled,
      confirmed in the conformance report, with the git diff as the audit trail

**Repository**
- [ ] `docs/`: primitives mapping, decisions and rejected alternatives, research with sources, Azure vs
      AWS comparison
- [ ] Every claim in the README links to evidence with raw output; limitations stated next to claims
- [ ] Adversarial review by an agent finds no false claims, gaps or security own-goals
- [ ] CI green before merge; history clean of secrets, tenant identifiers and forbidden names

**Budget:** about $15 or less. Free where possible, never more than $100.

## Environment facts

- Fabric needs a paid F2 capacity for data agents; trial capacity does not work. Users need Power BI
  Pro below F64 (included in E5). **Pause the capacity when a session ends.**
- Microsoft Graph cannot set library default column values or library default sensitivity labels, and
  term store writes are delegated-only; use the CLI for Microsoft 365 or SharePoint REST for those.
- An automation identity cannot apply a container sensitivity label; the user chooses it at team creation.
- Scripts a human runs on Windows target PowerShell 5.1 (no `&&` or `||`). Claude Code runs in bash.
- The owner prefers one consolidated, single-paste command block over step-by-step sequences.

## Working rules

- **Agree before building.** If a constraint (licences, cost, time) would change what end users see,
  stop and agree it with the owner first. Do not cut scope to fit a clock.
- **Sandbox shortcuts stay out of git.** Exploratory scripts go in `local/` (gitignored). Anything worth
  keeping is rewritten properly and arrives through a pull request.
- **No secrets in chat, code, commits or logs.** Prefer managed identity, federation and delegated sign-in.
- **Least privilege at runtime.** Agents and runtime identities get the narrowest access that works. The
  compiler runs at change time as the platform owner with admin roles; say so, and never reuse those
  rights at runtime.
- **Never name a real firm, employer, person or project** other than Contoso Capital and its fictional
  portfolio companies. CI enforces a deny-list over files and full history.
- **Stay on message.** Do not promote incidental findings into talking points.
- **Tear down what you create** when it is no longer needed, and say what you removed.
- **Teach as you go.** When you configure something in a portal or CLI, explain what it is and why, briefly.

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
An audit trail nobody can query. Personal email, tenant IDs or live public endpoints exposed through the
public repository. Claims of "production-ready", tests that do not test, or results without evidence.
Resources left running. An abstraction layer bigger than the problem it solves.

## Current state

A first build in a different tenant (2026-10-12) proved the portfolio store: sample data, lakehouse, TMDL
semantic model with glossary-bound measures, a data agent keyed by the workspace identity, and access
proofs (`results/2026-10-12/`). It is the starting point for the portfolio store in the new tenant.
`gateway/`, `bootstrap/` and `infra/` predate the current design; keep, rework or remove them as part of
the rebuild, and record which.
