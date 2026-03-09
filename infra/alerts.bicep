// ──────────────────────────────────────────────────────────
//  Azure Monitor Alert Rules & Action Group
//  Connects incident platform to Azure Monitor for
//  all Sales POC monitored resources.
// ──────────────────────────────────────────────────────────

@description('Webhook URL for the SRE agent (https://<fqdn>/api/alerts/webhook)')
param webhookUrl string

@description('Name of the action group')
param actionGroupName string = 'sre-ai-my-ag'

@description('SQL Server name')
param sqlServerName string = 'ai-db-poc'

@description('SQL Database name')
param sqlDatabaseName string = 'ai-db-poc'

@description('Cosmos DB account name')
param cosmosAccountName string = 'cosmos-ai-poc'

@description('Storage account name')
param storageAccountName string = 'aistoragemyaacoub'

@description('API App Service name')
param apiAppServiceName string = 'SalesPOC-API'

@description('APIM service name')
param apimServiceName string = 'apim-poc-my'

@description('AI Foundry (Cognitive Services) account name')
param aiFoundryName string = '001-ai-poc'

@description('Frontend App Service name')
param frontendAppServiceName string = 'SalesPOC'

@description('App Service Plan name')
param appServicePlanName string = 'ASP-aimyaacoub-87dc'

var rgId = resourceGroup().id

// ─── Monitored Resource IDs ─────────────────────────────
var sqlDbId = '${rgId}/providers/Microsoft.Sql/servers/${sqlServerName}/databases/${sqlDatabaseName}'
var cosmosId = '${rgId}/providers/Microsoft.DocumentDB/databaseAccounts/${cosmosAccountName}'
var storageId = '${rgId}/providers/Microsoft.Storage/storageAccounts/${storageAccountName}'
var apiId = '${rgId}/providers/Microsoft.Web/sites/${apiAppServiceName}'
var apimId = '${rgId}/providers/Microsoft.ApiManagement/service/${apimServiceName}'
var foundryId = '${rgId}/providers/Microsoft.CognitiveServices/accounts/${aiFoundryName}'
var frontendId = '${rgId}/providers/Microsoft.Web/sites/${frontendAppServiceName}'
var appServicePlanId = '${rgId}/providers/Microsoft.Web/serverfarms/${appServicePlanName}'

// ─── Action Group (routes alerts to SRE agent webhook) ──
resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: actionGroupName
  location: 'Global'
  properties: {
    groupShortName: 'SREAgent'
    enabled: true
    webhookReceivers: [
      {
        name: 'SREAgentWebhook'
        serviceUri: webhookUrl
        useCommonAlertSchema: true
      }
    ]
  }
}

