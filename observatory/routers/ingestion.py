from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from observatory.database import get_session
from observatory.dependencies import get_api_key_context, get_current_user
from observatory.models import ApiKey, Endpoint, LlmCall, Project, TokenCostRecord
from observatory.schemas import CurrentUser, IngestLlmCallRequest, IngestLlmCallResponse, MetricsSummary
from observatory.security import redact_text


router = APIRouter(prefix="/api/v1", tags=["ingestion"])


@router.post("/ingest/llm-calls", response_model=IngestLlmCallResponse, status_code=status.HTTP_201_CREATED)
def ingest_llm_call(
    payload: IngestLlmCallRequest,
    api_key: Annotated[ApiKey, Depends(get_api_key_context)],
    session: Session = Depends(get_session),
) -> IngestLlmCallResponse:
    project = session.get(Project, payload.project_id)
    if project is None or project.organization_id != api_key.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    if api_key.project_id and api_key.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key is not scoped to this project.")

    endpoint = None
    if payload.endpoint_id:
        endpoint = session.get(Endpoint, payload.endpoint_id)
        if endpoint is None or endpoint.organization_id != api_key.organization_id or endpoint.project_id != project.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found.")

    storage_mode = payload.prompt_storage_mode
    call = LlmCall(
        organization_id=api_key.organization_id,
        project_id=project.id,
        endpoint_id=endpoint.id if endpoint else None,
        trace_id=payload.trace_id,
        correlation_id=payload.correlation_id,
        session_id=payload.session_id,
        external_user_id=payload.user_id,
        provider=payload.provider,
        model=payload.model,
        deployment_name=payload.deployment_name,
        prompt=redact_text(payload.prompt, storage_mode),
        response=redact_text(payload.response, storage_mode),
        prompt_storage_mode=storage_mode,
        status=payload.status,
        error_code=payload.error_code,
        error_message=payload.error_message,
        latency_ms=payload.latency_ms,
        retry_count=payload.retry_count,
        metadata_json=json.dumps(payload.metadata),
    )
    session.add(call)
    session.flush()
    session.add(
        TokenCostRecord(
            llm_call_id=call.id,
            organization_id=api_key.organization_id,
            prompt_tokens=payload.prompt_tokens,
            completion_tokens=payload.completion_tokens,
            cached_tokens=payload.cached_tokens,
            total_tokens=payload.prompt_tokens + payload.completion_tokens + payload.cached_tokens,
            total_cost_usd=payload.total_cost_usd,
        )
    )
    session.commit()
    return IngestLlmCallResponse(id=call.id, trace_id=call.trace_id)


@router.get("/metrics/summary", response_model=MetricsSummary)
def metrics_summary(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Session = Depends(get_session),
    project_id: str | None = Query(default=None),
) -> MetricsSummary:
    stmt = (
        select(
            func.count(LlmCall.id),
            func.coalesce(func.sum(TokenCostRecord.total_cost_usd), 0.0),
            func.coalesce(func.avg(LlmCall.latency_ms), 0.0),
            func.sum((LlmCall.status != "success").cast(Integer)),
        )
        .select_from(LlmCall)
        .join(TokenCostRecord, TokenCostRecord.llm_call_id == LlmCall.id, isouter=True)
        .where(LlmCall.organization_id == current_user.organization_id)
    )
    if project_id:
        stmt = stmt.where(LlmCall.project_id == project_id)

    total_calls, total_cost, avg_latency, failed_calls = session.execute(stmt).one()
    return MetricsSummary(
        total_calls=total_calls or 0,
        failed_calls=failed_calls or 0,
        avg_latency_ms=round(float(avg_latency or 0), 2),
        total_cost_usd=round(float(total_cost or 0), 8),
    )
