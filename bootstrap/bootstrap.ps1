<#
.SYNOPSIS
  One-time bootstrap: creates the trust between GitHub Actions and Entra ID.

.DESCRIPTION
  This is the only manual step in the environment. Run it once from a clone of the repository,
  as a Global Administrator, in Windows PowerShell 5.1 or later. It is safe to re-run: every step
  checks for existing objects first.

  Settings come from .env in the repository root (copy .env.example). Nothing in .env is a secret.

  It creates:
    - The resource group that holds every Azure resource for this platform
    - The deploy identity (an Entra app registration with no secrets)
    - Federated credentials so GitHub Actions in this repository, and only this repository,
      can sign in as it
    - Contributor rights on that one resource group, and nothing else in Azure
    - The Graph application permissions listed in $GraphPermissions (checked in CI against
      config/guardrails.yaml)
    - The GitHub repository variables, production environment and DENYLIST secret

  Requires: Azure CLI (winget install -e --id Microsoft.AzureCLI) and GitHub CLI
  (winget install -e --id GitHub.cli).
#>
param(
  [string]$EnvFile = (Join-Path $PSScriptRoot '..\.env')
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = 'Tls12'

# Must stay within allowed_graph_application_permissions in config/guardrails.yaml (enforced in CI).
$GraphPermissions = @('Group.Create', 'Application.ReadWrite.OwnedBy')

# ---- Settings -------------------------------------------------------------------------------
if (-not (Test-Path $EnvFile)) { throw "No .env found at $EnvFile. Copy .env.example to .env and fill it in." }
$cfg = @{}
foreach ($line in Get-Content $EnvFile) {
  if ($line -match '^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*(#.*)?$') { $cfg[$Matches[1]] = $Matches[2].Trim('"', "'") }
}
$required = 'FIRM_PROFILE', 'AZURE_LOCATION', 'AZURE_RESOURCE_GROUP', 'DEPLOYER_APP_NAME', 'GITHUB_OWNER', 'GITHUB_REPO'
$missing = @($required | Where-Object { -not $cfg[$_] })
if ($missing.Count -gt 0) { throw "Fill in these values in .env: $($missing -join ', ')" }

$profilePath = Join-Path $PSScriptRoot "..\config\profiles\$($cfg.FIRM_PROFILE).yaml"
if (-not (Test-Path $profilePath)) { throw "Firm profile not found: config/profiles/$($cfg.FIRM_PROFILE).yaml" }
$prefixMatch = Select-String -Path $profilePath -Pattern '^\s*prefix:\s*([a-z][a-z0-9]*)' | Select-Object -First 1
if (-not $prefixMatch) { throw "No prefix found in config/profiles/$($cfg.FIRM_PROFILE).yaml" }
$prefix = $prefixMatch.Matches[0].Groups[1].Value
$repoRef = "$($cfg.GITHUB_OWNER)/$($cfg.GITHUB_REPO)"
Write-Host "Firm profile '$($cfg.FIRM_PROFILE)' (prefix '$prefix') for $repoRef"

function Assert-Command($name, $install) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) { throw "$name not found. Install it with: $install, then reopen PowerShell." }
}
Assert-Command 'az' 'winget install -e --id Microsoft.AzureCLI'
Assert-Command 'gh' 'winget install -e --id GitHub.cli'
if (-not (Get-Module -ListAvailable Microsoft.Graph.Authentication)) {
  Install-PackageProvider NuGet -Scope CurrentUser -Force | Out-Null
  Install-Module Microsoft.Graph.Authentication -Scope CurrentUser -Force -AllowClobber
}

# ---- Azure ----------------------------------------------------------------------------------
Write-Host '== Azure ==' -ForegroundColor Cyan
if ($cfg.AZURE_TENANT_ID) { az login --tenant $cfg.AZURE_TENANT_ID --only-show-errors | Out-Null } else { az login --only-show-errors | Out-Null }
if ($cfg.AZURE_SUBSCRIPTION_ID) { az account set --subscription $cfg.AZURE_SUBSCRIPTION_ID }
$subId = az account show --query id -o tsv
$tenantId = az account show --query tenantId -o tsv
Write-Host "Subscription $subId in tenant $tenantId"
az group create --name $cfg.AZURE_RESOURCE_GROUP --location $cfg.AZURE_LOCATION --tags managedBy=bootstrap domain=technology --only-show-errors | Out-Null
Write-Host "Resource group $($cfg.AZURE_RESOURCE_GROUP) ready"

# ---- Entra ID -------------------------------------------------------------------------------
Write-Host '== Entra ID ==' -ForegroundColor Cyan
Connect-MgGraph -TenantId $tenantId -Scopes 'Application.ReadWrite.All', 'AppRoleAssignment.ReadWrite.All' -NoWelcome
$graphAppId = '00000003-0000-0000-c000-000000000000'
$graphSp = (Invoke-MgGraphRequest GET "v1.0/servicePrincipals?`$filter=appId eq '$graphAppId'").value[0]
$roles = foreach ($name in $GraphPermissions) {
  $role = $graphSp.appRoles | Where-Object { $_.value -eq $name -and $_.allowedMemberTypes -contains 'Application' }
  if (-not $role) { throw "Graph application permission $name not found" }
  $role
}