// ─── Alert Rule Configurations ──────────────────────────
var alertConfigs = [
  // SQL Database
  { name: 'sre-sql-high-cpu', desc: 'SQL Database CPU > 90%', sev: 2, target: sqlDbId, metric: 'cpu_percent', op: 'GreaterThan', thresh: 90, agg: 'Average', plan: 'sql_high_cpu' }
  { name: 'sre-sql-connection-failures', desc: 'SQL connection failures > 20 in 5min', sev: 1, target: sqlDbId, metric: 'connection_failed', op: 'GreaterThan', thresh: 20, agg: 'Total', plan: 'sql_connection_failures' }
  { name: 'sre-sql-deadlocks', desc: 'SQL deadlocks > 5 in 5min', sev: 2, target: sqlDbId, metric: 'deadlock', op: 'GreaterThan', thresh: 5, agg: 'Total', plan: 'sql_deadlocks' }
  { name: 'sre-sql-storage-critical', desc: 'SQL storage > 90%', sev: 2, target: sqlDbId, metric: 'storage_percent', op: 'GreaterThan', thresh: 90, agg: 'Average', plan: 'sql_storage_critical' }

  // Cosmos DB
  { name: 'sre-cosmos-throttling', desc: 'Cosmos DB normalized RU > 90%', sev: 2, target: cosmosId, metric: 'NormalizedRUConsumption', op: 'GreaterThan', thresh: 90, agg: 'Average', plan: 'cosmos_throttling' }
  { name: 'sre-cosmos-replication-lag', desc: 'Cosmos replication latency > 500ms', sev: 2, target: cosmosId, metric: 'ReplicationLatency', op: 'GreaterThan', thresh: 500, agg: 'Average', plan: 'cosmos_replication_lag' }

  // Storage Account
  { name: 'sre-storage-availability-drop', desc: 'Storage availability < 99%', sev: 1, target: storageId, metric: 'Availability', op: 'LessThan', thresh: 99, agg: 'Average', plan: 'storage_availability_drop' }
  { name: 'sre-storage-high-latency', desc: 'Storage E2E latency > 500ms', sev: 3, target: storageId, metric: 'SuccessE2ELatency', op: 'GreaterThan', thresh: 500, agg: 'Average', plan: 'storage_high_latency' }

  // API (App Service)
  { name: 'sre-api-5xx-spike', desc: 'API 5xx errors > 5 in 1min', sev: 1, target: apiId, metric: 'Http5xx', op: 'GreaterThan', thresh: 5, agg: 'Total', plan: 'api_5xx_spike', evalFreq: 'PT1M', winSize: 'PT1M' }
  { name: 'sre-api-high-response-time', desc: 'API response time > 3s', sev: 2, target: apiId, metric: 'HttpResponseTime', op: 'GreaterThan', thresh: 3, agg: 'Average', plan: 'api_high_response_time' }
  { name: 'sre-api-cpu-exhaustion', desc: 'App Service Plan CPU > 90%', sev: 2, target: appServicePlanId, metric: 'CpuPercentage', op: 'GreaterThan', thresh: 90, agg: 'Average', plan: 'api_resource_exhaustion' }
  { name: 'sre-api-memory-exhaustion', desc: 'App Service Plan memory > 90%', sev: 2, target: appServicePlanId, metric: 'MemoryPercentage', op: 'GreaterThan', thresh: 90, agg: 'Average', plan: 'api_resource_exhaustion' }

  // API Management
  { name: 'sre-apim-capacity-high', desc: 'APIM capacity > 90%', sev: 2, target: apimId, metric: 'Capacity', op: 'GreaterThan', thresh: 90, agg: 'Average', plan: 'apim_capacity_high' }
  { name: 'sre-apim-backend-slow', desc: 'APIM backend duration > 5000ms', sev: 2, target: apimId, metric: 'BackendDuration', op: 'GreaterThan', thresh: 5000, agg: 'Average', plan: 'apim_backend_slow' }
  { name: 'sre-apim-auth-spike', desc: 'APIM unauthorized requests > 100 in 5min', sev: 2, target: apimId, metric: 'UnauthorizedRequests', op: 'GreaterThan', thresh: 100, agg: 'Total', plan: 'apim_auth_spike' }

  // AI Foundry
  { name: 'sre-foundry-high-error-rate', desc: 'AI Foundry errors > 20 in 5min', sev: 2, target: foundryId, metric: 'TotalErrors', op: 'GreaterThan', thresh: 20, agg: 'Total', plan: 'foundry_high_error_rate' }
  { name: 'sre-foundry-high-latency', desc: 'AI Foundry latency > 5000ms', sev: 3, target: foundryId, metric: 'Latency', op: 'GreaterThan', thresh: 5000, agg: 'Average', plan: 'foundry_high_latency' }

  // Frontend (App Service)
  { name: 'sre-frontend-http-errors', desc: 'Frontend HTTP 5xx errors > 20 in 5min', sev: 2, target: frontendId, metric: 'Http5xx', op: 'GreaterThan', thresh: 20, agg: 'Total', plan: 'frontend_http_errors' }
]

// ─── Metric Alert Rules ─────────────────────────────────
resource metricAlerts 'Microsoft.Insights/metricAlerts@2018-03-01' = [for config in alertConfigs: {
  name: config.name
  location: 'Global'
  properties: {
    description: config.desc
    severity: config.sev
    enabled: true
    scopes: [config.target]
    evaluationFrequency: contains(config, 'evalFreq') ? config.evalFreq : 'PT5M'
    windowSize: contains(config, 'winSize') ? config.winSize : 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'Criterion1'
          criterionType: 'StaticThresholdCriterion'
          metricName: config.metric
          operator: config.op
          threshold: config.thresh
          timeAggregation: config.agg
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
        webHookProperties: {
          planName: config.plan
        }
      }
    ]
  }
}]

output actionGroupId string = actionGroup.id
output alertRuleCount int = length(alertConfigs)
