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
- **Two pieces of code, both deterministic:**
  - **The compiler** (change time). Runs when the model changes, as the platform owner, through a Claude
    Code Skill that edits the model, validates it, shows the plan, applies on approval and reports.
    It emits the model-level objects (domain groups, term sets, content type, site and team templates,
    Fabric domain and roles) and produces the conformance report. Never in a user's request path.
  - **The backplane MCP server** (runtime). The tools an agent calls on a user's behalf, starting with
    `create_deal_room`. Input schemas are generated from the LinkML model, so required fields the user
    leaves out (e.g. sensitivity) make the agent ask. Each tool checks the model's rules (may this role
    open a deal room in this domain?), then does the work **as the calling user** with their own
    sign-in: the partner owns the new site, so no admin rights are used at runtime. Every call writes
    a receipt.
- **Agents propose, code applies, a human approves.** No agent touches the tenant except through these
  deterministic tools.
- If both are switched off, the tenant keeps working as plain Microsoft 365; only automation, the
  agent's deal-room tool and drift checks stop.
- **Tags are the source of truth for access.** Microsoft grants data access almost entirely through
  groups and roles (Fabric tags and domains do not affect access), so tag rules compile into Entra
  groups, team and site permissions, Fabric workspace roles and label settings.

Decisions already taken (rationale in `docs/decisions.md`):

| Decision | Choice | Rejected |
|---|---|---|
| Source of truth | LinkML model in git | Terraform (infrastructure layer, wrong owner); hand-configured tenant |
| Applying the model | Deterministic compiler, operated through a Claude Code Skill, using CLI for Microsoft 365 + `az` | Terraform providers; an agent acting on the tenant directly |
| Deal rooms | The partner asks their agent; the backplane MCP tool creates and tags the room (a Microsoft 365 group and its SharePoint site) as the partner | Users clicking through templates; approval workflow and Logic Apps provisioning (described only) |
| Partner's agent | **A:** Copilot in Outlook/Teams (Copilot Studio agent → MCP server hosted in Azure Functions, on-behalf-of sign-in, no stored secret), if pay-as-you-go authoring works. **B:** Claude desktop app beside Outlook with the same MCP server running locally as the partner. Same tools, model and guardrails either way | Per-user Copilot or Copilot Studio licences |
| Tenant | The existing tenant plus a Microsoft 365 E5 (no Teams) trial; the demo runs only from Contoso persona browser profiles | A new tenant (cleaner, but slower); upgrading real E3 seats |
| Foundry | Not used: hosting Claude in Foundry is billing consolidation, not a demo point | Claude Code on a Foundry deployment |
| Confidential vs public | Private teams with a sensitivity label vs a firm-wide research site; normal permission trimming | Restricted Content Discovery (hides from members too), Restricted SharePoint Search (retiring) |
| Metric interchange | Apache Ossie named as the future emit target for term-to-measure bindings; not built | Building on a 0.2 draft with no access constructs |
| AI over documents | Not demonstrated: permission-trimmed retrieval is Microsoft's promise, named not shown | A SharePoint agent demo (spend and time for no differentiation) |
| AI over portfolio data | Fabric data agent over the governed semantic model | Copilot Studio connected agent (needs a Copilot licence) |

## The five-minute demo (this is the scope)

**The line:** "One model of the firm's primitives, compiled into Microsoft's native controls and called
through MCP from where people already work, so governance happens automatically instead of by coordination."

Every beat starts from a business event. Test for anything else: could the audience see it in a Microsoft
demo? If yes, say it in a sentence; don't demo it. Anything not needed for these beats is out of scope
unless the owner agrees otherwise.