$appName = $cfg.DEPLOYER_APP_NAME
$existing = @((Invoke-MgGraphRequest GET "v1.0/applications?`$filter=displayName eq '$appName'").value)
if ($existing.Count -gt 0) {
  $app = $existing[0]
  Write-Host "Reusing app registration $appName"
} else {
  $body = @{
    displayName = $appName
    requiredResourceAccess = @(@{ resourceAppId = $graphAppId; resourceAccess = @($roles | ForEach-Object { @{ id = $_.id; type = 'Role' } }) })
  } | ConvertTo-Json -Depth 10
  $app = Invoke-MgGraphRequest POST 'v1.0/applications' -Body $body -ContentType 'application/json'
  Write-Host "Created app registration $appName"
}

$spList = @((Invoke-MgGraphRequest GET "v1.0/servicePrincipals?`$filter=appId eq '$($app.appId)'").value)
if ($spList.Count -gt 0) { $sp = $spList[0] } else {
  $sp = Invoke-MgGraphRequest POST 'v1.0/servicePrincipals' -Body (@{ appId = $app.appId } | ConvertTo-Json) -ContentType 'application/json'
}

$assigned = @((Invoke-MgGraphRequest GET "v1.0/servicePrincipals/$($sp.id)/appRoleAssignments").value)
foreach ($role in $roles) {
  if (-not ($assigned | Where-Object { $_.appRoleId -eq $role.id })) {
    $grant = @{ principalId = $sp.id; resourceId = $graphSp.id; appRoleId = $role.id } | ConvertTo-Json
    Invoke-MgGraphRequest POST "v1.0/servicePrincipals/$($sp.id)/appRoleAssignedTo" -Body $grant -ContentType 'application/json' | Out-Null
    Write-Host "Granted Graph permission $($role.value)"
  }
}

$subjects = @{
  'github-production'   = "repo:${repoRef}:environment:production"
  'github-pull-request' = "repo:${repoRef}:pull_request"
}
$credentials = @((Invoke-MgGraphRequest GET "v1.0/applications/$($app.id)/federatedIdentityCredentials").value)
foreach ($name in $subjects.Keys) {
  if (-not ($credentials | Where-Object { $_.name -eq $name })) {
    $credential = @{ name = $name; issuer = 'https://token.actions.githubusercontent.com'; subject = $subjects[$name]; audiences = @('api://AzureADTokenExchange') } | ConvertTo-Json
    Invoke-MgGraphRequest POST "v1.0/applications/$($app.id)/federatedIdentityCredentials" -Body $credential -ContentType 'application/json' | Out-Null
    Write-Host "Trusted $($subjects[$name])"
  }
}

# ---- Azure role -----------------------------------------------------------------------------
Write-Host '== Azure role ==' -ForegroundColor Cyan
$scope = "/subscriptions/$subId/resourceGroups/$($cfg.AZURE_RESOURCE_GROUP)"
$existingRole = az role assignment list --assignee $sp.id --scope $scope --role Contributor --query "[0].id" -o tsv
if (-not $existingRole) {
  Start-Sleep 20  # allow the new identity to replicate before assigning a role
  az role assignment create --assignee-object-id $sp.id --assignee-principal-type ServicePrincipal --role Contributor --scope $scope --only-show-errors | Out-Null
}
Write-Host "Contributor on $($cfg.AZURE_RESOURCE_GROUP) only"

# ---- GitHub ---------------------------------------------------------------------------------
Write-Host '== GitHub ==' -ForegroundColor Cyan
gh auth status 2>$null
if ($LASTEXITCODE -ne 0) { gh auth login --hostname github.com --web --git-protocol https }
$variables = [ordered]@{
  AZURE_CLIENT_ID       = $app.appId
  AZURE_TENANT_ID       = $tenantId
  AZURE_SUBSCRIPTION_ID = $subId
  AZURE_RESOURCE_GROUP  = $cfg.AZURE_RESOURCE_GROUP
  FIRM_PROFILE          = $cfg.FIRM_PROFILE
  FIRM_PREFIX           = $prefix
}
foreach ($key in $variables.Keys) { gh variable set $key --body $variables[$key] --repo $repoRef }
gh api --method PUT "repos/$repoRef/environments/production" --silent
Write-Host 'Repository variables and production environment set'

$denylist = gh secret list --repo $repoRef --json name --jq '.[].name' | Where-Object { $_ -eq 'DENYLIST' }
if (-not $denylist) {
  Write-Host ''
  Write-Host 'Enter the deny-list terms, comma-separated. They are stored only as a GitHub secret.' -ForegroundColor Yellow
  gh secret set DENYLIST --repo $repoRef
}

Write-Host ''
Write-Host 'Bootstrap complete. No Azure secrets were created; GitHub Actions signs in by federation.' -ForegroundColor Green
Write-Host 'Remaining manual setting: Settings > Environments > production, add required reviewers.'
