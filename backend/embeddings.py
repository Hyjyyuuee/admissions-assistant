import hashlib
import json
import math
import threading
from pathlib import Path


MODEL_NAME = "BAAI/bge-small-zh-v1.5"
MODEL_CACHE = Path(__file__).resolve().parents[1] / "data" / "model_cache"
VECTOR_CACHE = Path(__file__).resolve().parents[1] / "data" / "embedding_cache.json"

_model = None
_status = "not_loaded"
_error = ""
_document_cache_key = None
_document_vectors = []
_cache_status = "empty"
_lock = threading.Lock()


def _cosine(left, right) -> float:
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = math.sqrt(sum(float(value) ** 2 for value in left))
    right_norm = math.sqrt(sum(float(value) ** 2 for value in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def get_model():
    global _model, _status, _error
    if _model is not None:
        return _model
    with _lock:
        if _model is not None:
            return _model
        try:
            from fastembed import TextEmbedding

            MODEL_CACHE.mkdir(parents=True, exist_ok=True)
            _status = "loading"
            _model = TextEmbedding(model_name=MODEL_NAME, cache_dir=str(MODEL_CACHE))
            _status = "ready"
            _error = ""
            return _model
        except Exception as exc:
            _status = "fallback"
            _error = f"{type(exc).__name__}: {exc}"
            return None


def warm_up_embeddings() -> None:
    get_model()


def _fingerprint(docs) -> str:
    digest = hashlib.sha256(MODEL_NAME.encode("utf-8"))
    for doc in docs:
        digest.update(doc.id.encode("utf-8"))
        digest.update(doc.title.encode("utf-8"))
        digest.update(doc.content.encode("utf-8"))
    return digest.hexdigest()


def prepare_document_embeddings(docs) -> bool:
    global _document_cache_key, _document_vectors, _cache_status, _status, _error
    model = get_model()
    if model is None:
        return False

    cache_key = _fingerprint(docs)
    with _lock:
        if cache_key == _document_cache_key and _document_vectors:
            _cache_status = "memory"
            return True

        try:
            if VECTOR_CACHE.exists():
                payload = json.loads(VECTOR_CACHE.read_text(encoding="utf-8"))
                if payload.get("fingerprint") == cache_key:
                    _document_vectors = payload["vectors"]
                    _document_cache_key = cache_key
                    _cache_status = "disk"
                    return True

            passages = [f"{doc.title}。{doc.content}" for doc in docs]
            vectors = [vector.tolist() for vector in model.passage_embed(passages)]
            payload = {"model": MODEL_NAME, "fingerprint": cache_key, "vectors": vectors}
            temporary = VECTOR_CACHE.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            temporary.replace(VECTOR_CACHE)
            _document_vectors = vectors
            _document_cache_key = cache_key
            _cache_status = "rebuilt"
            return True
        except Exception as exc:
            _status = "fallback"
            _error = f"{type(exc).__name__}: {exc}"
            _cache_status = "error"
            return False


def semantic_scores(docs, query: str) -> dict[str, float] | None:
    global _status, _error
    model = get_model()
    if model is None:
        return None

    try:
        if not prepare_document_embeddings(docs):
            return None

        query_vector = list(model.query_embed([query]))[0]
        _status = "ready"
        return {
            doc.id: score
            for doc, vector in zip(docs, _document_vectors)
            if (score := _cosine(query_vector, vector)) > 0
        }
    except Exception as exc:
        _status = "fallback"
        _error = f"{type(exc).__name__}: {exc}"
        return None


def embedding_status() -> dict[str, str]:
    return {"status": _status, "model": MODEL_NAME, "cache": _cache_status, "error": _error}
