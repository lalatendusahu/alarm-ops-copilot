"""Build the FAISS retrieval index from the markdown corpus. Run from the repo root:

    python rag/ingestion/ingest.py
"""
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import faiss  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from rag.ingestion.chunker import chunk_document  # noqa: E402

DOCUMENTS_PATH = Path(os.getenv("RAG_DOCUMENTS_PATH", "./rag/documents"))
INDEX_PATH = Path(os.getenv("RAG_INDEX_PATH", "./rag/index"))
MODEL_NAME = os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def load_corpus(documents_path: Path) -> list:
    chunks = []
    for md_file in sorted(documents_path.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        chunks.extend(chunk_document(doc_id=md_file.stem, source_path=str(md_file), markdown=text))
    return chunks


def build_index(documents_path: Path = DOCUMENTS_PATH, index_path: Path = INDEX_PATH, model_name: str = MODEL_NAME) -> dict:
    chunks = load_corpus(documents_path)
    if not chunks:
        raise RuntimeError(f"no markdown documents found under {documents_path}")

    model = SentenceTransformer(model_name)
    embeddings = model.encode([c.text for c in chunks], convert_to_numpy=True, show_progress_bar=False)
    embeddings = embeddings.astype("float32")
    faiss.normalize_L2(embeddings)

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    index_path.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path / "index.faiss"))
    (index_path / "chunks.json").write_text(
        json.dumps([asdict(c) for c in chunks], indent=2), encoding="utf-8"
    )
    (index_path / "manifest.json").write_text(
        json.dumps({"model_name": model_name, "chunk_count": len(chunks), "dimensions": int(embeddings.shape[1])}, indent=2),
        encoding="utf-8",
    )

    return {"chunk_count": len(chunks), "documents": len(list(documents_path.glob("*.md")))}


if __name__ == "__main__":
    stats = build_index()
    print(f"indexed {stats['chunk_count']} chunks from {stats['documents']} documents into {INDEX_PATH}")
