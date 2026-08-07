from rag.ingestion.chunker import chunk_document

SAMPLE = """# Sample Document

## First Section
This is the first section body with a few words in it.

## Second Section
This is the second section body, also short.
"""


def test_splits_by_header_and_captures_title():
    chunks = chunk_document("sample", "rag/documents/sample.md", SAMPLE)
    assert len(chunks) == 2
    assert all(c.title == "Sample Document" for c in chunks)
    assert {c.section for c in chunks} == {"First Section", "Second Section"}


def test_chunk_ids_are_unique_and_stable():
    chunks = chunk_document("sample", "rag/documents/sample.md", SAMPLE)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert all(c.doc_id == "sample" for c in chunks)


def test_long_section_is_split_with_overlap():
    long_body = "word " * 500
    doc = f"# Long Doc\n\n## Only Section\n{long_body}\n"
    chunks = chunk_document("long", "rag/documents/long.md", doc)
    assert len(chunks) > 1
    # consecutive chunks should share some overlapping words
    first_tail = chunks[0].text.split()[-10:]
    second_head = chunks[1].text.split()[:10]
    assert set(first_tail) & set(second_head)


def test_empty_sections_are_skipped():
    doc = "# Title\n\n## Empty Section\n\n## Real Section\nhas content\n"
    chunks = chunk_document("doc", "path.md", doc)
    assert len(chunks) == 1
    assert chunks[0].section == "Real Section"
