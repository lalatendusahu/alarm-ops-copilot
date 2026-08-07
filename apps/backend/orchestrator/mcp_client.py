"""MCP client integration: discovers tools across all configured MCP servers and
dispatches namespaced tool calls to the right one, each over its own short-lived
streamable-http session.
"""
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from apps.backend.config import settings


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
        return f"{self.server}.{self.name}"

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


class MCPToolRegistry:
    def __init__(self, servers: dict[str, str] | None = None):
        self.servers = servers or settings.mcp_servers
        self._tools: list[DiscoveredTool] = []

    async def discover(self) -> list[DiscoveredTool]:
        discovered = []
        for server_name, url in self.servers.items():
            try:
                async with _session(url) as session:
                    result = await session.list_tools()
                    for tool in result.tools:
                        discovered.append(DiscoveredTool(
                            server=server_name, name=tool.name,
                            description=tool.description or "", input_schema=tool.inputSchema,
                        ))
            except ToolUnavailableError:
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
        if "." not in namespaced_name:
            return {"error": f"'{namespaced_name}' is not a valid namespaced tool name"}, True

        server_name, tool_name = namespaced_name.split(".", 1)
        url = self.servers.get(server_name)
        if not url:
            return {"error": f"unknown MCP server '{server_name}'"}, True

        try:
            async with _session(url) as session:
                result = await session.call_tool(tool_name, arguments)
        except ToolUnavailableError as exc:
            return {"error": f"MCP server '{server_name}' is unavailable: {exc}"}, True

        text = "\n".join(block.text for block in result.content if hasattr(block, "text"))
        if result.isError:
            return {"error": text or "tool returned an error"}, True

        import json
        try:
            return json.loads(text), False
        except json.JSONDecodeError:
            return {"text": text}, False
