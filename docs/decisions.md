# Decisions

What was chosen, what was not, and the constraint behind it where one was observed.

| # | Decision | Chosen | Not chosen |
|---|---|---|---|
| 1 | Source of truth | LinkML model in git ([`model/`](../model/)) | Terraform; Purview catalog; hand configuration |
| 2 | Applying changes | Deterministic compiler (`validate`, `plan`, `apply`, `report`), run through a Claude Code Skill; the Skill runs `apply` only after the person approves the plan | An agent calling Microsoft APIs directly |
| 3 | Runtime identity | MCP server acts with the caller's delegated sign-in through `contoso-backplane-runtime`; the compiler uses a separate app, `contoso-backplane`, assigned only to the platform owner | A service identity with application permissions |
| 4 | Deal room | Microsoft 365 group and SharePoint site, created by `create_deal_room` as the partner | Teams and site templates; a provisioning workflow |
| 5 | Sensitivity labels | Created once by an admin script (compliance PowerShell, Windows only); not compiled | Compiling labels |
| 6 | Portfolio access | Per store: Fabric workspace roles compiled from the model's rules | Table-level OneLake security |
| 7 | Tags and access | Rules over tags compiled into Entra groups and Fabric workspace roles | Fabric tags or domains as access controls |
| 8 | Business terms | SharePoint term store and semantic model measures | Purview business glossary |
| 9 | Partner's agent | Claude desktop with the MCP server running locally as the partner | Copilot Studio with a hosted MCP server (not built) |
| 10 | AI over documents | Not built | A SharePoint agent |

## Observed constraints

- LinkML validators do not check references between objects; the compiler checks them
  ([`backplane/model.py`](../backplane/model.py), [`tests/test_model.py`](../tests/test_model.py)).
- Microsoft Graph accepts but does not store library default column values; they are set through SharePoint
  REST and read back.
- An app-only identity cannot apply a container sensitivity label; the user's delegated sign-in can.
- Group creation by delegated sign-in needs `Group.ReadWrite.All`.
- `User.ReadBasic.All` returns no `userType`; guest detection needs `User.Read.All`. People whose type cannot
  be read are refused.
- Fabric tags cannot contain `:` or `&`. The term store stores `&` as `＆`.
- A new lakehouse table needs a SQL endpoint metadata refresh, a semantic model refresh and an entry in the
  data agent's data source before the agent can query it.
- Fabric caches group membership until the user next signs in to the Fabric service.
- The platform owner, not being a deal-team member, cannot read deal-room content through Graph; the
  conformance report reads label, privacy and members from the directory and library tags from receipts.
- The semantic model reads data through the workspace identity, so OneLake table security does not apply to
  queries through the model or the data agent.
- Fabric data agents need a paid F2 capacity; trial capacity does not work.

## Retired

- `gateway/`: a local MCP gateway that checked answers against a separate glossary file. Its 2026-10-12
  results remain in [`results/2026-10-12/`](../results/2026-10-12/).
- `bootstrap/`, `infra/` and the deploy pipeline.
- `contoso-demo-seeder`: a delegated app used once to place the CIM email in the partner's mailbox; deleted
  2026-10-13.

## Components: identity, access, revocation, logging, failure, cost

| Component | Runs as | Can access | Revoked by | Logged in | On failure | Cost |
|---|---|---|---|---|---|---|
| Compiler | Platform owner, delegated (`az`; CLI for Microsoft 365 through `contoso-backplane`) | What the owner's admin roles allow | Removing the owner's roles or app assignment | Plan and apply output; Entra, Fabric and Microsoft 365 audit logs | Stops; re-plan shows what remains | $0 |
| `create_deal_room` | The caller, delegated through `contoso-backplane-runtime` | What the caller can do | Removing the caller from the people group (assignment required) or revoking consent | Receipt per call; Microsoft 365 audit log | Refuses or stops; a created room stays private and labelled and can be resumed by its owner | $0 |
| `contoso-backplane` app | Delegated only; assigned to the platform owner. Scopes: User.Read, User.Read.All, Group.ReadWrite.All, Sites.ReadWrite.All, Files.ReadWrite.All, TermStore.ReadWrite.All, Mail.Read, SharePoint AllSites.FullControl | No more than the signed-in owner | Delete the app or consent grant | Entra sign-in logs | n/a | $0 |
| `contoso-backplane-runtime` app | Delegated only; assigned to the people group. Scopes: User.Read, User.Read.All, Group.ReadWrite.All, Sites.Manage.All, Mail.Read (whole mailbox), SharePoint AllSites.Manage | No more than the signed-in person | Delete the app or consent grant | Entra sign-in logs | n/a | $0 |
| Workspace identity | Fabric, as the semantic model's data connection | Read on the portfolio workspace | Remove its role or deprovision it | Microsoft 365 audit log (Fabric activity) | Queries fail | $0 |
| Portfolio data agent | The caller | Semantic model, through the workspace identity | Workspace role removal | Fabric activity | Says it cannot answer; may return a wrong figure (see README known gaps) | F2 capacity, paused when idle |
| Personas | Themselves | Licences and access from dynamic groups | Changing company or department | Entra and Microsoft 365 audit logs | n/a | Trial licences |
