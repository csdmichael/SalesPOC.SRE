"""SRE Agent implementation for Azure SRE service."""

import logging

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.monitor.opentelemetry import configure_azure_monitor

from src.config import settings
from src.github_connector import GitHubConnector

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
        self.github = GitHubConnector()
        logger.info("SRE Agent '%s' initialized.", self.agent_name)

    async def handle_incident(self, incident_data: dict) -> dict:
        """Handle an incoming incident alert."""
        logger.info("Processing incident: %s", incident_data.get("id", "unknown"))
        return {
            "status": "acknowledged",
            "agent": self.agent_name,
            "incident_id": incident_data.get("id"),
        }

    async def health_check(self) -> dict:
        """Return agent health status."""
        github_status = self.github.check_connectivity()
        return {
            "status": "healthy",
            "agent": self.agent_name,
            "endpoint": self.endpoint,
            "github_repos": github_status,
        }
