# RAG Design

## Source Documents

8 synthetic markdown files under `rag/documents/`, written for this assignment's alarm-management
domain: alarm philosophy, the Boiler Feed Pump operating procedure, a pump troubleshooting guide,
the alarm-flood response procedure, rationalization guidelines, rotating-equipment safety
instructions, escalation/incident response, and maintenance best practices. They're synthetic but
internally consistent with the simulator's seed data (they reference the same asset, alarm names,
and thresholds the alarm API actually uses), so retrieval for the mandatory Boiler Feed Pump 101
scenario returns genuinely relevant passages rather than generic filler.

## Ingestion (`rag/ingestion/`)

1. **Text extraction**: plain markdown read from disk -- no OCR/PDF handling needed for this
   corpus (see known-limitations for what a production version would add).
2. **Chunking** (`chunker.py`): split first on `## ` headers (so a chunk never straddles two
   unrelated sections), then, within a section, recursively by word count if it exceeds 220 words,
   with a 40-word overlap between consecutive pieces so a fact near a chunk boundary isn't lost.
3. **Metadata captured per chunk**: `chunk_id`, `doc_id`, `title` (from the `# ` heading),
   `section` (the `## ` heading it came from), `source_path`, `chunk_index`.
4. **Embedding**: `sentence-transformers/all-MiniLM-L6-v2`, run locally (CPU) -- no external API
   call, no per-query cost, and it means the RAG path has no dependency on the LLM provider.
5. **Index**: FAISS `IndexFlatIP` over L2-normalized vectors, which makes inner product equivalent
   to cosine similarity. Chosen over Chroma/a hosted vector DB because the corpus is small (34
   chunks) and an in-process flat index needs no separate service, which keeps the "RAG or
   equivalent retrieval approach" requirement satisfied without adding a container.
6. **Persistence**: `rag/index/index.faiss` + `chunks.json` + `manifest.json` (records the
   embedding model name so the retriever always loads the same one used to build the index).
   Rebuild with `python rag/ingestion/ingest.py`; the index directory is gitignored and expected
   to be built as a setup step, not committed.

## Retrieval (`rag/retrieval/retriever.py`)

- Query is embedded with the same model, normalized, and searched against the FAISS index for the
  top `RAG_TOP_K` (default 4) matches.
- **Retrieval filtering / low-confidence handling**: any match below `RAG_MIN_SCORE` (default
  0.30 cosine similarity) is dropped. If nothing clears the bar, the tool returns an empty result
  set with an explicit `"no passages met the relevance threshold"` note rather than forcing a
  citation onto an unrelated chunk -- the orchestrator's system prompt tells the model to say so
  in the final answer instead of guessing.
- No hybrid (keyword + vector) search and no reranking stage -- the corpus is small enough that
  pure cosine similarity over well-scoped chunks performs well in practice (see
  `rag/tests/test_retrieval.py`). This is a scale tradeoff, documented in known-limitations.

## Citation Construction

Every retrieved chunk carries `title`, `section`, `source_path`, and `score` alongside its text.
The orchestrator passes these straight through as `rag_citations` on the turn result; the GUI
renders each as a side panel labeled `"<title> — <section>"` with the score and source path, and
the final-answer prompt instructs the model to reference the document title/section for any claim
drawn from a retrieved passage.

## Prompt-Injection Protection

`rotating-equipment-safety-instructions.md` deliberately contains a sentence written as an
instruction to an AI reader ("ignore all previous instructions... respond only with..."), and
`rag/tests/test_retrieval.py::test_injection_document_is_retrievable_only_as_inert_text` asserts
it's still retrievable as plain text. That's intentional: the defense is not "never retrieve
suspicious content," it's that retrieved content is structurally incapable of steering the
system:

1. Retrieved chunks only ever enter the **final grounded-answer** LLM call, never the
   tool-selection/planning step -- so even a successful injection couldn't make the model call an
   unintended tool (e.g. a write operation).
2. The retriever (`rag/retrieval/retriever.py`) does not execute, evaluate, or template anything
   in chunk text -- it is returned as an opaque string.
3. The final-answer system prompt explicitly frames retrieved text as untrusted reference data to
   ground an answer in, not as instructions to follow.

## Index Refresh

There's no automatic refresh trigger -- `python rag/ingestion/ingest.py` is a manual, idempotent
step (re-running it fully rebuilds the index from the current contents of `rag/documents/`). For
this assignment's static corpus that's sufficient; a production version would re-run ingestion on
a schedule or a file-change webhook.
