"""Knowledge base for Sales POC SRE operations."""

from src.config import settings


# ──────────────────── Architecture ────────────────────
ARCHITECTURE = {
    "overview": "Sales POC is a multi-tier cloud-native application on Azure for AI-assisted sales workflows.",
    "components": {
        "frontend": {
            "type": "Azure Static Web App",
            "repo": "SalesPOC.UI",
            "description": "React/Next.js frontend hosted on Azure Static Web Apps",
            "dependencies": ["apim", "storage"],
        },
        "api": {
            "type": "Azure App Service",
            "repo": "SalesPOC.API",
            "description": "Backend REST API serving business logic",
            "dependencies": ["sql_db", "cosmos_db", "storage", "foundry"],
        },
        "apim": {
            "type": "Azure API Management",
            "repo": "SalesPOC.APIM",
            "description": "API gateway for routing, rate limiting, and authentication",
            "dependencies": ["api"],
        },
        "apic": {
            "type": "Azure API Center",
            "repo": "SalesPOC.APIC",
            "description": "API catalog and governance",
            "dependencies": ["apim"],
        },
        "mcp": {
            "type": "Model Context Protocol",
            "repo": "SalesPOC.MCP",
            "description": "MCP server bridging AI models to business tools and data",
            "dependencies": ["api", "foundry"],
        },
        "sql_db": {
            "type": "Azure SQL Database",
            "repo": "SalesPOC.DB",
            "description": "Relational database for transactional sales data",
            "dependencies": [],
        },
        "cosmos_db": {
            "type": "Azure Cosmos DB",
            "description": "NoSQL store for product catalog, sessions, and events",
            "dependencies": [],
        },
        "storage": {
            "type": "Azure Storage Account",
            "description": "Blob/file storage for documents, exports, and media",
            "dependencies": [],
        },
        "foundry": {
            "type": "Azure AI Foundry",
            "repo": "SalesPOC.AI",
            "description": "AI model hosting (GPT, embeddings) for sales intelligence",
            "dependencies": [],
        },
        "vnet": {
            "type": "Azure Virtual Network",
            "description": "Network isolation for Sales POC resources (mymsx-vnet, vnet-salespoc-westus2)",
            "dependencies": [],
        },
        "nsg": {
            "type": "Azure Network Security Group",
            "description": "Network traffic filtering for VNet subnets (app, appservice, private-endpoints)",
            "dependencies": ["vnet"],
        },
        "private_endpoint": {
            "type": "Azure Private Endpoint",
            "description": "Private connectivity to Storage, Cosmos DB, and SQL via VNet (pe-blob, pe-cosmos, pe-sql)",
            "dependencies": ["vnet", "nsg", "storage", "cosmos_db", "sql_db"],
        },
    },
    "data_flow": [
        "User -> Frontend (Static Web App)",
        "Frontend -> APIM (API Gateway)",
        "APIM -> API (App Service)",
        "API -> SQL Database (transactional data)",
        "API -> Cosmos DB (catalog, events)",
        "API -> Storage Account (documents)",
        "API -> AI Foundry (AI inference)",
        "MCP -> API + AI Foundry (tool bridge)",
        "API -> Private Endpoint (pe-sql-westus2) -> SQL Database",
        "API -> Private Endpoint (pe-cosmos-westus2) -> Cosmos DB",
        "API -> Private Endpoint (pe-blob-westus2) -> Storage Account",
        "NSGs -> VNet subnets (traffic filtering)",
    ],
}


