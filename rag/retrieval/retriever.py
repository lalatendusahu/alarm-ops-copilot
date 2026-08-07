import json
import os
from functools import lru_cache
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer

INDEX_PATH = Path(os.getenv("RAG_INDEX_PATH", "./rag/index"))
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
DEFAULT_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.30"))


class IndexNotBuiltError(Exception):
    pass


class Retriever:
    def __init__(self, index_path: Path = INDEX_PATH):
        self.index_path = Path(index_path)
        manifest_file = self.index_path / "manifest.json"
        if not manifest_file.exists():
            raise IndexNotBuiltError(
                f"no RAG index found at {self.index_path}; run `python rag/ingestion/ingest.py` first"
            )
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        self.model = SentenceTransformer(manifest["model_name"])
        self.index = faiss.read_index(str(self.index_path / "index.faiss"))
        self.chunks = json.loads((self.index_path / "chunks.json").read_text(encoding="utf-8"))

    def search(self, query: str, top_k: int = DEFAULT_TOP_K, min_score: float = DEFAULT_MIN_SCORE) -> list[dict]:
        if not query or not query.strip():
            return []

        vector = self.model.encode([query], convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(vector)
        scores, indices = self.index.search(vector, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or score < min_score:
                continue
            chunk = self.chunks[idx]
            results.append({
                "chunk_id": chunk["chunk_id"],
                "doc_id": chunk["doc_id"],
                "title": chunk["title"],
                "section": chunk["section"],
                "source_path": chunk["source_path"],
                "text": chunk["text"],
                "score": round(float(score), 4),
            })
        return results


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    return Retriever()
