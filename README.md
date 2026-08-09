# Multi-MCP Enterprise Operations Copilot

A copilot for alarm management operations that discovers and chains tools across two
candidate-built MCP servers (Alarm Management, Work Orders) and grounds its answers in a
document corpus through RAG -- all in one workflow, with full tool/citation traceability in the
GUI.

Please find the demo link here - https://www.loom.com/share/e398d170ab7d4e4e9e31ec86f29ce4ef


## Selected Use Case

**Multi-MCP Enterprise Operations Copilot** (Assignment_Use_Case.md, section 4). The mandatory
end-to-end scenario -- investigate recurring high-severity alarms on Boiler Feed Pump 101,
retrieve the applicable operating procedure, and recommend action with citations -- is covered by
an automated test at `tests/e2e/test_boiler_feed_pump_scenario.py`.

## Main Capabilities

- Natural-language chat that plans and chains MCP tool calls (no hard-coded question handling --
  a bounded ReAct loop decides what to call, in what order, based on the question).
- Two independently runnable MCP servers: **Alarm Management** (14 tools) and **Work Orders**
  (4 tools, including a confirm-gated write operation).
- Document RAG over an 8-document operating-procedure corpus, with citations and low-confidence
  handling.
- Full execution trace (server, tool, input/output, duration, status) and RAG citations surfaced
  in the GUI.
- Human-in-the-loop approval for the one write operation (creating a work order).

## Technology Stack

Python end-to-end. FastAPI + SQLite (both source systems) · `mcp` SDK / FastMCP over
streamable-http (both MCP servers) · sentence-transformers + FAISS (RAG, local/offline) ·
OpenAI function calling (orchestrator LLM, swappable) · Chainlit (GUI) · pytest (all tests) ·
Docker / docker-compose (packaging).

## MCP Servers

| Server | Tools | Wraps |
|---|---|---|
| `mcp-servers/alarm_management` | 14 | Alarm Management API simulator (`alarm-simulator/`) |
| `mcp-servers/work_orders` | 4 | Work order mock service (`work-order-service/`) |

Full tool-by-tool documentation (input/output schema, auth, error/timeout behavior, examples):
[`docs/mcp-tool-catalog.md`](docs/mcp-tool-catalog.md).

Run either server standalone (no copilot needed):

```bash
python mcp-servers/alarm_management/server.py   # streamable-http on :9001
python mcp-servers/work_orders/server.py        # streamable-http on :9002
```

## RAG Corpus and Ingestion

8 markdown documents under `rag/documents/` (alarm philosophy, Boiler Feed Pump operating
procedure, pump troubleshooting guide, flood response procedure, rationalization guidelines,
rotating-equipment safety instructions, escalation procedure, maintenance best practices).
Chunked by header then by size, embedded locally with `sentence-transformers/all-MiniLM-L6-v2`,
indexed with FAISS. Details: [`docs/rag-design.md`](docs/rag-design.md).

```bash
python rag/ingestion/ingest.py
```

## Quick Start

### Option A -- Docker Compose (recommended)

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY
docker compose up --build
```

Services: alarm-simulator (`:8000`), work-order-service (`:8010`), mcp-alarm (`:9001`),
mcp-workorders (`:9002`), copilot GUI (`:8501`). Open **http://localhost:8501**.

### Option B -- Local Python

```bash
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env   # set OPENAI_API_KEY

python scripts/seed_alarm_db.py
python scripts/seed_work_order_db.py
python rag/ingestion/ingest.py

# four separate terminals (each also runnable independently):
(cd alarm-simulator && uvicorn app.main:app --port 8000)
(cd work-order-service && uvicorn app.main:app --port 8010)
python mcp-servers/alarm_management/server.py
python mcp-servers/work_orders/server.py

