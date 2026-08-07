# Architecture

See [`architecture-diagram.png`](architecture-diagram.png) for the visual version of what's
described here.

## Layers

**GUI (`apps/frontend/chainlit_app.py`)** -- a Chainlit chat app. It owns nothing about how
tools are chosen or executed; its job is session bootstrapping (tool discovery on chat start),
rendering the execution trace and RAG citations returned by the orchestrator, and the work-order
approval buttons.

**Copilot orchestration (`apps/backend/orchestrator/`)** -- `engine.run_turn()` is the only entry
point. It runs a bounded ReAct loop: ask the LLM for the next step, execute whatever tool(s) it
asked for, feed the results back, repeat until the model stops or a max-iteration cap is hit,
then run one more constrained LLM call that must ground its answer only in what was actually
collected this turn. `trace.py` records every tool call (server, tool, input, output/error,
duration, trace id) regardless of outcome.

**MCP client (`apps/backend/orchestrator/mcp_client.py`)** -- `MCPToolRegistry` discovers tools
from every configured MCP server over streamable-http, namespaces them (`alarm.search_assets`,
`workorders.get_maintenance_history`), converts their schemas to OpenAI's function-calling
format, and dispatches calls back to the right server. A fresh session is opened per call rather
than held open for the process lifetime -- simpler, and it means a server that's down for one
call doesn't poison the next one.

**MCP servers (`mcp-servers/alarm_management`, `mcp-servers/work_orders`)** -- each is a
standalone `FastMCP` process exposing typed tools over streamable-http. Neither imports from the
other, and neither is imported by the orchestrator -- they're only reachable over the network,
the same way they'd be reached in a real deployment. Business logic never lives here; each tool
is a thin wrapper that validates input, calls a connector, and maps connector errors to a tool
error.

**Connectors (`connectors/`)** -- `AlarmApiClient` and `WorkOrderApiClient` share a `BaseConnector`
that handles bearer auth, trace-header injection, timeouts, and retry-with-backoff on 5xx/timeout
(never on 4xx). This is the only layer that talks HTTP to a source system.

**Source systems (`alarm-simulator/`, `work-order-service/`)** -- independent FastAPI + SQLite
services. Bearer-token auth on everything except `/health`. Business logic (summary/trend
aggregation, correlation, flood detection, rationalization, priority scoring, KPI calculations)
lives in `alarm-simulator/app/logic/`, separate from the route handlers, so it's testable without
spinning up the API.

**RAG (`rag/`)** -- ingestion (`rag/ingestion/`) chunks the markdown corpus, embeds it with a
local sentence-transformer, and writes a FAISS index. Retrieval (`rag/retrieval/`) is a thin
wrapper the orchestrator calls directly as a pseudo-tool (`rag.search_documents`) -- it is
**not** behind an MCP server. That's a deliberate choice: RAG isn't a source-system integration,
it's a capability of the copilot itself, so it doesn't need protocol indirection. The diagram
shows this as a separate path alongside the MCP path, not behind it.

## Request Flow

1. User sends a message in the Chainlit GUI.
2. `run_turn()` prepends the planner system prompt (once) and the tool schemas (MCP + RAG) and
   asks the LLM what to do.
3. For each tool call the model requests: dispatch to the MCP registry or the RAG retriever,
   record a trace step, feed the result back as a `tool` message.
4. Repeat until the model stops requesting tools or the iteration cap is hit.
5. Run the grounded-answer pass: same conversation, plus an instruction to answer only from what
   was gathered, with citations.
6. Return the answer, the full trace, and deduplicated RAG citations to the GUI, which renders
   the trace as nested steps and the citations as source panels.

## Why RAG isn't wrapped in MCP

Both are legitimate designs. Wrapping RAG as a third MCP server would make the "MCP path" and
"RAG path" look identical in the trace, which actually makes it *harder* to see that they are two
different kinds of thing: one is calling out to enterprise source systems, the other is searching
a document corpus the copilot owns directly. Keeping RAG as an in-process tool keeps that
distinction visible in the trace and the diagram, at the cost of RAG not being independently
network-addressable the way the two MCP servers are (see `docs/known-limitations.md`).

## Auth Boundaries

- Alarm Management API and Work Order API each require a static bearer token (`ALARM_API_TOKEN`,
  `WORK_ORDER_API_TOKEN`), checked on every route except `/health`. Tokens live only in the
  connector layer and environment variables -- they are never returned in a tool result or logged.
- The LLM provider is a second, independent auth boundary (`OPENAI_API_KEY`), isolated to
  `apps/backend/orchestrator/llm.py`, so swapping providers doesn't touch anything else.
- Write operations (creating a work order) require an explicit `confirm=true`, which the GUI
  only sends after a human clicks "Approve" -- the model can preview a draft but cannot persist
  one unilaterally.
