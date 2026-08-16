import json
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from .config import settings
from .database import Base, SessionLocal, engine, get_db
from .embeddings import embedding_status, prepare_document_embeddings, warm_up_embeddings
from .entities import enhance_query, extract_entities
from .llm import answer
from .knowledge_tools import tool_manifest
from .knowledge_tools import select_tools
from .knowledge_graph import build_graph, graph_query, graph_status
from .models import Conversation, KnowledgeChunk, Message, RetrievalLog
from .rag import retrieve
from .router import route_query
from .schemas import ChatRequest, ChatResponse, ConversationSummary
from .seed import sync_knowledge

TRACE_PAGE = Path(__file__).resolve().parent / "static" / "retrieval_trace.html"


def format_sources(hits: list[dict]) -> list[dict]:
    """Return one compact citation per Markdown document."""
    sources = []
    seen = set()
    for hit in hits:
        if hit["source"] in seen:
            continue
        seen.add(hit["source"])
        sources.append({
            "title": hit["title"].split(" · ", 1)[0],
            "source": hit["source"],
            "score": hit["score"],
        })
    return sources


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    sync_knowledge()
    warm_up_embeddings()
    db = SessionLocal()
    try:
        documents = db.query(KnowledgeChunk).all()
        prepare_document_embeddings(documents)
        build_graph(documents)
    finally:
        db.close()
    yield


app = FastAPI(title="Admissions Assistant API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_debug() -> None:
    if not settings.debug_endpoints_enabled:
        raise HTTPException(404, "Not found")


@app.get("/api/health")
def health():
    details = embedding_status()
    retrieval = "hybrid_bm25_bge_rrf" if details["status"] == "ready" else "hybrid_bm25_character_vector_rrf"
    return {
        "status": "ok",
        "environment": settings.app_env,
        "retrieval": retrieval,
        "router": "admissions_faculty_policy_soft_router_v1",
        "tools": tool_manifest(),
        "graph": graph_status(),
        "embedding": details,
    }


@app.get("/api/graph")
def inspect_graph(query: str, db: Session = Depends(get_db)):
    require_debug()
    return graph_query(query, db.query(KnowledgeChunk).all())


@app.get("/api/retrieval/trace")
def retrieval_trace(query: str, db: Session = Depends(get_db)):
    require_debug()
    entities = extract_entities(query)
    enhanced_query = enhance_query(query, entities)
    route = route_query(enhanced_query)
    tools = select_tools(route)
    hits = retrieve(db, enhanced_query)
    return {
        "query": query,
        "enhanced_query": enhanced_query,
        "route": {
            "primary": route.primary,
            "candidates": route.candidates,
            "scores": route.scores,
            "matched_keywords": route.matched_keywords,
        },
        "tools": [{"name": tool.name, "category": tool.category} for tool in tools],
        "entities": entities,
        "results": [{
            "title": hit["title"],
            "source": hit["source"],
            "category": hit["category"],
            "final_score": hit["score"],
            "bm25_score": hit["bm25_score"],
            "vector_score": hit["vector_score"],
            "graph_score": hit["graph_score"],
        } for hit in hits],
        "graph": graph_query(enhanced_query, db.query(KnowledgeChunk).all()),
    }


@app.get("/debug/retrieval", response_class=HTMLResponse)
def retrieval_debug_page():
    require_debug()
    return TRACE_PAGE.read_text(encoding="utf-8")


@app.get("/api/conversations", response_model=list[ConversationSummary])
def conversations(db: Session = Depends(get_db)):
    rows = db.query(Conversation).order_by(Conversation.created_at.desc()).all()
    return [{"id": x.id, "title": x.title, "created_at": x.created_at.isoformat()} for x in rows]


@app.get("/api/conversations/{conversation_id}")
def conversation(conversation_id: str, db: Session = Depends(get_db)):
    row = db.get(Conversation, conversation_id)
    if not row:
        raise HTTPException(404, "对话不存在")
    return {"id": row.id, "title": row.title, "messages": [{"role": m.role, "content": m.content, "sources": json.loads(m.sources)} for m in row.messages]}


@app.get("/api/retrieval/logs")
def retrieval_logs(limit: int = 20, db: Session = Depends(get_db)):
    require_debug()
    rows = db.query(RetrievalLog).order_by(RetrievalLog.created_at.desc()).limit(min(max(limit, 1), 100)).all()
    return [{
        "query": row.query,
        "enhanced_query": row.enhanced_query,
        "route": row.route,
        "tools": json.loads(row.tools),
        "entities": json.loads(row.entities),
        "sources": json.loads(row.sources),
        "created_at": row.created_at.isoformat(),
    } for row in rows]


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    conv = db.get(Conversation, payload.conversation_id) if payload.conversation_id else None
    if payload.conversation_id and not conv:
        raise HTTPException(404, "对话不存在")
    if not conv:
        conv = Conversation(id=str(uuid4()), title=payload.message[:30])
        db.add(conv)
        db.flush()
    previous = db.query(Message).filter_by(conversation_id=conv.id).order_by(Message.created_at).all()
    history = [{"role": x.role, "content": x.content} for x in previous]
    entities = extract_entities(payload.message)
    enhanced_query = enhance_query(payload.message, entities)
    route = route_query(enhanced_query)
    tools = [tool["name"] for tool in tool_manifest() if tool["category"] in route.candidates]
    hits = retrieve(db, enhanced_query)
    response_text, mode = await answer(payload.message, hits, history)
    sources = format_sources(hits)
    db.add_all([
        Message(id=str(uuid4()), conversation_id=conv.id, role="user", content=payload.message),
        Message(id=str(uuid4()), conversation_id=conv.id, role="assistant", content=response_text, sources=json.dumps(sources, ensure_ascii=False)),
        RetrievalLog(
            id=str(uuid4()),
            conversation_id=conv.id,
            query=payload.message,
            enhanced_query=enhanced_query,
            route=route.primary,
            tools=json.dumps(tools, ensure_ascii=False),
            entities=json.dumps(entities, ensure_ascii=False),
            sources=json.dumps(sources, ensure_ascii=False),
        ),
    ])
    db.commit()
    return {"conversation_id": conv.id, "answer": response_text, "sources": sources, "mode": mode}
