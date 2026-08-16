import hashlib
import threading
from collections import Counter, defaultdict

from .entities import extract_entities
from .router import route_query


_fingerprint = ""
_entity_to_docs = defaultdict(set)
_category_to_docs = defaultdict(set)
_documents = {}
_lock = threading.Lock()


def _docs_fingerprint(docs) -> str:
    digest = hashlib.sha256()
    for doc in docs:
        digest.update(doc.id.encode("utf-8"))
        digest.update(doc.category.encode("utf-8"))
        digest.update(doc.title.encode("utf-8"))
        digest.update(doc.content.encode("utf-8"))
    return digest.hexdigest()


def build_graph(docs) -> None:
    global _fingerprint, _entity_to_docs, _category_to_docs, _documents
    fingerprint = _docs_fingerprint(docs)
    if fingerprint == _fingerprint:
        return
    with _lock:
        if fingerprint == _fingerprint:
            return
        entity_to_docs = defaultdict(set)
        category_to_docs = defaultdict(set)
        documents = {}
        for doc in docs:
            documents[doc.id] = {
                "id": doc.id,
                "title": doc.title,
                "source": doc.source,
                "category": doc.category,
            }
            category_to_docs[doc.category].add(doc.id)
            for entity in extract_entities(f"{doc.title} {doc.content}"):
                entity_to_docs[entity["value"]].add(doc.id)
        _entity_to_docs = entity_to_docs
        _category_to_docs = category_to_docs
        _documents = documents
        _fingerprint = fingerprint


def graph_scores(docs, query: str) -> dict[str, float]:
    build_graph(docs)
    scores = Counter()
    for entity in extract_entities(query):
        for document_id in _entity_to_docs.get(entity["value"], set()):
            scores[document_id] += 2.0

    route = route_query(query)
    for category in route.candidates:
        multiplier = 0.5 if category == route.primary else 0.25
        for document_id in _category_to_docs.get(category, set()):
            scores[document_id] += multiplier
    return dict(scores)


def graph_status() -> dict[str, int | str]:
    edge_count = sum(len(ids) for ids in _entity_to_docs.values()) + sum(
        len(ids) for ids in _category_to_docs.values()
    )
    return {
        "status": "ready" if _fingerprint else "not_built",
        "documents": len(_documents),
        "entities": len(_entity_to_docs),
        "categories": len(_category_to_docs),
        "edges": edge_count,
    }


def graph_query(query: str, docs) -> dict:
    scores = graph_scores(docs, query)
    entities = extract_entities(query)
    related = [
        {**_documents[document_id], "graph_score": score}
        for document_id, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
    ]
    return {"query": query, "entities": entities, "related_documents": related[:10]}
