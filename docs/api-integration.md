# API Integration

## Alarm Management API Simulator (`alarm-simulator/`)

A FastAPI + SQLite implementation of the endpoint surface defined by the Postman collections in
`postman/` (`Alarm-API-Simulator.postman_collection.json` is the E2E baseline;
`postman/chaining/` has 10 multi-step chaining flows the simulator was built and validated
against).

- **Base URL**: `ALARM_API_BASE_URL` (default `http://localhost:8000`).
- **Auth**: `Authorization: Bearer <ALARM_API_TOKEN>` required on every route except `/health`.
  Missing or wrong token -> `401`.
- **Trace headers**: `trace_id`, `x-client-id`, `x-metadata-tag` are read if present; a
  `trace_id` is generated when absent. The resolved id is echoed back as the `x-trace-id`
  response header and included in structured log lines -- see `app/logging_utils.py`.
- **Pagination**: `GET /alarms` takes `page`, `page_size` (max 500), `sort_by`
  (`start_time`\|`severity`\|`asset_id`), `sort_order`. Response includes `page`, `page_size`,
  `total`, `total_pages`.
- **Error mapping**: `404` for unknown asset/alarm/calculation ids, `400` for invalid query
  combinations (bad `sort_by`, unknown `calculation_type`), `422` from FastAPI/Pydantic for
  malformed request bodies.
- **Endpoints**: `/health`, `/assets/search`, `/assets/{id}/metadata`, `/alarms`,
  `/alarms/{id}`, `/alarms/summary`, `/alarms/trends`, `/alarms/correlation`,
  `/alarms/flood-analysis`, `/alarms/rationalization-candidates`, `/alarms/priority-score`,
  `/recommendations/operator-actions`, `/calculation-code/generate`,
  `/calculation-code/execute`, `/analytics/kpi-definitions` -- see `docs/mcp-tool-catalog.md`
  for the request/response shape of each, since every endpoint is 1:1 with an MCP tool.

### Seed Data

`app/seed.py` generates a deterministic (fixed-seed) dataset: 20 assets across 5 units and 3
sites, with a few intentional patterns so every advanced operation has real signal to work with
without needing 90 days of live data:

- **Boiler Feed Pump 101** gets 20 forced occurrences of "High Bearing Vibration" at high/critical
  severity spread across the window -- the recurring-alarm signal the mandatory scenario
  investigates.
- **Unit 2** gets a 14-alarm burst inside an 8-minute window -- a genuine flood for
  `analyze_alarm_flood` to detect.
- **Unit 4**'s bypass valve gets 30 sub-minute chattering alarms -- signal for
  `nuisance_alarm_score`.
- **Unit 1**'s feedwater valve gets several multi-hour stale alarms -- signal for the
  rationalization stale-duration path.

Reseed with `python scripts/seed_alarm_db.py --reset`.

## Work Order API (`work-order-service/`)

A second, independently-designed source system (not from the Postman spec -- it's the
candidate-built "second MCP domain"). Same auth/trace conventions as the alarm API
(`WORK_ORDER_API_TOKEN`, `trace_id`/`x-client-id` headers, `x-trace-id` echoed back).

- **Endpoints**: `/health`, `/work-orders` (list, paginated), `/work-orders/{id}`,
  `/assets/{id}/maintenance-history`, `/work-orders/draft` (preview, never persists),
  `/work-orders` (POST, persists -- requires `confirm: true` in the body or returns `400`).
- **Seed data**: a handful of work orders tied to the same asset ids the alarm simulator uses,
  including two completed corrective work orders on Boiler Feed Pump 101 referencing the bearing
  replacement -- so `get_maintenance_history` has something meaningful to surface for the
  mandatory scenario.

Reseed with `python scripts/seed_work_order_db.py --reset`.

## Chaining Flows

The Postman `chaining/` collection documents 10 multi-step flows against the raw HTTP API (asset
search -> summary -> rationalization; flood -> alarms -> summary; KPI generate -> execute ->
summary; etc). The MCP layer preserves the same chaining shape one level up: the LLM calls
`alarm.search_assets`, gets an `asset_id` back, and passes it into `alarm.get_alarm_summary`,
exactly like the Postman flow does at the HTTP level -- see
`tests/e2e/test_boiler_feed_pump_scenario.py` for an automated version of this across MCP.
