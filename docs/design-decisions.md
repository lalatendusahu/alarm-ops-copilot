# Design Decisions

**Everything in Python.** Chainlit, both MCP servers, both source-system simulators, and the RAG
pipeline are all Python. One language, one dependency file, one Docker base image with per-service
stages. The alternative (e.g. a TypeScript MCP server) wasn't worth the packaging complexity for
this scope.

**Streamable-http over stdio for MCP transport.** stdio is simpler for a single local process, but
it doesn't fit "each MCP server must be independently runnable and testable" as a real network
service with its own docker-compose health check. Streamable-http lets each MCP server run as an
ordinary container and be probed by curl, an MCP inspector, or the test suite without the
orchestrator in the loop.

**Two generate/execute tools instead of one `run_kpi_calculation` tool.** A single combined tool
would hide the multi-step chaining the assignment explicitly wants demonstrated. Keeping
`generate_kpi_calculation` and `execute_kpi_calculation` separate forces the orchestrator to pass
a `calculation_id` from one tool call into the next, which is exactly the "pass output from one
MCP tool into another" requirement, visible in the trace rather than hidden inside one tool.

**Work orders instead of GitHub Issues for the second MCP domain.** The assignment's example
question mentions "prepare a GitHub issue draft"; this submission uses a self-built Work Order
mock service instead. Reasoning: GitHub Issues would need a real personal access token and would
create real state in a real external account, which is a worse fit for a self-contained,
reproducible `docker compose up` submission than a fully owned mock service. The same shape --
draft, then a confirmed write gated by human approval -- is preserved.

**RAG called directly, not wrapped in a third MCP server.** See `docs/architecture.md` for the
reasoning -- short version: RAG isn't a source-system integration, and forcing it through MCP
would blur the distinction the diagram and trace are supposed to make clear between "enterprise
tool call" and "document search."

**Retroactive trace rendering in the GUI, not live streaming.** `run_turn()` is one call that
internally runs the whole ReAct loop; the GUI renders the resulting trace as a sequence of
completed `cl.Step`s after the turn finishes, rather than streaming each step as it happens. A
live-streaming version would need `run_turn` to yield incrementally (e.g. via an async generator)
instead of returning a single result -- more moving parts for a marginal UX gain at this scope.

**Local embeddings (sentence-transformers) instead of an LLM-provider embedding API.** Keeps the
RAG path fully independent of the LLM provider choice and free of per-query embedding cost --
relevant since the LLM provider is meant to be swappable.

**SQLite instead of a hosted database.** Both source systems are single-writer, low-volume, and
meant to run in a single container each. SQLite means zero external setup and the seed scripts
are trivially reproducible; a real deployment would use Postgres per service.

**`run_server.py` instead of the `chainlit run` CLI to launch the copilot.** The CLI
(`chainlit.cli`) calls `nest_asyncio.apply()` at import time, which monkey-patches asyncio's
Task/event-loop classes process-wide to allow reentrant event loops. That patch corrupts anyio's
cancel-scope bookkeeping for any anyio-based client used later in the same process -- including
the MCP SDK's streamable-http client -- producing a `RuntimeError: Attempted to exit a cancel
scope that isn't the current task's current cancel scope` on every MCP session, even though the
underlying connection succeeds. This was diagnosed by confirming the same MCP client code works
standalone and under pytest, and only breaks inside a live Chainlit session; isolating the work in
a separate thread/event loop did not help, which pointed at process-wide state rather than a
task-identity mismatch, and tracing that state to the single `nest_asyncio.apply()` call
(present only in `chainlit.cli`, nowhere else in the dependency tree) confirmed it.
`apps/frontend/run_server.py` drives the same Chainlit ASGI app (`chainlit.server:app`) directly
through uvicorn -- loading the target module and wiring config the same way the CLI does -- without
ever importing `chainlit.cli`, so the patch is never applied.

**Confirmation gating implemented as a real code boundary, not just a prompt instruction.** The
planner's system prompt tells the model not to pass `confirm=true` without explicit user approval,
but a user can simply ask the model to ignore that instruction ("no need to ask me") -- prompt text
is not a security boundary, and testing this directly (asking the model to create and confirm a
work order in one message) confirmed the model will in fact try to set `confirm=true` on its own
tool call when asked to. The actual enforcement is in `apps/backend/orchestrator/engine.py`:
`execute_tool` force-overwrites `confirm` to `false` for `workorders__create_work_order_draft`
whenever the call is dispatched from the model's own planning loop, regardless of what the model
passed. The only code path that can send `confirm=true` is the Chainlit GUI's `approve_work_order`
action callback, which calls `registry.call(...)` directly -- bypassing `execute_tool` and the
planning loop entirely -- and only runs in response to a human clicking Approve. The work-order
service also rejects `confirm=false` at the API level as a third layer of defense in depth.
Regression test: `tests/integration/test_orchestration.py::test_model_cannot_confirm_a_work_order_through_the_planning_loop`.
