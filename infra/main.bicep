// Foundation: the audit trail every other component writes to.
targetScope = 'resourceGroup'

param location string = resourceGroup().location
@description('Firm prefix from config/profiles/<firm>.yaml, passed in by the pipeline.')
@minLength(2)
@maxLength(9)
param prefix string

var tags = {
  managedBy: 'github-actions'
  domain: 'technology'
}

// Platform logs and diagnostics
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Agent action log: one row per agent action, written by the harness
resource agentLog 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'st${prefix}${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource tableService 'Microsoft.Storage/storageAccounts/tableServices@2023-05-01' = {
  parent: agentLog
  name: 'default'
}

resource actionTable 'Microsoft.Storage/storageAccounts/tableServices/tables@2023-05-01' = {
  parent: tableService
  name: 'agentactions'
}

output logWorkspaceName string = logs.name
output agentLogAccountName string = agentLog.name