# then, in a fifth terminal:
CHAINLIT_PORT=8501 python apps/frontend/run_server.py
```

Use `run_server.py`, not the `chainlit run` CLI -- the CLI calls `nest_asyncio.apply()` at
import time, which patches asyncio process-wide in a way that breaks the MCP client's
streamable-http sessions (see `docs/known-limitations.md`). `run_server.py` drives the same
Chainlit ASGI app directly through uvicorn, without going through the CLI.

## Configuration

All configuration is via environment variables -- see [`.env.example`](.env.example) for the full
list (source-system URLs/tokens, MCP server URLs/ports, LLM provider/model/key, RAG paths and
thresholds). Never commit a real `.env`.

## Test Commands

Each service's tests run independently of the others (by design -- they're independently runnable
systems, and two of them both happen to have a top-level `app` package, so running them in one
pytest process would collide):

```bash
cd alarm-simulator && python -m pytest tests/ -q          # 42 tests: business logic + API
cd work-order-service && python -m pytest tests/ -q       # 10 tests
python -m pytest tests/ rag/tests/ -q                      # MCP servers, orchestration, RAG, e2e
```

Or `make test` from the repo root runs all three groups. `make coverage` adds coverage reporting.

What's covered: alarm business-logic unit tests, API-level auth/pagination/error-path tests for
both source systems, MCP tool discovery/schema/auth/retry/error-mapping tests (against real
FastMCP servers via an in-memory MCP session, HTTP mocked with `respx`), MCP client integration
tests, RAG ingestion/retrieval/citation/low-confidence/prompt-injection tests, orchestration
tests (multi-server chaining, RAG-in-loop, partial failure, unavailable tool, malformed args), and
one full end-to-end test running the real alarm simulator, real work-order service, and both real
MCP servers together for the mandatory Boiler Feed Pump 101 scenario.

## Sample Interactions

> Investigate recurring high-severity alarms for Boiler Feed Pump 101 over the last 90 days,
> identify likely contributing factors, retrieve the relevant operating procedure, and provide
> recommended actions with source evidence.

Chains: `alarm__search_assets` -> `alarm__get_alarm_summary` -> `alarm__get_rationalization_candidates`
-> `workorders__get_maintenance_history` -> `rag__search_documents`, then a grounded answer citing
the operating procedure and troubleshooting guide.

> Calculate operator response efficiency for SouthPlant and check the applicable operating
> guideline.

Chains: `alarm__generate_kpi_calculation` -> `alarm__execute_kpi_calculation` -> `rag__search_documents`.

> Draft a work order for AST-1001 to inspect the bearing.

Calls `workorders__create_work_order_draft` with `confirm=false`, returns a preview, and the GUI
shows Approve/Discard buttons -- nothing is persisted until a human clicks Approve.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) and
[`docs/architecture-diagram.png`](docs/architecture-diagram.png) for the full breakdown. In short:
GUI -> orchestrator (ReAct loop + trace collector) -> MCP client/tool registry -> two independent
MCP servers -> connectors -> two independent source-system APIs, with RAG called directly by the
orchestrator as a third tool alongside the two MCP servers rather than wrapped in MCP itself (see
`docs/design-decisions.md` for why).

## Assumptions

- A single OpenAI-compatible LLM provider is configured per deployment (not per-request).
- The Alarm Management API's endpoint surface follows the Postman collections in `postman/`
  exactly; the simulator was built and spot-checked against them.
- "Second MCP domain" was interpreted as a fully self-built mock service (Work Orders) rather than
  a real external system, to keep the submission self-contained and reproducible without external
  credentials -- see `docs/design-decisions.md`.

## Known Limitations

[`docs/known-limitations.md`](docs/known-limitations.md).

## Repository Layout

```text
alarm-simulator/      Alarm Management API simulator (FastAPI + SQLite)
work-order-service/   Work order mock service (FastAPI + SQLite)
connectors/           Shared HTTP clients (auth, retry, trace) used by both MCP servers
mcp-servers/          alarm_management/ and work_orders/ -- both FastMCP, streamable-http
rag/                  documents/, ingestion/, retrieval/, tests/
apps/backend/         Orchestrator: MCP client, ReAct loop, trace collector, RAG tool, LLM client
apps/frontend/        Chainlit GUI
tests/                integration/ (MCP servers + orchestration), e2e/ -- unit tests per source
                      system are colocated instead (alarm-simulator/tests, work-order-service/tests)
docs/                 architecture, MCP tool catalog, RAG design, API integration, decisions, limitations
scripts/              seed_alarm_db.py, seed_work_order_db.py, ingest.py wrapper
postman/              Reference API spec the simulator was built against
```

## Coverage Report

`make coverage` generates an HTML report at `htmlcov/index.html` for the root suite plus terminal
coverage summaries for both source-system services.

## Demo

See the demo video link and screenshots the submission message points to (recorded separately --
see `docs/known-limitations.md` for what was and wasn't exercised against a live LLM in this
environment).
