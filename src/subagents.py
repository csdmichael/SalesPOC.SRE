"""Specialized subagents for Sales POC SRE operations."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from src.monitors import AzureResourceMonitor, HealthStatus, ResourceType
from src.incidents import IncidentManager, IncidentPlan
from src.github_connector import GitHubConnector

logger = logging.getLogger(__name__)


class SubagentType(str, Enum):
    DATABASE = "database"
    API_GATEWAY = "api_gateway"
    AI_SERVICES = "ai_services"
    FRONTEND = "frontend"
    SECURITY = "security"
    COST = "cost"


@dataclass
class SubagentResult:
    agent: str
    success: bool
    findings: list[str]
    recommendations: list[str]
    incidents_created: list[str]
    timestamp: datetime


class BaseSubagent:
    """Base class for SRE subagents."""

    def __init__(self, monitor: AzureResourceMonitor, incident_mgr: IncidentManager):
        self._monitor = monitor
        self._incident_mgr = incident_mgr

    def _create_result(self, agent: str, findings: list[str], recommendations: list[str],
                       incidents: list[str] | None = None) -> SubagentResult:
        return SubagentResult(
            agent=agent, success=True, findings=findings,
            recommendations=recommendations,
            incidents_created=incidents or [],
            timestamp=datetime.now(timezone.utc),
        )


class DatabaseSubagent(BaseSubagent):
    """Monitors SQL Database and Cosmos DB health."""

    async def analyze(self) -> SubagentResult:
        findings = []
        recommendations = []
        incidents = []

        sql_health = self._monitor.query_resource(ResourceType.SQL_DB)
        cosmos_health = self._monitor.query_resource(ResourceType.COSMOS_DB)

        # SQL DB analysis
        if sql_health.status == HealthStatus.UNHEALTHY:
            findings.append(f"SQL DB CRITICAL: {sql_health.message}")
            for plan in self._incident_mgr.get_plans_for_resource("sql_db"):
                inc = self._incident_mgr.create_incident(plan.name, metadata={"source": "database_subagent"})
                incidents.append(inc.id)
        elif sql_health.status == HealthStatus.DEGRADED:
            findings.append(f"SQL DB degraded: {sql_health.message}")
            recommendations.append("Consider scaling SQL DTU tier proactively")

        for m in sql_health.metrics:
            if m.name == "deadlock" and m.value and m.value > 0:
                findings.append(f"SQL deadlocks detected: {m.value}")
                recommendations.append("Review transaction isolation levels and lock ordering")

        # Cosmos DB analysis
        if cosmos_health.status == HealthStatus.UNHEALTHY:
            findings.append(f"Cosmos DB CRITICAL: {cosmos_health.message}")
            for plan in self._incident_mgr.get_plans_for_resource("cosmos_db"):
                inc = self._incident_mgr.create_incident(plan.name, metadata={"source": "database_subagent"})
                incidents.append(inc.id)
        elif cosmos_health.status == HealthStatus.DEGRADED:
            findings.append(f"Cosmos DB degraded: {cosmos_health.message}")
            recommendations.append("Review partition key design and RU allocation")

        for m in cosmos_health.metrics:
            if m.name == "Http429" and m.value and m.value > 0:
                findings.append(f"Cosmos DB throttling: {m.value} 429s")
                recommendations.append("Increase provisioned RUs or enable autoscale")

        if not findings:
            findings.append("All databases healthy")

        return self._create_result("database", findings, recommendations, incidents)


class ApiGatewaySubagent(BaseSubagent):
    """Monitors API and APIM health."""

    async def analyze(self) -> SubagentResult:
        findings = []
        recommendations = []
        incidents = []

        api_health = self._monitor.query_resource(ResourceType.API)
        apim_health = self._monitor.query_resource(ResourceType.APIM)

        # API analysis
        if api_health.status == HealthStatus.UNHEALTHY:
            findings.append(f"API CRITICAL: {api_health.message}")
            for plan in self._incident_mgr.get_plans_for_resource("api"):
                if "5xx" in plan.name or "resource" in plan.name:
                    inc = self._incident_mgr.create_incident(plan.name, metadata={"source": "api_gateway_subagent"})
                    incidents.append(inc.id)
        elif api_health.status == HealthStatus.DEGRADED:
            findings.append(f"API degraded: {api_health.message}")

        for m in api_health.metrics:
            if m.name == "Http5xx" and m.value and m.value > 0:
                findings.append(f"API 5xx errors: {m.value}")
                recommendations.append("Check Application Insights for exception details")
            if m.name == "HttpResponseTime" and m.value and m.value > 1.0:
                findings.append(f"API avg response time: {m.value:.2f}s")
                recommendations.append("Profile slow endpoints and check downstream dependencies")

        # APIM analysis
        if apim_health.status == HealthStatus.UNHEALTHY:
            findings.append(f"APIM CRITICAL: {apim_health.message}")
            for plan in self._incident_mgr.get_plans_for_resource("apim"):
                inc = self._incident_mgr.create_incident(plan.name, metadata={"source": "api_gateway_subagent"})
                incidents.append(inc.id)
        elif apim_health.status == HealthStatus.DEGRADED:
            findings.append(f"APIM degraded: {apim_health.message}")

        for m in apim_health.metrics:
            if m.name == "UnauthorizedRequests" and m.value and m.value > 20:
                findings.append(f"APIM unauthorized requests spike: {m.value}")
                recommendations.append("Investigate source IPs for potential abuse")

        if not findings:
            findings.append("API and APIM healthy")

        return self._create_result("api_gateway", findings, recommendations, incidents)


class AIServicesSubagent(BaseSubagent):
    """Monitors AI Foundry health."""

    async def analyze(self) -> SubagentResult:
        findings = []
        recommendations = []
        incidents = []

        foundry_health = self._monitor.query_resource(ResourceType.FOUNDRY)

        if foundry_health.status == HealthStatus.UNHEALTHY:
            findings.append(f"AI Foundry CRITICAL: {foundry_health.message}")
            for plan in self._incident_mgr.get_plans_for_resource("foundry"):
                inc = self._incident_mgr.create_incident(plan.name, metadata={"source": "ai_services_subagent"})
                incidents.append(inc.id)
        elif foundry_health.status == HealthStatus.DEGRADED:
            findings.append(f"AI Foundry degraded: {foundry_health.message}")

        for m in foundry_health.metrics:
            if m.name == "TotalErrors" and m.value and m.value > 0:
                findings.append(f"AI Foundry errors: {m.value}")
                recommendations.append("Review error logs and check model deployment status")
            if m.name == "Latency" and m.value and m.value > 2000:
                findings.append(f"AI Foundry latency: {m.value:.0f}ms")
                recommendations.append("Consider reducing max_tokens or prompt size")
            if m.name == "TokenTransaction" and m.value:
                findings.append(f"Token usage: {m.value:.0f} tokens")

        if not findings:
            findings.append("AI Foundry healthy")

        return self._create_result("ai_services", findings, recommendations, incidents)


class FrontendSubagent(BaseSubagent):
    """Monitors Frontend and Storage health."""

    async def analyze(self) -> SubagentResult:
        findings = []
        recommendations = []
        incidents = []

        fe_health = self._monitor.query_resource(ResourceType.FRONTEND)
        storage_health = self._monitor.query_resource(ResourceType.STORAGE)

        # Frontend analysis
        if fe_health.status == HealthStatus.UNHEALTHY:
            findings.append(f"Frontend CRITICAL: {fe_health.message}")
            for plan in self._incident_mgr.get_plans_for_resource("frontend"):
                inc = self._incident_mgr.create_incident(plan.name, metadata={"source": "frontend_subagent"})
                incidents.append(inc.id)
        elif fe_health.status == HealthStatus.DEGRADED:
            findings.append(f"Frontend degraded: {fe_health.message}")

        for m in fe_health.metrics:
            if m.name == "FunctionErrors" and m.value and m.value > 0:
                findings.append(f"SWA function errors: {m.value}")
                recommendations.append("Check SWA API function logs and route config")

        # Storage analysis
        if storage_health.status == HealthStatus.UNHEALTHY:
            findings.append(f"Storage CRITICAL: {storage_health.message}")
            for plan in self._incident_mgr.get_plans_for_resource("storage"):
                inc = self._incident_mgr.create_incident(plan.name, metadata={"source": "frontend_subagent"})
                incidents.append(inc.id)
        elif storage_health.status == HealthStatus.DEGRADED:
            findings.append(f"Storage degraded: {storage_health.message}")

        if not findings:
            findings.append("Frontend and Storage healthy")

        return self._create_result("frontend", findings, recommendations, incidents)


class SecuritySubagent(BaseSubagent):
    """Monitors security-related signals across all resources."""

    def __init__(self, monitor: AzureResourceMonitor, incident_mgr: IncidentManager,
                 github: GitHubConnector | None = None):
        super().__init__(monitor, incident_mgr)
        self._github = github

    async def analyze(self) -> SubagentResult:
        findings = []
        recommendations = []

        # Check APIM unauthorized requests
        apim_health = self._monitor.query_resource(ResourceType.APIM)
        for m in apim_health.metrics:
            if m.name == "UnauthorizedRequests" and m.value and m.value > 50:
                findings.append(f"High unauthorized request count: {m.value}")
                recommendations.append("Review APIM access policies and IP restrictions")

        # Check SQL connection failures (potential brute force)
        sql_health = self._monitor.query_resource(ResourceType.SQL_DB)
        for m in sql_health.metrics:
            if m.name == "connection_failed" and m.value and m.value > 10:
                findings.append(f"Elevated SQL connection failures: {m.value}")
                recommendations.append("Verify firewall rules and check for credential issues")

        # Check API 4xx patterns
        api_health = self._monitor.query_resource(ResourceType.API)
        for m in api_health.metrics:
            if m.name == "Http4xx" and m.value and m.value > 100:
                findings.append(f"High 4xx rate on API: {m.value}")
                recommendations.append("Check for scanning/enumeration attempts")

        # Check GitHub repo security
        if self._github:
            connectivity = self._github.check_connectivity()
            if connectivity["failed"] > 0:
                findings.append(f"{connectivity['failed']} GitHub repos unreachable")
                recommendations.append("Verify repo visibility and access settings")

        if not findings:
            findings.append("No security anomalies detected")

        return self._create_result("security", findings, recommendations)


class CostSubagent(BaseSubagent):
    """Monitors resource usage patterns for cost optimization."""

    async def analyze(self) -> SubagentResult:
        findings = []
        recommendations = []

        # Check for over-provisioned resources
        api_health = self._monitor.query_resource(ResourceType.API)
        for m in api_health.metrics:
            if m.name == "CpuPercentage" and m.value is not None and m.value < 10:
                findings.append(f"API CPU utilization very low: {m.value:.1f}%")
                recommendations.append("Consider scaling down App Service plan")
            if m.name == "MemoryPercentage" and m.value is not None and m.value < 20:
                findings.append(f"API memory utilization low: {m.value:.1f}%")

        # Check Cosmos DB RU usage
        cosmos_health = self._monitor.query_resource(ResourceType.COSMOS_DB)
        for m in cosmos_health.metrics:
            if m.name == "TotalRequestUnits" and m.value is not None and m.value < 100:
                findings.append(f"Cosmos DB RU usage very low: {m.value:.0f}")
                recommendations.append("Consider reducing provisioned RUs or switching to serverless")

        # Check SQL DTU
        sql_health = self._monitor.query_resource(ResourceType.SQL_DB)
        for m in sql_health.metrics:
            if m.name == "dtu_consumption_percent" and m.value is not None and m.value < 10:
                findings.append(f"SQL DTU usage very low: {m.value:.1f}%")
                recommendations.append("Consider downgrading SQL service tier")

        # Check AI token usage
        foundry_health = self._monitor.query_resource(ResourceType.FOUNDRY)
        for m in foundry_health.metrics:
            if m.name == "TokenTransaction" and m.value is not None:
                findings.append(f"AI Foundry token usage: {m.value:.0f}")

        if not findings:
            findings.append("Resource utilization within expected ranges")

        return self._create_result("cost", findings, recommendations)


class SubagentOrchestrator:
    """Orchestrates all subagents and aggregates results."""

    def __init__(self, monitor: AzureResourceMonitor, incident_mgr: IncidentManager,
                 github: GitHubConnector | None = None):
        self.database = DatabaseSubagent(monitor, incident_mgr)
        self.api_gateway = ApiGatewaySubagent(monitor, incident_mgr)
        self.ai_services = AIServicesSubagent(monitor, incident_mgr)
        self.frontend = FrontendSubagent(monitor, incident_mgr)
        self.security = SecuritySubagent(monitor, incident_mgr, github)
        self.cost = CostSubagent(monitor, incident_mgr)

    async def run_all(self) -> dict:
        """Run all subagents and return aggregated results."""
        results = {}
        for name, agent in [
            ("database", self.database),
            ("api_gateway", self.api_gateway),
            ("ai_services", self.ai_services),
            ("frontend", self.frontend),
            ("security", self.security),
            ("cost", self.cost),
        ]:
            try:
                result = await agent.analyze()
                results[name] = {
                    "success": result.success,
                    "findings": result.findings,
                    "recommendations": result.recommendations,
                    "incidents_created": result.incidents_created,
                    "timestamp": result.timestamp.isoformat(),
                }
            except Exception as exc:
                logger.error("Subagent '%s' failed: %s", name, exc)
                results[name] = {"success": False, "error": str(exc)}

        return results

    async def run_single(self, agent_type: SubagentType) -> SubagentResult:
        """Run a specific subagent."""
        agent_map = {
            SubagentType.DATABASE: self.database,
            SubagentType.API_GATEWAY: self.api_gateway,
            SubagentType.AI_SERVICES: self.ai_services,
            SubagentType.FRONTEND: self.frontend,
            SubagentType.SECURITY: self.security,
            SubagentType.COST: self.cost,
        }
        return await agent_map[agent_type].analyze()
