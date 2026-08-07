import json
from dataclasses import dataclass

import pytest

from apps.backend.orchestrator import engine as engine_module
from apps.backend.orchestrator.engine import run_turn


@dataclass
class FakeFunctionCall:
    name: str
    arguments: str


@dataclass
class FakeToolCall:
    id: str
    function: FakeFunctionCall


@dataclass
class FakeAssistantMessage:
    content: str | None
    tool_calls: list


class FakeLLMClient:
    """Scripted LLM: each entry in `steps` is either ("tool", [(name, args_dict), ...])
    or ("stop", "final text"). plan_step consumes one entry per call; final_answer is
    only reached when the engine explicitly requests grounded synthesis."""

    def __init__(self, steps):
        self._steps = list(steps)
        self.final_answer_calls = 0
        self.plan_step_calls = 0

    async def plan_step(self, messages, tools):
        self.plan_step_calls += 1
        kind, payload = self._steps.pop(0)
        if kind == "stop":
            return FakeAssistantMessage(content=payload, tool_calls=[])
        tool_calls = [
            FakeToolCall(id=f"call-{i}", function=FakeFunctionCall(name=name, arguments=json.dumps(args)))
            for i, (name, args) in enumerate(payload)
        ]
        return FakeAssistantMessage(content=None, tool_calls=tool_calls)

    async def final_answer(self, messages):
        self.final_answer_calls += 1
        return "synthesized grounded answer"


class FakeRegistry:
    def __init__(self, responses: dict[str, tuple[dict, bool]]):
        self.responses = responses
        self.calls = []

    def openai_tool_specs(self):
        return [{"type": "function", "function": {"name": n, "parameters": {}}} for n in self.responses]

    async def call(self, name, args):
        self.calls.append((name, args))
        if name not in self.responses:
            return {"error": f"unknown tool {name}"}, True
        return self.responses[name]


@pytest.mark.asyncio
async def test_multi_step_chain_across_two_mcp_servers():
    llm = FakeLLMClient([
        ("tool", [("alarm.search_assets", {"query": "Boiler Feed Pump 101"})]),
        ("tool", [("workorders.get_maintenance_history", {"asset_id": "AST-1001"})]),
        ("stop", None),
    ])
    registry = FakeRegistry({
        "alarm.search_assets": ({"trace_id": "t1", "data": {"results": [{"asset_id": "AST-1001"}]}}, False),
        "workorders.get_maintenance_history": ({"trace_id": "t2", "data": {"history": []}}, False),
    })

    result = await run_turn("investigate Boiler Feed Pump 101", [], registry, llm)

    servers_called = {step["server"] for step in result.trace.as_dicts()}
    assert servers_called == {"alarm", "workorders"}
    assert registry.calls[0] == ("alarm.search_assets", {"query": "Boiler Feed Pump 101"})
    assert llm.final_answer_calls == 1  # loop used tools, so grounded synthesis pass runs


@pytest.mark.asyncio
async def test_rag_results_are_collected_as_citations(monkeypatch):
    canned = {"results": [
        {"chunk_id": "doc::sec::0", "doc_id": "doc", "title": "Doc", "section": "sec", "source_path": "x.md", "text": "...", "score": 0.9}
    ]}
    monkeypatch.setattr(engine_module, "search_documents", lambda query, top_k=None: (canned, False))

    llm = FakeLLMClient([
        ("tool", [("rag.search_documents", {"query": "bearing vibration"})]),
        ("stop", None),
    ])
    registry = FakeRegistry({})

    result = await run_turn("what does the procedure say about vibration?", [], registry, llm)

    assert len(result.rag_citations) == 1
    assert result.rag_citations[0]["doc_id"] == "doc"


@pytest.mark.asyncio
async def test_duplicate_rag_citations_are_deduplicated(monkeypatch):
    canned = {"results": [{"chunk_id": "a::b::0", "doc_id": "a", "title": "A", "section": "b", "source_path": "a.md", "text": "x", "score": 0.5}]}
    monkeypatch.setattr(engine_module, "search_documents", lambda query, top_k=None: (canned, False))

    llm = FakeLLMClient([
        ("tool", [("rag.search_documents", {"query": "one"}), ("rag.search_documents", {"query": "two"})]),
        ("stop", None),
    ])
    result = await run_turn("question", [], FakeRegistry({}), llm)

    assert len(result.rag_citations) == 1


