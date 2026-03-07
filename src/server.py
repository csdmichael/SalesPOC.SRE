"""HTTP server for Azure Monitor webhook alerts and health endpoints."""

import logging

from aiohttp import web

logger = logging.getLogger(__name__)


async def handle_webhook(request: web.Request) -> web.Response:
    """Process Azure Monitor common alert schema webhook."""
    try:
        payload = await request.json()
        agent = request.app["agent"]
        result = await agent.process_alert_webhook(payload)
        logger.info("Webhook processed: %s", result)
        return web.json_response(result)
    except Exception as exc:
        logger.error("Webhook processing failed: %s", exc)
        return web.json_response({"error": "internal_error"}, status=500)


async def handle_health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    agent = request.app.get("agent")
    if agent:
        health = await agent.health_check()
        return web.json_response(health)
    return web.json_response({"status": "healthy"})


async def handle_dashboard(request: web.Request) -> web.Response:
    """Dashboard summary endpoint."""
    agent = request.app.get("agent")
    if agent:
        dashboard = agent.monitor.get_dashboard_summary()
        return web.json_response(dashboard)
    return web.json_response({"error": "agent_not_initialized"}, status=503)


async def handle_incidents(request: web.Request) -> web.Response:
    """Active incidents endpoint."""
    agent = request.app.get("agent")
    if agent:
        summary = agent.incident_mgr.get_summary()
        return web.json_response(summary)
    return web.json_response({"error": "agent_not_initialized"}, status=503)


def create_app(agent=None) -> web.Application:
    """Create the aiohttp web application."""
    app = web.Application()
    app["agent"] = agent
    app.router.add_post("/api/alerts/webhook", handle_webhook)
    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/dashboard", handle_dashboard)
    app.router.add_get("/api/incidents", handle_incidents)
    return app