1. **A CIM arrives for Project Atlas** (0:00-2:00). The partner has the banker's email open in Outlook
   and tells their agent: "Set up a deal room for Project Atlas, add Priya and Sam, and file the CIM."
   - **The model talks back.** Sensitivity is required by the model, so the agent asks how confidential
     Atlas is. "I didn't prompt that. The model required it." The partner answers "Confidential".
   - **The backplane builds it.** The MCP tool checks the model's rules and, as the partner, creates the
     team, applies the site template and the domain, deal and sensitivity tags, adds the members and files
     the CIM. Open the CIM's properties: tagged, by nobody. Show the receipt and the model behind it.
   - **A deterministic no.** The partner asks to add an external banker contact. The tool refuses, citing
     the model's rule that Confidential rooms take no guests. The model decided, not the LLM.
   - *Plug-in: the CIM arrives from a banker's data room or the deal inbox; licensed research, prior IC
     memos and sector theses join as further stores in the model, and agents only retrieve as the asker.*
2. **The month-end portfolio pack lands** (2:00-3:00). The partner asks the portfolio data agent which
   companies are behind plan on EBITDA; the answer uses the same glossary terms that tag the documents.
   Then "What's Fabrikam's IRR?": IRR is not a defined term, so the agent says so and offers the closest
   defined terms. *Plug-in: the firm's warehouse, semantic models or portfolio monitoring tool; terms
   bind to whatever calculation finance already treats as authoritative.*
3. **Finance defines IRR** (3:00-4:15). The IRR refusal goes to Jordan, the Finance & Operations lead
   who owns the glossary. Jordan agrees a definition (Gross IRR from fund cash flows, as of quarter end)
   and names the fund administrator's cash-flow file as the source. The platform owner, in Claude Code
   through the `/backplane` Skill, adds the term to the model: a few lines, shown as a diff. The compiler
   loads the cash-flow file into the lakehouse with its domain, tags and access, adds the IRR measure to
   the semantic model bound to the term, adds the term to the term store, updates the data agent's
   vocabulary, and the conformance report shows it. The partner asks again and gets Fabrikam's IRR under
   the agreed definition, as of quarter end, with the source named. Normally that is four teams (data
   ingestion, BI, catalog, access) and weeks; here it is one decision and one reviewed change.
   **Framing (agreed):** access needed no compiling, because the data landed in a governed store. The
   definition was one decision by its owner. Everything else is Microsoft plumbing that doesn't yet
   follow tags (semantic model tables, the agent's table list, SQL endpoint sync), so the compiler does
   it: exactly the work four teams coordinate today. When Microsoft's semantic layer and agents discover
   by tag, those compiler steps disappear and the model doesn't change.
4. **Close** (4:15-5:00). Every object traces to its domain, terms and access. Switch the backplane off
   and everything still works as plain Microsoft 365. "I built this with Claude Code; the repo holds every
   decision and its evidence. Agents propose, deterministic code applies, a human approves: that's how
   I'd run the AI team too." Optional: a 10-second switch to the analyst's browser profile, where Atlas
   doesn't exist.

**Say, don't show:** permission-trimmed retrieval (Microsoft's promise); new joiners getting access from
their department; swapping the compile target (attribute-based access as it matures, or AWS Lake
Formation tags) without changing the model; drift detection. Hold these for questions.

Slow steps (agent answers take 20-60 seconds) are started early and talked over.

Demo content (all fictional, in the repo): a CIM for Project Atlas, the existing portfolio data, and a fund
administrator cash-flow file for the IRR beat.

No Teams: a deal room is a Microsoft 365 group with its SharePoint site and mailbox. In a firm with Teams,
the same tool would also create the Team on that group; governance is unchanged.

## Definition of done

**Tenant**
- [ ] Microsoft 365 E5 (no Teams) trial in the existing tenant; not cancelled until after the interview
      (cancelling suspends licences immediately); self-service trials and purchases off
- [ ] Licences assigned to a group; three Contoso personas (partner, analyst on another deal, ops lead who
      owns the glossary), each used only from its own browser profile
- [ ] F2 capacity in the existing subscription, paused when idle

