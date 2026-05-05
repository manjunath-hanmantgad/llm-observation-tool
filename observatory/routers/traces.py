from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from observatory.database import get_session
from observatory.dependencies import get_current_user
from observatory.models import EvaluationResult, Incident, LlmCall, TokenCostRecord
from observatory.schemas import (
    CurrentUser,
    EvaluationResultRead,
    IncidentRead,
    LlmCallLogRead,
    PaginatedLlmCalls,
    TraceDetail,
)


router = APIRouter(prefix="/api/v1", tags=["logs and traces"])


@router.get("/llm-calls", response_model=PaginatedLlmCalls)
def list_llm_calls(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Session = Depends(get_session),
    project_id: str | None = None,
    endpoint_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> PaginatedLlmCalls:
    base = (
        select(LlmCall, TokenCostRecord)
        .join(TokenCostRecord, TokenCostRecord.llm_call_id == LlmCall.id, isouter=True)
        .where(LlmCall.organization_id == current_user.organization_id)
    )
    count_stmt = select(func.count(LlmCall.id)).where(LlmCall.organization_id == current_user.organization_id)

    filters = []
    if project_id:
        filters.append(LlmCall.project_id == project_id)
    if endpoint_id:
        filters.append(LlmCall.endpoint_id == endpoint_id)
    if provider:
        filters.append(LlmCall.provider == provider)
    if model:
        filters.append(LlmCall.model == model)
    if status_filter:
        filters.append(LlmCall.status == status_filter)
    if search:
        filters.append(
            or_(
                LlmCall.trace_id.contains(search),
                LlmCall.prompt.contains(search),
                LlmCall.response.contains(search),
                LlmCall.error_message.contains(search),
            )
        )

    for condition in filters:
        base = base.where(condition)
        count_stmt = count_stmt.where(condition)

    rows = session.execute(base.order_by(LlmCall.created_at.desc()).limit(limit).offset(offset)).all()
    total = session.scalar(count_stmt) or 0
    return PaginatedLlmCalls(
        items=[to_call_log(call, cost) for call, cost in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/traces/{trace_id}", response_model=TraceDetail)
def get_trace_detail(
    trace_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> TraceDetail:
    row = session.execute(
        select(LlmCall, TokenCostRecord)
        .join(TokenCostRecord, TokenCostRecord.llm_call_id == LlmCall.id, isouter=True)
        .where(LlmCall.organization_id == current_user.organization_id, LlmCall.trace_id == trace_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found.")

    call, cost = row
    evaluations = list(
        session.scalars(
            select(EvaluationResult)
            .where(EvaluationResult.organization_id == current_user.organization_id, EvaluationResult.llm_call_id == call.id)
            .order_by(EvaluationResult.created_at.desc())
        )
    )
    incidents = list(
        session.scalars(
            select(Incident)
            .where(Incident.organization_id == current_user.organization_id, Incident.project_id == call.project_id)
            .order_by(Incident.triggered_at.desc())
        )
    )
    return TraceDetail(
        call=to_call_log(call, cost),
        prompt=call.prompt,
        response=call.response,
        error_code=call.error_code,
        error_message=call.error_message,
        metadata=json.loads(call.metadata_json or "{}"),
        evaluations=[EvaluationResultRead.model_validate(result) for result in evaluations],
        incidents=[IncidentRead.model_validate(incident) for incident in incidents],
    )


def to_call_log(call: LlmCall, cost: TokenCostRecord | None) -> LlmCallLogRead:
    return LlmCallLogRead(
        id=call.id,
        project_id=call.project_id,
        endpoint_id=call.endpoint_id,
        trace_id=call.trace_id,
        correlation_id=call.correlation_id,
        session_id=call.session_id,
        user_id=call.external_user_id,
        provider=call.provider,
        model=call.model,
        status=call.status,
        latency_ms=call.latency_ms,
        prompt_tokens=cost.prompt_tokens if cost else 0,
        completion_tokens=cost.completion_tokens if cost else 0,
        total_cost_usd=cost.total_cost_usd if cost else 0.0,
        created_at=call.created_at,
    )
