import json
from dataclasses import dataclass, field

from apps.backend.config import settings
from apps.backend.orchestrator.llm import FINAL_ANSWER_INSTRUCTION, PLANNER_SYSTEM_PROMPT, LLMClient
from apps.backend.orchestrator.mcp_client import NAMESPACE_SEP, MCPToolRegistry
from apps.backend.orchestrator.rag_tool import RAG_TOOL_NAME, RAG_TOOL_SPEC, search_documents
from apps.backend.orchestrator.trace import TraceCollector


@dataclass
class TurnResult:
    answer: str
    messages: list[dict]
    trace: TraceCollector
    rag_citations: list[dict] = field(default_factory=list)


def _assistant_tool_call_message(assistant_msg) -> dict:
    return {
        "role": "assistant",
        "content": assistant_msg.content,
        "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in assistant_msg.tool_calls
        ],
    }


def _dedupe_citations(citations: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for c in citations:
        if c["chunk_id"] in seen:
            continue
        seen.add(c["chunk_id"])
        deduped.append(c)
    return deduped


RAG_REDACTED_NOTICE = "[document search result withheld from planning context -- available only to the final answer]"


def _rag_call_ids(messages: list[dict]) -> set[str]:
    ids = set()
    for m in messages:
        if m.get("role") == "assistant":
            for tc in m.get("tool_calls") or []:
                if tc["function"]["name"] == RAG_TOOL_NAME:
                    ids.add(tc["id"])
    return ids


def _redact_rag_results(messages: list[dict]) -> list[dict]:
    """Retrieved document text must never reach the tool-selection step -- only the final
    grounded-answer call sees it -- so injected instructions in a document can't steer
    which tool the model calls next. Text is dropped by tool_call_id rather than content
    sniffing, since content is untrusted and any string match on it could itself be spoofed.
    """
    rag_ids = _rag_call_ids(messages)
    if not rag_ids:
        return messages
    return [
        {**m, "content": RAG_REDACTED_NOTICE} if m.get("role") == "tool" and m.get("tool_call_id") in rag_ids else m
        for m in messages
    ]


WRITE_TOOLS_FORCED_TO_PREVIEW = {"workorders__create_work_order_draft"}


async def execute_tool(name: str, args: dict, registry: MCPToolRegistry) -> tuple[dict, bool]:
    if name == RAG_TOOL_NAME:
        return search_documents(query=args.get("query", ""), top_k=args.get("top_k"))
    if name in WRITE_TOOLS_FORCED_TO_PREVIEW:
        # confirm=True must only ever come from the human clicking Approve in the GUI
        # (apps/frontend/chainlit_app.py:approve_work_order, which calls registry.call
        # directly and never goes through this function). A model deciding on its own --
        # even at a user's explicit request in the prompt -- cannot persist a write.
        args = {**args, "confirm": False}
    return await registry.call(name, args)


async def run_turn(
    user_message: str,
    history: list[dict],
    registry: MCPToolRegistry,
    llm: LLMClient | None = None,
) -> TurnResult:
    llm = llm or LLMClient()
    trace = TraceCollector()
    rag_citations: list[dict] = []

    messages = list(history)
    if not messages or messages[0].get("role") != "system":
        messages.insert(0, {"role": "system", "content": PLANNER_SYSTEM_PROMPT})
    messages.append({"role": "user", "content": user_message})

    tool_specs = registry.openai_tool_specs() + [RAG_TOOL_SPEC]

    used_tools = False
    final_text = None

    for _ in range(settings.max_tool_iterations):
        assistant_msg = await llm.plan_step(_redact_rag_results(messages), tool_specs)

        if not assistant_msg.tool_calls:
            messages.append({"role": "assistant", "content": assistant_msg.content or ""})
            if not used_tools:
                final_text = assistant_msg.content or ""
            break

        used_tools = True
        messages.append(_assistant_tool_call_message(assistant_msg))

        for tool_call in assistant_msg.tool_calls:
            name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            server = name.split(NAMESPACE_SEP, 1)[0] if NAMESPACE_SEP in name else name
            short_name = name.split(NAMESPACE_SEP, 1)[1] if NAMESPACE_SEP in name else name
            timer = trace.timer().begin(server, short_name, args)

            result, is_error = await execute_tool(name, args, registry)
            step_trace_id = result.get("trace_id", "") if isinstance(result, dict) else ""

            if is_error:
                timer.finish_error(str(result.get("error", result)), step_trace_id)
            else:
                timer.finish_ok(result, step_trace_id)
                if name == RAG_TOOL_NAME:
                    rag_citations.extend(result.get("results", []))

            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})

    if final_text is None:
        final_messages = messages + [{"role": "system", "content": FINAL_ANSWER_INSTRUCTION}]
        final_text = await llm.final_answer(final_messages)
        messages.append({"role": "assistant", "content": final_text})

    return TurnResult(answer=final_text, messages=messages, trace=trace, rag_citations=_dedupe_citations(rag_citations))
