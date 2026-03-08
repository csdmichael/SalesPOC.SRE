"""Configuration for the SRE agent."""

from pydantic_settings import BaseSettings


GITHUB_REPOS: list[dict[str, str]] = [
    {"name": "SalesPOC.UI", "url": "https://github.com/csdmichael/SalesPOC.UI", "component": "ui"},
    {"name": "SalesPOC.API", "url": "https://github.com/csdmichael/SalesPOC.API", "component": "api"},
    {"name": "SalesPOC.MCP", "url": "https://github.com/csdmichael/SalesPOC.MCP", "component": "mcp"},
    {"name": "SalesPOC.APIM", "url": "https://github.com/csdmichael/SalesPOC.APIM", "component": "apim"},
    {"name": "SalesPOC.APIC", "url": "https://github.com/csdmichael/SalesPOC.APIC", "component": "apic"},
    {"name": "SalesPOC.DB", "url": "https://github.com/csdmichael/SalesPOC.DB", "component": "db"},
    {"name": "SalesPOC.AI", "url": "https://github.com/csdmichael/SalesPOC.AI", "component": "ai"},
]


class AgentSettings(BaseSettings):
    """Settings loaded from environment variables."""

    # Agent identity
    agent_name: str = "sre-ai-my"
    agent_endpoint: str = "https://sre-ai-my--0cad75dc.4650bed8.eastus2.azuresre.ai"
    server_port: int = 8080

    # Azure environment
    azure_subscription_id: str = "86b37969-9445-49cf-b03f-d8866235171c"
    azure_resource_group: str = "ai-myaacoub"
    azure_region: str = "eastus2"
    azure_managed_identity: str = "sre-ai-my-bvrrtvop7umme"

    # Monitoring
    app_insights_resource: str = "sre-ai-my-b8bc7f81-ab86-app-insights"
    applicationinsights_connection_string: str = ""

    # GitHub
    github_token: str = ""
    github_org: str = "csdmichael"

    # Azure resource names
    sql_server_name: str = "ai-db-poc"
    sql_database_name: str = "ai-db-poc"
    cosmos_account_name: str = "cosmos-ai-poc"
    cosmos_database_name: str = "salespoc"
    cosmos_container_name: str = "orders"
    storage_account_name: str = "aistoragemyaacoub"
    api_app_service_name: str = "SalesPOC-API"
    apim_service_name: str = "apim-poc-my"
    ai_foundry_name: str = "001-ai-poc"
    frontend_app_service_name: str = "SalesPOC"
    app_service_plan_name: str = "ASP-aimyaacoub-87dc"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def resource_id(self, provider: str, resource_path: str) -> str:
        """Build a full Azure resource ID."""
        return (
            f"/subscriptions/{self.azure_subscription_id}"
            f"/resourceGroups/{self.azure_resource_group}"
            f"/providers/{provider}/{resource_path}"
        )


settings = AgentSettings()
