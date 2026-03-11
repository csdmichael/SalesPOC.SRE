@description('Name of the SRE agent')
param agentName string = 'sre-ai-my'

@description('Azure region for deployment')
param location string = 'eastus2'

@description('Container image to deploy')
param containerImage string

@description('Application Insights connection string')
@secure()
param appInsightsConnectionString string = ''

@description('Application Insights resource ID')
param appInsightsResourceId string = '/subscriptions/${subscription().subscriptionId}/resourceGroups/${resourceGroup().name}/providers/Microsoft.Insights/components/sre-poc-ai-my-b8bc7f81-ab86-app-insights'

@description('Grafana URL for dashboard')
param grafanaUrl string = 'https://grafana-20251216100414-dud6eccwdyh7b3an.wus.grafana.azure.com'

@description('Azure Monitor Workspace metrics ingestion endpoint')
param metricsIngestionEndpoint string = 'https://defaultazuremonitorworkspace-wus-jfog.westus-1.metrics.ingest.monitor.azure.com/dataCollectionRules/dcr-1ab9a75fbec94d5d9f25b09cf0e224f0/streams/Microsoft-PrometheusMetrics/api/v1/write?api-version=2023-04-24'

@description('Azure Monitor Workspace query endpoint')
param metricsQueryEndpoint string = 'https://defaultazuremonitorworkspace-wus-dwdtc7bqb9gzc4ft.westus.prometheus.monitor.azure.com'

@description('Deploy role assignments (requires Owner/User Access Admin on the RG). Set to false when the deploying principal lacks roleAssignments/write.')
param deployRoleAssignments bool = false

@description('Managed resources — each entry has a provider and path used to build full resource IDs. Populated from config.py via PATCH post-deploy; defaults here ensure valid initial deployment.')
param managedResources array = [
  { provider: 'Microsoft.ApiManagement', path: 'service/apim-poc-my' }
  { provider: 'Microsoft.Web', path: 'sites/SalesPOC-API' }
  { provider: 'Microsoft.Sql', path: 'servers/ai-db-poc/databases/ai-db-poc' }
  { provider: 'Microsoft.DocumentDB', path: 'databaseAccounts/cosmos-ai-poc' }
  { provider: 'Microsoft.Storage', path: 'storageAccounts/aistoragemyaacoub' }
  { provider: 'Microsoft.Web', path: 'sites/SalesPOC' }
  { provider: 'Microsoft.Web', path: 'serverfarms/ASP-aimyaacoub-87dc' }
  { provider: 'Microsoft.CognitiveServices', path: 'accounts/001-ai-poc' }
]

// --- Built-in Role Definition IDs ---
var contributorRoleId = 'b24988ac-6180-42a0-ab88-20f7382dd24c'
var monitoringContributorRoleId = '749f88d5-cbae-40b8-bcfc-e573ddc772fa'

// --- Managed Resource IDs (built from managedResources param) ---
var rgId = resourceGroup().id
var subId = '/subscriptions/${subscription().subscriptionId}'
var resourceSpecificIds = [for r in managedResources: '${rgId}/providers/${r.provider}/${r.path}']
var managedResourceIds = concat([subId, rgId], resourceSpecificIds)

// --- Log Analytics Workspace ---
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${agentName}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// --- Container Apps Environment ---
resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${agentName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// --- User-Assigned Managed Identity ---
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${agentName}-identity'
  location: location
}

// --- SRE Agent (Microsoft.App/agents) ---
resource sreAgent 'Microsoft.App/agents@2025-05-01-preview' = {
  name: agentName
  location: location
  identity: {
    type: 'SystemAssigned, UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  tags: {
    'hidden-link: /app-insights-resource-id': appInsightsResourceId
  }
  properties: {
    actionConfiguration: {
      accessLevel: 'High'
      identity: managedIdentity.id
      mode: 'review'
    }
    defaultModel: {
      name: 'Automatic'
      provider: 'Anthropic'
    }
    experimentalSettings: {
      EnableHttpTriggers: true
      EnableWorkspaceTools: true
    }
    incidentManagementConfiguration: {
      connectionName: 'azmonitor'
      type: 'AzMonitor'
    }
    knowledgeGraphConfiguration: {
      identity: managedIdentity.id
      managedResources: managedResourceIds
    }
    logConfiguration: {
      applicationInsightsConfiguration: {
        applicationInsightsResourceId: appInsightsResourceId
      }
    }
    dashboardConfiguration: {
      azureMonitorWorkspaceMetricsIngestionEndpoint: metricsIngestionEndpoint
      azureMonitorWorkspaceQueryEndpoint: metricsQueryEndpoint
      grafanaUrl: grafanaUrl
      identity: managedIdentity.id
    }
    monthlyAgentUnitLimit: 50000
    upgradeChannel: 'Stable'
  }
}

// --- Role Assignments (skipped when deployRoleAssignments is false) ---
resource rgContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (deployRoleAssignments) {
  name: guid(resourceGroup().id, managedIdentity.id, contributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', contributorRoleId)
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource rgMonitoringContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (deployRoleAssignments) {
  name: guid(resourceGroup().id, managedIdentity.id, monitoringContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', monitoringContributorRoleId)
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// --- Container App ---
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${agentName}-app'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
      }
    }
    template: {
      containers: [
        {
          name: agentName
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'AGENT_NAME'
              value: agentName
            }
            {
              name: 'AZURE_REGION'
              value: location
            }
            {
              name: 'AZURE_MANAGED_IDENTITY'
              value: managedIdentity.properties.clientId
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsightsConnectionString
            }
            {
              name: 'GITHUB_ORG'
              value: 'csdmichael'
            }
            {
              name: 'AZURE_SUBSCRIPTION_ID'
              value: subscription().subscriptionId
            }
            {
              name: 'AZURE_RESOURCE_GROUP'
              value: resourceGroup().name
            }
          ]
          probes: [
            {
              type: 'Startup'
              httpGet: {
                path: '/healthz'
                port: 8080
              }
              initialDelaySeconds: 2
              periodSeconds: 3
              failureThreshold: 10
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/healthz'
                port: 8080
              }
              periodSeconds: 30
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

output sreAgentEndpoint string = sreAgent.properties.agentEndpoint
output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output managedIdentityClientId string = managedIdentity.properties.clientId
output managedIdentityPrincipalId string = managedIdentity.properties.principalId
