// ──────────────────────────────────────────────────────────
//  Subscription-level role assignments for SRE Agent
//  Deploys Contributor + Monitoring Contributor at subscription scope
//  Usage: az deployment sub create --location eastus2 --template-file infra/sub-roles.bicep --parameters principalId=<managed-identity-principal-id>
// ──────────────────────────────────────────────────────────

targetScope = 'subscription'

@description('Principal ID of the SRE agent managed identity')
param principalId string

var contributorRoleId = 'b24988ac-6180-42a0-ab88-20f7382dd24c'
var monitoringContributorRoleId = '749f88d5-cbae-40b8-bcfc-e573ddc772fa'

resource subContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(subscription().id, principalId, contributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', contributorRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

resource subMonitoringContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(subscription().id, principalId, monitoringContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', monitoringContributorRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
