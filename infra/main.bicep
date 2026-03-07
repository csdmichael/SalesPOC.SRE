@description('Name of the SRE agent')
param agentName string = 'sre-poc-ai-my'

@description('Azure region for deployment')
param location string = 'eastus2'

@description('Container image to deploy')
param containerImage string

@description('Application Insights connection string')
@secure()
param appInsightsConnectionString string = ''

@description('GitHub personal access token for repo connectors')
@secure()
param githubToken string = ''

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

// --- Container App ---
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: agentName
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
      secrets: [
        {
          name: 'github-token'
          value: githubToken
        }
      ]
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
              name: 'GITHUB_TOKEN'
              secretRef: 'github-token'
            }
            {
              name: 'GITHUB_ORG'
              value: 'csdmichael'
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

output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output managedIdentityClientId string = managedIdentity.properties.clientId
output managedIdentityPrincipalId string = managedIdentity.properties.principalId
