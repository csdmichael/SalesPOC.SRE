"""Main entry point for the SRE agent."""

import asyncio
import logging

from src.agent import SREAgent, configure_monitoring
from src.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the SRE agent with scheduler."""
    configure_monitoring()

    agent = SREAgent()
    health = await agent.health_check()
    logger.info("Agent started: %s", health.get("status"))
    logger.info("Monitoring %d Azure resources", len(health.get("azure_resources", {}).get("resources", {})))
    logger.info("Tracking %d GitHub repos", health.get("github_repos", {}).get("total", 0))
    logger.info("Scheduler has %d tasks", len(health.get("scheduler", {}).get("tasks", {})))

    # Run initial full analysis
    logger.info("Running initial analysis...")
    analysis = await agent.run_analysis()
    for name, result in analysis.items():
        status = "OK" if result.get("success") else "FAILED"
        logger.info("  [%s] %s: %s", status, name, result.get("findings", [result.get("error", "")]))

    # Start the scheduler loop
    logger.info("Starting scheduled task loop...")
    await agent.scheduler.start()


if __name__ == "__main__":
    logger.info(
        "Starting SRE Agent '%s' in %s...",
        settings.agent_name,
        settings.azure_region,
    )
    asyncio.run(main())
