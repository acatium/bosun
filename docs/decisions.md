# Decisions

Each decision says what was chosen, what was rejected and why. Evidence is linked where it exists.

## 1. One model is the source of truth

**Chosen:** a small LinkML model in git ([`model/bosun.yaml`](../model/bosun.yaml) is the schema,
[`model/contoso.yaml`](../model/contoso.yaml) the firm). It holds only what changes slowly: domains, roles,
business terms, stores and entitlement rules.

**Rejected:** Terraform (an infrastructure tool, owned by the wrong team for organisational objects that
change weekly); Purview's catalog as the source (it is one consumer of the definitions, and it covers data,
not documents); configuring the tenant by hand (that is the coordination tax).

**Limits:** LinkML's validators check types, enums, required fields and patterns but not references
between objects, so the compiler checks references itself ([`backplane/model.py`](../backplane/model.py),
tested in [`tests/test_model.py`](../tests/test_model.py)).

## 2. Agents propose, deterministic code applies, a person approves

**Chosen:** a compiler ([`backplane/`](../backplane/)) with `validate`, `plan`, `apply` and `report`, operated
through a Claude Code Skill ([`.claude/skills/backplane/SKILL.md`](../.claude/skills/backplane/SKILL.md)).
The agent edits the model and explains the plan; the compiler makes every change; `apply` waits for approval.

**Rejected:** an agent calling Microsoft APIs directly to make governance changes.

## 3. The runtime tool runs as the person asking, and holds no keys

**Chosen:** the backplane MCP server ([`backplane/mcp_server.py`](../backplane/mcp_server.py)) does its work
with the caller's own delegated sign-in, through an app registration, `contoso-backplane-runtime`, that is
delegated-only, has no secret, and can be used only by the firm's people group. The compiler uses a separate
app, `contoso-backplane`, assigned only to the platform owner, so change-time scopes such as term store
writes never reach the runtime path. The tool's input schema is generated from the model.

**Honest limit:** in this demo the server runs on the partner's own machine (option B below). The tool's
rule checks are therefore a guardrail on the agent's path, not a control the partner cannot bypass: the
partner could call Microsoft directly with their own rights. The native controls that also stop a person
are the sensitivity label (private, no guests) and group membership. Hosting the server (option A) removes
the partner's ability to edit the rules it runs.

## 4. A deal room is a Microsoft 365 group and its SharePoint site

**Chosen:** the tool creates a private group with the sensitivity label, adds the team, sets the library's
default tags (domain, deal, sensitivity) and default label through SharePoint's own API, files the CIM and
verifies the tags as the partner. It fails closed: no label, no room. A failure after the group exists
leaves it private and labelled, and the same request resumes it, but only for the caller's own room at the
same sensitivity. People are classified as guests from the directory's `userType`, never from their address.

**Rejected:** Teams templates plus SharePoint site templates (Teams templates cannot carry SharePoint
configuration, and site scripts cannot set default values or labels); a provisioning workflow with approvals
(described, not built). No Teams: the tenant's trial licence excludes it, and a Team is a layer on the same
group, so governance is unchanged.

**Evidence:** [`results/2026-10-13/model-talks-back.md`](../results/2026-10-13/model-talks-back.md).

## 5. Sensitivity labels are a documented prerequisite, not compiled

Creating and editing labels needs Microsoft's compliance PowerShell, whose sign-in works only from the
owner's Windows machine. The labels were created once by an admin script, kept outside the repository with
the other local admin steps. The conformance report says plainly that it does not check label settings.
The model's rule (only Confidential rooms refuse guests) and the labels' settings must agree; the owner
aligns them with a one-time admin edit.

## 6. Access is per store, nothing finer

The portfolio semantic model reads its data through the workspace's own identity (the store key), so
table-level security in OneLake would not constrain users who query through the model or its agent.
Access is therefore granted per store, by the model's rules, compiled into Fabric workspace roles. A
dataset's `domain` names who is accountable for it, not who may read it.

## 7. Tags are the source of truth; Microsoft enforces groups and roles

Microsoft's native tag- or attribute-based access is narrow (Azure storage conditions, Information Barriers,
Purview protection policies on whole Fabric items). Fabric tags and domains do not grant or restrict anything.
So the model's rules, written over tags, compile into Entra groups, workspace roles and label settings. When
Microsoft's attribute-based access matures, only the compiler's targets change.

## 8. What adding data needs, and why

From the IRR rehearsal ([`results/2026-10-13/irr-rehearsal.md`](../results/2026-10-13/irr-rehearsal.md)):
access needed nothing, because the data landed in a governed store. The definition was authored once by its
owner. Everything else (adding the table to the semantic model, telling the data agent about it, syncing the
SQL endpoint) is plumbing that Microsoft does not yet drive from tags, so the compiler does it.

