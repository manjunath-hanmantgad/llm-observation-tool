from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from observatory.audit import write_audit_log
from observatory.database import get_session
from observatory.dependencies import require_owner_or_admin
from observatory.models import ApiKey, Project
from observatory.schemas import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyRead, CurrentUser
from observatory.security import generate_api_key


router = APIRouter(prefix="/api/v1/api-keys", tags=["api keys"])


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreate,
    current_user: Annotated[CurrentUser, Depends(require_owner_or_admin)],
    session: Session = Depends(get_session),
) -> ApiKeyCreateResponse:
    if payload.project_id:
        project = session.get(Project, payload.project_id)
        if project is None or project.organization_id != current_user.organization_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    raw_key, prefix, key_hash = generate_api_key()
    api_key = ApiKey(
        organization_id=current_user.organization_id,
        project_id=payload.project_id,
        name=payload.name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=payload.scopes,
        created_by_user_id=current_user.user_id,
    )
    session.add(api_key)
    session.flush()
    write_audit_log(
        session,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        action="api_key.created",
        target_type="api_key",
        target_id=api_key.id,
        metadata={"key_prefix": prefix},
    )
    session.commit()
    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        api_key=raw_key,
        scopes=api_key.scopes,
    )


@router.get("", response_model=list[ApiKeyRead])
def list_api_keys(
    current_user: Annotated[CurrentUser, Depends(require_owner_or_admin)],
    session: Session = Depends(get_session),
) -> list[ApiKeyRead]:
    keys = session.scalars(select(ApiKey).where(ApiKey.organization_id == current_user.organization_id)).all()
    return [
        ApiKeyRead(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            scopes=key.scopes,
            project_id=key.project_id,
            revoked_at=key.revoked_at,
            created_at=key.created_at,
        )
        for key in keys
    ]


@router.delete("/{api_key_id}")
def revoke_api_key(
    api_key_id: str,
    current_user: Annotated[CurrentUser, Depends(require_owner_or_admin)],
    session: Session = Depends(get_session),
) -> dict[str, str]:
    api_key = session.get(ApiKey, api_key_id)
    if api_key is None or api_key.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")

    api_key.revoked_at = datetime.now(UTC)
    write_audit_log(
        session,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        action="api_key.revoked",
        target_type="api_key",
        target_id=api_key.id,
    )
    session.commit()
    return {"status": "revoked"}
