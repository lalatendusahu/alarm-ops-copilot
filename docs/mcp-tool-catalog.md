# MCP Tool Catalog

Two MCP servers, both `FastMCP` over streamable-http. Common to every tool on both servers:

- **Authentication**: the tool itself takes no auth parameters. The MCP server holds a static
  bearer token (`ALARM_API_TOKEN` / `WORK_ORDER_API_TOKEN`) read from its environment at startup
  and attaches it to every upstream HTTP call. The token is never part of a tool's input schema,
  output, or log line.
- **Timeout**: 10 seconds per upstream HTTP call (`connectors/base.py`).
- **Retry**: up to 3 attempts with exponential backoff (0.2s, 0.4s, 0.8s ...), only for timeouts,
  connection errors, and 5xx responses. 4xx responses are never retried.
- **Trace propagation**: every tool accepts an optional `trace_id`. If omitted, one is generated.
  It is sent upstream as the `trace_id` header and returned in the tool result so the orchestrator
  can correlate a whole multi-step turn under one id.
- **Error behavior**: connector exceptions are mapped to a tool-level error (MCP `isError: true`)
  with a message prefixed by the tool name and a category -- `not found`, `invalid request`,
  `authentication ... failed`, or `unavailable after retries` -- never a raw stack trace or the
  token.
- **Output envelope**: every successful call returns `{"trace_id": "...", "data": {...}}`.

Start either server independently with `python mcp-servers/<name>/server.py`; each is a normal
streamable-http MCP endpoint, so any MCP-compatible client or inspector can connect to it without
the copilot.

## Alarm Management MCP Server (`mcp-servers/alarm_management`)

14 tools, one per Alarm Management API operation, all backed by `connectors/alarm_client.py` ->
the alarm simulator (`ALARM_API_BASE_URL`).

### `search_assets`
- **Purpose**: resolve a free-text asset name/type to an `asset_id`. Usually the first call in a
  chain.
- **Input**: `query` (required), `unit`, `site`, `limit` (default 10), `trace_id`.
- **Output**: `data.results[]` of `{asset_id, asset_name, asset_type, unit, site, criticality, status}`, `data.count`.
- **Underlying operation**: `GET /assets/search`.
- **Example**: `search_assets(query="Boiler Feed Pump 101")` ->
  `{"trace_id": "...", "data": {"results": [{"asset_id": "AST-1001", "asset_name": "Boiler Feed Pump 101", ...}], "count": 1}}`

### `get_asset_metadata`
- **Purpose**: full metadata for a known asset id.
- **Input**: `asset_id` (required), `trace_id`.
- **Output**: `data` = the asset record.
- **Underlying operation**: `GET /assets/{asset_id}/metadata`.
- **Error behavior**: unknown id -> `not found`.

### `get_alarms`
- **Purpose**: list raw alarm records with filtering, sorting, pagination.
- **Input**: `asset_id`, `unit`, `site`, `status`, `start_time`, `end_time`, `page` (default 1),
  `page_size` (default 50, max 500), `sort_by` (`start_time`\|`severity`\|`asset_id`),
  `sort_order` (`asc`\|`desc`), `trace_id`.
- **Output**: `data.data[]` (alarm records), `data.page`, `data.page_size`, `data.total`, `data.total_pages`.
- **Underlying operation**: `GET /alarms`.
- **Error behavior**: invalid `sort_by` -> `invalid request`.

### `get_alarm_by_id`
- **Purpose**: full detail for one alarm.
- **Input**: `alarm_id` (required), `trace_id`.
- **Underlying operation**: `GET /alarms/{alarm_id}`. 404 -> `not found`.

### `get_alarm_summary`
- **Purpose**: aggregate counts and KPIs grouped by asset/name/severity over a time window --
  the main tool for "how often has this happened" questions.
- **Input**: `start_time`, `end_time` (required), `asset_ids`, `unit`, `site`, `severity`,
  `alarm_types`, `group_by` (e.g. `["alarm_name"]`), `kpis` (e.g.
  `["alarm_count","recurring_rate","avg_ack_delay"]`), `trace_id`.
- **Output**: `data.groups[]`, `data.total_alarm_count`.
- **Underlying operation**: `POST /alarms/summary`.
- **Example response** (Boiler Feed Pump 101, 90-day window, high/critical only):
  `{"data": {"groups": [{"alarm_name": "High Bearing Vibration", "alarm_count": 24, "recurring_rate": 0.261, "avg_ack_delay": 1400.9}], "total_alarm_count": 32}}`

### `get_alarm_trends`
- **Purpose**: time-bucketed alarm activity (hourly/daily).
- **Input**: `start_time`, `end_time` (required), `asset_ids`, `unit`, `site`, `bucket`
  (`hourly`\|`daily`), `metrics`, `trace_id`.
- **Underlying operation**: `POST /alarms/trends`.

### `analyze_alarm_correlation`
- **Purpose**: find asset pairs whose alarms fire close together in time -- root-cause hints.
- **Input**: `asset_ids` (required, 1+), `start_time`, `end_time` (required),
  `correlation_method` (default `cooccurrence`), `lag_window_minutes` (default 15),
  `severity_threshold`, `min_support` (default 1), `trace_id`.
