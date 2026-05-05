from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from observatory.database import get_session
from observatory.dependencies import get_current_user, require_engineer
from observatory.evaluation_service import create_evaluation_job, run_evaluation_job
from observatory.models import EvaluationJob, EvaluationResult, Project
from observatory.schemas import CurrentUser, EvaluationJobCreate, EvaluationJobRead, EvaluationResultRead


router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])


@router.post("/jobs", response_model=EvaluationJobRead, status_code=status.HTTP_201_CREATED)
def queue_evaluation_job(
    payload: EvaluationJobCreate,
    current_user: Annotated[CurrentUser, Depends(require_engineer)],
    session: Session = Depends(get_session),
) -> EvaluationJob:
    project = session.get(Project, payload.project_id)
    if project is None or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return create_evaluation_job(session, organization_id=current_user.organization_id, project_id=project.id)


@router.post("/jobs/{job_id}/run", response_model=EvaluationJobRead)
def run_job_now(
    job_id: str,
    current_user: Annotated[CurrentUser, Depends(require_engineer)],
    session: Session = Depends(get_session),
) -> EvaluationJob:
    job = session.get(EvaluationJob, job_id)
    if job is None or job.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation job not found.")
    run_evaluation_job(session, job.id)
    session.refresh(job)
    return job


@router.get("/jobs", response_model=list[EvaluationJobRead])
def list_jobs(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[EvaluationJob]:
    return list(
        session.scalars(
            select(EvaluationJob)
            .where(EvaluationJob.organization_id == current_user.organization_id)
            .order_by(EvaluationJob.created_at.desc())
        )
    )


@router.get("/results", response_model=list[EvaluationResultRead])
def list_results(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Session = Depends(get_session),
    project_id: str | None = None,
) -> list[EvaluationResult]:
    stmt = (
        select(EvaluationResult)
        .where(EvaluationResult.organization_id == current_user.organization_id)
        .order_by(EvaluationResult.created_at.desc())
    )
    if project_id:
        stmt = stmt.where(EvaluationResult.project_id == project_id)
    return list(session.scalars(stmt))
