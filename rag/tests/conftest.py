from pathlib import Path

import pytest

from rag.ingestion.ingest import build_index
from rag.retrieval.retriever import Retriever

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def retriever(tmp_path_factory):
    index_dir = tmp_path_factory.mktemp("rag_index")
    build_index(documents_path=REPO_ROOT / "rag" / "documents", index_path=index_dir)
    return Retriever(index_path=index_dir)
