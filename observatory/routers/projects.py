from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from observatory.audit import write_audit_log
from observatory.database import get_session
from observatory.dependencies import get_current_user, require_engineer
from observatory.models import Endpoint, Project
from observatory.schemas import CurrentUser, EndpointCreate, EndpointRead, ProjectCreate, ProjectRead


router = APIRouter(prefix="/api/v1", tags=["projects"])


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    current_user: Annotated[CurrentUser, Depends(require_engineer)],
    session: Session = Depends(get_session),
) -> Project:
    existing = session.scalar(
        select(Project).where(Project.organization_id == current_user.organization_id, Project.slug == payload.slug)
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project slug already exists.")

    project = Project(
        organization_id=current_user.organization_id,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
    )
    session.add(project)
    session.flush()
    write_audit_log(
        session,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        action="project.created",
        target_type="project",
        target_id=project.id,
    )
    session.commit()
    return project


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[Project]:
    return list(session.scalars(select(Project).where(Project.organization_id == current_user.organization_id)))


@router.post("/endpoints", response_model=EndpointRead, status_code=status.HTTP_201_CREATED)
def create_endpoint(
    payload: EndpointCreate,
    current_user: Annotated[CurrentUser, Depends(require_engineer)],
    session: Session = Depends(get_session),
) -> Endpoint:
    project = session.get(Project, payload.project_id)
    if project is None or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    existing = session.scalar(
        select(Endpoint).where(Endpoint.project_id == project.id, Endpoint.slug == payload.slug)
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Endpoint slug already exists.")

    endpoint = Endpoint(
        organization_id=current_user.organization_id,
        project_id=project.id,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
    )
    session.add(endpoint)
    session.flush()
    write_audit_log(
        session,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        action="endpoint.created",
        target_type="endpoint",
        target_id=endpoint.id,
    )
    session.commit()
    return endpoint
