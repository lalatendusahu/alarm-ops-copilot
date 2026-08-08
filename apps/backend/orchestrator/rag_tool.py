from apps.backend.config import settings
from rag.retrieval.retriever import IndexNotBuiltError, get_retriever

RAG_TOOL_NAME = "rag__search_documents"

RAG_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": RAG_TOOL_NAME,
        "description": (
            "Search the operating procedure, troubleshooting, safety, and rationalization document "
            "corpus for passages relevant to a question. Returns excerpts with a title, section, and "
            "relevance score -- use it whenever the answer might depend on documented procedure or "
            "policy rather than only on live alarm/work-order data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural-language search query"},
                "top_k": {"type": "integer", "description": "Maximum passages to return", "default": settings.rag_top_k},
            },
            "required": ["query"],
        },
    },
}


def search_documents(query: str, top_k: int | None = None) -> tuple[dict, bool]:
    try:
        retriever = get_retriever()
    except IndexNotBuiltError as exc:
        return {"error": str(exc)}, True

    results = retriever.search(query, top_k=top_k or settings.rag_top_k, min_score=settings.rag_min_score)
    if not results:
        return {"results": [], "note": "no passages met the relevance threshold for this query"}, False
    return {"results": results}, False
