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
  "Check health of all monitored Azure resources every 5 minutes" \
  "Perform a comprehensive health check on all monitored Azure resources: SQL Database (ai-db-poc), Cosmos DB (cosmos-ai-poc), Storage Account (aistoragemyaacoub), API App Service (SalesPOC-API), APIM (apim-poc-my), AI Foundry (001-ai-poc), Frontend (SalesPOC). Check CPU, memory, availability, error rates, and connection health. Report any anomalies."

create_task "Subagent Analysis" "*/15 * * * *" \
  "Run subagent health analysis every 15 minutes" \
  "Execute analysis across all subagent domains: Database (SQL + Cosmos performance), API Gateway (APIM metrics), AI Services (Foundry response times and errors), Frontend (HTTP errors, latency), Security (unauthorized requests, certificate expiry), Cost (spending trends, budget alerts). Summarize findings and flag issues."

create_task "Security Scan" "*/15 * * * *" \
  "Scan for security anomalies every 15 minutes" \
  "Scan all monitored resources for security issues: check APIM for unauthorized request spikes, review SQL firewall rules, verify storage account access policies, check for exposed secrets or misconfigured RBAC, review network security group rules. Alert on any anomalies."

create_task "GitHub Repository Check" "0 * * * *" \
  "Check GitHub repositories for issues every hour" \
  "Check all monitored GitHub repositories (SalesPOC.UI, SalesPOC.API, SalesPOC.MCP, SalesPOC.APIM, SalesPOC.APIC, SalesPOC.DB, SalesPOC.AI) for: open pull requests needing review, failing CI/CD pipelines, open issues with high priority, recent commits affecting monitored resources, dependency security alerts."

create_task "Cost Analysis" "0 */6 * * *" \
  "Analyze Azure spending every 6 hours" \
  "Analyze Azure resource costs for resource group ai-myaacoub: review current spending vs budget, identify cost anomalies or unexpected spikes, check for idle or underutilized resources, recommend optimization opportunities, project month-end spend."

create_task "Daily SRE Report" "0 8 * * *" \
  "Generate daily SRE report at 8 AM UTC" \
  "Generate a comprehensive daily SRE report covering the last 24 hours: resource health summary, incident summary (created, resolved, open), key metrics (availability, error rates, latency p95), top alerts fired, GitHub activity summary, cost trend, and recommended actions for the day."

echo ""

# ──────────────────────────────────────────────────────────
#  Incident Response Plans (HTTP Triggers)
# ──────────────────────────────────────────────────────────
echo "=== Provisioning Incident Response Plans ==="

existing_triggers=$(api GET /httptriggers | jq -r '.[].name // empty' 2>/dev/null || echo "")

create_trigger() {
  local name=$1 description=$2 prompt=$3
  if echo "$existing_triggers" | grep -qF "$name"; then
    echo "  [skip] $name (already exists)"
    return
  fi
  local body
  body=$(jq -n --arg n "$name" --arg d "$description" --arg p "$prompt" \
    '{name:$n, description:$d, agentPrompt:$p, agentMode:"autonomous"}')
  api POST /httptriggers/create -d "$body" >/dev/null
  echo "  [created] $name"
}

# SQL Database
create_trigger "SQL High CPU" \
  "SQL Database CPU consumption critically high (cpu_percent > 90%)" \
  "INCIDENT: SQL Database High CPU. Severity: SEV2. Trigger: cpu_percent > 90%.
RUNBOOK:
1. Identify top CPU queries: Run sys.dm_exec_query_stats to find top CPU consumers
   Command: az sql db show --name ai-db-poc --server ai-db-poc --resource-group ai-myaacoub --query '{sku:currentSku,status:status}'
2. Check long-running queries: Identify and optionally kill long-running transactions
3. Scale up compute: Temporarily scale to a higher vCore tier if load is legitimate
   Command: az sql db update --name ai-db-poc --server ai-db-poc --resource-group ai-myaacoub --service-objective S3
4. Notify team: Alert backend team to investigate query patterns
Auto-remediate: Yes"

create_trigger "SQL Connection Failures" \
  "SQL Database experiencing connection failures (connection_failed > 20 in 5min)" \
  "INCIDENT: SQL Connection Failures. Severity: SEV1 (Critical). Trigger: connection_failed > 20 in 5min.
