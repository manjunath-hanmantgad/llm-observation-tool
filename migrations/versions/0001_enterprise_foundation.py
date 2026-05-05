"""enterprise foundation

Revision ID: 0001_enterprise_foundation
Revises:
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_enterprise_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("prompt_storage_mode", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "email", name="uq_users_org_email"),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "slug", name="uq_projects_org_slug"),
    )
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"])

    op.create_table(
        "endpoints",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "slug", name="uq_endpoints_project_slug"),
    )
    op.create_index("ix_endpoints_organization_id", "endpoints", ["organization_id"])
    op.create_index("ix_endpoints_project_id", "endpoints", ["project_id"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(24), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False),
        sa.Column("scopes", sa.String(512), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_api_keys_organization_id", "api_keys", ["organization_id"])
    op.create_index("ix_api_keys_project_id", "api_keys", ["project_id"])
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])

    op.create_table(
        "llm_provider_models",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("deployment_name", sa.String(128), nullable=False),
        sa.Column("input_cost_per_token", sa.Float(), nullable=False),
        sa.Column("output_cost_per_token", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_provider_models_organization_id", "llm_provider_models", ["organization_id"])

    op.create_table(
        "llm_calls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("endpoint_id", sa.String(36), sa.ForeignKey("endpoints.id"), nullable=True),
        sa.Column("trace_id", sa.String(128), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("session_id", sa.String(128), nullable=False),
        sa.Column("external_user_id", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("deployment_name", sa.String(128), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("prompt_storage_mode", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_code", sa.String(128), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_calls_org_project_time", "llm_calls", ["organization_id", "project_id", "created_at"])
    op.create_index("ix_llm_calls_org_endpoint_time", "llm_calls", ["organization_id", "endpoint_id", "created_at"])
    op.create_index("ix_llm_calls_org_provider_model_time", "llm_calls", ["organization_id", "provider", "model", "created_at"])
    op.create_index("ix_llm_calls_org_status_time", "llm_calls", ["organization_id", "status", "created_at"])
    for column in ["organization_id", "project_id", "endpoint_id", "trace_id", "correlation_id", "session_id", "external_user_id", "provider", "model", "status", "created_at"]:
        op.create_index(f"ix_llm_calls_{column}", "llm_calls", [column])

    op.create_table(
        "token_cost_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("llm_call_id", sa.String(36), sa.ForeignKey("llm_calls.id"), nullable=False, unique=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("cached_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("total_cost_usd", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_token_cost_records_llm_call_id", "token_cost_records", ["llm_call_id"])
    op.create_index("ix_token_cost_records_organization_id", "token_cost_records", ["organization_id"])
    op.create_index("ix_token_cost_records_created_at", "token_cost_records", ["created_at"])

    op.create_table(
        "evaluation_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("evaluator_type", sa.String(64), nullable=False),
        sa.Column("evaluator_version", sa.String(64), nullable=False),
        sa.Column("prompt_template", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_evaluation_jobs_organization_id", "evaluation_jobs", ["organization_id"])
    op.create_index("ix_evaluation_jobs_project_id", "evaluation_jobs", ["project_id"])
    op.create_index("ix_evaluation_jobs_status", "evaluation_jobs", ["status"])

    op.create_table(
        "platform_evaluation_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("llm_call_id", sa.String(36), sa.ForeignKey("llm_calls.id"), nullable=False),
        sa.Column("evaluation_job_id", sa.String(36), sa.ForeignKey("evaluation_jobs.id"), nullable=True),
        sa.Column("faithfulness_score", sa.Float(), nullable=False),
        sa.Column("relevancy_score", sa.Float(), nullable=False),
        sa.Column("hallucination_flag", sa.Boolean(), nullable=False),
        sa.Column("toxicity_flag", sa.Boolean(), nullable=False),
        sa.Column("pii_exposure_flag", sa.Boolean(), nullable=False),
        sa.Column("refusal_quality_score", sa.Float(), nullable=False),
        sa.Column("groundedness_score", sa.Float(), nullable=False),
        sa.Column("judge_reasoning", sa.Text(), nullable=False),
        sa.Column("evaluator_version", sa.String(64), nullable=False),
        sa.Column("judge_model", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_eval_results_org_project_time", "platform_evaluation_results", ["organization_id", "project_id", "created_at"])
    op.create_index("ix_eval_results_org_hallucination_time", "platform_evaluation_results", ["organization_id", "hallucination_flag", "created_at"])
    for column in ["organization_id", "project_id", "llm_call_id", "evaluation_job_id", "hallucination_flag", "created_at"]:
        op.create_index(f"ix_platform_evaluation_results_{column}", "platform_evaluation_results", [column])

    op.create_table(
        "alert_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("channel_type", sa.String(64), nullable=False),
        sa.Column("channel_config_json", sa.Text(), nullable=False),
        sa.Column("suppression_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alert_rules_organization_id", "alert_rules", ["organization_id"])
    op.create_index("ix_alert_rules_project_id", "alert_rules", ["project_id"])

    op.create_table(
        "incidents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("endpoint_id", sa.String(36), sa.ForeignKey("endpoints.id"), nullable=True),
        sa.Column("alert_rule_id", sa.String(36), sa.ForeignKey("alert_rules.id"), nullable=True),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in ["organization_id", "project_id", "endpoint_id", "alert_rule_id", "severity", "status", "triggered_at"]:
        op.create_index(f"ix_incidents_{column}", "incidents", [column])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("target_type", sa.String(128), nullable=False),
        sa.Column("target_id", sa.String(128), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ["organization_id", "actor_user_id", "action", "created_at"]:
        op.create_index(f"ix_audit_logs_{column}", "audit_logs", [column])


def downgrade() -> None:
    for table in [
        "audit_logs",
        "incidents",
        "alert_rules",
        "platform_evaluation_results",
        "evaluation_jobs",
        "token_cost_records",
        "llm_calls",
        "llm_provider_models",
        "api_keys",
        "endpoints",
        "projects",
        "users",
        "organizations",
    ]:
        op.drop_table(table)