## 9. Business terms: term store for documents, Purview for data (named)

The term store holds the vocabulary in SharePoint, and the semantic model's measures carry the same terms.
Documents in deal rooms are tagged with domain, deal and sensitivity (library defaults), not with business
terms. Purview's business glossary is the right enterprise home for terms over data; it is named, not built,
because its catalog is billed separately and its glossary API is in preview.

## 10. Apache Ossie is named, not built

Apache Ossie (formerly Open Semantic Interchange) is the right interchange format for metric definitions,
and Microsoft now contributes a Power BI converter. Its spec is a 0.2 draft with nothing for access control,
and the LinkML converters are unmerged. It is the future emit target for term-to-measure bindings.

## 11. Microsoft Foundry

The same backplane MCP server plugs into a Foundry agent as a tool, under the same model and rules, so an
agent built in Foundry gets the same governed actions. Hosting models in Foundry was not needed for the
demo's beats.

## 12. Where the partner talks to the agent

**Option B (built):** the Claude desktop app beside Outlook, with the backplane MCP server running locally
as the partner. **Option A (described):** Copilot in Outlook and Teams, through a Copilot Studio agent calling
the same MCP server hosted in Azure, with on-behalf-of sign-in and no stored secret. Same tools, model and
rules; only the chat window and where the server runs differ.

## 13. The platform owner cannot read deal rooms

The platform owner is a Global Administrator but not a deal team member, and cannot read a deal room's
content through Graph. The conformance report therefore reads label, privacy, members and guests from the
directory, and reports the library's tags as attested by the backplane when it created the room.

## 14. Retired

- `gateway/` (a local MCP gateway that blocked figures without a glossary term): it read a second glossary
  that drifted from the model. Its results from 2026-10-12 remain as evidence.
- `bootstrap/`, `infra/` and the deploy pipeline (GitHub-to-Azure federation for Bicep deployments): nothing
  in the current design deploys Azure resources from the repository.

## The six questions, per component

| Component | Runs as | Can access | Revoked by | Logged in | On failure | Cost |
|---|---|---|---|---|---|---|
| Compiler | The platform owner, delegated (`az`, and the CLI for Microsoft 365 through `contoso-backplane`, which only the platform owner is assigned to) | What the owner's admin roles allow, at change time only | Removing the owner's roles or the app assignment | Plan and apply output; Entra, Fabric and Microsoft 365 audit logs | Stops; re-plan shows what remains | $0 |
| Backplane MCP tool | The calling person, delegated through `contoso-backplane-runtime` | What that person can do: create groups they own, read the directory, their own mailbox, sites they own | Removing the person from the people group (the app requires assignment) or revoking consent | Receipt per call; Microsoft 365 audit log | Refuses or stops; a created room stays private and labelled and can be resumed | $0 |
| `contoso-backplane` app (change time) | Delegated only; assigned to the platform owner only; scopes: User.Read, User.Read.All, Group.ReadWrite.All, Sites.ReadWrite.All, Files.ReadWrite.All, TermStore.ReadWrite.All, Mail.Read, SharePoint AllSites.FullControl | Never more than the signed-in owner | Delete the app or its consent grant | Entra sign-in logs | n/a | $0 |
| `contoso-backplane-runtime` app (runtime) | Delegated only; assigned to the firm's people group only; scopes: User.Read, User.Read.All (to tell guests from members), Group.ReadWrite.All (Microsoft offers no narrower delegated scope that creates a group), Sites.Manage.All, Mail.Read, SharePoint AllSites.Manage. Mail.Read lets the agent read the person's whole mailbox, not just the CIM email | Never more than the signed-in person | Delete the app or its consent grant | Entra sign-in logs | n/a | $0 |
| Workspace identity (store key) | Fabric, for the portfolio semantic model's data connection | Read on the portfolio workspace | Remove its role, or deprovision it | Fabric activity in the Microsoft 365 audit log | Queries fail; nothing falls back to user access | $0 |
| Portfolio data agent | The calling person | Read on the semantic model, through the store key | Workspace role removal | Fabric activity | Says it cannot answer | Fabric F2 capacity, paused when idle |
| Personas | Themselves | Licences and access from the dynamic people and domain groups | Changing their company or department attribute | Entra and Microsoft 365 audit logs | n/a | Trial licences |
| `contoso-demo-seeder` app (demo setup only) | The partner persona, delegated, Mail.ReadWrite | That persona's mailbox | Deleted after seeding (done 2026-10-13) | Entra sign-in logs | n/a | $0 |
