"""Incident response plans for Sales POC Azure resources."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    SEV1 = "sev1"  # Critical - complete outage
    SEV2 = "sev2"  # Major - significant degradation
    SEV3 = "sev3"  # Minor - partial impact
    SEV4 = "sev4"  # Low - cosmetic / informational


class IncidentStatus(str, Enum):
    DETECTED = "detected"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"


@dataclass
class RunbookStep:
    order: int
    action: str
    description: str
    automated: bool = False
    command: str | None = None


@dataclass
class IncidentPlan:
    name: str
    resource_type: str
    trigger_condition: str
    severity: Severity
    description: str
    runbook: list[RunbookStep] = field(default_factory=list)
    notification_channels: list[str] = field(default_factory=lambda: ["teams", "email"])
    auto_remediate: bool = False


@dataclass
class Incident:
    id: str
    plan_name: str
    severity: Severity
    status: IncidentStatus
    description: str
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    actions_taken: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ──────────────────────────────────────────────────────────
#  Incident Response Plans per Azure Resource
# ──────────────────────────────────────────────────────────

INCIDENT_PLANS: list[IncidentPlan] = [
    # ─── SQL Database ───
    IncidentPlan(
        name="sql_high_dtu",
        resource_type="sql_db",
        trigger_condition="dtu_consumption_percent > 90%",
        severity=Severity.SEV2,
        description="SQL Database DTU consumption critically high",
        runbook=[
            RunbookStep(1, "Identify queries", "Run sys.dm_exec_query_stats to find top CPU queries", automated=True,
                        command="az sql db show --name salespoc-db --server salespoc-sql --resource-group ai-myaacoub --query '{dtu:currentServiceObjectiveName,status:status}'"),
            RunbookStep(2, "Check long-running queries", "Identify and optionally kill long-running transactions"),
            RunbookStep(3, "Scale up DTU tier", "Temporarily scale to a higher tier if load is legitimate", automated=True,
                        command="az sql db update --name salespoc-db --server salespoc-sql --resource-group ai-myaacoub --service-objective S3"),
            RunbookStep(4, "Notify team", "Alert backend team to investigate query patterns"),
        ],
        auto_remediate=True,
    ),
    IncidentPlan(
        name="sql_connection_failures",
        resource_type="sql_db",
        trigger_condition="connection_failed > 20 in 5min",
        severity=Severity.SEV1,
        description="SQL Database experiencing connection failures",
        runbook=[
            RunbookStep(1, "Check firewall rules", "Verify IP allowlists and VNet rules"),
            RunbookStep(2, "Check server status", "Verify SQL server is responding", automated=True,
                        command="az sql server show --name salespoc-sql --resource-group ai-myaacoub --query '{state:state,fullyQualifiedDomainName:fullyQualifiedDomainName}'"),
            RunbookStep(3, "Check connection pool", "Review API connection pool settings and active connections"),
            RunbookStep(4, "Restart API service", "Restart the API App Service to reset connection pools"),
        ],
    ),
    IncidentPlan(
        name="sql_deadlocks",
        resource_type="sql_db",
        trigger_condition="deadlock > 5 in 5min",
        severity=Severity.SEV2,
        description="SQL Database deadlocks detected",
        runbook=[
            RunbookStep(1, "Capture deadlock graph", "Enable extended events to capture deadlock XML"),
            RunbookStep(2, "Identify conflicting transactions", "Analyze lock ordering in application code"),
            RunbookStep(3, "Apply index tuning", "Check missing indexes that may reduce lock contention"),
        ],
    ),
    IncidentPlan(
        name="sql_storage_critical",
        resource_type="sql_db",
        trigger_condition="storage_percent > 90%",
        severity=Severity.SEV2,
        description="SQL Database running out of storage",
        runbook=[
            RunbookStep(1, "Identify large tables", "Query sys.dm_db_partition_stats for table sizes"),
            RunbookStep(2, "Archive old data", "Move historical records to cold storage"),
            RunbookStep(3, "Scale storage", "Increase max database size", automated=True,
                        command="az sql db update --name salespoc-db --server salespoc-sql --resource-group ai-myaacoub --max-size 250GB"),
        ],
    ),

    # ─── Cosmos DB ───
    IncidentPlan(
        name="cosmos_throttling",
        resource_type="cosmos_db",
        trigger_condition="Http429 > 50 in 5min",
        severity=Severity.SEV2,
        description="Cosmos DB request throttling (429s)",
        runbook=[
            RunbookStep(1, "Check RU consumption", "Review partition-level RU usage", automated=True,
                        command="az cosmosdb show --name salespoc-cosmos --resource-group ai-myaacoub --query '{enableAutomaticFailover:enableAutomaticFailover,provisioningState:provisioningState}'"),
            RunbookStep(2, "Identify hot partitions", "Analyze partition key distribution"),
            RunbookStep(3, "Scale RU throughput", "Increase provisioned or autoscale max RUs", automated=True,
                        command="az cosmosdb sql container throughput update --account-name salespoc-cosmos --database-name salespoc --name orders --resource-group ai-myaacoub --throughput 1000"),
            RunbookStep(4, "Review query patterns", "Optimize cross-partition queries"),
        ],
        auto_remediate=True,
    ),
    IncidentPlan(
        name="cosmos_replication_lag",
        resource_type="cosmos_db",
        trigger_condition="ReplicationLatency > 500ms",
        severity=Severity.SEV2,
        description="Cosmos DB geo-replication lag is high",
        runbook=[
            RunbookStep(1, "Check region status", "Verify all configured regions are online"),
            RunbookStep(2, "Review consistency level", "Check if strong consistency is causing bottleneck"),
            RunbookStep(3, "Check write volume", "Unusually high write volume can increase replication lag"),
        ],
    ),

    # ─── Storage Account ───
    IncidentPlan(
        name="storage_availability_drop",
        resource_type="storage",
        trigger_condition="Availability < 99.0%",
        severity=Severity.SEV1,
        description="Storage account availability below SLA",
        runbook=[
            RunbookStep(1, "Check Azure status", "Verify if there is a regional Azure outage"),
            RunbookStep(2, "Check storage account health", "Review storage account diagnostics", automated=True,
                        command="az storage account show --name salespocstore --resource-group ai-myaacoub --query '{provisioningState:provisioningState,statusOfPrimary:statusOfPrimary}'"),
            RunbookStep(3, "Initiate failover", "Trigger account failover to secondary if GRS configured"),
            RunbookStep(4, "Verify blob containers", "Check container-level access and lease status"),
        ],
    ),
    IncidentPlan(
        name="storage_high_latency",
        resource_type="storage",
        trigger_condition="SuccessE2ELatency > 500ms",
        severity=Severity.SEV3,
        description="Storage account experiencing high latency",
        runbook=[
            RunbookStep(1, "Check throttling", "Review if storage account is being throttled"),
            RunbookStep(2, "Analyze request patterns", "Look for large sequential reads that should be parallelized"),
            RunbookStep(3, "Consider CDN", "Enable Azure CDN for frequently accessed blobs"),
        ],
    ),

    # ─── API (App Service) ───
    IncidentPlan(
        name="api_5xx_spike",
        resource_type="api",
        trigger_condition="Http5xx > 20 in 5min",
        severity=Severity.SEV1,
        description="API returning high rate of server errors",
        runbook=[
            RunbookStep(1, "Check App Insights", "Review exception telemetry for root cause", automated=True,
                        command="az webapp log tail --name salespoc-api --resource-group ai-myaacoub"),
            RunbookStep(2, "Check dependencies", "Verify SQL DB, Cosmos DB, and Storage connectivity"),
            RunbookStep(3, "Restart API", "Restart the App Service", automated=True,
                        command="az webapp restart --name salespoc-api --resource-group ai-myaacoub"),
            RunbookStep(4, "Scale out", "Add instances if load is too high", automated=True,
                        command="az appservice plan update --name salespoc-api-plan --resource-group ai-myaacoub --number-of-workers 3"),
        ],
        auto_remediate=True,
    ),
    IncidentPlan(
        name="api_high_response_time",
        resource_type="api",
        trigger_condition="HttpResponseTime > 3s",
        severity=Severity.SEV2,
        description="API response times critically slow",
        runbook=[
            RunbookStep(1, "Profile slow endpoints", "Use App Insights to identify slowest routes"),
            RunbookStep(2, "Check downstream latency", "Verify SQL and Cosmos response times"),
            RunbookStep(3, "Scale up/out", "Increase App Service plan tier or instance count"),
            RunbookStep(4, "Review connection pooling", "Check for connection exhaustion"),
        ],
    ),
    IncidentPlan(
        name="api_resource_exhaustion",
        resource_type="api",
        trigger_condition="CpuPercentage > 90% OR MemoryPercentage > 90%",
        severity=Severity.SEV2,
        description="API server resource exhaustion",
        runbook=[
            RunbookStep(1, "Identify resource hog", "Check per-instance CPU/memory profiles"),
            RunbookStep(2, "Scale out", "Add more instances", automated=True,
                        command="az appservice plan update --name salespoc-api-plan --resource-group ai-myaacoub --number-of-workers 4"),
            RunbookStep(3, "Scale up", "Move to higher App Service plan tier"),
            RunbookStep(4, "Check for memory leaks", "Review App Insights memory trends over 24h"),
        ],
        auto_remediate=True,
    ),

    # ─── APIM ───
    IncidentPlan(
        name="apim_capacity_high",
        resource_type="apim",
        trigger_condition="Capacity > 90%",
        severity=Severity.SEV2,
        description="API Management gateway capacity near limit",
        runbook=[
            RunbookStep(1, "Check request volume", "Review traffic patterns for unexpected spikes"),
            RunbookStep(2, "Scale APIM units", "Add capacity units to APIM instance", automated=True,
                        command="az apim update --name salespoc-apim --resource-group ai-myaacoub --sku-capacity 2"),
            RunbookStep(3, "Enable rate limiting", "Apply or tighten rate-limit policies"),
            RunbookStep(4, "Review caching", "Ensure response caching is configured for eligible APIs"),
        ],
    ),
    IncidentPlan(
        name="apim_backend_slow",
        resource_type="apim",
        trigger_condition="BackendDuration > 5000ms",
        severity=Severity.SEV2,
        description="APIM backend response times critically slow",
        runbook=[
            RunbookStep(1, "Identify slow backend", "Check per-API backend duration in diagnostics"),
            RunbookStep(2, "Check API health", "Verify backend App Service is healthy"),
            RunbookStep(3, "Check circuit breaker", "Review APIM retry/timeout policies"),
            RunbookStep(4, "Enable response caching", "Cache responses for read-heavy endpoints"),
        ],
    ),
    IncidentPlan(
        name="apim_auth_spike",
        resource_type="apim",
        trigger_condition="UnauthorizedRequests > 100 in 5min",
        severity=Severity.SEV2,
        description="Spike in unauthorized API requests — potential security concern",
        runbook=[
            RunbookStep(1, "Analyze request origins", "Check source IPs for patterns"),
            RunbookStep(2, "Review subscription keys", "Verify no keys were revoked or expired"),
            RunbookStep(3, "Enable IP filtering", "Block suspicious IPs via APIM policy"),
            RunbookStep(4, "Rotate credentials", "Rotate subscription keys if compromise suspected"),
        ],
    ),

    # ─── AI Foundry ───
    IncidentPlan(
        name="foundry_high_error_rate",
        resource_type="foundry",
        trigger_condition="TotalErrors > 20 in 5min",
        severity=Severity.SEV2,
        description="AI Foundry model error rate elevated",
        runbook=[
            RunbookStep(1, "Check model deployment", "Verify model endpoint is healthy", automated=True,
                        command="az cognitiveservices account show --name salespoc-ai-foundry --resource-group ai-myaacoub --query '{provisioningState:properties.provisioningState}'"),
            RunbookStep(2, "Review error types", "Categorize errors (rate limit, model errors, input validation)"),
            RunbookStep(3, "Check quota", "Verify TPM/RPM limits haven't been exceeded"),
            RunbookStep(4, "Fallback model", "Switch to fallback model deployment if primary fails"),
        ],
    ),
    IncidentPlan(
        name="foundry_high_latency",
        resource_type="foundry",
        trigger_condition="Latency > 5000ms",
        severity=Severity.SEV3,
        description="AI Foundry inference latency is high",
        runbook=[
            RunbookStep(1, "Check prompt sizes", "Review if input token counts have increased"),
            RunbookStep(2, "Check regional load", "Verify Azure region is not experiencing congestion"),
            RunbookStep(3, "Reduce max_tokens", "Lower max output tokens to reduce generation time"),
            RunbookStep(4, "Add retry with backoff", "Implement exponential backoff for retries"),
        ],
    ),

    # ─── Frontend ───
    IncidentPlan(
        name="frontend_function_errors",
        resource_type="frontend",
        trigger_condition="FunctionErrors > 20 in 5min",
        severity=Severity.SEV2,
        description="Static Web App API function errors elevated",
        runbook=[
            RunbookStep(1, "Check function logs", "Review SWA function execution logs"),
            RunbookStep(2, "Check linked API", "Verify APIM and backend API connectivity"),
            RunbookStep(3, "Redeploy", "Trigger redeployment from latest commit"),
            RunbookStep(4, "Verify routes", "Check staticwebapp.config.json route rules"),
        ],
    ),
]


class IncidentManager:
    """Manages incident lifecycle based on response plans."""

    def __init__(self):
        self._plans = {p.name: p for p in INCIDENT_PLANS}
        self._active_incidents: dict[str, Incident] = {}
        self._incident_counter = 0

    def get_plan(self, plan_name: str) -> IncidentPlan | None:
        return self._plans.get(plan_name)

    def get_plans_for_resource(self, resource_type: str) -> list[IncidentPlan]:
        return [p for p in self._plans.values() if p.resource_type == resource_type]

    def create_incident(self, plan_name: str, description: str = "", metadata: dict | None = None) -> Incident:
        plan = self._plans.get(plan_name)
        if not plan:
            raise ValueError(f"Unknown incident plan: {plan_name}")

        self._incident_counter += 1
        incident_id = f"INC-{self._incident_counter:04d}"

        incident = Incident(
            id=incident_id,
            plan_name=plan_name,
            severity=plan.severity,
            status=IncidentStatus.DETECTED,
            description=description or plan.description,
            metadata=metadata or {},
        )
        self._active_incidents[incident_id] = incident
        logger.warning("Incident created: %s [%s] - %s", incident_id, plan.severity.value, incident.description)
        return incident

    def acknowledge(self, incident_id: str) -> Incident:
        incident = self._active_incidents.get(incident_id)
        if not incident:
            raise ValueError(f"Incident not found: {incident_id}")
        incident.status = IncidentStatus.ACKNOWLEDGED
        incident.acknowledged_at = datetime.now(timezone.utc)
        logger.info("Incident %s acknowledged.", incident_id)
        return incident

    def resolve(self, incident_id: str, resolution: str = "") -> Incident:
        incident = self._active_incidents.get(incident_id)
        if not incident:
            raise ValueError(f"Incident not found: {incident_id}")
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = datetime.now(timezone.utc)
        if resolution:
            incident.actions_taken.append(resolution)
        logger.info("Incident %s resolved: %s", incident_id, resolution)
        return incident

    def get_active_incidents(self) -> list[Incident]:
        return [i for i in self._active_incidents.values() if i.status != IncidentStatus.RESOLVED]

    def get_summary(self) -> dict:
        active = self.get_active_incidents()
        return {
            "total_active": len(active),
            "by_severity": {
                s.value: len([i for i in active if i.severity == s])
                for s in Severity
            },
            "incidents": [
                {"id": i.id, "severity": i.severity.value, "status": i.status.value, "description": i.description}
                for i in active
            ],
            "plans_available": len(self._plans),
        }
