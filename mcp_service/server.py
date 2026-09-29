"""
Model Context Protocol (MCP) Server for Operations Assistant.
Exposes external tools for weather and factory navigation/maps.
Compatible with MCP 2.x MCPServer specification.
"""

import sys
import asyncio
from mcp.server.mcpserver import MCPServer

mcp_server = MCPServer("factory-operations-mcp")


@mcp_server.tool(name="get_weather", description="Get weather forecast and environmental conditions for factory locations.")
def get_weather(location: str = "Bengaluru Factory", time_period: str = "tomorrow") -> str:
    loc_lower = location.lower()
    
    if "bengaluru" in loc_lower or "factory" in loc_lower or "peenya" in loc_lower:
        return (
            f"Weather Report for Bengaluru Factory (Peenya Industrial Area) for {time_period.title()}:\n"
            f"- Temperature: 28°C (High: 31°C, Low: 21°C)\n"
            f"- Conditions: Partly Cloudy with moderate breeze\n"
            f"- Humidity: 62%\n"
            f"- Wind: 14 km/h SW\n"
            f"- Precipitation Probability: 15% (No heavy rain expected)\n"
            f"- Status: Ideal operational conditions for machine cooling and logistics."
        )
    else:
        return (
            f"Weather Report for {location.title()} ({time_period.title()}):\n"
            f"- Temperature: 27°C\n"
            f"- Conditions: Clear to partly cloudy\n"
            f"- Humidity: 58%\n"
            f"- Precipitation: 10%\n"
            f"- Operational Status: Normal."
        )


@mcp_server.tool(name="get_distance_maps", description="Calculate distance, estimated travel time, and driving route between locations.")
def get_distance_maps(origin: str = "Electronic City", destination: str = "Bengaluru Factory") -> str:
    return (
        f"Map & Navigation Route Summary:\n"
        f"- Origin: {origin}\n"
        f"- Destination: {destination}\n"
        f"- Total Distance: 38.5 km\n"
        f"- Estimated Travel Time: 45 - 55 minutes\n"
        f"- Recommended Route: via NICE Road (Toll road, smooth flow) -> Tumkur Road Exit\n"
        f"- Traffic Condition: Moderate flow, no active road closures reported."
    )


@mcp_server.tool(name="external_info", description="Unified gateway for weather, factory location, distance, and map queries via MCP.")
def external_info_handler(request: str) -> str:
    req_lower = request.lower()
    
    if any(k in req_lower for k in ["distance", "far", "route", "map", "electronic city", "travel time", "how to reach"]):
        origin = "Electronic City" if "electronic city" in req_lower else "City Center"
        destination = "Bengaluru Factory (Peenya)"
        return get_distance_maps(origin=origin, destination=destination)
    
    if any(k in req_lower for k in ["weather", "temperature", "rain", "forecast", "climate", "hot", "cold"]):
        time_period = "tomorrow" if "tomorrow" in req_lower else ("today" if "today" in req_lower else "current")
        location = "Bengaluru Factory"
        return get_weather(location=location, time_period=time_period)
    
    return (
        f"External Info Service (MCP):\n"
        f"Processed query: '{request}'\n"
        f"Location: Bengaluru Industrial Operations Hub.\n"
        f"Conditions: Normal operational status across all external factory services."
    )


if __name__ == "__main__":
    print("Starting MCP Server via stdio...")
    asyncio.run(mcp_server.run_stdio_async())
