# SRE Agent: sre-poc-ai-my

Azure SRE Agent deployed to East US 2 via GitHub Actions.

## Resource Details

| Property | Value |
|---|---|
| **Name** | `sre-poc-ai-my` |
| **Subscription** | ME-MngEnvMCAP829495-myaacoub-1 (`86b37969-9445-49cf-b03f-d8866235171c`) |
| **Resource Group** | `ai-myaacoub` |
| **Region** | East US 2 |
| **Agent Endpoint** | `https://sre-poc-ai-my--618da5b9.daa74423.eastus2.azuresre.ai` |
| **Managed Identity** | `sre-poc-ai-my-bvrrtvop7umme` |
| **App Insights** | `sre-poc-ai-my-b8bc7f81-ab86-app-insights` |

## Project Structure

```
├── .github/workflows/deploy.yml   # CI/CD pipeline
├── infra/
│   ├── main.bicep                 # Infrastructure as Code
│   └── main.bicepparam            # Bicep parameters
├── src/
│   ├── __init__.py
│   ├── agent.py                   # SRE agent logic
│   ├── config.py                  # Configuration / settings
│   └── main.py                    # Entry point
├── Dockerfile
├── requirements.txt
└── .env.example
```

## GitHub Actions Setup

The workflow requires these **repository secrets**:

| Secret | Description |
|---|---|
| `AZURE_CLIENT_ID` | Service principal / federated credential client ID |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `APP_INSIGHTS_CONNECTION_STRING` | Application Insights connection string |

### Configure OIDC for GitHub Actions

1. Create an Azure AD app registration or use an existing service principal.
2. Add a federated credential for your GitHub repository (`repo:<owner>/<repo>:ref:refs/heads/main`).
3. Grant the service principal **Contributor** role on resource group `ai-myaacoub`.
4. Set the three secrets above in your GitHub repository settings.

## Local Development

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your values

# Run agent
python -m src.main
```

## Deployment

Pushing to `main` triggers the GitHub Actions workflow which:

1. **Build** – Lints code, builds Docker image, pushes to GHCR.
2. **Deploy** – Logs into Azure via OIDC, deploys Bicep template to `ai-myaacoub` resource group.
