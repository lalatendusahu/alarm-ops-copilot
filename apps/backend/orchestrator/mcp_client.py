"""MCP client integration: discovers tools across all configured MCP servers and
dispatches namespaced tool calls to the right one, each over its own short-lived
streamable-http session.
"""
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from apps.backend.config import settings

logger = logging.getLogger("orchestrator.mcp_client")

# OpenAI function names must match ^[a-zA-Z0-9_-]+$ -- a "." is not allowed, so tools
# are namespaced with a double underscore instead (alarm__search_assets, not alarm.search_assets).
NAMESPACE_SEP = "__"


class ToolUnavailableError(Exception):
    """Raised when an MCP server can't be reached at all (connection refused, DNS, timeout)."""


@dataclass
class DiscoveredTool:
    server: str
    name: str
    description: str
    input_schema: dict

    @property
    def namespaced_name(self) -> str:
        return f"{self.server}{NAMESPACE_SEP}{self.name}"

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.namespaced_name,
                "description": self.description or "",
                "parameters": self.input_schema or {"type": "object", "properties": {}},
            },
        }


@asynccontextmanager
async def _session(url: str):
    try:
        async with streamablehttp_client(url) as (read, write, _get_session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    except* Exception as group:
        raise ToolUnavailableError(str(group.exceptions[0]) if group.exceptions else str(group)) from group


async def _discover_from(server_name: str, url: str) -> list[DiscoveredTool]:
    async with _session(url) as session:
        result = await session.list_tools()
        return [
            DiscoveredTool(server=server_name, name=tool.name, description=tool.description or "", input_schema=tool.inputSchema)
            for tool in result.tools
        ]


async def _call_tool(url: str, tool_name: str, arguments: dict):
    async with _session(url) as session:
        return await session.call_tool(tool_name, arguments)


class MCPToolRegistry:
    def __init__(self, servers: dict[str, str] | None = None):
        self.servers = servers or settings.mcp_servers
        self._tools: list[DiscoveredTool] = []

    async def discover(self) -> list[DiscoveredTool]:
        discovered = []
        for server_name, url in self.servers.items():
            try:
                discovered.extend(await _discover_from(server_name, url))
            except ToolUnavailableError as exc:
                logger.warning("MCP server %r unreachable during discovery (%s): %s", server_name, url, exc)
                continue  # server down at discovery time; its tools are simply not offered this turn
        self._tools = discovered
        return discovered

    @property
    def tools(self) -> list[DiscoveredTool]:
        return self._tools

    def openai_tool_specs(self) -> list[dict]:
        return [t.to_openai_tool() for t in self._tools]

    async def call(self, namespaced_name: str, arguments: dict) -> tuple[dict, bool]:
        """Returns (result_dict, is_error)."""
        if NAMESPACE_SEP not in namespaced_name:
            return {"error": f"'{namespaced_name}' is not a valid namespaced tool name"}, True

        server_name, tool_name = namespaced_name.split(NAMESPACE_SEP, 1)
        url = self.servers.get(server_name)
        if not url:
            return {"error": f"unknown MCP server '{server_name}'"}, True

        try:
            result = await _call_tool(url, tool_name, arguments)
        except ToolUnavailableError as exc:
            logger.warning("MCP server %r unavailable during call to %r: %s", server_name, tool_name, exc)
            return {"error": f"MCP server '{server_name}' is unavailable: {exc}"}, True

        text = "\n".join(block.text for block in result.content if hasattr(block, "text"))
        if result.isError:
            return {"error": text or "tool returned an error"}, True

        try:
            return json.loads(text), False
        except json.JSONDecodeError:
            return {"text": text}, False
