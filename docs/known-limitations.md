# Known Limitations

- **RAG retrieval is pure cosine similarity, no hybrid/keyword search or reranking.** Works well
  at this corpus size (34 chunks over 8 documents); would need BM25 + reranking to stay accurate
  over a much larger, more heterogeneous corpus.
- **RAG ingestion only handles markdown.** No PDF/DOCX text extraction, which a real operating
  procedure corpus would likely need.
- **No automatic RAG index refresh.** `python rag/ingestion/ingest.py` is a manual step; there's
  no file-watcher or scheduled rebuild.
- **MCP sessions are opened per tool call, not held open for a chat session.** Simpler and more
  fault-isolating (one server being briefly down doesn't break the next call), at the cost of a
  connection-setup round trip on every single tool invocation.
- **No conversation persistence.** Chat history lives in the Chainlit session (`cl.user_session`)
  and is lost on server restart or between browser sessions -- there's no database-backed thread
  storage.
- **Single-user, no authN/authZ on the copilot GUI itself.** The bearer tokens protect the two
  source-system APIs; nothing currently gates who can open the Chainlit app itself. A real
  deployment would put it behind SSO/an API gateway.
- **Only OpenAI has actually been exercised end-to-end.** `LLMClient` is a thin, swappable wrapper
  and the architecture doc claims "swappable provider," but only the OpenAI function-calling path
  has been run against a real model; a different provider's tool-calling response shape may need
  small adjustments in `apps/backend/orchestrator/llm.py`.
- **The automated end-to-end test stubs the LLM, not the rest of the stack.** A real OpenAI call
  is nondeterministic, costs money, and needs a live key, none of which belong in a CI-run test.
  `tests/e2e/test_boiler_feed_pump_scenario.py` runs the real alarm simulator, the real work-order
  service, both real MCP servers over real network connections, and real RAG retrieval over the
  real corpus -- only the model's own reasoning is replaced with a scripted tool-call sequence.
  Actual answer quality from a live model has been checked manually, not by an automated
  assertion.
- **No rate limiting or backpressure** on either source-system API or the MCP servers.
- **All five Docker images share one `requirements.txt`-based base layer**, so the alarm simulator
  and work-order service images carry the RAG/ML dependencies (torch, sentence-transformers,
  faiss) they never use, at roughly 3GB per image. Splitting into per-service requirement files
  would shrink the source-system images substantially; not done here to keep one dependency file
  and one Dockerfile for the whole repo.
- **SQLite, single writer.** Fine for a demo/assignment; a real deployment would use Postgres per
  service and would need to revisit the synchronous SQLModel session usage under real concurrency.
- **Chainlit step rendering is retroactive, not streamed.** The whole tool loop for a turn runs
  before any step appears in the GUI; a long multi-step investigation shows a single loading
  state rather than steps appearing live as they execute.
- **Seed data is synthetic and fixed-seed**, not sampled from a real plant. Good enough to make
  every advanced analytic (correlation, flood, rationalization, KPIs) return non-trivial results,
  but the numbers themselves are not meaningful outside this demo.
