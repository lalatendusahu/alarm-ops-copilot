import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import chainlit as cl  # noqa: E402

from apps.backend.orchestrator.engine import run_turn  # noqa: E402
from apps.backend.orchestrator.llm import LLMClient  # noqa: E402
from apps.backend.orchestrator.mcp_client import MCPToolRegistry  # noqa: E402
from rag.retrieval.retriever import IndexNotBuiltError, get_retriever  # noqa: E402

WELCOME_HINT = (
    "Ask about assets, alarms, KPIs, work orders, or operating procedures. Try:\n\n"
    "> Investigate recurring high-severity alarms for Boiler Feed Pump 101 over the last "
    "90 days, identify likely contributing factors, retrieve the relevant operating "
    "procedure, and provide recommended actions with source evidence.\n\n"
    "Type `/tools` at any time to see the live MCP tool schemas."
)


@cl.on_chat_start
async def start():
    registry = MCPToolRegistry()
    tools = await registry.discover()
    cl.user_session.set("registry", registry)
    cl.user_session.set("history", [])
    cl.user_session.set("llm", LLMClient())
    cl.user_session.set("pending_draft", None)

    by_server: dict[str, list] = {}
    for t in tools:
        by_server.setdefault(t.server, []).append(t)

    lines = ["**MCP servers connected**"]
    if not tools:
        lines.append("_No MCP servers reachable. Start the alarm-management and work-orders MCP "
                      "servers (see README), then start a new chat._")
    for server, server_tools in sorted(by_server.items()):
        lines.append(f"\n**{server}** -- {len(server_tools)} tools")
        for t in sorted(server_tools, key=lambda x: x.name):
            lines.append(f"- `{t.name}`: {t.description}")

    try:
        get_retriever()
        rag_status = "RAG index loaded and ready."
    except IndexNotBuiltError as exc:
        rag_status = f"RAG index not available: {exc}"

    await cl.Message(content="\n".join(lines) + f"\n\n**Document RAG:** {rag_status}\n\n{WELCOME_HINT}").send()


@cl.on_message
async def on_message(message: cl.Message):
    text = message.content.strip()
    if text == "/tools":
        await _send_tool_catalog()
        return

    registry: MCPToolRegistry = cl.user_session.get("registry")
    llm: LLMClient = cl.user_session.get("llm")
    history: list[dict] = cl.user_session.get("history")

    try:
        async with cl.Step(name="Copilot reasoning", type="run") as run_step:
            run_step.input = text
            result = await run_turn(text, history, registry, llm)
            run_step.output = f"{len(result.trace.steps)} tool call(s), {len(result.rag_citations)} document citation(s)"
    except Exception as exc:  # noqa: BLE001 -- surface any failure as a chat message, never crash the session
        await cl.Message(content=f"Something went wrong while processing that request: {exc}").send()
        return

    for step in result.trace.steps:
        async with cl.Step(name=f"{step.server}.{step.tool}", type="tool") as ui_step:
            ui_step.input = json.dumps(step.input, indent=2)
            if step.status == "ok":
                ui_step.output = json.dumps(step.output, indent=2)[:4000]
            else:
                ui_step.is_error = True
                ui_step.output = step.error

    elements = [
        cl.Text(
            name=f"{c['title']} — {c['section']}",
            content=f"Relevance score: {c['score']}\nSource: {c['source_path']}\n\n{c['text']}",
            display="side",
        )
        for c in result.rag_citations
    ]

    actions = _draft_actions_if_present(result.trace.steps)

    failed = result.trace.failed_steps()
    footer = ""
    if failed:
        failed_desc = ", ".join(f"{s.server}.{s.tool}" for s in failed)
        footer = f"\n\n_{len(failed)} tool call(s) failed this turn ({failed_desc}); the answer reflects only what was successfully gathered._"

    cl.user_session.set("history", result.messages)
    await cl.Message(content=result.answer + footer, elements=elements, actions=actions).send()


def _draft_actions_if_present(steps) -> list:
    for step in steps:
        if step.tool != "create_work_order_draft" or step.status != "ok":
            continue
        data = (step.output or {}).get("data", {})
        if data.get("status") != "draft":
            continue
        cl.user_session.set("pending_draft", {
            "asset_id": step.input.get("asset_id"),
            "title": step.input.get("title"),
            "description": step.input.get("description", ""),
            "work_type": step.input.get("work_type", "corrective"),
            "priority": step.input.get("priority", "medium"),
        })
        return [
            cl.Action(name="approve_work_order", label="Approve & create work order", payload={}),
            cl.Action(name="reject_work_order", label="Discard draft", payload={}),
        ]
    return []


@cl.action_callback("approve_work_order")
async def approve_work_order(action: cl.Action):
    draft = cl.user_session.get("pending_draft")
    registry: MCPToolRegistry = cl.user_session.get("registry")
    await action.remove()

    if not draft:
        await cl.Message(content="No pending draft to confirm -- it may have already been actioned.").send()
        return

    result, is_error = await registry.call("workorders__create_work_order_draft", {**draft, "confirm": True})
    cl.user_session.set("pending_draft", None)

    if is_error:
        await cl.Message(content=f"Could not create the work order: {result.get('error')}").send()
        return

    wo = result["data"]
    await cl.Message(content=f"Work order **{wo['work_order_id']}** created for {draft['asset_id']} (status: {wo['status']}).").send()


@cl.action_callback("reject_work_order")
async def reject_work_order(action: cl.Action):
    cl.user_session.set("pending_draft", None)
    await action.remove()
    await cl.Message(content="Draft discarded. No work order was created.").send()


async def _send_tool_catalog():
    registry: MCPToolRegistry = cl.user_session.get("registry")
    if not registry or not registry.tools:
        await cl.Message(content="No MCP tools discovered yet.").send()
        return
    blocks = []
    for t in sorted(registry.tools, key=lambda x: x.namespaced_name):
        blocks.append(f"### `{t.namespaced_name}`\n{t.description}\n```json\n{json.dumps(t.input_schema, indent=2)}\n```")
    await cl.Message(content="\n\n".join(blocks)).send()
