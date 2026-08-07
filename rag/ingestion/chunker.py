import re
from dataclasses import dataclass, field

MAX_WORDS = 220
OVERLAP_WORDS = 40


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    section: str
    source_path: str
    chunk_index: int
    text: str
    metadata: dict = field(default_factory=dict)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _split_sections(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    lines = markdown.strip().splitlines()
    title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else "Untitled"

    sections: list[tuple[str, list[str]]] = []
    current_heading = "Overview"
    current_body: list[str] = []
    for line in lines[1:]:
        if line.startswith("## "):
            if current_body:
                sections.append((current_heading, current_body))
            current_heading = line.lstrip("# ").strip()
            current_body = []
        else:
            current_body.append(line)
    if current_body:
        sections.append((current_heading, current_body))

    return title, [(heading, "\n".join(body).strip()) for heading, body in sections if "\n".join(body).strip()]


def _split_by_words(text: str, max_words: int, overlap: int) -> list[str]:
    words = text.split()
    if len(words) <= max_words:
        return [text]
    parts = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        parts.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return parts


def chunk_document(doc_id: str, source_path: str, markdown: str) -> list[Chunk]:
    title, sections = _split_sections(markdown)
    chunks = []
    idx = 0
    for heading, body in sections:
        for piece in _split_by_words(body, MAX_WORDS, OVERLAP_WORDS):
            chunks.append(Chunk(
                chunk_id=f"{doc_id}::{_slug(heading)}::{idx}",
                doc_id=doc_id,
                title=title,
                section=heading,
                source_path=source_path,
                chunk_index=idx,
                text=piece,
            ))
            idx += 1
    return chunks
