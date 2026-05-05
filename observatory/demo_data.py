from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from observatory.audit import write_audit_log
from observatory.models import (
    AlertRule,
    ApiKey,
    AuditLog,
    Endpoint,
    EvaluationJob,
    EvaluationResult,
    Incident,
    LlmCall,
    Organization,
    Project,
    TokenCostRecord,
    User,
)
from observatory.security import generate_api_key, hash_password


DEMO_PASSWORD = "correct-horse-battery-staple"
DEMO_EMAIL = "owner@demo.local"
DEMO_ORG_SLUG = "demo-observatory"


def reset_demo_workspace(session: Session) -> int:
    organization = session.scalar(select(Organization).where(Organization.slug == DEMO_ORG_SLUG))
    if organization is None:
        return 0

    org_id = organization.id
    deleted = 0
    for model in [
        AuditLog,
        Incident,
        AlertRule,
        EvaluationResult,
        EvaluationJob,
        TokenCostRecord,
        LlmCall,
        ApiKey,
        Endpoint,
        Project,
        User,
        Organization,
    ]:
        query = session.query(model)
        if model is Organization:
            count = query.filter(model.id == org_id).delete(synchronize_session=False)
        else:
            count = query.filter(model.organization_id == org_id).delete(synchronize_session=False)
        deleted += count
    session.commit()
    return deleted


def seed_demo_workspace(session: Session) -> dict[str, str]:
    organization = session.scalar(select(Organization).where(Organization.slug == DEMO_ORG_SLUG))
    raw_api_key = ""

    if organization is None:
        organization = Organization(name="Demo Observatory", slug=DEMO_ORG_SLUG, prompt_storage_mode="redacted")
        session.add(organization)
        session.flush()

        user = User(
            organization_id=organization.id,
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            role="owner",
        )
        session.add(user)
        session.flush()
        write_audit_log(
            session,
            organization_id=organization.id,
            actor_user_id=user.id,
            action="demo.workspace_created",
            target_type="organization",
            target_id=organization.id,
        )
    else:
        user = session.scalar(select(User).where(User.organization_id == organization.id, User.email == DEMO_EMAIL))
        if user is None:
            user = User(
                organization_id=organization.id,
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                role="owner",
            )
            session.add(user)
            session.flush()

    project = session.scalar(select(Project).where(Project.organization_id == organization.id, Project.slug == "customer-ai"))
    if project is None:
        project = Project(
            organization_id=organization.id,
            name="Customer AI Platform",
            slug="customer-ai",
            description="Support, sales, and research LLM traffic for demo operations.",
        )
        session.add(project)
        session.flush()

    endpoints = {}
    for name, slug in [
        ("Support Assistant", "support-assistant"),
        ("Sales Copilot", "sales-copilot"),
        ("Research Assistant", "research-assistant"),
    ]:
        endpoint = session.scalar(select(Endpoint).where(Endpoint.project_id == project.id, Endpoint.slug == slug))
        if endpoint is None:
            endpoint = Endpoint(organization_id=organization.id, project_id=project.id, name=name, slug=slug)
            session.add(endpoint)
            session.flush()
        endpoints[slug] = endpoint

    api_key = session.scalar(select(ApiKey).where(ApiKey.organization_id == organization.id, ApiKey.name == "Demo ingestion key"))
    if api_key is None:
        raw_api_key, prefix, key_hash = generate_api_key()
        api_key = ApiKey(
            organization_id=organization.id,
            project_id=project.id,
            name="Demo ingestion key",
            key_prefix=prefix,
            key_hash=key_hash,
            scopes="ingest:write",
            created_by_user_id=user.id,
        )
        session.add(api_key)

    existing_calls = session.scalar(select(LlmCall).where(LlmCall.project_id == project.id))
    if existing_calls is None:
        _seed_calls(session, organization.id, project.id, endpoints)
        _seed_alerts(session, organization.id, project.id, endpoints["research-assistant"].id)

    session.commit()
    return {
        "organization_id": organization.id,
        "project_id": project.id,
        "user_id": user.id,
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD,
        "api_key": raw_api_key,
    }


