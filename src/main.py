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
    """Start the SRE agent."""
    configure_monitoring()

    agent = SREAgent()
    health = await agent.health_check()
    logger.info("Agent started: %s", health)


if __name__ == "__main__":
    logger.info(
        "Starting SRE Agent '%s' in %s...",
        settings.agent_name,
        settings.azure_region,
    )
    asyncio.run(main())
