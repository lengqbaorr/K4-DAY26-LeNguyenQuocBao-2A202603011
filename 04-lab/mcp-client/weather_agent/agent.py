"""Google ADK agent using weather tools from a Streamable HTTP MCP server."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import (
    McpToolset,
    StreamableHTTPConnectionParams,
)


load_dotenv(Path(__file__).resolve().parents[3] / ".env")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")

weather_tools = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=MCP_SERVER_URL,
        timeout=30.0,
    ),
)

root_agent = Agent(
    name="weather_agent",
    model=LiteLlm(model="openai/gpt-4o"),
    instruction=(
        "Answer weather questions using the MCP weather tools. "
        "Use get_current_weather for current conditions and get_forecast "
        "for a 1 to 3 day forecast. If a tool fails, explain the failure "
        "instead of inventing weather data."
    ),
    tools=[weather_tools],
)

