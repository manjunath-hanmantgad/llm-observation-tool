from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    organization_slug: str = Field(pattern=r"^[a-z0-9-]{2,100}$")
    email: EmailStr
    password: str = Field(min_length=10, max_length=256)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    organization_slug: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    user_id: str
    organization_id: str
    email: str
    role: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9-]{2,100}$")
    description: str = ""


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    slug: str
    description: str
    created_at: datetime


class EndpointCreate(BaseModel):
    project_id: str
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9-]{2,100}$")
    description: str = ""


class EndpointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    project_id: str
    name: str
    slug: str
    description: str
    created_at: datetime


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    project_id: str | None = None
    scopes: str = "ingest:write"


class ApiKeyCreateResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    api_key: str
    scopes: str


class ApiKeyRead(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: str
    project_id: str | None
    revoked_at: datetime | None
    created_at: datetime


class IngestLlmCallRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    project_id: str
    endpoint_id: str | None = None
    trace_id: str = Field(min_length=1, max_length=128)
    correlation_id: str = ""
    session_id: str = ""
    user_id: str = ""
    provider: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=128)
    deployment_name: str = ""
    prompt: str = ""
    response: str = ""
    prompt_storage_mode: str = "redacted"
    status: str = "success"
    error_code: str = ""
    error_message: str = ""
    latency_ms: float = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    total_cost_usd: float = 0
    retry_count: int = 0
    metadata: dict = Field(default_factory=dict)


class IngestLlmCallResponse(BaseModel):
    id: str
    trace_id: str


class MetricsSummary(BaseModel):
    total_calls: int
    failed_calls: int
    avg_latency_ms: float
    total_cost_usd: float


class EvaluationJobCreate(BaseModel):
    project_id: str


class EvaluationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    project_id: str
    status: str
    evaluator_type: str
    evaluator_version: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class EvaluationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    llm_call_id: str
    faithfulness_score: float
    relevancy_score: float
    hallucination_flag: bool
    toxicity_flag: bool
    pii_exposure_flag: bool
    refusal_quality_score: float
    groundedness_score: float
    judge_reasoning: str
    evaluator_version: str
    judge_model: str
    created_at: datetime


class AlertRuleCreate(BaseModel):
    project_id: str | None = None
    name: str = Field(min_length=2, max_length=255)
    metric: str = Field(pattern=r"^(hallucination_rate|latency_p95_ms|error_rate|cost_spike)$")
    threshold: float
    severity: str = Field(default="warning", pattern=r"^(info|warning|critical)$")
    channel_type: str = "console"
    suppression_minutes: int = 30


class AlertRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str | None
    name: str
    metric: str
    threshold: float
    severity: str
    channel_type: str
    suppression_minutes: int
    is_active: bool
    created_at: datetime


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str | None
    endpoint_id: str | None
    alert_rule_id: str | None
    severity: str
    status: str
    summary: str
    triggered_at: datetime
    resolved_at: datetime | None


class LlmCallLogRead(BaseModel):
    id: str
    project_id: str
    endpoint_id: str | None
    trace_id: str
    correlation_id: str
    session_id: str
    user_id: str
    provider: str
    model: str
    status: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_cost_usd: float
    created_at: datetime


class PaginatedLlmCalls(BaseModel):
    items: list[LlmCallLogRead]
    total: int
    limit: int
    offset: int


class TraceDetail(BaseModel):
    call: LlmCallLogRead
    prompt: str
    response: str
    error_code: str
    error_message: str
    metadata: dict
    evaluations: list[EvaluationResultRead]
    incidents: list[IncidentRead]
