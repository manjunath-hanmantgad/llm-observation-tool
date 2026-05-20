# Infrastructure — LLM Observatory

## Prerequisites
- Azure CLI (`az`): `brew install azure-cli`
- Bicep CLI: `az bicep install`
- Access to an Azure subscription

## Deploy (dev)

```bash
az login

az group create --name llm-observatory-dev-rg --location eastus

az deployment group create \
  --resource-group llm-observatory-dev-rg \
  --template-file infra/bicep/main.bicep \
  --parameters infra/environments/dev.parameters.json \
  --parameters postgresAdminPassword="$(openssl rand -base64 24)"
```

## Outputs
After deployment, the CLI prints:
- `gatewayUrl` — public HTTPS URL for the FastAPI gateway
- `dashboardUrl` — public HTTPS URL for the Streamlit dashboard
- `acrLoginServer` — push container images here
- `keyVaultUri` — store production secrets here

## Environment separation
| Environment | Min replicas | SKU | Notes |
|---|---|---|---|
| dev | 0 (scales to zero) | Standard_B1ms | Cheapest; stops when idle |
| staging | 1 | Standard_B1ms | Always-on for demo |
| prod | 2 | Standard_D2s_v3 | HA, private endpoints |

## Containers
This deployment provisions four Container Apps:
- `gateway` (FastAPI, ingress on port 8001)
- `dashboard` (Streamlit, ingress on port 8501)
- `evaluation-worker` (no ingress)
- `alert-worker` (no ingress)

## Secrets
Store production values in Key Vault and wire them into Container Apps as secret references:
- `JWT_SECRET_KEY`
- `API_KEY_PEPPER`
- `OPENAI_API_KEY` or `AZURE_OPENAI_KEY`
- `SLACK_WEBHOOK_URL`