# ──────────────────── Troubleshooting Guides ────────────────────
TROUBLESHOOTING = {
    "sql_db": {
        "high_dtu": {
            "symptoms": ["Slow queries", "Timeouts", "DTU > 80%"],
            "causes": ["Missing indexes", "Table scans", "Large transactions", "Blocking queries"],
            "resolution": [
                "Run: SELECT TOP 10 * FROM sys.dm_exec_query_stats ORDER BY total_worker_time DESC",
                "Check missing indexes: sys.dm_db_missing_index_details",
                "Consider scaling to higher service tier",
                "Review and optimize the most expensive queries",
            ],
        },
        "connection_issues": {
            "symptoms": ["Connection refused", "Login failed", "Timeout connecting"],
            "causes": ["Firewall rules", "Max connection limit", "Connection pool exhaustion", "AAD token expiry"],
            "resolution": [
                "Verify firewall: az sql server firewall-rule list",
                "Check sessions: SELECT COUNT(*) FROM sys.dm_exec_sessions",
                "Restart API to reset connection pool",
                "Verify managed identity permissions",
            ],
        },
    },
    "cosmos_db": {
        "throttling": {
            "symptoms": ["HTTP 429 responses", "Request rate too large", "Increased latency"],
            "causes": ["Exceeding provisioned RUs", "Hot partitions", "Cross-partition queries"],
            "resolution": [
                "Enable autoscale on the container",
                "Review partition key for even distribution",
                "Add composite indexes for frequent queries",
                "Use change feed instead of frequent polling",
            ],
        },
        "high_ru_cost": {
            "symptoms": ["Higher than expected RU consumption"],
            "causes": ["Missing indexes", "Large document reads", "Fan-out queries"],
            "resolution": [
                "Add composite indexes for multi-field queries",
                "Use projection to limit returned fields",
                "Prefer point reads (id + partition key) over queries",
            ],
        },
    },
    "api": {
        "5xx_errors": {
            "symptoms": ["HTTP 500 errors", "Service unavailable", "Internal server error"],
            "causes": ["Unhandled exceptions", "Downstream failures", "Memory/CPU exhaustion", "Deployment issues"],
            "resolution": [
                "Check App Insights exceptions: az monitor app-insights query",
                "Verify downstream service connectivity (SQL, Cosmos, Storage)",
                f"Restart: az webapp restart --name {settings.api_app_service_name}",
                "Check for recent deployments that may have introduced bugs",
            ],
        },
        "slow_responses": {
            "symptoms": ["Response times > 1s", "User-reported slowness"],
            "causes": ["N+1 queries", "Missing caching", "Large payloads", "Downstream latency"],
            "resolution": [
                "Profile with App Insights dependency tracking",
                "Add Redis cache for frequent queries",
                "Implement response pagination",
                "Check SQL and Cosmos latency metrics",
            ],
        },
    },
    "apim": {
        "capacity_issues": {
            "symptoms": ["Increased latency at gateway", "Capacity metric > 70%"],
            "causes": ["Traffic spike", "Complex policies", "Insufficient units"],
            "resolution": [
                "Add APIM capacity units: az apim update --sku-capacity 2",
                "Review and simplify request/response policies",
                "Enable response caching for GET endpoints",
                "Configure rate limiting to protect backend",
            ],
        },
        "auth_failures": {
            "symptoms": ["401 Unauthorized spikes", "Subscription key errors"],
            "causes": ["Expired keys", "Wrong audience in JWT", "IP restrictions"],
            "resolution": [
                "Regenerate subscription keys if compromised",
                "Verify JWT validation policy audience and issuer",
                "Review IP filter policies",
            ],
        },
    },
    "foundry": {
        "model_errors": {
            "symptoms": ["AI calls returning errors", "Increased TotalErrors"],
            "causes": ["Model deployment issues", "Quota exceeded", "Invalid prompts", "Region outage"],
            "resolution": [
                "Check model status: az cognitiveservices account deployment list",
                "Verify TPM/RPM quota is not exceeded",
                "Review recent prompt changes for invalid content",
                "Try failover to alternate region deployment",
            ],
        },
        "high_latency": {
            "symptoms": ["AI responses taking > 3s", "User-perceived slowness"],
            "causes": ["Large prompts", "High max_tokens", "Model congestion", "Regional load"],
            "resolution": [
                "Reduce prompt length with summarization",
                "Lower max_tokens for predictable outputs",
                "Implement streaming responses",
                "Cache frequent prompt/response pairs",
            ],
        },
    },
    "frontend": {
        "deployment_issues": {
            "symptoms": ["404 on routes", "Stale content", "Function API errors"],
            "causes": ["Failed SWA deployment", "Route misconfiguration", "API link broken"],
            "resolution": [
                "Check SWA deployment status in GitHub Actions",
                "Verify staticwebapp.config.json route rules",
                "Check linked API backend in SWA configuration",
                "Clear CDN cache if content is stale",
            ],
        },
    },
    "storage": {
        "access_issues": {
            "symptoms": ["403 Forbidden", "Blob not found", "Authorization failure"],
            "causes": ["SAS token expired", "RBAC misconfigured", "Container access policy"],
            "resolution": [
                "Check managed identity role assignments",
                "Regenerate SAS tokens if needed",
                "Verify container access level settings",
                "Review network rules and private endpoints",
            ],
        },
    },
    "vnet": {
        "ddos_attack": {
            "symptoms": ["IfUnderDDoSAttack metric = 1", "High packet/byte drop rates", "Service degradation"],
            "causes": ["Volumetric DDoS attack", "Protocol-level attack", "Application-layer attack"],
            "resolution": [
                "Verify DDoS Protection Standard is enabled on the VNet",
                "Review DDoS mitigation reports in Azure Portal",
                "Check NSG rules to block known attack source IPs",
                "Contact Azure Support for large-scale attacks",
                "Enable flow logs to analyze traffic patterns",
            ],
        },
        "connectivity_issues": {
            "symptoms": ["Services unreachable via VNet", "Subnet routing failures", "Peering down"],
            "causes": ["NSG blocking traffic", "UDR misconfiguration", "VNet peering disconnected", "Address space conflict"],
            "resolution": [
                "Check NSG rules on relevant subnets",
                "Verify route tables and next-hop configurations",
                "Check VNet peering status: az network vnet peering list",
                "Verify address spaces don't overlap between peered VNets",
            ],
        },
    },
    "nsg": {
        "rule_misconfiguration": {
            "symptoms": ["Legitimate traffic blocked", "Unexpected denied flows spike", "Service connectivity lost"],
            "causes": ["Overly restrictive deny rules", "Missing allow rules", "Priority ordering issues", "Unauthorized rule changes"],
            "resolution": [
                "Review NSG effective security rules: az network nsg show",
                "Check flow logs for denied traffic patterns",
                "Verify rule priorities (lower number = higher priority)",
                "Restore rules from ARM template if unauthorized changes detected",
            ],
        },
    },
    "private_endpoint": {
        "connection_failure": {
            "symptoms": ["Private endpoint connection state not Approved", "DNS resolution fails", "Cannot reach linked resource"],
            "causes": ["Connection manually rejected", "Private DNS zone misconfigured", "NSG blocking PE subnet traffic", "Linked resource deleted/moved"],
            "resolution": [
                "Check PE connection state: az network private-endpoint show",
                "Verify private DNS zone records resolve to correct private IP",
                "Ensure NSG on PE subnet allows traffic to linked resource",
                "Re-create private endpoint connection if rejected",
            ],
        },
        "dns_resolution": {
            "symptoms": ["Public IP returned instead of private IP", "Connection timeouts from VNet"],
            "causes": ["Private DNS zone not linked to VNet", "DNS record missing", "Custom DNS server not forwarding"],
            "resolution": [
                "Verify private DNS zone is linked to the VNet",
                "Check A records in private DNS zone for the PE",
                "If using custom DNS, ensure conditional forwarding to Azure DNS (168.63.129.16)",
            ],
        },
    },
}