RUNBOOK:
1. Check firewall rules: Verify IP allowlists and VNet rules
2. Check server status: Verify SQL server is responding
   Command: az sql server show --name ai-db-poc --resource-group ai-myaacoub --query '{state:state,fullyQualifiedDomainName:fullyQualifiedDomainName}'
3. Check connection pool: Review API connection pool settings and active connections
4. Restart API service: Restart the API App Service to reset connection pools"

create_trigger "SQL Deadlocks" \
  "SQL Database deadlocks detected (deadlock > 5 in 5min)" \
  "INCIDENT: SQL Deadlocks. Severity: SEV2. Trigger: deadlock > 5 in 5min.
RUNBOOK:
1. Capture deadlock graph: Enable extended events to capture deadlock XML
2. Identify conflicting transactions: Analyze lock ordering in application code
3. Apply index tuning: Check missing indexes that may reduce lock contention"

create_trigger "SQL Storage Critical" \
  "SQL Database running out of storage (storage_percent > 90%)" \
  "INCIDENT: SQL Storage Critical. Severity: SEV2. Trigger: storage_percent > 90%.
RUNBOOK:
1. Identify large tables: Query sys.dm_db_partition_stats for table sizes
2. Archive old data: Move historical records to cold storage
3. Scale storage: Increase max database size
   Command: az sql db update --name ai-db-poc --server ai-db-poc --resource-group ai-myaacoub --max-size 250GB"

# Cosmos DB
create_trigger "Cosmos DB Throttling" \
  "Cosmos DB request throttling - 429s (Http429 > 50 in 5min)" \
  "INCIDENT: Cosmos DB Throttling (429s). Severity: SEV2. Trigger: Http429 > 50 in 5min.
RUNBOOK:
1. Check RU consumption: Review partition-level RU usage
   Command: az cosmosdb show --name cosmos-ai-poc --resource-group ai-myaacoub --query '{enableAutomaticFailover:enableAutomaticFailover,provisioningState:provisioningState}'
2. Identify hot partitions: Analyze partition key distribution
3. Scale RU throughput: Increase provisioned or autoscale max RUs
   Command: az cosmosdb sql container throughput update --account-name cosmos-ai-poc --database-name salespoc --name orders --resource-group ai-myaacoub --throughput 1000
4. Review query patterns: Optimize cross-partition queries
Auto-remediate: Yes"

create_trigger "Cosmos DB Replication Lag" \
  "Cosmos DB geo-replication lag is high (ReplicationLatency > 500ms)" \
  "INCIDENT: Cosmos DB Replication Lag. Severity: SEV2. Trigger: ReplicationLatency > 500ms.
RUNBOOK:
1. Check region status: Verify all configured regions are online
2. Review consistency level: Check if strong consistency is causing bottleneck
3. Check write volume: Unusually high write volume can increase replication lag"

# Storage
create_trigger "Storage Availability Drop" \
  "Storage account availability below SLA (Availability < 99.0%)" \
  "INCIDENT: Storage Availability Drop. Severity: SEV1 (Critical). Trigger: Availability < 99.0%.
RUNBOOK:
1. Check Azure status: Verify if there is a regional Azure outage
2. Check storage account health: Review storage account diagnostics
   Command: az storage account show --name aistoragemyaacoub --resource-group ai-myaacoub --query '{provisioningState:provisioningState,statusOfPrimary:statusOfPrimary}'
3. Initiate failover: Trigger account failover to secondary if GRS configured
4. Verify blob containers: Check container-level access and lease status"

create_trigger "Storage High Latency" \
  "Storage account experiencing high latency (SuccessE2ELatency > 500ms)" \
  "INCIDENT: Storage High Latency. Severity: SEV3. Trigger: SuccessE2ELatency > 500ms.
RUNBOOK:
1. Check throttling: Review if storage account is being throttled
2. Analyze request patterns: Look for large sequential reads that should be parallelized
3. Consider CDN: Enable Azure CDN for frequently accessed blobs"

# API (App Service)
create_trigger "API 5xx Spike" \
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
Auto-remediate: Yes"

create_trigger "API High Response Time" \
  "API response times critically slow (HttpResponseTime > 3s)" \
  "INCIDENT: API High Response Time. Severity: SEV2. Trigger: HttpResponseTime > 3s.
RUNBOOK:
1. Profile slow endpoints: Use App Insights to identify slowest routes
2. Check downstream latency: Verify SQL and Cosmos response times
3. Scale up/out: Increase App Service plan tier or instance count
4. Review connection pooling: Check for connection exhaustion"

