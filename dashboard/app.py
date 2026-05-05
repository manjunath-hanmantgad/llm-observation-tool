from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import func, select

sys.path.append(str(Path(__file__).resolve().parents[1]))

from observatory.database import SessionLocal, init_platform_db
from observatory.demo_data import DEMO_EMAIL, DEMO_PASSWORD, seed_demo_workspace
from observatory.audit import write_audit_log
from observatory.models import (
    AlertRule,
    ApiKey,
    AuditLog,
    Endpoint,
    EvaluationResult,
    Incident,
    LlmCall,
    Organization,
    Project,
    TokenCostRecord,
    User,
)
from observatory.security import generate_api_key, verify_password


st.set_page_config(page_title="LLM Observatory", layout="wide")
init_platform_db()

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
      [data-testid="stMetric"] {background: #ffffff; border: 1px solid #e5e7eb; padding: 14px; border-radius: 6px;}
      div[data-testid="stSidebar"] {background: #0f172a;}
      div[data-testid="stSidebar"] * {color: #f8fafc;}
      .section-label {font-size: 0.78rem; color: #64748b; text-transform: uppercase; letter-spacing: 0; font-weight: 700;}
    </style>
    """,
    unsafe_allow_html=True,
)


def session_get(key: str, default=None):
    return st.session_state.get(key, default)


def set_auth(user: User, organization: Organization) -> None:
    st.session_state["user_id"] = user.id
    st.session_state["organization_id"] = organization.id
    st.session_state["user_email"] = user.email
    st.session_state["organization_name"] = organization.name
    st.session_state["role"] = user.role


def current_context(session):
    user_id = session_get("user_id")
    org_id = session_get("organization_id")
    if not user_id or not org_id:
        return None, None
    return session.get(User, user_id), session.get(Organization, org_id)


def auth_screen() -> None:
    st.title("LLM Observatory")
    st.caption("Enterprise LLM observability for quality, cost, latency, and incidents.")
    left, right = st.columns([1.1, 0.9])

    with left:
        st.subheader("Start with demo data")
        st.write(
            "Create a local organization with sample projects, API key, LLM traces, evaluations, "
            "an alert rule, and an open incident."
        )
        if st.button("Load demo workspace", type="primary"):
            with SessionLocal() as session:
                result = seed_demo_workspace(session)
                user = session.get(User, result["user_id"])
                organization = session.get(Organization, result["organization_id"])
                set_auth(user, organization)
                if result["api_key"]:
                    st.session_state["last_api_key"] = result["api_key"]
            st.rerun()

        st.info(f"Demo login: `{DEMO_EMAIL}` / `{DEMO_PASSWORD}`")

    with right:
        tab_login, tab_register = st.tabs(["Login", "Register"])
        with tab_login:
            org_slug = st.text_input("Organization slug", value="demo-observatory")
            email = st.text_input("Email", value=DEMO_EMAIL)
            password = st.text_input("Password", value=DEMO_PASSWORD, type="password")
            if st.button("Login"):
                with SessionLocal() as session:
                    organization = session.scalar(select(Organization).where(Organization.slug == org_slug))
                    user = None
                    if organization:
                        user = session.scalar(
                            select(User).where(User.organization_id == organization.id, User.email == email.lower())
                        )
                    if user and verify_password(password, user.password_hash):
                        set_auth(user, organization)
                        st.rerun()
                    st.error("Invalid organization, email, or password.")

        with tab_register:
            st.write("Use the API for full registration flow, or load demo data for dashboard review.")
            st.code("POST /api/v1/auth/register", language="http")


def org_projects(session, organization_id: str) -> list[Project]:
    return list(session.scalars(select(Project).where(Project.organization_id == organization_id).order_by(Project.name)))


def org_endpoints(session, organization_id: str, project_id: str | None = None) -> list[Endpoint]:
    stmt = select(Endpoint).where(Endpoint.organization_id == organization_id).order_by(Endpoint.name)
    if project_id:
        stmt = stmt.where(Endpoint.project_id == project_id)
    return list(session.scalars(stmt))


def calls_dataframe(session, organization_id: str, project_id: str | None, endpoint_id: str | None) -> pd.DataFrame:
    stmt = (
        select(
            LlmCall.id,
            LlmCall.created_at,
            LlmCall.trace_id,
            LlmCall.provider,
            LlmCall.model,
            LlmCall.status,
            LlmCall.latency_ms,
            LlmCall.prompt,
            LlmCall.response,
            LlmCall.error_code,
            Project.name.label("project"),
            Endpoint.name.label("endpoint"),
            TokenCostRecord.prompt_tokens,
            TokenCostRecord.completion_tokens,
            TokenCostRecord.total_cost_usd,
        )
        .join(Project, Project.id == LlmCall.project_id)
        .join(Endpoint, Endpoint.id == LlmCall.endpoint_id, isouter=True)
        .join(TokenCostRecord, TokenCostRecord.llm_call_id == LlmCall.id, isouter=True)
        .where(LlmCall.organization_id == organization_id)
        .order_by(LlmCall.created_at.desc())
    )
    if project_id:
        stmt = stmt.where(LlmCall.project_id == project_id)
    if endpoint_id:
        stmt = stmt.where(LlmCall.endpoint_id == endpoint_id)
    return pd.DataFrame(session.execute(stmt).mappings().all())


def evaluations_dataframe(session, organization_id: str, project_id: str | None) -> pd.DataFrame:
    stmt = (
        select(
            EvaluationResult.created_at,
            EvaluationResult.llm_call_id,
            EvaluationResult.faithfulness_score,
            EvaluationResult.relevancy_score,
            EvaluationResult.groundedness_score,
            EvaluationResult.hallucination_flag,
            EvaluationResult.toxicity_flag,
            EvaluationResult.pii_exposure_flag,
            EvaluationResult.judge_reasoning,
            LlmCall.trace_id,
            Endpoint.name.label("endpoint"),
        )
        .join(LlmCall, LlmCall.id == EvaluationResult.llm_call_id)
        .join(Endpoint, Endpoint.id == LlmCall.endpoint_id, isouter=True)
        .where(EvaluationResult.organization_id == organization_id)
        .order_by(EvaluationResult.created_at.desc())
    )
    if project_id:
        stmt = stmt.where(EvaluationResult.project_id == project_id)
    return pd.DataFrame(session.execute(stmt).mappings().all())


def sidebar_filters(session, organization_id: str):
    st.sidebar.title("LLM Observatory")
    st.sidebar.caption(session_get("organization_name"))
    st.sidebar.divider()

    projects = org_projects(session, organization_id)
    project_options = {"All projects": None} | {project.name: project.id for project in projects}
    project_name = st.sidebar.selectbox("Project", list(project_options.keys()))
    project_id = project_options[project_name]

    endpoints = org_endpoints(session, organization_id, project_id)
    endpoint_options = {"All endpoints": None} | {endpoint.name: endpoint.id for endpoint in endpoints}
    endpoint_name = st.sidebar.selectbox("Endpoint", list(endpoint_options.keys()))
    endpoint_id = endpoint_options[endpoint_name]

    page = st.sidebar.radio(
        "Navigation",
        [
            "Overview",
            "Projects",
            "Request Logs",
            "Trace Detail",
            "Evaluations",
            "Alert Rules",
            "Incidents",
            "API Keys",
            "Settings",
        ],
    )
    st.sidebar.divider()
    if st.sidebar.button("Sign out"):
        st.session_state.clear()
        st.rerun()
    return page, project_id, endpoint_id


def overview(session, organization_id: str, project_id: str | None, endpoint_id: str | None) -> None:
    calls = calls_dataframe(session, organization_id, project_id, endpoint_id)
    evals = evaluations_dataframe(session, organization_id, project_id)

    st.title("Overview")
    st.caption("Operational health across LLM features and providers.")

    total_calls = len(calls)
    failed = int((calls["status"] != "success").sum()) if not calls.empty else 0
    avg_latency = float(calls["latency_ms"].mean()) if not calls.empty else 0
    total_cost = float(calls["total_cost_usd"].fillna(0).sum()) if not calls.empty else 0
    hallucination_rate = float(evals["hallucination_flag"].mean()) if not evals.empty else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Calls", total_calls)
    c2.metric("Error Rate", f"{(failed / total_calls) if total_calls else 0:.1%}")
    c3.metric("Avg Latency", f"{avg_latency:.0f} ms")
    c4.metric("Total Cost", f"${total_cost:.6f}")
    c5.metric("Hallucination", f"{hallucination_rate:.1%}")

    if calls.empty:
        st.info("No platform calls found. Load demo data from the login screen or ingest calls using an API key.")
        return

    left, right = st.columns(2)
    with left:
        st.subheader("Latency by Endpoint")
        fig = px.line(calls.sort_values("created_at"), x="created_at", y="latency_ms", color="endpoint", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Cost by Endpoint")
        cost = calls.groupby("endpoint", dropna=False, as_index=False)["total_cost_usd"].sum()
        fig = px.bar(cost, x="endpoint", y="total_cost_usd")
        st.plotly_chart(fig, use_container_width=True)


def projects_view(session, organization_id: str) -> None:
    st.title("Projects")
    projects = org_projects(session, organization_id)
    st.dataframe(
        pd.DataFrame([{"id": p.id, "name": p.name, "slug": p.slug, "description": p.description} for p in projects]),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Create project"):
        name = st.text_input("Project name")
        slug = st.text_input("Project slug")
        description = st.text_area("Description")
        if st.button("Create project"):
            if not name or not slug:
                st.error("Name and slug are required.")
            else:
                project = Project(organization_id=organization_id, name=name, slug=slug, description=description)
                session.add(project)
                session.commit()
                st.success("Project created.")
                st.rerun()


def request_logs(session, organization_id: str, project_id: str | None, endpoint_id: str | None) -> None:
    st.title("Request Logs")
    calls = calls_dataframe(session, organization_id, project_id, endpoint_id)
    if calls.empty:
        st.info("No request logs match the current filters.")
        return

    search = st.text_input("Search trace, prompt, response, or error")
    status = st.selectbox("Status", ["all"] + sorted(calls["status"].dropna().unique().tolist()))
    page_size = st.selectbox("Rows", [10, 25, 50], index=1)

    filtered = calls.copy()
    if status != "all":
        filtered = filtered[filtered["status"] == status]
    if search:
        haystack = filtered[["trace_id", "prompt", "response", "error_code"]].fillna("").agg(" ".join, axis=1)
        filtered = filtered[haystack.str.contains(search, case=False, regex=False)]

    st.dataframe(
        filtered.head(page_size)[
            [
                "created_at",
                "trace_id",
                "project",
                "endpoint",
                "provider",
                "model",
                "status",
                "latency_ms",
                "prompt_tokens",
                "completion_tokens",
                "total_cost_usd",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


def trace_detail(session, organization_id: str) -> None:
    st.title("Trace Detail")
    trace_id = st.text_input("Trace ID", value="trace-demo-004")
    if not trace_id:
        return
    calls = calls_dataframe(session, organization_id, None, None)
    row = calls[calls["trace_id"] == trace_id] if not calls.empty else pd.DataFrame()
    if row.empty:
        st.info("Trace not found.")
        return
    record = row.iloc[0]
    st.metric("Latency", f"{record['latency_ms']} ms")
    st.metric("Status", record["status"])
    st.subheader("Prompt")
    st.code(record["prompt"] or "", language="text")
    st.subheader("Response")
    st.code(record["response"] or "", language="text")


def evaluations_view(session, organization_id: str, project_id: str | None) -> None:
    st.title("Quality Evaluations")
    evals = evaluations_dataframe(session, organization_id, project_id)
    if evals.empty:
        st.info("No evaluation results found.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Avg Faithfulness", f"{evals['faithfulness_score'].mean():.2f}")
    c2.metric("Avg Relevancy", f"{evals['relevancy_score'].mean():.2f}")
    c3.metric("Hallucination Rate", f"{evals['hallucination_flag'].mean():.1%}")
    st.dataframe(evals, use_container_width=True, hide_index=True)


def alert_rules_view(session, organization_id: str, project_id: str | None) -> None:
    st.title("Alert Rules")
    stmt = select(AlertRule).where(AlertRule.organization_id == organization_id)
    if project_id:
        stmt = stmt.where(AlertRule.project_id == project_id)
    rules = list(session.scalars(stmt))
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "name": r.name,
                    "metric": r.metric,
                    "threshold": r.threshold,
                    "severity": r.severity,
                    "channel": r.channel_type,
                    "active": r.is_active,
                    "suppression_minutes": r.suppression_minutes,
                }
                for r in rules
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Create alert rule"):
        name = st.text_input("Rule name", value="Latency p95 above 2s")
        metric = st.selectbox("Metric", ["hallucination_rate", "latency_p95_ms", "error_rate", "cost_spike"])
        threshold = st.number_input("Threshold", min_value=0.0, value=0.2)
        severity = st.selectbox("Severity", ["info", "warning", "critical"])
        if st.button("Create alert rule"):
            session.add(
                AlertRule(
                    organization_id=organization_id,
                    project_id=project_id,
                    name=name,
                    metric=metric,
                    threshold=threshold,
                    severity=severity,
                )
            )
            session.commit()
            st.success("Alert rule created.")
            st.rerun()


def incidents_view(session, organization_id: str, project_id: str | None, user_id: str) -> None:
    st.title("Incidents")
    stmt = select(Incident).where(Incident.organization_id == organization_id).order_by(Incident.triggered_at.desc())
    if project_id:
        stmt = stmt.where(Incident.project_id == project_id)
    incidents = list(session.scalars(stmt))
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "triggered_at": i.triggered_at,
                    "severity": i.severity,
                    "status": i.status,
                    "summary": i.summary,
                    "resolved_at": i.resolved_at,
                }
                for i in incidents
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    active_incidents = [incident for incident in incidents if incident.status in {"open", "acknowledged"}]
    if active_incidents:
        st.subheader("Incident actions")
        incident_options = {f"{i.severity.upper()} - {i.summary[:80]} ({i.status})": i for i in active_incidents}
        selected_label = st.selectbox("Select incident", list(incident_options))
        selected_incident = incident_options[selected_label]
        col_ack, col_resolve = st.columns(2)
        with col_ack:
            if st.button("Acknowledge incident", disabled=selected_incident.status == "acknowledged"):
                selected_incident.status = "acknowledged"
                write_audit_log(
                    session,
                    organization_id=organization_id,
                    actor_user_id=user_id,
                    action="incident.acknowledged",
                    target_type="incident",
                    target_id=selected_incident.id,
                )
                session.commit()
                st.success("Incident acknowledged.")
                st.rerun()
        with col_resolve:
            if st.button("Resolve incident", type="primary"):
                selected_incident.status = "resolved"
                selected_incident.resolved_at = datetime.now(UTC)
                write_audit_log(
                    session,
                    organization_id=organization_id,
                    actor_user_id=user_id,
                    action="incident.resolved",
                    target_type="incident",
                    target_id=selected_incident.id,
                )
                session.commit()
                st.success("Incident resolved.")
                st.rerun()
    else:
        st.info("No active incidents for the selected filters.")


def api_keys_view(session, organization_id: str, user_id: str, projects: list[Project]) -> None:
    st.title("API Keys")
    keys = list(session.scalars(select(ApiKey).where(ApiKey.organization_id == organization_id)))
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "name": k.name,
                    "prefix": k.key_prefix,
                    "project_id": k.project_id,
                    "scopes": k.scopes,
                    "created_at": k.created_at,
                    "revoked_at": k.revoked_at,
                }
                for k in keys
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    if session_get("last_api_key"):
        st.warning("Demo API key shown once. Store it securely if you intend to use it.")
        st.code(session_get("last_api_key"), language="text")
    st.subheader("Create API key")
    with st.form("create_api_key_form"):
        name = st.text_input("Key name", value="Production ingestion key")
        project_labels = ["Organization-wide"] + [project.name for project in projects]
        project_label = st.selectbox("Scope", project_labels)
        scopes = st.text_input("Scopes", value="ingest:write")
        submitted = st.form_submit_button("Create key", type="primary")
    if submitted:
        project_id = None
        if project_label != "Organization-wide":
            project_id = next(project.id for project in projects if project.name == project_label)
        raw_key, prefix, key_hash = generate_api_key()
        api_key = ApiKey(
            organization_id=organization_id,
            project_id=project_id,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=scopes,
            created_by_user_id=user_id,
        )
        session.add(api_key)
        session.flush()
        write_audit_log(
            session,
            organization_id=organization_id,
            actor_user_id=user_id,
            action="api_key.created",
            target_type="api_key",
            target_id=api_key.id,
            metadata={"key_prefix": prefix},
        )
        session.commit()
        st.session_state["last_api_key"] = raw_key
        st.success("API key created. Copy it now; only the prefix is stored after this view.")
        st.rerun()

    active_keys = [key for key in keys if key.revoked_at is None]
    if active_keys:
        st.subheader("Revoke API key")
        key_options = {f"{key.name} ({key.key_prefix})": key for key in active_keys}
        selected_key_label = st.selectbox("Active key", list(key_options))
        selected_key = key_options[selected_key_label]
        if st.button("Revoke selected key"):
            selected_key.revoked_at = datetime.now(UTC)
            write_audit_log(
                session,
                organization_id=organization_id,
                actor_user_id=user_id,
                action="api_key.revoked",
                target_type="api_key",
                target_id=selected_key.id,
            )
            session.commit()
            st.success("API key revoked.")
            st.rerun()


def settings_view(session, organization: Organization) -> None:
    st.title("Settings")
    st.write("Organization")
    st.json(
        {
            "id": organization.id,
            "name": organization.name,
            "slug": organization.slug,
            "retention_days": organization.retention_days,
            "prompt_storage_mode": organization.prompt_storage_mode,
        }
    )
    st.subheader("Audit Log")
    logs = list(
        session.scalars(
            select(AuditLog).where(AuditLog.organization_id == organization.id).order_by(AuditLog.created_at.desc())
        )
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "created_at": log.created_at,
                    "action": log.action,
                    "target_type": log.target_type,
                    "target_id": log.target_id,
                }
                for log in logs
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )


with SessionLocal() as session:
    user, organization = current_context(session)
    if user is None or organization is None:
        auth_screen()
        st.stop()

    page, selected_project_id, selected_endpoint_id = sidebar_filters(session, organization.id)

    if page == "Overview":
        overview(session, organization.id, selected_project_id, selected_endpoint_id)
    elif page == "Projects":
        projects_view(session, organization.id)
    elif page == "Request Logs":
        request_logs(session, organization.id, selected_project_id, selected_endpoint_id)
    elif page == "Trace Detail":
        trace_detail(session, organization.id)
    elif page == "Evaluations":
        evaluations_view(session, organization.id, selected_project_id)
    elif page == "Alert Rules":
        alert_rules_view(session, organization.id, selected_project_id)
    elif page == "Incidents":
        incidents_view(session, organization.id, selected_project_id, user.id)
    elif page == "API Keys":
        api_keys_view(session, organization.id, user.id, org_projects(session, organization.id))
    elif page == "Settings":
        settings_view(session, organization)
