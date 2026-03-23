"""Azure resource monitors for Sales POC infrastructure."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from azure.identity import DefaultAzureCredential
from azure.monitor.query import MetricsQueryClient, MetricAggregationType

from src.config import settings

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    SQL_DB = "sql_db"
    COSMOS_DB = "cosmos_db"
    STORAGE = "storage"
    API = "api"
    APIM = "apim"
    FOUNDRY = "foundry"
    FRONTEND = "frontend"
    VNET = "vnet"
    NSG = "nsg"
    PRIVATE_ENDPOINT = "private_endpoint"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class MetricResult:
    name: str
    value: float | None
    unit: str
    timestamp: datetime | None = None


@dataclass
class ResourceHealth:
    resource_type: ResourceType
    resource_name: str
    status: HealthStatus
    metrics: list[MetricResult] = field(default_factory=list)
    message: str = ""
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# --- Azure resource IDs for the Sales POC ---
MONITORED_RESOURCES: dict[ResourceType, dict] = {
    ResourceType.SQL_DB: {
        "resource_id": settings.resource_id("Microsoft.Sql", f"servers/{settings.sql_server_name}/databases/{settings.sql_database_name}"),
        "display_name": "Sales POC SQL Database",
        "metrics": [
            {"name": "cpu_percent", "aggregation": "Average", "threshold_warn": 70, "threshold_crit": 90},
            {"name": "storage_percent", "aggregation": "Average", "threshold_warn": 75, "threshold_crit": 90},
            {"name": "connection_failed", "aggregation": "Total", "threshold_warn": 5, "threshold_crit": 20},
            {"name": "deadlock", "aggregation": "Total", "threshold_warn": 1, "threshold_crit": 5},
            {"name": "workers_percent", "aggregation": "Average", "threshold_warn": 70, "threshold_crit": 90},
        ],
    },
    ResourceType.COSMOS_DB: {
        "resource_id": settings.resource_id("Microsoft.DocumentDB", f"databaseAccounts/{settings.cosmos_account_name}"),
        "display_name": "Sales POC Cosmos DB",
        "metrics": [
            {"name": "TotalRequestUnits", "aggregation": "Total", "threshold_warn": 800, "threshold_crit": 950},
            {"name": "TotalRequests", "aggregation": "Count", "threshold_warn": None, "threshold_crit": None},
            {"name": "Http2xx", "aggregation": "Count", "threshold_warn": None, "threshold_crit": None},
            {"name": "Http429", "aggregation": "Count", "threshold_warn": 10, "threshold_crit": 50},
            {"name": "AvailableStorage", "aggregation": "Average", "threshold_warn": None, "threshold_crit": None},
            {"name": "ReplicationLatency", "aggregation": "Average", "threshold_warn": 100, "threshold_crit": 500},
        ],
    },
    ResourceType.STORAGE: {
        "resource_id": settings.resource_id("Microsoft.Storage", f"storageAccounts/{settings.storage_account_name}"),
        "display_name": "Sales POC Storage Account",
        "metrics": [
            {"name": "Availability", "aggregation": "Average", "threshold_warn": 99.5, "threshold_crit": 99.0},
            {"name": "SuccessE2ELatency", "aggregation": "Average", "threshold_warn": 100, "threshold_crit": 500},
            {"name": "Transactions", "aggregation": "Total", "threshold_warn": None, "threshold_crit": None},
            {"name": "UsedCapacity", "aggregation": "Average", "threshold_warn": None, "threshold_crit": None},
        ],
    },
    ResourceType.API: {
        "resource_id": settings.resource_id("Microsoft.Web", f"sites/{settings.api_app_service_name}"),
        "display_name": "Sales POC API (App Service)",
        "metrics": [
            {"name": "HttpResponseTime", "aggregation": "Average", "threshold_warn": 1.0, "threshold_crit": 3.0},
            {"name": "Http5xx", "aggregation": "Total", "threshold_warn": 5, "threshold_crit": 20},
            {"name": "Http4xx", "aggregation": "Total", "threshold_warn": 50, "threshold_crit": 200},
            {"name": "Requests", "aggregation": "Total", "threshold_warn": None, "threshold_crit": None},
            {"name": "AverageMemoryWorkingSet", "aggregation": "Average", "threshold_warn": None, "threshold_crit": None},
            {"name": "AverageResponseTime", "aggregation": "Average", "threshold_warn": 1.0, "threshold_crit": 3.0},
        ],
    },
    ResourceType.APIM: {
        "resource_id": settings.resource_id("Microsoft.ApiManagement", f"service/{settings.apim_service_name}"),
        "display_name": "Sales POC API Management",
        "metrics": [
            {"name": "TotalRequests", "aggregation": "Total", "threshold_warn": None, "threshold_crit": None},
            {"name": "FailedRequests", "aggregation": "Total", "threshold_warn": 10, "threshold_crit": 50},
            {"name": "BackendDuration", "aggregation": "Average", "threshold_warn": 1000, "threshold_crit": 5000},
            {"name": "Capacity", "aggregation": "Average", "threshold_warn": 70, "threshold_crit": 90},
            {"name": "UnauthorizedRequests", "aggregation": "Total", "threshold_warn": 20, "threshold_crit": 100},
        ],
    },
    ResourceType.FOUNDRY: {
        "resource_id": settings.resource_id("Microsoft.CognitiveServices", f"accounts/{settings.ai_foundry_name}"),
        "display_name": "Sales POC AI Foundry",
        "metrics": [
            {"name": "TotalCalls", "aggregation": "Total", "threshold_warn": None, "threshold_crit": None},
            {"name": "TotalErrors", "aggregation": "Total", "threshold_warn": 5, "threshold_crit": 20},
            {"name": "Latency", "aggregation": "Average", "threshold_warn": 2000, "threshold_crit": 5000},
            {"name": "TokenTransaction", "aggregation": "Total", "threshold_warn": None, "threshold_crit": None},
            {"name": "SuccessRate", "aggregation": "Average", "threshold_warn": 95, "threshold_crit": 90},
        ],
    },
    ResourceType.FRONTEND: {
        "resource_id": settings.resource_id("Microsoft.Web", f"sites/{settings.frontend_app_service_name}"),
        "display_name": "Sales POC Frontend (App Service)",
        "metrics": [
            {"name": "HttpResponseTime", "aggregation": "Average", "threshold_warn": 1.0, "threshold_crit": 3.0},
            {"name": "Http5xx", "aggregation": "Total", "threshold_warn": 5, "threshold_crit": 20},
            {"name": "Requests", "aggregation": "Total", "threshold_warn": None, "threshold_crit": None},
            {"name": "AverageMemoryWorkingSet", "aggregation": "Average", "threshold_warn": None, "threshold_crit": None},
            {"name": "AverageResponseTime", "aggregation": "Average", "threshold_warn": 1.0, "threshold_crit": 3.0},
        ],
    },
}

# ── Network resource monitors (one entry per named resource) ──
# VNets – limited platform metrics; rely on activity-log / resource-health alerts
for _vnet_name in settings.vnet_names:
    _key = f"vnet_{_vnet_name}"
    MONITORED_RESOURCES[ResourceType.VNET] = MONITORED_RESOURCES.get(ResourceType.VNET) or {
        "resource_id": settings.resource_id("Microsoft.Network", f"virtualNetworks/{settings.vnet_names[0]}"),
        "display_name": f"VNet – {settings.vnet_names[0]}",
        "metrics": [
            {"name": "IfUnderDDoSAttack", "aggregation": "Maximum", "threshold_warn": 1, "threshold_crit": 1},
            {"name": "BytesDroppedDDoS", "aggregation": "Total", "threshold_warn": None, "threshold_crit": None},
            {"name": "PacketsInDDoS", "aggregation": "Total", "threshold_warn": None, "threshold_crit": None},
            {"name": "PacketsDroppedDDoS", "aggregation": "Total", "threshold_warn": None, "threshold_crit": None},
        ],
    }

# NSGs – flow-log and rule-hit metrics
for _nsg_name in settings.nsg_names:
    pass  # NSGs have no platform metrics; monitored via activity-log alerts

NSG_MONITORED_RESOURCES = {
    nsg: {
        "resource_id": settings.resource_id("Microsoft.Network", f"networkSecurityGroups/{nsg}"),
        "display_name": f"NSG – {nsg}",
    }
    for nsg in settings.nsg_names
}

# Private Endpoints – connectivity status metric
PE_MONITORED_RESOURCES = {
    pe: {
        "resource_id": settings.resource_id("Microsoft.Network", f"privateEndpoints/{pe}"),
        "display_name": f"Private Endpoint – {pe}",
    }
    for pe in settings.private_endpoint_names
}


AGGREGATION_MAP = {
    "Average": MetricAggregationType.AVERAGE,
    "Total": MetricAggregationType.TOTAL,
    "Count": MetricAggregationType.COUNT,
    "Maximum": MetricAggregationType.MAXIMUM,
    "Minimum": MetricAggregationType.MINIMUM,
}


class AzureResourceMonitor:
    """Queries Azure Monitor metrics for Sales POC resources."""

    def __init__(self, credential=None):
        self._credential = credential or DefaultAzureCredential()
        self._client = MetricsQueryClient(self._credential)

    def _evaluate_health(self, metric_cfg: dict, value: float | None) -> HealthStatus:
        if value is None:
            return HealthStatus.UNKNOWN
        warn = metric_cfg.get("threshold_warn")
        crit = metric_cfg.get("threshold_crit")
        if warn is None or crit is None:
            return HealthStatus.HEALTHY
        # For availability-type metrics, lower is worse
        metric_name = metric_cfg["name"].lower()
        if "availability" in metric_name or "healthcheck" in metric_name or "successrate" in metric_name:
            if value < crit:
                return HealthStatus.UNHEALTHY
            if value < warn:
                return HealthStatus.DEGRADED
            return HealthStatus.HEALTHY
        # For error/latency metrics, higher is worse
        if value >= crit:
            return HealthStatus.UNHEALTHY
        if value >= warn:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def query_resource(self, resource_type: ResourceType, timespan_minutes: int = 5) -> ResourceHealth:
        """Query all metrics for a specific resource."""
        resource_cfg = MONITORED_RESOURCES.get(resource_type)
        if not resource_cfg:
            return ResourceHealth(
                resource_type=resource_type, resource_name="unknown",
                status=HealthStatus.UNKNOWN, message="No config found",
            )

        resource_id = resource_cfg["resource_id"]
        metric_names = [m["name"] for m in resource_cfg["metrics"]]
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=timespan_minutes)

        results: list[MetricResult] = []
        worst_status = HealthStatus.HEALTHY
        messages = []

        try:
            response = self._client.query_resource(
                resource_uri=resource_id,
                metric_names=metric_names,
                timespan=(start_time, end_time),
                granularity=timedelta(minutes=1),
                aggregations=[AGGREGATION_MAP.get(m["aggregation"], MetricAggregationType.AVERAGE) for m in resource_cfg["metrics"]],
            )

            for i, metric in enumerate(response.metrics):
                metric_cfg = resource_cfg["metrics"][i] if i < len(resource_cfg["metrics"]) else {}
                value = None
                ts = None
                if metric.timeseries:
                    for ts_data in reversed(metric.timeseries):
                        for dp in reversed(ts_data.data):
                            agg = metric_cfg.get("aggregation", "Average").lower()
                            val = getattr(dp, agg, None) or dp.average or dp.total
                            if val is not None:
                                value = val
                                ts = dp.timestamp
                                break
                        if value is not None:
                            break

                results.append(MetricResult(
                    name=metric.name, value=value,
                    unit=metric.unit, timestamp=ts,
                ))

                status = self._evaluate_health(metric_cfg, value)
                if status == HealthStatus.UNHEALTHY:
                    worst_status = HealthStatus.UNHEALTHY
                    messages.append(f"{metric.name} CRITICAL: {value}")
                elif status == HealthStatus.DEGRADED and worst_status != HealthStatus.UNHEALTHY:
                    worst_status = HealthStatus.DEGRADED
                    messages.append(f"{metric.name} WARNING: {value}")

        except Exception as exc:
            logger.error("Failed to query metrics for %s: %s", resource_type.value, exc)
            return ResourceHealth(
                resource_type=resource_type,
                resource_name=resource_cfg["display_name"],
                status=HealthStatus.UNKNOWN,
                message=f"Query failed: {exc}",
            )

        return ResourceHealth(
            resource_type=resource_type,
            resource_name=resource_cfg["display_name"],
            status=worst_status,
            metrics=results,
            message="; ".join(messages) if messages else "All metrics nominal",
        )

    def query_all(self, timespan_minutes: int = 5) -> list[ResourceHealth]:
        """Query all monitored resources."""
        return [self.query_resource(rt, timespan_minutes) for rt in MONITORED_RESOURCES]

    def get_dashboard_summary(self, timespan_minutes: int = 5) -> dict:
        """Get a summary dashboard of all resource health."""
        results = self.query_all(timespan_minutes)
        return {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "overall_status": (
                HealthStatus.UNHEALTHY if any(r.status == HealthStatus.UNHEALTHY for r in results)
                else HealthStatus.DEGRADED if any(r.status == HealthStatus.DEGRADED for r in results)
                else HealthStatus.HEALTHY
            ).value,
            "resources": {
                r.resource_type.value: {
                    "name": r.resource_name,
                    "status": r.status.value,
                    "message": r.message,
                    "metrics": {m.name: m.value for m in r.metrics},
                }
                for r in results
            },
        }

    # ── Async wrappers (run sync Azure SDK calls in thread pool) ──

    async def async_query_resource(self, resource_type: ResourceType, timespan_minutes: int = 5) -> ResourceHealth:
        """Non-blocking wrapper around query_resource."""
        return await asyncio.to_thread(self.query_resource, resource_type, timespan_minutes)

    async def async_query_all(self, timespan_minutes: int = 5) -> list[ResourceHealth]:
        """Non-blocking wrapper around query_all."""
        return await asyncio.to_thread(self.query_all, timespan_minutes)

    async def async_get_dashboard_summary(self, timespan_minutes: int = 5) -> dict:
        """Non-blocking wrapper around get_dashboard_summary."""
        return await asyncio.to_thread(self.get_dashboard_summary, timespan_minutes)
