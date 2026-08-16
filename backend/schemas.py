from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


class Source(BaseModel):
    title: str
    source: str
    score: float


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[Source]
    mode: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str

