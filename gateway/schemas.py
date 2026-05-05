from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: str = Field(..., examples=["user"])
    content: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    messages: list[ChatMessage]
    endpoint: str = "default"
    session_id: str = ""
    model_purpose: str = "chat"


class ChatResponse(BaseModel):
    id: str
    response: str
    provider: str
    model: str
    latency_ms: float
    cost_usd: float
    tokens: dict[str, int]
