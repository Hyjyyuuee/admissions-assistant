import math
import re
from collections import Counter

import jieba
from sqlalchemy.orm import Session

from .embeddings import semantic_scores
from .knowledge_tools import load_tool_documents, select_tools
from .knowledge_graph import graph_scores
from .models import KnowledgeChunk
from .router import category_multiplier, route_query


STOPWORDS = {
    "什么", "哪些", "怎么", "如何", "可以", "是否", "有没有", "方面",
    "一下", "以后", "之后", "哪里", "哪儿", "知道", "需要", "通常",
    "相关", "问题", "多少", "学生", "申请人",
}


def tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in jieba.lcut(text)
        if re.search(r"[\w\u4e00-\u9fff]", token)
        and len(token.strip()) > 1
        and token.strip().lower() not in STOPWORDS
    ]


def character_vector(text: str) -> Counter:
    """Create a sparse offline vector from Chinese-friendly character n-grams."""
    normalized = "".join(re.findall(r"[a-z0-9\u4e00-\u9fff]", text.lower()))
    return Counter(
        normalized[index:index + size]
        for size in (2, 3)
        for index in range(max(0, len(normalized) - size + 1))
    )


def cosine_similarity(left: Counter, right: Counter) -> float:
    if not left or not right:
        return 0.0
    common = left.keys() & right.keys()
    dot = sum(left[key] * right[key] for key in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def bm25_scores(docs: list[KnowledgeChunk], query: str) -> dict[str, float]:
    corpus = [tokenize(f"{doc.title} {doc.title} {doc.title} {doc.category} {doc.content}") for doc in docs]
    query_tokens = tokenize(query)
    count = len(corpus)
    document_frequency = Counter(token for tokens in corpus for token in set(tokens))
    average_length = sum(map(len, corpus)) / max(count, 1)
    scores = {}

    for doc, tokens in zip(docs, corpus):
        frequencies = Counter(tokens)
        score = 0.0
        for term in query_tokens:
            frequency = frequencies[term]
            if not frequency:
                continue
            inverse_frequency = math.log(
                1 + (count - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5)
            )
            score += inverse_frequency * frequency * 2.5 / (
                frequency + 1.5 * (1 - 0.75 + 0.75 * len(tokens) / max(average_length, 1))
            )
        if score > 0:
            scores[doc.id] = score
    return scores


def character_vector_scores(docs: list[KnowledgeChunk], query: str) -> dict[str, float]:
    query_vector = character_vector(query)
    scores = {}
    for doc in docs:
        # Repeating the title gives document and section names slightly more weight.
        document_vector = character_vector(f"{doc.title} {doc.title} {doc.content}")
        score = cosine_similarity(query_vector, document_vector)
        if score > 0:
            scores[doc.id] = score
    return scores


def reciprocal_rank_fusion(
    bm25: dict[str, float], vectors: dict[str, float], graph: dict[str, float], rank_constant: int = 60
) -> dict[str, float]:
    fused = Counter()
    rankings = (
        (bm25, 0.5),
        (vectors, 0.35),
        (graph, 0.15),
    )
    for scores, weight in rankings:
        ranked_ids = sorted(scores, key=scores.get, reverse=True)
        for rank, document_id in enumerate(ranked_ids, start=1):
            fused[document_id] += weight / (rank_constant + rank)
    return dict(fused)


def retrieve(db: Session, query: str, top_k: int = 4) -> list[dict]:
    route = route_query(query)
    tools = select_tools(route)
    docs = load_tool_documents(db, tools)
    if not docs:
        return []

    bm25 = bm25_scores(docs, query)
    # Keep one stable embedding cache for the complete corpus, then expose only
    # the scores belonging to tools selected for this request.
    all_docs = db.query(KnowledgeChunk).all()
    all_vectors = semantic_scores(all_docs, query)
    if all_vectors is None:
        vectors = character_vector_scores(docs, query)
    else:
        selected_ids = {doc.id for doc in docs}
        vectors = {document_id: score for document_id, score in all_vectors.items() if document_id in selected_ids}
    graph = graph_scores(all_docs, query)
    graph = {document_id: score for document_id, score in graph.items() if document_id in {doc.id for doc in docs}}
    fused = reciprocal_rank_fusion(bm25, vectors, graph)
    docs_by_id = {doc.id: doc for doc in docs}
    fused = {
        document_id: score * category_multiplier(docs_by_id[document_id].category, route)
        for document_id, score in fused.items()
    }
    ranked_ids = sorted(fused, key=fused.get, reverse=True)
    if not ranked_ids:
        return []

    best_score = fused[ranked_ids[0]]
    selected = []
    per_source = Counter()
    selected_sources = set()

    for document_id in ranked_ids:
        score = fused[document_id]
        if score < best_score * 0.55:
            break
        doc = docs_by_id[document_id]
        if doc.source not in selected_sources and len(selected_sources) >= 2:
            continue
        if per_source[doc.source] >= 2:
            continue
        selected.append({
            "title": doc.title,
            "source": doc.source,
            "category": doc.category,
            "content": doc.content,
            "score": round(score * 100, 4),
            "bm25_score": round(bm25.get(document_id, 0.0), 4),
            "vector_score": round(vectors.get(document_id, 0.0), 4),
            "graph_score": round(graph.get(document_id, 0.0), 4),
            "route": route.primary,
            "tools": [tool.name for tool in tools],
        })
        selected_sources.add(doc.source)
        per_source[doc.source] += 1
        if len(selected) == top_k:
            break
    return selected
