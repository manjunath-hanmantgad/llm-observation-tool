from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from gateway.cost import calculate_cost
from gateway.schemas import ChatRequest, ChatResponse
from observatory.database import SessionLocal, init_platform_db
from observatory.routers import alerts, api_keys, auth, evaluations, ingestion, projects, traces
from shared.config import get_settings
from shared.llm_client import get_llm_client
from shared.telemetry import metrics, setup_logger, track_event
from storage.db import init_db, insert_llm_log, summary


init_db()
init_platform_db()
settings = get_settings()
logger = setup_logger("llm-observatory.gateway")

app = FastAPI(
    title="LLM Observatory Gateway",
    version="0.1.0",
    description="Gateway that logs LLM requests, latency, token usage, and cost.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(api_keys.router)
app.include_router(ingestion.router)
app.include_router(evaluations.router)
app.include_router(alerts.router)
app.include_router(traces.router)


@app.middleware("http")
async def request_observability_and_security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    started = time.perf_counter()
    response = await call_next(request)
    latency_seconds = time.perf_counter() - started
    metrics.observe_request(latency_seconds=latency_seconds, status_code=response.status_code)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-ms"] = f"{latency_seconds * 1000:.2f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "provider": settings.llm_provider, "storage": settings.storage_mode}


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def readiness() -> dict[str, str]:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics() -> Response:
    return Response(content=metrics.render(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/stats/summary")
def stats_summary() -> dict:
    return summary()


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    client = get_llm_client()
    call_id = str(uuid.uuid4())
    messages = [message.model_dump() for message in payload.messages]
    started = time.time()

    try:
        result = client.chat(messages, purpose=payload.model_purpose)
        latency_ms = round((time.time() - started) * 1000, 2)
        cost = round(calculate_cost(result.model, result.prompt_tokens, result.completion_tokens), 8)
        insert_llm_log(
            {
                "id": call_id,
                "timestamp": datetime.now(UTC),
                "prompt": str(messages),
                "response": result.content,
                "model": result.model,
                "provider": settings.llm_provider,
                "latency_ms": latency_ms,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_cost_usd": cost,
                "endpoint": payload.endpoint,
                "session_id": payload.session_id,
                "status": "success",
                "error": "",
            }
        )
        track_event(
            "llm_call_success",
            {
                "endpoint": payload.endpoint,
                "model": result.model,
                "latency_ms": latency_ms,
                "cost_usd": cost,
            },
        )
        metrics.observe_llm_call(latency_ms=latency_ms, cost_usd=cost, status="success")
        return ChatResponse(
            id=call_id,
            response=result.content,
            provider=settings.llm_provider,
            model=result.model,
            latency_ms=latency_ms,
            cost_usd=cost,
            tokens={"prompt": result.prompt_tokens, "completion": result.completion_tokens},
        )
    except Exception as exc:
        latency_ms = round((time.time() - started) * 1000, 2)
        insert_llm_log(
            {
                "id": call_id,
                "timestamp": datetime.now(UTC),
                "prompt": str(messages),
                "response": "",
                "model": payload.model_purpose,
                "provider": settings.llm_provider,
                "latency_ms": latency_ms,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_cost_usd": 0,
                "endpoint": payload.endpoint,
                "session_id": payload.session_id,
                "status": "error",
                "error": str(exc),
            }
        )
        logger.exception("LLM call failed")
        track_event("llm_call_error", {"endpoint": payload.endpoint, "error": str(exc)})
        metrics.observe_llm_call(latency_ms=latency_ms, cost_usd=0, status="error")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
