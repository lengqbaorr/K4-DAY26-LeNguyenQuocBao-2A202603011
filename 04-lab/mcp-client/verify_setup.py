#!/usr/bin/env python3
"""Verify client configuration and the remote MCP tool contract."""

import asyncio
import importlib
import os
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def check_environment():
    """Check if .env file exists and is configured"""
    print("🔍 Checking environment configuration...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        print("   Run: echo 'GOOGLE_API_KEY=your_key' > .env")
        return False
    
    # Check if GOOGLE_API_KEY is set
    from dotenv import load_dotenv

    load_dotenv(CLIENT_DIR.parents[1] / ".env")
    value = os.getenv("OPENAI_API_KEY", "").strip()
    configured = bool(value) and value not in {
        "your_openai_api_key", "replace_with_your_openai_api_key", "your_key"
    }
    print(f"OPENAI_API_KEY: {'configured' if configured else 'missing'}")
    if not configured:
        print("Set OPENAI_API_KEY in the repository root .env or in the environment.")
    return configured


def check_dependencies() -> bool:
    required = {
        "google.adk": "Google ADK", "litellm": "LiteLLM",
        "mcp": "MCP SDK", "dotenv": "python-dotenv"
    }
    missing = []
    for module, label in required.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(label)
    print(f"Dependencies: {'OK' if not missing else 'missing ' + ', '.join(missing)}")
    return not missing


def check_agent() -> bool:
    try:
        from weather_agent import root_agent
        assert root_agent.name == "weather_agent"
        assert root_agent.tools
    except (ImportError, AssertionError, ValueError) as exc:
        print(f"Agent: failed ({exc})")
        return False
    print(f"Agent: OK ({root_agent.model.model})")
    return True


async def check_mcp_server() -> bool:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    url = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")
    try:
        async with streamable_http_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                missing = EXPECTED_TOOLS - names
                if missing:
                    print(f"MCP server: missing tools {sorted(missing)}")
                    return False
                result = await session.call_tool("health_check", {})
                if result.isError:
                    print("MCP server: health_check returned an error")
                    return False
                health_text = result.content[0].text
                if "WEATHERAPI_KEY: configured" not in health_text:
                    print("MCP server: WEATHERAPI_KEY is missing")
                    return False
                print(f"MCP server: OK ({url}; {', '.join(sorted(EXPECTED_TOOLS))})")
                return True
    except Exception as exc:
        print(f"MCP server: failed ({type(exc).__name__}: {exc})")
        return False


async def main() -> int:
    environment_ok = check_environment()
    dependencies_ok = check_dependencies()
    structure_ok = all(
        (CLIENT_DIR / path).is_file()
        for path in ("weather_agent/agent.py", "weather_agent/__init__.py")
    )
    print(f"Agent files: {'OK' if structure_ok else 'missing'}")
    agent_ok = check_agent() if dependencies_ok and structure_ok else False
    server_ok = await check_mcp_server() if dependencies_ok else False
    success = all((environment_ok, dependencies_ok, structure_ok, agent_ok, server_ok))
    print("Setup: PASS" if success else "Setup: FAIL")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