@pytest.mark.asyncio
async def test_tool_error_does_not_crash_the_turn_and_is_recorded():
    llm = FakeLLMClient([
        ("tool", [("alarm.get_alarm_by_id", {"alarm_id": "missing"})]),
        ("stop", None),
    ])
    registry = FakeRegistry({"alarm.get_alarm_by_id": ({"error": "not found"}, True)})

    result = await run_turn("look up alarm missing", [], registry, llm)

    assert len(result.trace.failed_steps()) == 1
    assert result.trace.failed_steps()[0].error == "not found"
    assert result.answer  # turn still produces an answer instead of raising


@pytest.mark.asyncio
async def test_unavailable_mcp_server_is_reported_as_a_failed_step_not_an_exception():
    llm = FakeLLMClient([
        ("tool", [("workorders.search_work_orders", {})]),
        ("stop", None),
    ])
    registry = FakeRegistry({"workorders.search_work_orders": ({"error": "MCP server 'workorders' is unavailable: connection refused"}, True)})

    result = await run_turn("find work orders", [], registry, llm)

    assert result.trace.failed_steps()[0].server == "workorders"
    assert "unavailable" in result.trace.failed_steps()[0].error


@pytest.mark.asyncio
async def test_malformed_tool_arguments_default_to_empty_dict():
    registry = FakeRegistry({"alarm.list_kpi_definitions": ({"trace_id": "t", "data": {}}, False)})
    llm = FakeLLMClient([("stop", "done")])  # unused; plan_step is overridden below

    call_count = {"n": 0}

    async def scripted_plan_step(messages, tools):
        call_count["n"] += 1
        if call_count["n"] == 1:
            bad_call = FakeToolCall(id="c1", function=FakeFunctionCall(name="alarm.list_kpi_definitions", arguments="{not valid json"))
            return FakeAssistantMessage(content=None, tool_calls=[bad_call])
        return FakeAssistantMessage(content="done", tool_calls=[])

    llm.plan_step = scripted_plan_step

    result = await run_turn("run a kpi", [], registry, llm)

    assert registry.calls == [("alarm.list_kpi_definitions", {})]
    assert result.answer


@pytest.mark.asyncio
async def test_direct_answer_skips_grounded_synthesis_pass():
    llm = FakeLLMClient([("stop", "hi there, how can I help?")])
    result = await run_turn("hello", [], FakeRegistry({}), llm)

    assert result.answer == "hi there, how can I help?"
    assert llm.final_answer_calls == 0
    assert result.trace.steps == []


@pytest.mark.asyncio
async def test_max_iterations_cap_still_produces_a_grounded_answer(monkeypatch):
    monkeypatch.setattr(engine_module.settings, "max_tool_iterations", 3)
    registry = FakeRegistry({"alarm.get_alarms": ({"trace_id": "t", "data": {"data": []}}, False)})
    llm = FakeLLMClient([("tool", [("alarm.get_alarms", {})]) for _ in range(10)])

    await run_turn("keep looking", [], registry, llm)

    assert llm.plan_step_calls == 3
    assert llm.final_answer_calls == 1
    assert len(registry.calls) == 3


@pytest.mark.asyncio
async def test_prior_history_is_preserved_and_system_prompt_not_duplicated():
    history = [
        {"role": "system", "content": "existing system prompt"},
        {"role": "user", "content": "earlier question"},
        {"role": "assistant", "content": "earlier answer"},
    ]
    llm = FakeLLMClient([("stop", "second answer")])
    result = await run_turn("follow-up question", history, FakeRegistry({}), llm)

    system_messages = [m for m in result.messages if m["role"] == "system"]
    assert len(system_messages) == 1
    assert result.messages[-2]["content"] == "follow-up question"
    assert result.messages[-1]["content"] == "second answer"
