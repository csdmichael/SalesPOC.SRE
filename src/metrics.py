"""Metric definitions and thresholds for Sales POC SRE monitoring."""

from dataclasses import dataclass


@dataclass
class MetricDefinition:
    name: str
    display_name: str
    unit: str
    description: str
    warn_threshold: float | None = None
    crit_threshold: float | None = None
    higher_is_worse: bool = True


# ──────────────────── SQL Database Metrics ────────────────────
SQL_DB_METRICS = [
    MetricDefinition("dtu_consumption_percent", "DTU Consumption", "%", "Database Throughput Unit usage", 70, 90),
    MetricDefinition("cpu_percent", "CPU Usage", "%", "CPU utilization percentage", 70, 90),
    MetricDefinition("storage_percent", "Storage Usage", "%", "Storage space consumed", 75, 90),
    MetricDefinition("connection_failed", "Failed Connections", "count", "Failed connection attempts", 5, 20),
    MetricDefinition("deadlock", "Deadlocks", "count", "Deadlock occurrences", 1, 5),
    MetricDefinition("sessions_percent", "Active Sessions", "%", "Percentage of allowed sessions in use", 70, 90),
    MetricDefinition("workers_percent", "Active Workers", "%", "Percentage of allowed workers in use", 70, 90),
]

# ──────────────────── Cosmos DB Metrics ────────────────────
COSMOS_DB_METRICS = [
    MetricDefinition("TotalRequestUnits", "RU Consumption", "RU/s", "Total Request Units consumed", 800, 950),
    MetricDefinition("TotalRequests", "Total Requests", "count", "Total number of requests"),
    MetricDefinition("Http429", "Throttled Requests (429)", "count", "Rate-limited requests", 10, 50),
    MetricDefinition("AvailableStorage", "Available Storage", "bytes", "Remaining storage capacity"),
    MetricDefinition("ReplicationLatency", "Replication Latency", "ms", "Geo-replication lag", 100, 500),
    MetricDefinition("NormalizedRUConsumption", "Normalized RU %", "%", "RU consumption as percent of provisioned", 70, 90),
]

# ──────────────────── Storage Account Metrics ────────────────────
STORAGE_METRICS = [
    MetricDefinition("Availability", "Availability", "%", "Service availability percentage", 99.5, 99.0, higher_is_worse=False),
    MetricDefinition("SuccessE2ELatency", "E2E Latency", "ms", "End-to-end request latency", 100, 500),
    MetricDefinition("SuccessServerLatency", "Server Latency", "ms", "Server processing latency", 50, 200),
    MetricDefinition("Transactions", "Transactions", "count", "Total storage transactions"),
    MetricDefinition("UsedCapacity", "Used Capacity", "bytes", "Storage capacity consumed"),
    MetricDefinition("Egress", "Egress", "bytes", "Data transferred out"),
    MetricDefinition("Ingress", "Ingress", "bytes", "Data transferred in"),
]

# ──────────────────── API (App Service) Metrics ────────────────────
API_METRICS = [
    MetricDefinition("HttpResponseTime", "Response Time", "seconds", "Average HTTP response time", 1.0, 3.0),
    MetricDefinition("Http5xx", "Server Errors (5xx)", "count", "HTTP 500-level errors", 5, 20),
    MetricDefinition("Http4xx", "Client Errors (4xx)", "count", "HTTP 400-level errors", 50, 200),
    MetricDefinition("Requests", "Total Requests", "count", "Total HTTP requests served"),
    MetricDefinition("CpuPercentage", "CPU %", "%", "CPU utilization", 70, 90),
    MetricDefinition("MemoryPercentage", "Memory %", "%", "Memory utilization", 75, 90),
    MetricDefinition("HealthCheckStatus", "Health Check", "%", "Health check pass rate", 90, 50, higher_is_worse=False),
]

# ──────────────────── APIM Metrics ────────────────────
APIM_METRICS = [
    MetricDefinition("TotalRequests", "Total Requests", "count", "Total API gateway requests"),
    MetricDefinition("FailedRequests", "Failed Requests", "count", "Requests returning errors", 10, 50),
    MetricDefinition("BackendDuration", "Backend Duration", "ms", "Backend response time", 1000, 5000),
    MetricDefinition("Capacity", "Gateway Capacity", "%", "APIM capacity utilization", 70, 90),
    MetricDefinition("UnauthorizedRequests", "Unauthorized (401)", "count", "Unauthorized requests", 20, 100),
    MetricDefinition("OtherRequests", "Other Requests", "count", "Non-2xx/4xx/5xx responses"),
]

