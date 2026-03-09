"""SRE Agent implementation for Azure SRE service."""

import asyncio
import logging

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.monitor.opentelemetry import configure_azure_monitor

from src.config import settings
from src.github_connector import GitHubConnector
from src.monitors import AzureResourceMonitor
from src.incidents import IncidentManager
from src.scheduler import TaskScheduler, ScheduledTask, TaskFrequency
from src.subagents import SubagentOrchestrator

logger = logging.getLogger(__name__)


def configure_monitoring() -> None:
    """Configure Application Insights telemetry."""
    if settings.applicationinsights_connection_string:
        configure_azure_monitor(
            connection_string=settings.applicationinsights_connection_string,
        )
        logger.info("Application Insights configured.")
    else:
        logger.warning(
            "APPLICATIONINSIGHTS_CONNECTION_STRING not set. Telemetry disabled."
        )


def get_credential():
    """Get Azure credential using managed identity or default chain."""
    if settings.azure_managed_identity:
        return ManagedIdentityCredential(
            client_id=settings.azure_managed_identity,
        )
    return DefaultAzureCredential()


class SREAgent:
    """Site Reliability Engineering Agent."""

    def __init__(self):
        self.credential = get_credential()
        self.agent_name = settings.agent_name
        self.endpoint = settings.agent_endpoint

        # Components
        self.github = GitHubConnector()
        self.monitor = AzureResourceMonitor(self.credential)
        self.incident_mgr = IncidentManager()
        self.scheduler = TaskScheduler()
        self.subagents = SubagentOrchestrator(self.monitor, self.incident_mgr, self.github)

        # Register scheduled tasks
        self._register_tasks()

        logger.info("SRE Agent '%s' initialized with all components.", self.agent_name)

    def _register_tasks(self) -> None:
        """Register all scheduled monitoring tasks."""
        self.scheduler.register(ScheduledTask(
            name="health_check_all",
            description="Full health check of all Azure resources",
            frequency=TaskFrequency.EVERY_5_MINUTES,
            handler=self._task_health_check,
        ))
        self.scheduler.register(ScheduledTask(
            name="subagent_analysis",
            description="Run all subagent analyses",
            frequency=TaskFrequency.EVERY_15_MINUTES,
            handler=self._task_subagent_analysis,
        ))
        self.scheduler.register(ScheduledTask(
            name="github_repo_check",
            description="Check GitHub repository connectivity and status",
            frequency=TaskFrequency.EVERY_HOUR,
            handler=self._task_github_check,
        ))
        self.scheduler.register(ScheduledTask(
            name="security_scan",
            description="Run security subagent analysis",
            frequency=TaskFrequency.EVERY_15_MINUTES,
            handler=self._task_security_scan,
        ))
        self.scheduler.register(ScheduledTask(
            name="cost_analysis",
            description="Run cost optimization analysis",
            frequency=TaskFrequency.EVERY_6_HOURS,
            handler=self._task_cost_analysis,
        ))
        self.scheduler.register(ScheduledTask(
            name="daily_report",
            description="Generate daily SRE summary report",
            frequency=TaskFrequency.EVERY_DAY,
            handler=self._task_daily_report,
        ))

    # ── Scheduled task handlers ──

    async def _task_health_check(self) -> dict:
        return await self.monitor.async_get_dashboard_summary()

    async def _task_subagent_analysis(self) -> dict:
        return await self.subagents.run_all()

    async def _task_github_check(self) -> dict:
        return await asyncio.to_thread(self.github.check_connectivity)

    async def _task_security_scan(self) -> dict:
        result = await self.subagents.security.analyze()
        return {"findings": result.findings, "recommendations": result.recommendations}

    async def _task_cost_analysis(self) -> dict:
        result = await self.subagents.cost.analyze()
        return {"findings": result.findings, "recommendations": result.recommendations}

    async def _task_daily_report(self) -> dict:
        dashboard = await self.monitor.async_get_dashboard_summary()
        incidents = self.incident_mgr.get_summary()
        github = await asyncio.to_thread(self.github.check_connectivity)
        return {"dashboard": dashboard, "incidents": incidents, "github": github}

    # ── Public API ──

    async def handle_incident(self, incident_data: dict) -> dict:
        """Handle an incoming incident alert."""
        logger.info("Processing incident: %s", incident_data.get("id", "unknown"))
        plan_name = incident_data.get("plan_name")
        if plan_name:
            incident = self.incident_mgr.create_incident(
                plan_name, metadata=incident_data,
            )
            return {
                "status": "acknowledged",
                "agent": self.agent_name,
                "incident_id": incident.id,
                "severity": incident.severity.value,
            }
        return {
            "status": "acknowledged",
            "agent": self.agent_name,
            "incident_id": incident_data.get("id"),
        }

    async def health_check(self) -> dict:
        """Return agent health status."""
        github_status = await asyncio.to_thread(self.github.check_connectivity)
        dashboard = await self.monitor.async_get_dashboard_summary()
        incidents = self.incident_mgr.get_summary()
        scheduler = self.scheduler.get_status()
        return {
            "status": "healthy",
            "agent": self.agent_name,
            "endpoint": self.endpoint,
            "azure_resources": dashboard,
            "github_repos": github_status,
            "active_incidents": incidents,
            "scheduler": scheduler,
        }

    async def run_analysis(self) -> dict:
        """Run a full analysis using all subagents."""
        return await self.subagents.run_all()

    async def process_alert_webhook(self, payload: dict) -> dict:
        """Process an Azure Monitor common alert schema webhook."""
        data = payload.get("data", {})
        essentials = data.get("essentials", {})
        custom_properties = data.get("customProperties", {})
        monitor_condition = essentials.get("monitorCondition", "")

        # Only process fired alerts, not resolved
        if monitor_condition == "Resolved":
            logger.info("Alert resolved: %s", essentials.get("alertRule", ""))
            return {"status": "ignored", "reason": "alert_resolved"}

        alert_rule = essentials.get("alertRule", "")

        # Prefer planName from customProperties (set via Bicep webHookProperties)
        plan_name = custom_properties.get("planName")

        # Fall back to resolving from alert rule name
        if not plan_name:
            plan_name = self._resolve_plan_from_alert_rule(alert_rule)

        if plan_name and self.incident_mgr.get_plan(plan_name):
            incident = self.incident_mgr.create_incident(
                plan_name,
                description=essentials.get("description", ""),
                metadata={
                    "alert_id": essentials.get("alertId", ""),
                    "alert_rule": alert_rule,
                    "severity": essentials.get("severity", ""),
                    "source": "azure_monitor_webhook",
                },
            )
            logger.info("Incident created from alert: %s -> %s", alert_rule, incident.id)
            return {
                "status": "incident_created",
                "incident_id": incident.id,
                "plan_name": plan_name,
            }

        logger.warning("No matching plan for alert: %s", alert_rule)
        return {"status": "no_matching_plan", "alert_rule": alert_rule}

    @staticmethod
    def _resolve_plan_from_alert_rule(alert_rule_name: str) -> str | None:
        """Map Azure Monitor alert rule name to incident plan name."""
        # Handle full ARM resource IDs by extracting the last segment
        if "/" in alert_rule_name:
            alert_rule_name = alert_rule_name.rsplit("/", 1)[-1]
        mapping = {
            "sre-sql-high-cpu": "sql_high_cpu",
            "sre-sql-connection-failures": "sql_connection_failures",
            "sre-sql-deadlocks": "sql_deadlocks",
            "sre-sql-storage-critical": "sql_storage_critical",
            "sre-cosmos-throttling": "cosmos_throttling",
            "sre-cosmos-replication-lag": "cosmos_replication_lag",
            "sre-storage-availability-drop": "storage_availability_drop",
            "sre-storage-high-latency": "storage_high_latency",
            "sre-api-5xx-spike": "api_5xx_spike",
            "sre-api-high-response-time": "api_high_response_time",
            "sre-api-cpu-exhaustion": "api_resource_exhaustion",
            "sre-api-memory-exhaustion": "api_resource_exhaustion",
            "sre-apim-capacity-high": "apim_capacity_high",
            "sre-apim-backend-slow": "apim_backend_slow",
            "sre-apim-auth-spike": "apim_auth_spike",
            "sre-foundry-high-error-rate": "foundry_high_error_rate",
            "sre-foundry-high-latency": "foundry_high_latency",
            "sre-frontend-http-errors": "frontend_http_errors",
        }
        return mapping.get(alert_rule_name)
