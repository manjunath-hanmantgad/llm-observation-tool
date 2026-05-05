from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from observatory.database import get_session
from observatory.models import ApiKey, User
from observatory.rbac import Role, ensure_role
from observatory.schemas import CurrentUser
from observatory.security import decode_access_token, hash_api_key


bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[Session, Depends(get_session)],
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required.")

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token.") from exc

    user = session.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive or missing.")

    if user.organization_id != payload.get("org"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token organization mismatch.")

    return CurrentUser(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        role=user.role,
    )


def require_owner_or_admin(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    ensure_role(current_user.role, Role.ADMIN)
    return current_user


def require_engineer(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    ensure_role(current_user.role, Role.ENGINEER)
    return current_user


def get_api_key_context(
    session: Annotated[Session, Depends(get_session)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> ApiKey:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-API-Key header required.")

    key_hash = hash_api_key(x_api_key)
    api_key = session.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
    if api_key is None or api_key.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key.")
    return api_key
