from uuid import NAMESPACE_URL, uuid5
from .database import SessionLocal
from .knowledge_loader import load_chunks
from .models import KnowledgeChunk


def sync_knowledge():
    db = SessionLocal()
    try:
        chunks = load_chunks()
        expected_ids = set()
        for index, chunk in enumerate(chunks):
            chunk_id = str(uuid5(NAMESPACE_URL, f"{chunk['source']}#{index}"))
            expected_ids.add(chunk_id)
            row = db.get(KnowledgeChunk, chunk_id)
            if row is None:
                row = KnowledgeChunk(id=chunk_id, entities="[]", **chunk)
                db.add(row)
            else:
                for key, value in chunk.items():
                    setattr(row, key, value)

        for row in db.query(KnowledgeChunk).all():
            if row.id not in expected_ids:
                db.delete(row)
        db.commit()
    finally:
        db.close()


def seed_if_empty():
    """Backward-compatible alias for older startup code."""
    sync_knowledge()
