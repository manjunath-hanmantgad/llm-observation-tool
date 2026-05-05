import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock").lower()
    storage_mode: str = os.getenv("STORAGE_MODE", "local").lower()
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///storage/observatory.db")
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "local-dev-secret-change-me")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "llm-observatory")
    jwt_access_token_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "30"))
    api_key_pepper: str = os.getenv("API_KEY_PEPPER", "local-dev-pepper-change-me")
    cors_allowed_origins: str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:8501,http://localhost:8510")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")
    openai_eval_model: str = os.getenv("OPENAI_EVAL_MODEL", "gpt-4o-mini")

    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_key: str = os.getenv("AZURE_OPENAI_KEY", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    azure_openai_chat_deployment: str = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
    azure_openai_eval_deployment: str = os.getenv("AZURE_OPENAI_EVAL_DEPLOYMENT", "gpt-4o-mini")
    azure_tenant_id: str = os.getenv("AZURE_TENANT_ID", "")
    azure_client_id: str = os.getenv("AZURE_CLIENT_ID", "")

    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")
    applicationinsights_connection_string: str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
    hallucination_rate_threshold: float = float(os.getenv("ALERT_HALLUCINATION_RATE_THRESHOLD", "0.20"))
    avg_latency_ms_threshold: float = float(os.getenv("ALERT_AVG_LATENCY_MS_THRESHOLD", "2500"))

    @property
    def azure_tenant_configured(self) -> bool:
        return bool(self.azure_tenant_id and self.azure_client_id)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def require_provider_credentials(settings: Settings) -> None:
    if settings.llm_provider == "openai" and not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")

    if settings.llm_provider == "azure":
        missing = [
            name
            for name, value in {
                "AZURE_OPENAI_ENDPOINT": settings.azure_openai_endpoint,
                "AZURE_OPENAI_KEY": settings.azure_openai_key,
                "AZURE_OPENAI_CHAT_DEPLOYMENT": settings.azure_openai_chat_deployment,
                "AZURE_OPENAI_EVAL_DEPLOYMENT": settings.azure_openai_eval_deployment,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Azure OpenAI mode is selected but required variables are missing: "
                + ", ".join(missing)
            )
