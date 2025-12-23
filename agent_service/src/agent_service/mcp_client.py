"""MCP client for connecting to tool servers."""
from __future__ import annotations

import json
import logging
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

log = logging.getLogger("mcp-client")


class McpConnection:
    """Manages connection to an MCP server over stdio."""

    def __init__(self) -> None:
        self._exit_stack = AsyncExitStack()
        self.session: ClientSession | None = None

    async def connect(
        self, server_script: str, env: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Connect to an MCP server subprocess and return available tools."""
        # Get the src directory for the MCP server so Python can find the module
        script_path = Path(server_script)
        src_dir = str(script_path.parent.parent)  # Go up from mcp_server/ to src/
        
        # Add src directory to PYTHONPATH so relative imports work
        current_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{src_dir}:{current_pythonpath}" if current_pythonpath else src_dir
        
        params = StdioServerParameters(
            command="python",
            args=[server_script],
            env=env,
        )
        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(params)
        )
        read_stream, write_stream = stdio_transport
        self.session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self.session.initialize()

        tools_result = await self.session.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.inputSchema,
            }
            for t in tools_result.tools
        ]

    async def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Call a tool and return the parsed result."""
        assert self.session is not None

        result = await self.session.call_tool(name, args)

        # MCP tools return content blocks; extract and parse JSON from text
        if result.content and len(result.content) > 0:
            first_block = result.content[0]
            if hasattr(first_block, "text") and first_block.text:
                try:
                    return json.loads(first_block.text)
                except json.JSONDecodeError as e:
                    log.warning("Failed to parse tool response as JSON: %s", e)
                    return {"ok": True, "raw": first_block.text}

        # Fallback for empty or unexpected responses
        return {"ok": True, "result": "completed"}

    async def close(self) -> None:
        """Close the connection."""
        await self._exit_stack.aclose()