def _seed_calls(session: Session, organization_id: str, project_id: str, endpoints: dict[str, Endpoint]) -> None:
    job = EvaluationJob(
        organization_id=organization_id,
        project_id=project_id,
        status="succeeded",
        evaluator_type="heuristic",
        evaluator_version="demo-v1",
        prompt_template="Demo heuristic evaluator with hallucination and relevancy checks.",
        started_at=datetime.now(UTC) - timedelta(minutes=9),
        completed_at=datetime.now(UTC) - timedelta(minutes=8),
    )
    session.add(job)
    session.flush()

    samples = [
        ("support-assistant", "trace-demo-001", "success", 412, 148, 46, 0.000049, False, 0.91, 0.88),
        ("support-assistant", "trace-demo-002", "success", 533, 190, 61, 0.000064, False, 0.86, 0.84),
        ("sales-copilot", "trace-demo-003", "success", 820, 244, 95, 0.000093, False, 0.89, 0.81),
        ("research-assistant", "trace-demo-004", "success", 1240, 310, 132, 0.000129, True, 0.22, 0.74),
        ("research-assistant", "trace-demo-005", "error", 2100, 80, 0, 0.000012, False, 0.0, 0.0),
        ("support-assistant", "trace-demo-006", "success", 468, 160, 54, 0.000055, False, 0.93, 0.9),
    ]

    for idx, (endpoint_slug, trace_id, status, latency, prompt_tokens, completion_tokens, cost, hallucination, faithfulness, relevancy) in enumerate(samples):
        endpoint = endpoints[endpoint_slug]
        call = LlmCall(
            organization_id=organization_id,
            project_id=project_id,
            endpoint_id=endpoint.id,
            trace_id=trace_id,
            correlation_id=f"corr-demo-{idx + 1:03d}",
            session_id=f"session-demo-{idx + 1:03d}",
            external_user_id=f"user-{idx + 1:03d}",
            provider="mock",
            model="mock-observatory-model",
            deployment_name="local-demo",
            prompt=f"Demo prompt for {endpoint.name}",
            response=(
                "Unsupported lunar claim generated for evaluation demo."
                if hallucination
                else f"Grounded demo response for {endpoint.name}."
            ),
            status=status,
            error_code="provider_timeout" if status == "error" else "",
            error_message="Provider timeout after retry budget exhausted." if status == "error" else "",
            latency_ms=latency,
            retry_count=1 if status == "error" else 0,
            metadata_json=json.dumps({"environment": "demo", "source": "seed"}),
            created_at=datetime.now(UTC) - timedelta(minutes=30 - idx * 4),
        )
        session.add(call)
        session.flush()
        session.add(
            TokenCostRecord(
                llm_call_id=call.id,
                organization_id=organization_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                total_cost_usd=cost,
                created_at=call.created_at,
            )
        )
        session.add(
            EvaluationResult(
                organization_id=organization_id,
                project_id=project_id,
                llm_call_id=call.id,
                evaluation_job_id=job.id,
                faithfulness_score=faithfulness,
                relevancy_score=relevancy,
                hallucination_flag=hallucination,
                toxicity_flag=False,
                pii_exposure_flag=False,
                refusal_quality_score=0.82 if not hallucination else 0.4,
                groundedness_score=faithfulness,
                judge_reasoning=(
                    "Response includes unsupported factual claim and should be reviewed."
                    if hallucination
                    else "Response appears relevant and operationally acceptable for the demo scenario."
                ),
                evaluator_version="demo-v1",
                judge_model="mock-judge",
                created_at=call.created_at + timedelta(seconds=30),
            )
        )


def _seed_alerts(session: Session, organization_id: str, project_id: str, endpoint_id: str) -> None:
    rule = AlertRule(
        organization_id=organization_id,
        project_id=project_id,
        name="Hallucination rate above 20%",
        metric="hallucination_rate",
        threshold=0.2,
        severity="critical",
        channel_type="console",
        suppression_minutes=30,
    )
    session.add(rule)
    session.flush()
    session.add(
        Incident(
            organization_id=organization_id,
            project_id=project_id,
            endpoint_id=endpoint_id,
            alert_rule_id=rule.id,
            severity="critical",
            status="open",
            summary="Research Assistant exceeded hallucination threshold in the demo time window.",
            triggered_at=datetime.now(UTC) - timedelta(minutes=10),
        )
    )