**Model and compiler (change time)**
- [ ] LinkML schema and Contoso instance data, validated in CI; `gen-doc` output in `docs/`
- [ ] Compiler, operated through a Claude Code Skill (validate → plan → apply → report), emits:
      dynamic domain groups (from the user's department), term sets and terms, content type and
      per-domain site templates, the Fabric domain, tags and workspace roles; the portfolio store
      redeployed from the repo
- [ ] Conformance report: every store's domain, terms and access group, and drift

**Backplane MCP server (runtime)**
- [ ] `create_deal_room` tool: input schema generated from the model; rule check against the model;
      runs as the calling user; creates the team with its label, applies the site template and library
      defaults, adds members, files the CIM, writes a receipt
- [ ] Rule refusal: adding a guest to a Confidential room is refused with the rule's name
- [ ] Verified from the Claude desktop app as the partner (option B)
- [ ] Pay-as-you-go authoring check for Copilot Studio (about 10 minutes, $0). If it passes: the same
      server hosted in Azure Functions with on-behalf-of sign-in and no stored secret, behind a Copilot
      Studio agent in Outlook and Teams (option A). If it fails: B is the demo and A is described

**One proof per primitive, from the user's seat**
- [ ] Identity: setting a persona's department places them in the right domain group, nothing else done
- [ ] Group membership: the partner's request creates "Project Atlas" with the right members
- [ ] Business terms: the CIM carries domain, deal and sensitivity tags no user applied; portfolio
      answers use the same glossary terms; an undefined term (IRR) is refused, not estimated
- [ ] Entitlements: the agent asks for the missing sensitivity; the guest request is refused; Atlas only
      visible to its team; portfolio only to its domain
- [ ] Observability: receipts, conformance report, model history in git, Microsoft 365 audit log entries

**The live moment**
- [ ] "Finance defines IRR": one model change (term, owner, source, domain) compiled into a lakehouse
      table with domain, tags and access, an IRR measure bound to the term, the term store, and the data
      agent's vocabulary; the partner's re-asked question is answered under the agreed definition
- [ ] The data agent's term list is generated from the model, so new terms reach it automatically

**Repository**
- [ ] `docs/`: primitives mapping, decisions and rejected alternatives, research with sources, Azure vs
      AWS comparison
- [ ] Every claim in the README links to evidence with raw output; limitations stated next to claims
- [ ] Adversarial review by an agent finds no false claims, gaps or security own-goals
- [ ] CI green before merge; history clean of secrets, tenant identifiers and forbidden names

**Budget:** about $15 or less. Free where possible, never more than $100. No purchase with a
multi-month commitment.

## Build order

1. Microsoft 365 E5 (no Teams) trial and personas (owner starts the trial; the rest is scripted).
2. LinkML model and schema, merging `config/profiles/contoso.yaml` and `config/glossary.yaml`.
3. Compiler and conformance report for the model-level objects.
4. Backplane MCP server with `create_deal_room`; verify end to end from the Claude desktop app (B).
5. In parallel: the Copilot Studio pay-as-you-go check. Then A if it passes.
6. Portfolio store redeployed; Atlas CIM and fund cash-flow content; the IRR beat.
7. Docs, evidence, adversarial review, merge.

## Environment facts

- Fabric needs a paid F2 capacity for data agents; trial capacity does not work. Users need Power BI
  Pro below F64 (included in E5). **Pause the capacity when a session ends.**
- Microsoft Graph cannot set library default column values or library default sensitivity labels, and
  term store writes are delegated-only; use the CLI for Microsoft 365 or SharePoint REST for those.
- An app-only identity cannot apply a container sensitivity label; the backplane applies it as the calling
  user, which Microsoft allows.
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

A first build (2026-10-12) proved the portfolio store in this tenant: sample data, lakehouse, TMDL
semantic model with glossary-bound measures, a data agent keyed by the workspace identity, and access
proofs (`results/2026-10-12/`). Its F2 capacity is paused. It is the starting point for the portfolio
store. `gateway/`, `bootstrap/` and `infra/` predate the current design; keep, rework or remove them as
part of the rebuild, and record which.
