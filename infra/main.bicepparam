using './main.bicep'

param agentName = 'sre-ai-my'
param location = 'eastus2'
param containerImage = 'ghcr.io/${readEnvironmentVariable('GITHUB_REPOSITORY', 'local/sre-ai-my')}:latest'

param appInsightsResourceId = '/subscriptions/86b37969-9445-49cf-b03f-d8866235171c/resourceGroups/ai-myaacoub/providers/Microsoft.Insights/components/sre-poc-ai-my-b8bc7f81-ab86-app-insights'
param grafanaUrl = 'https://grafana-20251216100414-dud6eccwdyh7b3an.wus.grafana.azure.com'
param metricsIngestionEndpoint = 'https://defaultazuremonitorworkspace-wus-jfog.westus-1.metrics.ingest.monitor.azure.com/dataCollectionRules/dcr-1ab9a75fbec94d5d9f25b09cf0e224f0/streams/Microsoft-PrometheusMetrics/api/v1/write?api-version=2023-04-24'
param metricsQueryEndpoint = 'https://defaultazuremonitorworkspace-wus-dwdtc7bqb9gzc4ft.westus.prometheus.monitor.azure.com'

param managedResources = [
  { provider: 'Microsoft.ApiManagement', path: 'service/apim-poc-my' }
  { provider: 'Microsoft.Web', path: 'sites/SalesPOC-API' }
  { provider: 'Microsoft.Sql', path: 'servers/ai-db-poc/databases/ai-db-poc' }
  { provider: 'Microsoft.DocumentDB', path: 'databaseAccounts/cosmos-ai-poc' }
  { provider: 'Microsoft.Storage', path: 'storageAccounts/aistoragemyaacoub' }
  { provider: 'Microsoft.Web', path: 'sites/SalesPOC' }
  { provider: 'Microsoft.Web', path: 'serverfarms/ASP-aimyaacoub-87dc' }
  { provider: 'Microsoft.CognitiveServices', path: 'accounts/001-ai-poc' }
]