- **Output**: `data.pairs[]` of `{asset_id_a, asset_id_b, cooccurrence_count, support, sample_alarm_pair}`.
- **Underlying operation**: `POST /alarms/correlation`.

### `analyze_alarm_flood`
- **Purpose**: detect alarm-flood windows (bursts exceeding a rate threshold).
- **Input**: `start_time`, `end_time` (required), `unit`, `site`, `threshold_count` (default 10),
  `rolling_window_minutes` (default 10), `trace_id`.
- **Output**: `data.flood_windows[]` of `{start, end, alarm_count, peak_rate_per_min}`.
- **Underlying operation**: `POST /alarms/flood-analysis`.

### `get_rationalization_candidates`
- **Purpose**: flag alarms that chatter or stay active too long -- candidates for rationalization.
- **Input**: `start_time`, `end_time` (required), `asset_ids`, `unit`, `site`,
  `recurrence_threshold` (default 5), `stale_minutes_threshold` (default 180), `trace_id`.
- **Output**: `data.candidates[]` of `{asset_id, asset_name, alarm_name, occurrence_count, avg_duration_minutes, reasons[], recommendation}`.
- **Underlying operation**: `POST /alarms/rationalization-candidates`.

### `get_alarm_priority_score`
- **Purpose**: 0-100 priority score for a single alarm (severity + asset criticality + recurrence
  + duration).
- **Input**: `alarm_id` (required), `trace_id`.
- **Output**: `data.priority_score`, `data.priority_band`, `data.factors`.
- **Underlying operation**: `POST /alarms/priority-score`. 404 on unknown alarm.

### `get_operator_recommendations`
- **Purpose**: rule-based recommended operator actions for an alarm, optionally with related
  alarms / asset context / 90-day recurrence pattern.
- **Input**: `alarm_id` (required), `include_related`, `include_asset_context`,
  `include_historical_pattern` (all default `false`), `trace_id`.
- **Underlying operation**: `POST /recommendations/operator-actions`.

### `generate_kpi_calculation`
- **Purpose**: register a KPI calculation (`alarm_flood_index`, `critical_alarm_density`,
  `operator_response_efficiency`, or `nuisance_alarm_score`) and get a `calculation_id`.
- **Input**: `calculation_type` (required), `unit`, `site`, `start_time`, `end_time`, `trace_id`.
- **Underlying operation**: `POST /calculation-code/generate`. Unknown type -> `invalid request`.
- **Chaining**: always followed by `execute_kpi_calculation` with the returned id -- this is the
  intentional two-step tool the orchestrator must chain (see `docs/design-decisions.md`).

### `execute_kpi_calculation`
- **Purpose**: run a previously generated calculation and get its numeric result.
- **Input**: `calculation_id` (required), optional filter overrides, `trace_id`.
- **Underlying operation**: `POST /calculation-code/execute`. Unknown id -> `not found`.

### `list_kpi_definitions`
- **Purpose**: enumerate every KPI name the API can compute, with description and unit.
- **Input**: `trace_id` only.
- **Underlying operation**: `GET /analytics/kpi-definitions`.

## Work Order MCP Server (`mcp-servers/work_orders`)

4 tools, backed by `connectors/workorder_client.py` -> the work-order mock service
(`WORK_ORDER_API_BASE_URL`).

### `search_work_orders`
- **Purpose**: list work orders filtered by asset and/or status.
- **Input**: `asset_id`, `status` (`open`\|`in_progress`\|`completed`), `page` (default 1),
  `page_size` (default 20, max 200), `trace_id`.
- **Underlying operation**: `GET /work-orders`.

### `get_work_order_by_id`
- **Purpose**: full detail for one work order.
- **Input**: `work_order_id` (required), `trace_id`.
- **Underlying operation**: `GET /work-orders/{id}`. 404 on unknown id.

### `get_maintenance_history`
- **Purpose**: an asset's completed work orders -- used to check whether a recurring alarm has
  already had a corrective repair attempted.
- **Input**: `asset_id` (required), `limit` (default 20, max 100), `trace_id`.
- **Output**: `data.asset_id`, `data.history[]`.
- **Underlying operation**: `GET /assets/{asset_id}/maintenance-history`.
- **Example**: `get_maintenance_history(asset_id="AST-1001")` returns the bearing-replacement and
  vibration-follow-up work orders seeded for Boiler Feed Pump 101.

### `create_work_order_draft`
- **Purpose**: the one write-capable tool in the catalog. Drafts a new work order.
- **Input**: `asset_id`, `title` (required), `description`, `work_type` (default `corrective`),
  `priority` (default `medium`), `confirm` (default `false`), `trace_id`.
- **Behavior**: with `confirm=false` (the default), calls `POST /work-orders/draft` -- a
  **preview only**, nothing is written. With `confirm=true`, calls `POST /work-orders`, which
  persists the record and returns a real `work_order_id`. The planner's system prompt instructs
  the model to only pass `confirm=true` once a human has approved it in the conversation; the
  Chainlit GUI enforces this with an explicit Approve/Discard action button rather than trusting
  the model's word for it.
- **Error behavior**: calling the create endpoint with `confirm=false` server-side is rejected
  with 400 -> `invalid request` (defense in depth, in case a client bypasses the MCP tool's own
  default).
