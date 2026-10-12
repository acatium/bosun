<#
.SYNOPSIS
  One-time bootstrap: creates the trust between GitHub Actions and Entra ID.

.DESCRIPTION
  This is the only manual step in the environment. Run it once, as a Global Administrator,
  in Windows PowerShell 5.1. It is safe to re-run: every step checks for existing objects first.

  It creates:
    - The resource group that holds every Contoso Capital Azure resource
    - The deploy identity (an Entra app registration with no secrets)
    - Federated credentials so GitHub Actions in this repo, and only this repo, can sign in as it
    - Contributor rights on that one resource group, and nothing else in Azure
    - The Graph application permissions listed in $GraphPermissions (checked in CI against
      config/guardrails.yaml)
    - The GitHub repository variables, production environment and DENYLIST secret

  Requires: Azure CLI (winget install -e --id Microsoft.AzureCLI) and GitHub CLI
  (winget install -e --id GitHub.cli), both signed in.
#>
param(
  [string]$GitHubOwner = 'acatium',
  [string]$GitHubRepo = 'bosun',
  [string]$ResourceGroup = 'rg-contoso-demo',
  [string]$Location = 'eastus',
  [string]$AppName = 'contoso-deployer'
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = 'Tls12'

# Must stay within allowed_graph_application_permissions in config/guardrails.yaml (enforced in CI).
$GraphPermissions = @('Group.Create', 'Application.ReadWrite.OwnedBy')

function Assert-Command($name, $install) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) { throw "$name not found. Install it with: $install, then reopen PowerShell." }
}
Assert-Command 'az' 'winget install -e --id Microsoft.AzureCLI'
Assert-Command 'gh' 'winget install -e --id GitHub.cli'
if (-not (Get-Module -ListAvailable Microsoft.Graph.Authentication)) {
  Install-PackageProvider NuGet -Scope CurrentUser -Force | Out-Null
  Install-Module Microsoft.Graph.Authentication -Scope CurrentUser -Force -AllowClobber
}

Write-Host '== Azure ==' -ForegroundColor Cyan
az login --only-show-errors | Out-Null
$subId = az account show --query id -o tsv
$tenantId = az account show --query tenantId -o tsv
Write-Host "Subscription $subId in tenant $tenantId"
az group create --name $ResourceGroup --location $Location --tags managedBy=bootstrap domain=technology --only-show-errors | Out-Null
Write-Host "Resource group $ResourceGroup ready"

Write-Host '== Entra ID ==' -ForegroundColor Cyan
Connect-MgGraph -TenantId $tenantId -Scopes 'Application.ReadWrite.All', 'AppRoleAssignment.ReadWrite.All' -NoWelcome
$graphAppId = '00000003-0000-0000-c000-000000000000'
$graphSp = (Invoke-MgGraphRequest GET "v1.0/servicePrincipals?`$filter=appId eq '$graphAppId'").value[0]
$roles = foreach ($name in $GraphPermissions) {
  $role = $graphSp.appRoles | Where-Object { $_.value -eq $name -and $_.allowedMemberTypes -contains 'Application' }
  if (-not $role) { throw "Graph application permission $name not found" }
  $role
}

$existing = @((Invoke-MgGraphRequest GET "v1.0/applications?`$filter=displayName eq '$AppName'").value)
if ($existing.Count -gt 0) {
  $app = $existing[0]
  Write-Host "Reusing app registration $AppName"
} else {
  $body = @{
    displayName = $AppName
    requiredResourceAccess = @(@{ resourceAppId = $graphAppId; resourceAccess = @($roles | ForEach-Object { @{ id = $_.id; type = 'Role' } }) })
  } | ConvertTo-Json -Depth 10
  $app = Invoke-MgGraphRequest POST 'v1.0/applications' -Body $body -ContentType 'application/json'
  Write-Host "Created app registration $AppName"
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
  'github-production'   = "repo:$GitHubOwner/${GitHubRepo}:environment:production"
  'github-pull-request' = "repo:$GitHubOwner/${GitHubRepo}:pull_request"
}
$credentials = @((Invoke-MgGraphRequest GET "v1.0/applications/$($app.id)/federatedIdentityCredentials").value)
foreach ($name in $subjects.Keys) {
  if (-not ($credentials | Where-Object { $_.name -eq $name })) {
    $credential = @{ name = $name; issuer = 'https://token.actions.githubusercontent.com'; subject = $subjects[$name]; audiences = @('api://AzureADTokenExchange') } | ConvertTo-Json
    Invoke-MgGraphRequest POST "v1.0/applications/$($app.id)/federatedIdentityCredentials" -Body $credential -ContentType 'application/json' | Out-Null
    Write-Host "Trusted $($subjects[$name])"
  }
}

Write-Host '== Azure role ==' -ForegroundColor Cyan
$scope = "/subscriptions/$subId/resourceGroups/$ResourceGroup"
$existingRole = az role assignment list --assignee $sp.id --scope $scope --role Contributor --query "[0].id" -o tsv
if (-not $existingRole) {
  Start-Sleep 20  # allow the new identity to replicate before assigning a role
  az role assignment create --assignee-object-id $sp.id --assignee-principal-type ServicePrincipal --role Contributor --scope $scope --only-show-errors | Out-Null
}
Write-Host "Contributor on $ResourceGroup only"

Write-Host '== GitHub ==' -ForegroundColor Cyan
$repoRef = "$GitHubOwner/$GitHubRepo"
$variables = [ordered]@{ AZURE_CLIENT_ID = $app.appId; AZURE_TENANT_ID = $tenantId; AZURE_SUBSCRIPTION_ID = $subId; AZURE_RESOURCE_GROUP = $ResourceGroup }
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
Write-Host 'Remaining manual setting: in the repo, Settings > Environments > production, add yourself as a required reviewer.'