# ──────────────────── AI Foundry Metrics ────────────────────
FOUNDRY_METRICS = [
    MetricDefinition("TotalCalls", "Total Calls", "count", "Total AI model invocations"),
    MetricDefinition("TotalErrors", "Total Errors", "count", "Failed AI calls", 5, 20),
    MetricDefinition("Latency", "Latency", "ms", "Average inference latency", 2000, 5000),
    MetricDefinition("TokenTransaction", "Token Usage", "count", "Total tokens processed"),
    MetricDefinition("SuccessRate", "Success Rate", "%", "Percentage of successful calls", 95, 90, higher_is_worse=False),
    MetricDefinition("ProcessedPromptTokens", "Prompt Tokens", "count", "Input tokens processed"),
    MetricDefinition("GeneratedCompletionTokens", "Completion Tokens", "count", "Output tokens generated"),
]

# ──────────────────── Frontend (Static Web App) Metrics ────────────────────
FRONTEND_METRICS = [
    MetricDefinition("BytesSent", "Bytes Sent", "bytes", "Total response bytes"),
    MetricDefinition("FunctionErrors", "Function Errors", "count", "SWA API function errors", 5, 20),
    MetricDefinition("RequestCount", "Request Count", "count", "Total requests served"),
]

# ──────────────────── VNet Metrics ────────────────────
VNET_METRICS = [
    MetricDefinition("IfUnderDDoSAttack", "DDoS Attack", "bool", "Whether the VNet is under DDoS attack", 1, 1),
    MetricDefinition("BytesDroppedDDoS", "DDoS Bytes Dropped", "bytes", "Bytes dropped by DDoS protection"),
    MetricDefinition("PacketsInDDoS", "DDoS Packets In", "count", "Inbound packets during DDoS"),
    MetricDefinition("PacketsDroppedDDoS", "DDoS Packets Dropped", "count", "Packets dropped by DDoS protection"),
    MetricDefinition("BytesInDDoS", "DDoS Bytes In", "bytes", "Inbound bytes during DDoS"),
    MetricDefinition("BytesForwardedDDoS", "DDoS Bytes Forwarded", "bytes", "Bytes forwarded after DDoS mitigation"),
]

# ──────────────────── NSG Metrics ────────────────────
NSG_METRICS = [
    MetricDefinition("AllowedFlows", "Allowed Flows", "count", "Number of allowed network flows"),
    MetricDefinition("DeniedFlows", "Denied Flows", "count", "Number of denied network flows", 50, 200),
    MetricDefinition("AllowedFlowsPerRule", "Allowed Flows Per Rule", "count", "Allowed flows broken down by rule"),
    MetricDefinition("DeniedFlowsPerRule", "Denied Flows Per Rule", "count", "Denied flows broken down by rule"),
]

# ──────────────────── Private Endpoint Metrics ────────────────────
PRIVATE_ENDPOINT_METRICS = [
    MetricDefinition("PEBytesIn", "Bytes In", "bytes", "Bytes received by the private endpoint"),
    MetricDefinition("PEBytesOut", "Bytes Out", "bytes", "Bytes sent from the private endpoint"),
]

# ──────────────────── SLA Targets ────────────────────
SLA_TARGETS = {
    "sql_db": {"availability": 99.99, "response_time_ms": 100},
    "cosmos_db": {"availability": 99.999, "latency_ms": 10},
    "storage": {"availability": 99.9, "latency_ms": 60},
    "api": {"availability": 99.95, "response_time_ms": 500},
    "apim": {"availability": 99.95, "response_time_ms": 1000},
    "foundry": {"availability": 99.9, "latency_ms": 3000},
    "frontend": {"availability": 99.95, "response_time_ms": 200},
    "vnet": {"availability": 99.99},
    "nsg": {"availability": 99.99},
    "private_endpoint": {"availability": 99.99},
}
