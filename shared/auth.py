from __future__ import annotations

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from shared.config import get_settings


def validate_optional_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> dict:
    settings = get_settings()

    if not settings.azure_tenant_configured:
        return {"user_id": "local-dev-user", "roles": ["AI.Admin"], "mode": "local"}

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required when Entra ID is configured.",
        )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Entra ID validation is a production integration placeholder in this local-first build.",
    )
