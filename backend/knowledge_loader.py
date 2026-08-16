import re
from dataclasses import dataclass
from pathlib import Path


KNOWLEDGE_ROOT = Path(__file__).resolve().parents[1] / "knowledge"


@dataclass(frozen=True)
class Document:
    source: str
    title: str
    category: str
    content: str


def _plain_heading(line: str) -> str:
    return re.sub(r"^#{1,6}\s+", "", line).strip()


def load_documents(root: Path = KNOWLEDGE_ROOT) -> list[Document]:
    documents = []
    for path in sorted(root.glob("*/*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        first_heading = next((line for line in text.splitlines() if line.startswith("# ")), path.stem)
        documents.append(
            Document(
                source=path.relative_to(root).as_posix(),
                title=_plain_heading(first_heading),
                category=path.parent.name,
                content=text,
            )
        )
    return documents


def chunk_document(document: Document, max_chars: int = 500) -> list[dict]:
    lines = document.content.splitlines()
    sections: list[tuple[str, list[str]]] = []
    heading = document.title
    body: list[str] = []

    for line in lines:
        if re.match(r"^#{2,6}\s+", line):
            if body:
                sections.append((heading, body))
            heading, body = _plain_heading(line), []
        elif not line.startswith("# "):
            body.append(line)
    if body:
        sections.append((heading, body))

    chunks = []
    for section_title, section_lines in sections:
        paragraphs = [x.strip() for x in re.split(r"\n\s*\n", "\n".join(section_lines)) if x.strip()]
        current = ""
        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}".strip()
            if current and len(candidate) > max_chars:
                chunks.append(current)
                current = paragraph
            else:
                current = candidate
        if current:
            chunks.append(current)

    return [
        {
            "source": document.source,
            "category": document.category,
            "title": f"{document.title} · {section_title}" if section_title != document.title else document.title,
            "content": content,
        }
        for content in chunks
    ]


def load_chunks(root: Path = KNOWLEDGE_ROOT) -> list[dict]:
    return [chunk for document in load_documents(root) for chunk in chunk_document(document)]
