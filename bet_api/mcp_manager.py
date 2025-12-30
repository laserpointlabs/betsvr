import os
import sys
import logging
from contextlib import AsyncExitStack
from typing import Dict, List, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPManager:
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.tools_map: Dict[str, str] = {}  # tool_name -> server_name

    async def start_servers(self) -> None:
        """
        Start the MCP servers needed by betsvr.

        Note: The `mcp_servers/` directory is mounted into the container at `/mcp_servers`.
        """
        servers = {
            "betting_monitor": {
                "command": sys.executable,
                "args": ["/mcp_servers/betting_monitor/server.py"],
                "env": os.environ.copy(),
            },
            "betting_context": {
                "command": sys.executable,
                "args": ["/mcp_servers/betting_context/server.py"],
                "env": os.environ.copy(),
            },
            "prizepicks": {
                "command": sys.executable,
                "args": ["/mcp_servers/prizepicks/server.py"],
                "env": os.environ.copy(),
            },
        }

        for name, config in servers.items():
            try:
                logger.info(
                    "Starting MCP server %s: %s %s",
                    name,
                    config["command"],
                    " ".join(config["args"]),
                )
                server_params = StdioServerParameters(
                    command=config["command"],
                    args=config["args"],
                    env=config.get("env"),
                )

                read, write = await self.exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                session = await self.exit_stack.enter_async_context(
                    ClientSession(read, write)
                )
                await session.initialize()
                self.sessions[name] = session
                logger.info("Connected to MCP server: %s", name)
            except Exception as e:
                logger.error(
                    "Failed to connect to MCP server %s: %s", name, e, exc_info=True
                )

    async def get_tools_ollama_format(self) -> List[Dict[str, Any]]:
        """
        Load tools from MCP servers and build a tool->server map.
        (Naming retained from lmsvr for compatibility; this API uses it internally.)
        """
        tools: List[Dict[str, Any]] = []
        self.tools_map = {}

        for server_name, session in self.sessions.items():
            try:
                result = await session.list_tools()
                for tool in result.tools:
                    tools.append(
                        {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.inputSchema,
                            },
                        }
                    )
                    self.tools_map[tool.name] = server_name
            except Exception as e:
                logger.error("Error fetching tools from %s: %s", server_name, e)

        return tools

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        server_name = self.tools_map.get(tool_name)
        if not server_name:
            return f"Error: Tool {tool_name} not found."

        session = self.sessions.get(server_name)
        if not session:
            return f"Error: Server {server_name} not connected."

        try:
            logger.info("Executing tool %s on server %s", tool_name, server_name)
            result = await session.call_tool(tool_name, arguments)

            output: List[str] = []
            for content in result.content:
                if content.type == "text":
                    output.append(content.text)
            return "\n".join(output)
        except Exception as e:
            logger.error("Error executing tool %s: %s", tool_name, e, exc_info=True)
            return f"Error executing tool {tool_name}: {str(e)}"

    async def cleanup(self) -> None:
        await self.exit_stack.aclose()


mcp_manager = MCPManager()
