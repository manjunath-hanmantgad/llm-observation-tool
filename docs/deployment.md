# Forward Deployment Guide

This project is intentionally local-first and Azure-ready. Local mode is suitable for development, demonstrations, and architecture review. Azure mode is intended for production deployment once cloud credentials are available.

## Local Deployment

1. Copy `.env.example` to `.env`.
2. Keep `LLM_PROVIDER=mock` for a no-key demo, or set `LLM_PROVIDER=openai` and provide `OPENAI_API_KEY`.
3. Install dependencies with Python 3.11+.
4. Initialize and seed data.
5. Run the gateway and dashboard.

```bash
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python storage/db.py
python demo/seed_data.py
uvicorn gateway.gateway:app --reload --port 8001
streamlit run dashboard/app.py --server.port 8501
```

## Optional Docker Deployment

Docker is optional for local development. The verified public-release path is the Python local mode documented above. Docker Compose is included for environment parity with PostgreSQL-backed deployment and can be verified when Docker is available.

```bash
cp .env.example .env
docker compose up --build
```

Gateway: `http://localhost:8001`

Dashboard: `http://localhost:8501`

The Compose topology includes:

- PostgreSQL
- FastAPI gateway/API
- Streamlit dashboard
- evaluation worker command container
- alert worker command container

## Azure Deployment Path

Azure credentials are not required for local mode. They are required only for production deployment.

Required Azure services:

- Azure OpenAI for chat and evaluation models
- Azure Container Apps for gateway and dashboard containers
- Azure Key Vault for secrets
- Application Insights for cloud telemetry
- Cosmos DB or Azure PostgreSQL for production metrics storage
- Azure Container Registry for images

Required environment variables:

```env
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EVAL_DEPLOYMENT=gpt-4o-mini
APPLICATIONINSIGHTS_CONNECTION_STRING=your_connection_string
AZURE_KEY_VAULT_URL=https://your-vault.vault.azure.net/
COSMOS_URL=your_cosmos_url
COSMOS_KEY=your_cosmos_key
```

Production storage adapters can be added behind the same repository interface used by local DuckDB. The current implementation keeps Azure storage variables as explicit placeholders so the repository remains safe to publish before cloud setup.
