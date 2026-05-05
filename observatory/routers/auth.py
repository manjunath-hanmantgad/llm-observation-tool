from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from observatory.audit import write_audit_log
from observatory.database import get_session
from observatory.models import Organization, User
from observatory.schemas import LoginRequest, RegisterRequest, TokenResponse
from observatory.security import create_access_token, hash_password, verify_password


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: Session = Depends(get_session)) -> TokenResponse:
    existing_org = session.scalar(select(Organization).where(Organization.slug == payload.organization_slug))
    if existing_org is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization slug already exists.")

    organization = Organization(name=payload.organization_name, slug=payload.organization_slug)
    session.add(organization)
    session.flush()

    user = User(
        organization_id=organization.id,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role="owner",
    )
    session.add(user)
    session.flush()
    write_audit_log(
        session,
        organization_id=organization.id,
        actor_user_id=user.id,
        action="organization.registered",
        target_type="organization",
        target_id=organization.id,
    )
    session.commit()

    return TokenResponse(access_token=create_access_token(user.id, organization.id, user.role))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    organization = session.scalar(select(Organization).where(Organization.slug == payload.organization_slug))
    if organization is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    user = session.scalar(
        select(User).where(User.organization_id == organization.id, User.email == payload.email.lower())
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    user.last_login_at = datetime.now(UTC)
    write_audit_log(
        session,
        organization_id=organization.id,
        actor_user_id=user.id,
        action="user.login",
        target_type="user",
        target_id=user.id,
    )
    session.commit()
    return TokenResponse(access_token=create_access_token(user.id, organization.id, user.role))
