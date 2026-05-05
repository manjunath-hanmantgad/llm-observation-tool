from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from observatory.alerting_service import evaluate_alert_rules
from observatory.audit import write_audit_log
from observatory.database import get_session
from observatory.dependencies import get_current_user, require_engineer
from observatory.models import AlertRule, Incident, Project
from observatory.schemas import AlertRuleCreate, AlertRuleRead, CurrentUser, IncidentRead


router = APIRouter(prefix="/api/v1", tags=["alerts"])


@router.post("/alert-rules", response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED)
def create_alert_rule(
    payload: AlertRuleCreate,
    current_user: Annotated[CurrentUser, Depends(require_engineer)],
    session: Session = Depends(get_session),
) -> AlertRule:
    if payload.project_id:
        project = session.get(Project, payload.project_id)
        if project is None or project.organization_id != current_user.organization_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    rule = AlertRule(
        organization_id=current_user.organization_id,
        project_id=payload.project_id,
        name=payload.name,
        metric=payload.metric,
        threshold=payload.threshold,
        severity=payload.severity,
        channel_type=payload.channel_type,
        suppression_minutes=payload.suppression_minutes,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


@router.get("/alert-rules", response_model=list[AlertRuleRead])
def list_alert_rules(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[AlertRule]:
    return list(
        session.scalars(
            select(AlertRule).where(AlertRule.organization_id == current_user.organization_id).order_by(AlertRule.created_at.desc())
        )
    )


@router.post("/alert-rules/evaluate")
def evaluate_rules_now(
    current_user: Annotated[CurrentUser, Depends(require_engineer)],
    session: Session = Depends(get_session),
) -> dict[str, int]:
    return {"incidents_created": evaluate_alert_rules(session, organization_id=current_user.organization_id)}


@router.get("/incidents", response_model=list[IncidentRead])
def list_incidents(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[Incident]:
    return list(
        session.scalars(
            select(Incident).where(Incident.organization_id == current_user.organization_id).order_by(Incident.triggered_at.desc())
        )
    )


@router.post("/incidents/{incident_id}/acknowledge", response_model=IncidentRead)
def acknowledge_incident(
    incident_id: str,
    current_user: Annotated[CurrentUser, Depends(require_engineer)],
    session: Session = Depends(get_session),
) -> Incident:
    incident = session.get(Incident, incident_id)
    if incident is None or incident.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    if incident.status == "resolved":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resolved incidents cannot be acknowledged.")

    incident.status = "acknowledged"
    write_audit_log(
        session,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        action="incident.acknowledged",
        target_type="incident",
        target_id=incident.id,
    )
    session.commit()
    session.refresh(incident)
    return incident


@router.post("/incidents/{incident_id}/resolve", response_model=IncidentRead)
def resolve_incident(
    incident_id: str,
    current_user: Annotated[CurrentUser, Depends(require_engineer)],
    session: Session = Depends(get_session),
) -> Incident:
    incident = session.get(Incident, incident_id)
    if incident is None or incident.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")

    incident.status = "resolved"
    incident.resolved_at = datetime.now(UTC)
    write_audit_log(
        session,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        action="incident.resolved",
        target_type="incident",
        target_id=incident.id,
    )
    session.commit()
    session.refresh(incident)
    return incident