# ──────────────────── Operational Procedures ────────────────────
OPERATIONAL_PROCEDURES = {
    "daily_health_check": {
        "description": "Daily review of all Sales POC resource health",
        "steps": [
            "Run full health dashboard scan",
            "Review overnight incidents and alerts",
            "Check GitHub repo CI/CD pipeline statuses",
            "Verify all Azure resources are in running/ok state",
            "Review cost trends in Azure Cost Management",
        ],
    },
    "deployment_verification": {
        "description": "Post-deployment verification checklist",
        "steps": [
            "Verify container/app provisioning state is Succeeded",
            "Run health check endpoint",
            "Verify API responses for critical endpoints",
            "Check Application Insights for new exceptions",
            "Monitor error rates for 15 minutes post-deploy",
            "Verify database migrations completed (if applicable)",
        ],
    },
    "scaling_procedure": {
        "description": "Scaling resources up or out in response to load",
        "steps": [
            "Identify the bottleneck resource (CPU, memory, DTU, RU)",
            "Determine if scale-up or scale-out is appropriate",
            "Apply scaling change via CLI or Bicep update",
            "Monitor metrics for 10 minutes to verify improvement",
            "Document the change and reason in incident log",
        ],
    },
    "incident_response": {
        "description": "Standard incident response procedure",
        "steps": [
            "Acknowledge the incident within 5 minutes",
            "Classify severity (SEV1-4) based on impact",
            "Execute the relevant runbook steps",
            "Communicate status to stakeholders",
            "Document root cause and resolution",
            "Schedule post-incident review if SEV1 or SEV2",
        ],
    },
    "backup_verification": {
        "description": "Verify backup integrity for data stores",
        "steps": [
            "Check SQL Database automated backup status",
            "Verify Cosmos DB continuous backup is active",
            "Confirm Storage Account soft delete is enabled",
            "Test point-in-time restore capability quarterly",
        ],
    },
}


# ──────────────────── Azure Resource Reference ────────────────────
AZURE_RESOURCE_MAP = {
    "subscription_id": settings.azure_subscription_id,
    "resource_group": settings.azure_resource_group,
    "region": settings.azure_region,
    "resources": {
        "sql_server": settings.sql_server_name,
        "sql_database": settings.sql_database_name,
        "cosmos_account": settings.cosmos_account_name,
        "storage_account": settings.storage_account_name,
        "api_app_service": settings.api_app_service_name,
        "apim_service": settings.apim_service_name,
        "ai_foundry": settings.ai_foundry_name,
        "frontend_app_service": settings.frontend_app_service_name,
        "sre_agent": settings.agent_name,
        "app_insights": settings.app_insights_resource,
    },
}
