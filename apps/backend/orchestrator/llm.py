from openai import AsyncOpenAI

from apps.backend.config import settings

PLANNER_SYSTEM_PROMPT = """You are an enterprise operations copilot for alarm management. You have
access to tools from two MCP servers (namespaced "alarm__*" and "workorders__*") and a document
search tool ("rag__search_documents"). Use tools to gather the facts you need before answering --
do not guess at asset ids, alarm ids, or numeric results. Resolve a named asset to its asset_id
with alarm__search_assets before calling tools that require one. Chain tools when a later call
needs the output of an earlier one (for example: generate a KPI calculation before executing it,
or look up an alarm before scoring or recommending it). Call rag__search_documents whenever the
question could benefit from operating procedures, troubleshooting guidance, or policy. Creating a
work order is a write operation: only call workorders__create_work_order_draft with confirm=true
if the user has explicitly approved it in this conversation; otherwise leave confirm=false so the
user sees a preview first. When you have enough information, stop calling tools and let the final
answer be written from what you have gathered."""

FINAL_ANSWER_INSTRUCTION = """Write the final answer now. Base it only on the tool results and
document excerpts already gathered in this conversation -- do not introduce facts that did not
come from a tool call or a retrieved document. Cite document titles/sections for anything drawn
from a retrieved document, and name the MCP tool(s) that produced any data point. If the
gathered evidence does not fully answer the question, say what is missing instead of guessing."""


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.model = model or settings.openai_model
        self._client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)

    async def plan_step(self, messages: list[dict], tools: list[dict]):
        response = await self._client.chat.completions.create(
            model=self.model, messages=messages, tools=tools or None, tool_choice="auto" if tools else None,
        )
        return response.choices[0].message

    async def final_answer(self, messages: list[dict]) -> str:
        response = await self._client.chat.completions.create(model=self.model, messages=messages)
        return response.choices[0].message.content or ""
