def test_relevant_query_surfaces_the_right_document(retriever):
    results = retriever.search("recurring high bearing vibration on a boiler feed pump", top_k=3, min_score=0.0)
    assert results
    assert results[0]["doc_id"] in {"boiler-feed-pump-operating-procedure", "pump-troubleshooting-guide"}


def test_results_are_sorted_by_descending_score(retriever):
    results = retriever.search("alarm flood response", top_k=5, min_score=0.0)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_citation_fields_are_present(retriever):
    results = retriever.search("escalation path for a recurring critical alarm", top_k=1, min_score=0.0)
    assert results
    chunk = results[0]
    for field in ["chunk_id", "doc_id", "title", "section", "source_path", "text", "score"]:
        assert field in chunk
    assert 0.0 <= chunk["score"] <= 1.0


def test_low_confidence_query_is_filtered_out(retriever):
    results = retriever.search("xkq7 zzyxwvut nonsense token sequence", top_k=5, min_score=0.75)
    assert results == []


def test_empty_query_returns_no_results(retriever):
    assert retriever.search("", top_k=5) == []


def test_injection_document_is_retrievable_only_as_inert_text(retriever):
    results = retriever.search("field data entry note for AI assistants", top_k=3, min_score=0.0)
    matched = [r for r in results if r["doc_id"] == "rotating-equipment-safety-instructions"]
    assert matched, "the injection-bearing chunk should still be retrievable as ordinary content"
    # the retriever only ever returns plain text -- it never executes or interprets it
    assert isinstance(matched[0]["text"], str)
    assert "ignore all previous instructions" in matched[0]["text"].lower()
