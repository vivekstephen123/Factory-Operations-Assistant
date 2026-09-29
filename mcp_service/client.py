import sys
import os
import asyncio
from typing import Dict, Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mcp_service.server import mcp_server


async def call_mcp_tool_async(tool_name: str, arguments: Dict[str, Any]) -> str:
    try:
        result = await mcp_server.call_tool(tool_name, arguments)
        if result and result.content:
            text_outputs = []
            for item in result.content:
                if hasattr(item, "text"):
                    text_outputs.append(item.text)
                elif isinstance(item, dict) and "text" in item:
                    text_outputs.append(item["text"])
            return "\n".join(text_outputs) if text_outputs else str(result)
        return "MCP: Tool executed with no output."
    except Exception as e:
        return f"MCP Protocol Error: {str(e)}"


def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, call_mcp_tool_async(tool_name, arguments))
                return future.result()
        else:
            return loop.run_until_complete(call_mcp_tool_async(tool_name, arguments))
    except Exception:
        return asyncio.run(call_mcp_tool_async(tool_name, arguments))


def external_info(request: str) -> str:
    return call_mcp_tool("external_info", {"request": request})
