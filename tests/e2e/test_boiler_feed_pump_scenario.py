"""End-to-end coverage for the mandatory acceptance scenario:

    "Investigate recurring high-severity alarms for Boiler Feed Pump 101 over the last
    90 days, identify likely contributing factors, retrieve the relevant operating
    procedure, and provide recommended actions with source evidence."

This runs the real alarm simulator, the real work-order service, both real MCP servers
over real streamable-http connections, and the real RAG retriever against the real
document corpus. The only thing stubbed out is the LLM call itself -- a real OpenAI call
would make this test flaky, slow, and dependent on a paid API key, so a scripted planner
reproduces the tool-call sequence a real model would make for this question. Everything
downstream of that -- MCP transport, tool execution, error handling, and retrieval -- is
exercised for real.
"""
import json

import pytest

from apps.backend.orchestrator.engine import run_turn
from apps.backend.orchestrator.mcp_client import MCPToolRegistry


class ScriptedPlanner:
    def __init__(self, plan):
        self._plan = list(plan)
        self.final_answer_calls = 0

    async def plan_step(self, messages, tools):
        from dataclasses import dataclass

        @dataclass
        class Call:
            id: str
            function: "Fn"

        @dataclass
        class Fn:
            name: str
            arguments: str

        @dataclass
        class Msg:
            content: str | None
            tool_calls: list

        if not self._plan:
            return Msg(content=None, tool_calls=[])
        name, args = self._plan.pop(0)
        return Msg(content=None, tool_calls=[Call(id="c1", function=Fn(name=name, arguments=json.dumps(args)))])

    async def final_answer(self, messages):
        self.final_answer_calls += 1
        tool_messages = [m for m in messages if m.get("role") == "tool"]
        return f"Grounded answer synthesized from {len(tool_messages)} tool results."


@pytest.mark.asyncio
async def test_boiler_feed_pump_investigation_end_to_end(live_stack):
    registry = MCPToolRegistry(servers={
        "alarm": live_stack["alarm_mcp_url"],
        "workorders": live_stack["workorder_mcp_url"],
    })
    discovered = await registry.discover()
    assert {t.namespaced_name for t in discovered} >= {"alarm__search_assets", "workorders__get_maintenance_history"}

    time_range = {"start_time": "2026-05-01T00:00:00Z", "end_time": "2026-08-01T00:00:00Z"}
    planner = ScriptedPlanner([
        ("alarm__search_assets", {"query": "Boiler Feed Pump 101"}),
        ("alarm__get_alarm_summary", {**time_range, "asset_ids": ["AST-1001"], "severity": ["high", "critical"], "group_by": ["alarm_name"]}),
        ("alarm__get_rationalization_candidates", {**time_range, "asset_ids": ["AST-1001"], "recurrence_threshold": 5}),
        ("workorders__get_maintenance_history", {"asset_id": "AST-1001"}),
        ("rag__search_documents", {"query": "recurring high bearing vibration boiler feed pump response procedure"}),
    ])

    result = await run_turn(
        "Investigate recurring high-severity alarms for Boiler Feed Pump 101 over the last 90 "
        "days, identify likely contributing factors, retrieve the relevant operating procedure, "
        "and provide recommended actions with source evidence.",
        [], registry, planner,
    )

    steps = result.trace.as_dicts()
    alarm_steps = [s for s in steps if s["server"] == "alarm"]
    workorder_steps = [s for s in steps if s["server"] == "workorders"]

    # 1. asset resolution through an MCP tool
    search_step = next(s for s in alarm_steps if s["tool"] == "search_assets")
    assert search_step["status"] == "ok"
    assert search_step["output"]["data"]["results"][0]["asset_id"] == "AST-1001"

    # 2. multi-step alarm API chaining through MCP
    assert {s["tool"] for s in alarm_steps} >= {"get_alarm_summary", "get_rationalization_candidates"}
    summary_groups = next(s for s in alarm_steps if s["tool"] == "get_alarm_summary")["output"]["data"]["groups"]
    assert any(g["alarm_name"] == "High Bearing Vibration" for g in summary_groups)
    candidates = next(s for s in alarm_steps if s["tool"] == "get_rationalization_candidates")["output"]["data"]["candidates"]
    assert any(c["alarm_name"] == "High Bearing Vibration" for c in candidates)

    # maintenance history from the second MCP server
    assert workorder_steps and workorder_steps[0]["status"] == "ok"

    # 3. document retrieval through RAG, with citations
    assert result.rag_citations
    cited_docs = {c["doc_id"] for c in result.rag_citations}
    assert cited_docs & {"boiler-feed-pump-operating-procedure", "pump-troubleshooting-guide"}

    # 4/5/6. combined reasoning, citations, and a grounded final answer referencing gathered evidence
    assert result.answer
    assert planner.final_answer_calls == 1

    # 7. MCP execution trace captured every step with no unexplained failures
    assert all(s["status"] == "ok" for s in steps)
    assert len(steps) == 5
