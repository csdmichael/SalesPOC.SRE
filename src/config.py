"""Configuration for the SRE agent."""

from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    """Settings loaded from environment variables."""

    agent_name: str = "sre-poc-ai-my"
    azure_subscription_id: str = "86b37969-9445-49cf-b03f-d8866235171c"
    azure_resource_group: str = "ai-myaacoub"
    azure_region: str = "eastus2"
    agent_endpoint: str = "https://sre-poc-ai-my--618da5b9.daa74423.eastus2.azuresre.ai"
    azure_managed_identity: str = "sre-poc-ai-my-bvrrtvop7umme"
    app_insights_resource: str = "sre-poc-ai-my-b8bc7f81-ab86-app-insights"
    applicationinsights_connection_string: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = AgentSettings()