create_trigger "API Resource Exhaustion" \
  "API server resource exhaustion (CpuPercentage > 90% OR MemoryPercentage > 90%)" \
  "INCIDENT: API Resource Exhaustion. Severity: SEV2. Trigger: CpuPercentage > 90% OR MemoryPercentage > 90%.
RUNBOOK:
1. Identify resource hog: Check per-instance CPU/memory profiles
2. Scale out: Add more instances
   Command: az appservice plan update --name ASP-aimyaacoub-87dc --resource-group ai-myaacoub --number-of-workers 4
3. Scale up: Move to higher App Service plan tier
4. Check for memory leaks: Review App Insights memory trends over 24h
Auto-remediate: Yes"

# APIM
create_trigger "APIM Capacity High" \
  "API Management gateway capacity near limit (Capacity > 90%)" \
  "INCIDENT: APIM Capacity High. Severity: SEV2. Trigger: Capacity > 90%.
RUNBOOK:
1. Check request volume: Review traffic patterns for unexpected spikes
2. Scale APIM units: Add capacity units to APIM instance
   Command: az apim update --name apim-poc-my --resource-group ai-myaacoub --sku-capacity 2
3. Enable rate limiting: Apply or tighten rate-limit policies
4. Review caching: Ensure response caching is configured for eligible APIs"

create_trigger "APIM Backend Slow" \
  "APIM backend response times critically slow (BackendDuration > 5000ms)" \
  "INCIDENT: APIM Backend Slow. Severity: SEV2. Trigger: BackendDuration > 5000ms.
RUNBOOK:
1. Identify slow backend: Check per-API backend duration in diagnostics
2. Check API health: Verify backend App Service is healthy
3. Check circuit breaker: Review APIM retry/timeout policies
4. Enable response caching: Cache responses for read-heavy endpoints"

create_trigger "APIM Unauthorized Request Spike" \
  "Spike in unauthorized API requests - potential security concern (UnauthorizedRequests > 100 in 5min)" \
  "INCIDENT: APIM Unauthorized Request Spike. Severity: SEV2. Trigger: UnauthorizedRequests > 100 in 5min.
RUNBOOK:
1. Analyze request origins: Check source IPs for patterns
2. Review subscription keys: Verify no keys were revoked or expired
3. Enable IP filtering: Block suspicious IPs via APIM policy
4. Rotate credentials: Rotate subscription keys if compromise suspected"

# AI Foundry
create_trigger "AI Foundry High Error Rate" \
  "AI Foundry model error rate elevated (TotalErrors > 20 in 5min)" \
  "INCIDENT: AI Foundry High Error Rate. Severity: SEV2. Trigger: TotalErrors > 20 in 5min.
RUNBOOK:
1. Check model deployment: Verify model endpoint is healthy
   Command: az cognitiveservices account show --name 001-ai-poc --resource-group ai-myaacoub --query '{provisioningState:properties.provisioningState}'
2. Review error types: Categorize errors (rate limit, model errors, input validation)
3. Check quota: Verify TPM/RPM limits haven't been exceeded
4. Fallback model: Switch to fallback model deployment if primary fails"

create_trigger "AI Foundry High Latency" \
  "AI Foundry inference latency is high (Latency > 5000ms)" \
  "INCIDENT: AI Foundry High Latency. Severity: SEV3. Trigger: Latency > 5000ms.
RUNBOOK:
1. Check prompt sizes: Review if input token counts have increased
2. Check regional load: Verify Azure region is not experiencing congestion
3. Reduce max_tokens: Lower max output tokens to reduce generation time
4. Add retry with backoff: Implement exponential backoff for retries"

# Frontend
create_trigger "Frontend HTTP Errors" \
  "Frontend App Service HTTP 5xx errors elevated (Http5xx > 20 in 5min)" \
  "INCIDENT: Frontend HTTP Errors. Severity: SEV2. Trigger: Http5xx > 20 in 5min.
RUNBOOK:
1. Check application logs: Review App Service application logs
2. Check linked API: Verify APIM and backend API connectivity
3. Restart frontend: Restart the App Service
   Command: az webapp restart --name SalesPOC --resource-group ai-myaacoub
4. Check deployments: Review recent deployments for regressions"

echo ""
echo "=== Summary ==="
task_count=$(api GET /scheduledtasks | jq 'length')
trigger_count=$(api GET /httptriggers | jq 'length')
echo "Scheduled tasks: $task_count"
echo "Incident response plans: $trigger_count"
