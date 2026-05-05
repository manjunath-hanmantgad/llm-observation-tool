from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from observatory.models import AlertRule, EvaluationResult, Incident, LlmCall, TokenCostRecord


def evaluate_alert_rules(session: Session, *, organization_id: str | None = None) -> int:
    stmt = select(AlertRule).where(AlertRule.is_active.is_(True))
    if organization_id:
        stmt = stmt.where(AlertRule.organization_id == organization_id)
    rules = list(session.scalars(stmt))

    created = 0
    for rule in rules:
        value = metric_value(session, rule)
        if value is None or value <= rule.threshold:
            continue
        if has_recent_open_incident(session, rule):
            continue
        session.add(
            Incident(
                organization_id=rule.organization_id,
                project_id=rule.project_id,
                alert_rule_id=rule.id,
                severity=rule.severity,
                status="open",
                summary=f"{rule.metric} value {value:.4f} exceeded threshold {rule.threshold:.4f}.",
                triggered_at=datetime.now(UTC),
            )
        )
        created += 1
    session.commit()
    return created


def metric_value(session: Session, rule: AlertRule) -> float | None:
    since = datetime.now(UTC) - timedelta(hours=24)
    if rule.metric == "hallucination_rate":
        stmt = select(func.avg(EvaluationResult.hallucination_flag.cast(Integer))).where(
            EvaluationResult.organization_id == rule.organization_id,
            EvaluationResult.created_at >= since,
        )
        if rule.project_id:
            stmt = stmt.where(EvaluationResult.project_id == rule.project_id)
        value = session.scalar(stmt)
        return float(value) if value is not None else None

    if rule.metric == "error_rate":
        stmt = select(func.avg((LlmCall.status != "success").cast(Integer))).where(
            LlmCall.organization_id == rule.organization_id,
            LlmCall.created_at >= since,
        )
        if rule.project_id:
            stmt = stmt.where(LlmCall.project_id == rule.project_id)
        value = session.scalar(stmt)
        return float(value) if value is not None else None

    if rule.metric == "latency_p95_ms":
        stmt = select(LlmCall.latency_ms).where(LlmCall.organization_id == rule.organization_id, LlmCall.created_at >= since)
        if rule.project_id:
            stmt = stmt.where(LlmCall.project_id == rule.project_id)
        values = sorted(float(v) for v in session.scalars(stmt) if v is not None)
        if not values:
            return None
        index = min(len(values) - 1, int(round((len(values) - 1) * 0.95)))
        return values[index]

    if rule.metric == "cost_spike":
        stmt = (
            select(func.coalesce(func.sum(TokenCostRecord.total_cost_usd), 0.0))
            .select_from(TokenCostRecord)
            .join(LlmCall, LlmCall.id == TokenCostRecord.llm_call_id)
            .where(TokenCostRecord.organization_id == rule.organization_id, TokenCostRecord.created_at >= since)
        )
        if rule.project_id:
            stmt = stmt.where(LlmCall.project_id == rule.project_id)
        return float(session.scalar(stmt) or 0)

    return None


def has_recent_open_incident(session: Session, rule: AlertRule) -> bool:
    since = datetime.now(UTC) - timedelta(minutes=rule.suppression_minutes)
    existing = session.scalar(
        select(Incident).where(
            Incident.alert_rule_id == rule.id,
            Incident.status.in_(("open", "acknowledged")),
            Incident.triggered_at >= since,
        )
    )
    return existing is not None
