# Replicating Bosun

Everything here uses the files in this repository and Microsoft's own tooling: the Azure CLI, the CLI for
Microsoft 365, the Fabric REST API and, for labels, Microsoft's compliance PowerShell. Environment-specific
identifiers go in a gitignored `local/bosun.env`; nothing in tracked files names a tenant.

## Prerequisites

- A Microsoft 365 tenant with Entra ID P1 and Power BI Pro for the people in the demo (a Microsoft 365 E5
  trial covers both; the no-Teams edition is enough). Do not cancel a trial before you are finished:
  cancelling suspends its licences at once.
- A pay-as-you-go Azure subscription in the same tenant, with quota for a Fabric F2 capacity in your region.
- Fabric tenant settings: "Users can use Copilot and other features powered by Azure OpenAI", "Capacities can
  be designated as Fabric Copilot capacities", "Users can create Fabric items".
- Python 3.13 and Node 22. `python -m venv model/.venv && model/.venv/bin/pip install -r requirements.txt`,
  `npm install -g @pnp/cli-microsoft365`.

## One-time admin steps

1. **People:** set `companyName` and `department` (and `jobTitle` for partners) on the demo users. A dynamic
   group on `companyName` assigns their licences.
2. **Labels:** in Windows PowerShell with the ExchangeOnlineManagement module, after `Connect-IPPSSession`:
   ```powershell
   foreach ($l in @(@('contoso-public','Contoso Public','Public',$true), @('contoso-internal','Contoso Internal','Private',$true), @('contoso-confidential','Contoso Confidential','Private',$false))) {
     New-Label -Name $l[0] -DisplayName $l[1] -Tooltip $l[1] -ContentType 'File, Email, Site, UnifiedGroup'
     Set-Label -Identity $l[0] -SiteAndGroupProtectionEnabled $true -SiteAndGroupProtectionPrivacy $l[2] -SiteAndGroupProtectionAllowAccessToGuestUsers $l[3] -SiteExternalSharingControlType ExistingExternalUserSharingOnly
   }
   New-LabelPolicy -Name contoso-labels -Labels contoso-public,contoso-internal,contoso-confidential -ExchangeLocation <demo users>
   Execute-AzureAdLabelSync
   ```
   Guests are allowed on Public and Internal and refused on Confidential, matching the model's rule. Also
   enable labels for groups (the Entra `Group.Unified` setting `EnableMIPLabels`) and for SharePoint files
   (`Set-SPOTenant -EnableAIPIntegration $true`). Labels take hours to reach users; after that, put each
   label's id in `local/bosun.env` as `BOSUN_LABEL_<SENSITIVITY>`.
3. **App registration:** a public-client, delegated-only app (no secret) with the scopes listed in
   [`docs/decisions.md`](docs/decisions.md), admin consent, and "assignment required" with the demo users'
   group and the platform owner assigned. Sign in the CLI for Microsoft 365 through it as the platform owner.
4. **Portfolio store:** an F2 capacity, a workspace, a lakehouse loaded from `data/portfolio/`, the semantic
   model from `semantic-model/` (substitute the SQL endpoint host and id), the workspace identity bound to the
   model as its connection, and the data agent from `data-agent/` (substitute workspace and model ids).

## Compile the model

```bash
set -a; source local/bosun.env; set +a
model/.venv/bin/python -m backplane validate
model/.venv/bin/python -m backplane plan
model/.venv/bin/python -m backplane apply     # after reviewing the plan
model/.venv/bin/python -m backplane report
```

## The partner's agent

Run the MCP server as the partner: sign the CLI for Microsoft 365 in as the partner in a separate home
directory, then start `python -m backplane.mcp_server` with that `HOME`. In Claude desktop, register it as a
local MCP server (on Windows with WSL: `wsl.exe -d <distro> -- <launcher> <persona>`).

## Tear down

Delete the deal-room groups (and purge their sites from the SharePoint recycle bin), the Contoso groups, the
term group, the Fabric workspace, domains, tags and connection, the app registration, the labels and label
policy, the demo users and guest, and the resource group with the capacity. Then let the trial lapse.
