# Azure Deployment Guide — LLM Observatory

## Prerequisites
- Azure CLI 2.50+
- Bicep installed (`az bicep install`)
- Docker installed
- Access to Azure subscription and resource group creation rights
- Local `.env` values for required secrets

## First-time deployment

### Step 1 — Create resource group
```bash
az login
az group create \
  --name llm-observatory-dev-rg \
  --location eastus
```

### Step 2 — Deploy infrastructure
```bash
az deployment group create \
  --resource-group llm-observatory-dev-rg \
  --template-file infra/bicep/main.bicep \
  --parameters infra/environments/dev.parameters.json \
  --parameters postgresAdminPassword="$(openssl rand -base64 24)"
```

Save deployment outputs such as ACR login server, Key Vault name, and Container App environment.

### Step 3 — Build and push container image
```bash
az acr login --name <ACR_NAME>

docker build -t <ACR_LOGIN_SERVER>/llm-observatory:latest .
docker push <ACR_LOGIN_SERVER>/llm-observatory:latest
```

### Step 4 — Add secrets to Key Vault
```bash
az keyvault secret set \
  --vault-name <KEY_VAULT_NAME> \
  --name openai-api-key \
  --value "$OPENAI_API_KEY"

az keyvault secret set \
  --vault-name <KEY_VAULT_NAME> \
  --name observatory-db-url \
  --value "postgresql+psycopg://<user>:<password>@<host>:5432/observatory"
```

### Step 5 — Configure Container App environment variables
```bash
az containerapp update \
  --name <GATEWAY_CONTAINER_APP> \
  --resource-group llm-observatory-dev-rg \
  --set-env-vars \
    LLM_PROVIDER=azure \
    AZURE_OPENAI_ENDPOINT=https://<your-openai-resource>.openai.azure.com/ \
    AZURE_KEY_VAULT_URL=https://<your-keyvault>.vault.azure.net/ \
    DATABASE_URL="postgresql+psycopg://<user>:<password>@<host>:5432/observatory"
```

### Step 6 — Verify
```bash
curl https://<GATEWAY_FQDN>/health
```
Expected response includes `"status":"ok"`.

## Ongoing deployments
- Build and push a new image tag.
- Update Container App image revision.
- Verify `/health`, `/health/ready`, and `/metrics` before announcing availability.

## Rollback
Use revision rollback steps documented in `RUNBOOK.md`.
