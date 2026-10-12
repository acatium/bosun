# Replicating the Contoso Portfolio run

Everything below uses the files in this repository and standard Microsoft tooling (Azure CLI and the Fabric
REST API). Expect about two hours the first time, most of it waiting on licences and sign-ups. The run
costs a few dollars if you tear it down the same day.

Commands are shown for bash. `$WS`, `$LH`, `$SM` and `$DA` are the IDs each step returns.

## Before you start

- A Microsoft 365 tenant where you are Global Administrator (E3 is enough)
- A pay-as-you-go Azure subscription. Free trial and credit-only subscriptions cannot buy Fabric capacity
  in every region, and cannot deploy Claude models from Microsoft Foundry
- Azure CLI, signed in: `az login`
- Fabric enabled for the tenant: sign in once at app.fabric.microsoft.com and start the Power BI trial
- Fabric tenant settings (Admin portal > Tenant settings), which can take up to an hour to apply:
  "Users can use Copilot and other features powered by Azure OpenAI", "Capacities can be designated as
  Fabric Copilot capacities" and "Users can create Fabric items"

## 1. Capacity, workspace, domain

1. Find a region with Fabric quota: `az rest --url "https://management.azure.com/subscriptions/<sub>/providers/Microsoft.Fabric/locations/<region>/usages?api-version=2023-11-01"`.
   New subscriptions often have zero quota in some regions (East US 2 had none on 2026-10-12; Central US had 16 CUs).
2. Create a resource group and an **F2** capacity (`Microsoft.Fabric/capacities`, API `2023-11-01`) with
   yourself as administrator. Data agents do not run on trial capacity.
3. Create a workspace on the capacity: `POST /v1/workspaces`.
4. Create the domains in `config/profiles/contoso.yaml` (`POST /v1/admin/domains`) and assign the
   workspace to Finance & Operations (`POST /v1/admin/domains/{id}/assignWorkspaces`).

## 2. Data

1. Create a lakehouse: `POST /v1/workspaces/$WS/lakehouses`.
2. Upload `data/portfolio/*.csv` to `Files/portfolio/` in OneLake
   (`https://onelake.dfs.fabric.microsoft.com/$WS/$LH/Files/...`, ADLS Gen2 API, storage token).
3. Load each file as a Delta table: `POST /v1/workspaces/$WS/lakehouses/$LH/tables/<name>/load` with
   `{"relativePath": "Files/portfolio/<name>.csv", "pathType": "File", "mode": "Overwrite", "formatOptions": {"format": "Csv", "header": true, "delimiter": ","}}`.

## 3. Semantic model

1. Read the lakehouse's SQL endpoint host and ID: `GET /v1/workspaces/$WS/lakehouses/$LH`
   (`properties.sqlEndpointProperties`).
2. Substitute them for `{{SQL_ENDPOINT_HOST}}` and `{{SQL_ENDPOINT_ID}}` in
   `semantic-model/ContosoPortfolio.SemanticModel/definition/expressions.tmdl`, base64 each file under
   `ContosoPortfolio.SemanticModel/`, and `POST /v1/workspaces/$WS/semanticModels` with the parts.
3. **Store key.** Provision the workspace identity (`POST /v1/workspaces/$WS/provisionIdentity`), give it
   Viewer on the workspace, create a shareable cloud SQL connection to the SQL endpoint that
   authenticates as the workspace identity (`POST /v1/connections`, `credentialType: WorkspaceIdentity`),
   and bind the model to it (`POST /v1/workspaces/$WS/semanticModels/$SM/bindConnection`). The model now
   reads data as the store, not as each user.

## 4. Store agent

1. Substitute `{{WORKSPACE_ID}}` and `{{SEMANTIC_MODEL_ID}}` in the files under
   `data-agent/ContosoPortfolioAgent.DataAgent/` and `POST /v1/workspaces/$WS/dataAgents` with the parts.
   The definition includes the published stage, so the agent is published on creation.
2. Its MCP endpoint is `https://api.fabric.microsoft.com/v1/mcp/workspaces/$WS/dataagents/$DA/agent`.

## 5. Identity and access

1. Create the Entra security group `contoso-portfolio-readers` and give it Viewer on the workspace. This
   group is the store's access list and its agent's invocation gate.
2. Create two cloud-only test users, `contoso-partner` (in the group) and `contoso-outsider` (not in it).
   Sign each in once to app.fabric.microsoft.com and start the Power BI trial, so both have identical
   licences. They need MFA, so sign them in to the Azure CLI with `az login --use-device-code`, each in
   its own `AZURE_CONFIG_DIR`.

## 6. Gateway and Claude Code

```bash
python3 -m venv gateway/.venv && gateway/.venv/bin/pip install -r gateway/requirements.txt
export BOSUN_FABRIC_WORKSPACE_ID=$WS BOSUN_DATA_AGENT_ID=$DA
claude   # approve the bosun-gateway server from .mcp.json when prompted
```

To act as a test user, start Claude Code with that user's Azure CLI profile:
`AZURE_CONFIG_DIR=<partner profile dir> claude`. Calls are logged to `local/agent-actions.jsonl`.

## 7. Validate

Run the questions in `evals/golden-questions.yaml` and the cases in
`results/2026-10-12/access-and-guardrail.md` and compare.

## 8. Tear down

Delete the Fabric workspace, the cloud connection, the three Fabric domains, the Entra group and both test
users, then delete the resource group (which removes the capacity). Pause the capacity
(`az rest --method post .../capacities/<name>/suspend?api-version=2023-11-01`) whenever you stop for the day.
