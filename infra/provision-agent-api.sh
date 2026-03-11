#!/usr/bin/env bash
# Provisions scheduled tasks and incident response plans on the SRE Agent API.
# Requires: az CLI authenticated, jq
# Usage: ./infra/provision-agent-api.sh <agent-endpoint>
# Example: ./infra/provision-agent-api.sh https://sre-ai-my--0cad75dc.4650bed8.eastus2.azuresre.ai

set -euo pipefail

AGENT_ENDPOINT="${1:?Usage: $0 <agent-endpoint>}"

if [[ ! "$AGENT_ENDPOINT" =~ ^https:// ]]; then
  echo "Error: AGENT_ENDPOINT must start with https:// (got: '$AGENT_ENDPOINT')" >&2
  exit 1
fi

TOKEN=$(az account get-access-token --resource "https://azuresre.ai" --query "accessToken" -o tsv)
if [ -z "$TOKEN" ]; then
  echo "Error: Failed to obtain token for https://azuresre.ai" >&2
  exit 1
fi

api() {
  local method=$1 path=$2
  shift 2
  curl -sfS -X "$method" \
    "${AGENT_ENDPOINT}/api/v1${path}" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    "$@"
}

# ──────────────────────────────────────────────────────────
#  Scheduled Tasks
# ──────────────────────────────────────────────────────────
echo "=== Provisioning Scheduled Tasks ==="

existing_tasks=$(api GET /scheduledtasks | jq -r '.[].name // empty' 2>/dev/null || echo "")

create_task() {
  local name=$1 cron=$2 description=$3 prompt=$4
  if echo "$existing_tasks" | grep -qF "$name"; then
    echo "  [skip] $name (already exists)"
    return
  fi
  local body
  body=$(jq -n --arg n "$name" --arg c "$cron" --arg d "$description" --arg p "$prompt" \
    '{Name:$n, CronExpression:$c, Description:$d, AgentPrompt:$p}')
  api POST /scheduledtasks -d "$body" >/dev/null
  echo "  [created] $name"
}

create_task "Health Check All Resources" "*/5 * * * *" \
  "Full health check of all monitored Azure resources including SQL DB, Cosmos DB, Storage, API, APIM, AI Foundry, and Frontend" \
  "Perform a comprehensive health check on all monitored Azure resources in the ai-myaacoub resource group. Check CPU, memory, response times, error rates, and availability for SQL Database (ai-db-poc), Cosmos DB (cosmos-ai-poc), Storage (aistoragemyaacoub), API (SalesPOC-API), APIM (apim-poc-my), AI Foundry (001-ai-poc), and Frontend (SalesPOC). Report any degraded or unhealthy resources with severity levels."

create_task "Subagent Analysis" "*/15 * * * *" \
  "Run all 6 specialized subagent analyses: Database (SQL DB + Cosmos DB), API Gateway (API + APIM), AI Services (AI Foundry), Frontend (App Service + Storage), Security (all resources + GitHub), and Cost (utilization + right-sizing)" \
  "Run a comprehensive analysis using all specialized subagents. Database subagent: check SQL DTU usage, deadlocks, connection failures, and Cosmos DB RU consumption, throttling, replication lag. API Gateway subagent: check API response times, 5xx error rates, APIM capacity and backend duration. AI Services subagent: check AI Foundry error rates, latency, token usage. Frontend subagent: check App Service HTTP errors, response times, Storage availability. Security subagent: check for unauthorized access spikes, connection abuse, scanning patterns across all resources. Cost subagent: identify under-utilized resources and right-sizing opportunities."

create_task "Security Scan" "*/15 * * * *" \
  "Security-focused analysis across all monitored resources and GitHub repositories. Detects unauthorized access spikes, connection abuse patterns, and potential scanning activity." \
  "Perform a security-focused scan across all resources in the ai-myaacoub resource group. Check APIM for unauthorized request spikes (>50 in 5 min), SQL DB for elevated connection failures that may indicate brute force attempts, API for high 4xx rates that suggest scanning/enumeration, and GitHub repositories for access anomalies. Report any security concerns with severity levels and recommended mitigations."

create_task "GitHub Repository Check" "0 * * * *" \
  "Verify connectivity and status of all 8 connected GitHub repositories: SalesPOC.UI, SalesPOC.API, SalesPOC.MCP, SalesPOC.APIM, SalesPOC.APIC, SalesPOC.DB, SalesPOC.AI, SalesPOC.Containerized.API" \
  "Check the status and connectivity of all 8 GitHub repositories under the csdmichael organization: SalesPOC.UI (Frontend), SalesPOC.API (API), SalesPOC.MCP (MCP Server), SalesPOC.APIM (API Management), SalesPOC.APIC (API Center), SalesPOC.DB (Database), SalesPOC.AI (AI), SalesPOC.Containerized.API (ACA). Verify each repo is accessible, check for recent commits, open pull requests, and any failed CI/CD workflow runs. Report any connectivity issues or stale repositories."

create_task "Cost Analysis" "0 */6 * * *" \
  "Cost optimization analysis across all monitored Azure resources. Identifies under-utilized resources and provides right-sizing recommendations." \
  "Perform a cost optimization analysis across all resources in the ai-myaacoub resource group. Check for under-utilized resources: SQL DB with CPU <10%, Cosmos DB with low RU usage (<100 RU/s), API App Service with low memory working set (<50MB), and AI Foundry token consumption patterns. Provide specific right-sizing recommendations: consider downgrading SQL service tier, reducing Cosmos DB provisioned RUs or switching to serverless, scaling down App Service plan. Calculate estimated monthly savings for each recommendation."

create_task "Daily SRE Report" "0 8 * * *" \
  "Comprehensive daily SRE summary report covering all monitored resources, incidents, SLA compliance, and operational recommendations." \
  "Generate a comprehensive daily SRE report for the Sales POC infrastructure in the ai-myaacoub resource group. Include: 1) Executive summary of overall system health. 2) Resource-by-resource status for SQL DB (ai-db-poc), Cosmos DB (cosmos-ai-poc), Storage (aistoragemyaacoub), API (SalesPOC-API), APIM (apim-poc-my), AI Foundry (001-ai-poc), Frontend (SalesPOC). 3) SLA compliance against targets: SQL 99.99%, Cosmos 99.999%, Storage 99.9%, API 99.95%, APIM 99.95%, AI Foundry 99.9%, Frontend 99.95%. 4) Incident summary: total incidents, severity breakdown, MTTR. 5) Key metrics trends over the past 24 hours. 6) Cost optimization opportunities. 7) Security observations. 8) Actionable recommendations for the operations team."

echo ""

# ──────────────────────────────────────────────────────────
#  Incident Response Plans (Handlers + Filters)
# ──────────────────────────────────────────────────────────
echo "=== Provisioning Incident Response Plans ==="

existing_handlers=$(api GET /incidentplayground/handlers | jq -r '.[].id // empty' 2>/dev/null || echo "")

create_handler() {
  local id=$1 name=$2 description=$3 prompt=$4
  shift 4
  local priorities=("$@")

  if echo "$existing_handlers" | grep -qF "$id"; then
    echo "  [skip] $name (already exists)"
    return
  fi

  # Create incident filter
  local prio_json
  prio_json=$(printf '%s\n' "${priorities[@]}" | jq -R . | jq -s .)
  local filter_body
  filter_body=$(jq -n --arg i "$id" --arg n "$name Filter" --argjson p "$prio_json" \
    '{id:$i, name:$n, priorities:$p, incidentType:"", handlingAgent:"", agentMode:"autonomous", deepInvestigationEnabled:false}')
  api PUT "/incidentplayground/filters/$id" -d "$filter_body" >/dev/null 2>&1 || true

  # Create incident handler
  local handler_body
  handler_body=$(jq -n --arg i "$id" --arg n "$name" --arg d "$description" --arg g "$prompt" \
    '{id:$i, name:$n, description:$d, incidentFilterId:$i, incidentProcessingGuide:[$g], tools:[], incidents:[], customInstructions:""}')
  api PUT "/incidentplayground/handlers/$id" -d "$handler_body" >/dev/null
  echo "  [created] $name"
}

# SQL Database
create_handler "sql-high-cpu" "SQL High CPU" \
  "SQL Database CPU consumption critically high (cpu_percent > 90%)" \
  "INCIDENT: SQL Database High CPU. Severity: SEV2. Trigger: cpu_percent > 90%.
RUNBOOK:
1. Identify top CPU queries: Run sys.dm_exec_query_stats to find top CPU consumers
   Command: az sql db show --name ai-db-poc --server ai-db-poc --resource-group ai-myaacoub --query '{sku:currentSku,status:status}'
2. Check long-running queries: Identify and optionally kill long-running transactions
3. Scale up compute: Temporarily scale to a higher vCore tier if load is legitimate
   Command: az sql db update --name ai-db-poc --server ai-db-poc --resource-group ai-myaacoub --service-objective S3
4. Notify team: Alert backend team to investigate query patterns
Auto-remediate: Yes" \
  Sev2

create_handler "sql-connection-failures" "SQL Connection Failures" \
  "SQL Database experiencing connection failures (connection_failed > 20 in 5min)" \
  "INCIDENT: SQL Connection Failures. Severity: SEV1 (Critical). Trigger: connection_failed > 20 in 5min.
RUNBOOK:
1. Check firewall rules: Verify IP allowlists and VNet rules
2. Check server status: Verify SQL server is responding
   Command: az sql server show --name ai-db-poc --resource-group ai-myaacoub --query '{state:state,fullyQualifiedDomainName:fullyQualifiedDomainName}'
3. Check connection pool: Review API connection pool settings and active connections
4. Restart API service: Restart the API App Service to reset connection pools" \
  Sev0 Sev1

create_handler "sql-deadlocks" "SQL Deadlocks" \
  "SQL Database deadlocks detected (deadlock > 5 in 5min)" \
  "INCIDENT: SQL Deadlocks. Severity: SEV2. Trigger: deadlock > 5 in 5min.
RUNBOOK:
1. Capture deadlock graph: Enable extended events to capture deadlock XML
2. Identify conflicting transactions: Analyze lock ordering in application code
3. Apply index tuning: Check missing indexes that may reduce lock contention" \
  Sev2

create_handler "sql-storage-critical" "SQL Storage Critical" \
  "SQL Database running out of storage (storage_percent > 90%)" \
  "INCIDENT: SQL Storage Critical. Severity: SEV2. Trigger: storage_percent > 90%.
RUNBOOK:
1. Identify large tables: Query sys.dm_db_partition_stats for table sizes
2. Archive old data: Move historical records to cold storage
3. Scale storage: Increase max database size
   Command: az sql db update --name ai-db-poc --server ai-db-poc --resource-group ai-myaacoub --max-size 250GB" \
  Sev2

# Cosmos DB
create_handler "cosmos-db-throttling" "Cosmos DB Throttling" \
  "Cosmos DB request throttling - 429s (Http429 > 50 in 5min)" \
  "INCIDENT: Cosmos DB Throttling (429s). Severity: SEV2. Trigger: Http429 > 50 in 5min.
RUNBOOK:
1. Check RU consumption: Review partition-level RU usage
   Command: az cosmosdb show --name cosmos-ai-poc --resource-group ai-myaacoub --query '{enableAutomaticFailover:enableAutomaticFailover,provisioningState:provisioningState}'
2. Identify hot partitions: Analyze partition key distribution
3. Scale RU throughput: Increase provisioned or autoscale max RUs
   Command: az cosmosdb sql container throughput update --account-name cosmos-ai-poc --database-name salespoc --name orders --resource-group ai-myaacoub --throughput 1000
4. Review query patterns: Optimize cross-partition queries
Auto-remediate: Yes" \
  Sev2

create_handler "cosmos-db-replication-lag" "Cosmos DB Replication Lag" \
  "Cosmos DB geo-replication lag is high (ReplicationLatency > 500ms)" \
  "INCIDENT: Cosmos DB Replication Lag. Severity: SEV2. Trigger: ReplicationLatency > 500ms.
RUNBOOK:
1. Check region status: Verify all configured regions are online
2. Review consistency level: Check if strong consistency is causing bottleneck
3. Check write volume: Unusually high write volume can increase replication lag" \
  Sev2

# Storage
create_handler "storage-availability-drop" "Storage Availability Drop" \
  "Storage account availability below SLA (Availability < 99.0%)" \
  "INCIDENT: Storage Availability Drop. Severity: SEV1 (Critical). Trigger: Availability < 99.0%.
RUNBOOK:
1. Check Azure status: Verify if there is a regional Azure outage
2. Check storage account health: Review storage account diagnostics
   Command: az storage account show --name aistoragemyaacoub --resource-group ai-myaacoub --query '{provisioningState:provisioningState,statusOfPrimary:statusOfPrimary}'
3. Initiate failover: Trigger account failover to secondary if GRS configured
4. Verify blob containers: Check container-level access and lease status" \
  Sev0 Sev1

create_handler "storage-high-latency" "Storage High Latency" \
  "Storage account experiencing high latency (SuccessE2ELatency > 500ms)" \
  "INCIDENT: Storage High Latency. Severity: SEV3. Trigger: SuccessE2ELatency > 500ms.
RUNBOOK:
1. Check throttling: Review if storage account is being throttled
2. Analyze request patterns: Look for large sequential reads that should be parallelized
3. Consider CDN: Enable Azure CDN for frequently accessed blobs" \
  Sev3

# API (App Service)
create_handler "api-5xx-spike" "API 5xx Spike" \
  "API returning high rate of server errors (Http5xx > 20 in 5min)" \
  "INCIDENT: API 5xx Spike. Severity: SEV1 (Critical). Trigger: Http5xx > 20 in 5min.
RUNBOOK:
1. Check App Insights: Review exception telemetry for root cause
   Command: az webapp log tail --name SalesPOC-API --resource-group ai-myaacoub
2. Check dependencies: Verify SQL DB, Cosmos DB, and Storage connectivity
3. Restart API: Restart the App Service
   Command: az webapp restart --name SalesPOC-API --resource-group ai-myaacoub
4. Scale out: Add instances if load is too high
   Command: az appservice plan update --name ASP-aimyaacoub-87dc --resource-group ai-myaacoub --number-of-workers 3
Auto-remediate: Yes" \
  Sev0 Sev1

create_handler "api-high-response-time" "API High Response Time" \
  "API response times critically slow (HttpResponseTime > 3s)" \
  "INCIDENT: API High Response Time. Severity: SEV2. Trigger: HttpResponseTime > 3s.
RUNBOOK:
1. Profile slow endpoints: Use App Insights to identify slowest routes
2. Check downstream latency: Verify SQL and Cosmos response times
3. Scale up/out: Increase App Service plan tier or instance count
4. Review connection pooling: Check for connection exhaustion" \
  Sev2

create_handler "api-resource-exhaustion" "API Resource Exhaustion" \
  "API server resource exhaustion (CpuPercentage > 90% OR MemoryPercentage > 90%)" \
  "INCIDENT: API Resource Exhaustion. Severity: SEV2. Trigger: CpuPercentage > 90% OR MemoryPercentage > 90%.
RUNBOOK:
1. Identify resource hog: Check per-instance CPU/memory profiles
2. Scale out: Add more instances
   Command: az appservice plan update --name ASP-aimyaacoub-87dc --resource-group ai-myaacoub --number-of-workers 4
3. Scale up: Move to higher App Service plan tier
4. Check for memory leaks: Review App Insights memory trends over 24h
Auto-remediate: Yes" \
  Sev2

# APIM
create_handler "apim-capacity-high" "APIM Capacity High" \
  "API Management gateway capacity near limit (Capacity > 90%)" \
  "INCIDENT: APIM Capacity High. Severity: SEV2. Trigger: Capacity > 90%.
RUNBOOK:
1. Check request volume: Review traffic patterns for unexpected spikes
2. Scale APIM units: Add capacity units to APIM instance
   Command: az apim update --name apim-poc-my --resource-group ai-myaacoub --sku-capacity 2
3. Enable rate limiting: Apply or tighten rate-limit policies
4. Review caching: Ensure response caching is configured for eligible APIs" \
  Sev2

create_handler "apim-backend-slow" "APIM Backend Slow" \
  "APIM backend response times critically slow (BackendDuration > 5000ms)" \
  "INCIDENT: APIM Backend Slow. Severity: SEV2. Trigger: BackendDuration > 5000ms.
RUNBOOK:
1. Identify slow backend: Check per-API backend duration in diagnostics
2. Check API health: Verify backend App Service is healthy
3. Check circuit breaker: Review APIM retry/timeout policies
4. Enable response caching: Cache responses for read-heavy endpoints" \
  Sev2

create_handler "apim-unauthorized-spike" "APIM Unauthorized Request Spike" \
  "Spike in unauthorized API requests - potential security concern (UnauthorizedRequests > 100 in 5min)" \
  "INCIDENT: APIM Unauthorized Request Spike. Severity: SEV2. Trigger: UnauthorizedRequests > 100 in 5min.
RUNBOOK:
1. Analyze request origins: Check source IPs for patterns
2. Review subscription keys: Verify no keys were revoked or expired
3. Enable IP filtering: Block suspicious IPs via APIM policy
4. Rotate credentials: Rotate subscription keys if compromise suspected" \
  Sev2

# AI Foundry
create_handler "ai-foundry-high-error-rate" "AI Foundry High Error Rate" \
  "AI Foundry model error rate elevated (TotalErrors > 20 in 5min)" \
  "INCIDENT: AI Foundry High Error Rate. Severity: SEV2. Trigger: TotalErrors > 20 in 5min.
RUNBOOK:
1. Check model deployment: Verify model endpoint is healthy
   Command: az cognitiveservices account show --name 001-ai-poc --resource-group ai-myaacoub --query '{provisioningState:properties.provisioningState}'
2. Review error types: Categorize errors (rate limit, model errors, input validation)
3. Check quota: Verify TPM/RPM limits haven't been exceeded
4. Fallback model: Switch to fallback model deployment if primary fails" \
  Sev2

create_handler "ai-foundry-high-latency" "AI Foundry High Latency" \
  "AI Foundry inference latency is high (Latency > 5000ms)" \
  "INCIDENT: AI Foundry High Latency. Severity: SEV3. Trigger: Latency > 5000ms.
RUNBOOK:
1. Check prompt sizes: Review if input token counts have increased
2. Check regional load: Verify Azure region is not experiencing congestion
3. Reduce max_tokens: Lower max output tokens to reduce generation time
4. Add retry with backoff: Implement exponential backoff for retries" \
  Sev3

# Frontend
create_handler "frontend-http-errors" "Frontend HTTP Errors" \
  "Frontend App Service HTTP 5xx errors elevated (Http5xx > 20 in 5min)" \
  "INCIDENT: Frontend HTTP Errors. Severity: SEV2. Trigger: Http5xx > 20 in 5min.
RUNBOOK:
1. Check application logs: Review App Service application logs
2. Check linked API: Verify APIM and backend API connectivity
3. Restart frontend: Restart the App Service
   Command: az webapp restart --name SalesPOC --resource-group ai-myaacoub
4. Check deployments: Review recent deployments for regressions" \
  Sev2

echo ""

# ──────────────────────────────────────────────────────────
#  GitHub Repositories
# ──────────────────────────────────────────────────────────
echo "=== Provisioning GitHub Repositories ==="

repo_api() {
  local method=$1 path=$2
  shift 2
  curl -sfS -X "$method" \
    "${AGENT_ENDPOINT}/api/v2${path}" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    "$@"
}

create_repo() {
  local name=$1 url=$2 description=$3
  local body
  body=$(jq -n --arg n "$name" --arg u "$url" --arg d "$description" \
    '{name:$n, type:"CodeRepo", properties:{url:$u, type:"github", description:$d}}')
  # PUT is idempotent — safe to call if repo already exists
  repo_api PUT "/repos/$name" -d "$body" >/dev/null
  echo "  [ok] $name"
}

create_repo "Sales POC - UI"      "https://github.com/csdmichael/SalesPOC.UI"               "Frontend Angular application"
create_repo "Sales POC - API"     "https://github.com/csdmichael/SalesPOC.API"              "Backend .NET API"
create_repo "Sales POC - MCP"     "https://github.com/csdmichael/SalesPOC.MCP"              "Model Context Protocol server"
create_repo "Sales POC - APIM"    "https://github.com/csdmichael/SalesPOC.APIM"             "API Management configuration"
create_repo "Sales POC - DB"      "https://github.com/csdmichael/SalesPOC.DB"               "Database migrations and scripts"
create_repo "Sales POC - AI Foundry" "https://github.com/csdmichael/SalesPOC.AI"            "AI Foundry configuration"
create_repo "Sales POC - ACA"     "https://github.com/csdmichael/SalesPOC.Containerized.API" "Containerized API (Azure Container Apps)"

echo ""
echo "=== Summary ==="
task_count=$(api GET /scheduledtasks | jq 'length')
handler_count=$(api GET /incidentplayground/handlers | jq 'length')
echo "Scheduled tasks: $task_count"
echo "Incident response plans: $handler_count"
repo_count=$(repo_api GET /repos 2>/dev/null | jq '.repos | length' 2>/dev/null || echo "?")
echo "GitHub repos: $repo_count"
