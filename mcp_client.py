import json
import os
import asyncio
import sys
from pathlib import Path
import traceback
from urllib.parse import urlencode
import certifi
import shutil
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_google_genai import ChatGoogleGenerativeAI

# Set the SSL certificate file and request CA bundle to use certifi's certificate
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# Load environment variables from .env file
load_dotenv()

# Load the TAVILY_API_KEY from environment variables
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATION_STACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


# Automatically find the current project folder.
# This replaces the hard-coded Windows paths.
PROJECT_DIR = Path(__file__).resolve().parent
WEATHER_SERVER_PATH = PROJECT_DIR / "custom_weather_mcp.py"

# Preserve the complete Windows environment when starting
# local stdio MCP servers.
AVIATION_ENV = os.environ.copy()
AVIATION_ENV["AVIATIONSTACK_API_KEY"] = AVIATION_STACK_API_KEY or ""
UVX_COMMAND = os.getenv("UVX_COMMAND") or shutil.which("uvx") or "uvx"
TAVILY_URL = "https://mcp.tavily.com/mcp/?" + urlencode(
    {"tavilyApiKey": TAVILY_API_KEY or ""}
)


# ==========================================
# MCP client configuration
# ==========================================

client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": TAVILY_URL,
        },
        "aviationstack": {
            "transport": "stdio",
            "command": UVX_COMMAND,
            "args": ["--with", "mcp<2", "aviationstack-mcp"],
            "env": AVIATION_ENV,
        },
        "weather": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(WEATHER_SERVER_PATH)],
            "env": {
                "OPENWEATHER_API_KEY": OPENWEATHER_API_KEY,
            },
        },
    }
)


# Asynchronous function to get all tools from the client
async def get_all_tools():
    """
    Load each MCP server separately.

    A broken server will no longer prevent the other
    working servers from loading.
    """

    all_tools = []

    for server_name in ("tavily", "aviationstack", "weather"):
        try:
            tools = await client.get_tools(server_name=server_name)
            all_tools.extend(tools)
            print(f"\nAvailable tools from {server_name} MCP:\n")
            for tool in tools:
                print(tool.name)
        except Exception as error:
            print(f"\nCould not connect to {server_name} MCP:\n{error}\n")
            traceback.print_exc()  # <-- tambahkan ini, akan print full stack trace

    return all_tools


# ================================
# Tavily and aviationstack tools
# ================================


search_tool = None
aviation_tool = {}


async def initialize_mcp():
    global search_tool, aviation_tool

    if search_tool is not None and aviation_tool:
        return

    tools = await client.get_tools()

    # print("Available MCP tools:")
    # for tool in tools:
    #     print(tool.name)

    search_tool = next(tool for tool in tools if tool.name == "tavily_search")

    aviation_tool = {tool.name: tool for tool in tools if tool.name != "tavily_search"}


async def tavily_mcp_search(query: str, max_results: int = 5):
    """Search for flights using the Tavily MCP tool."""
    await initialize_mcp()

    if search_tool is None:
        raise ValueError("Tavily search tool is not available.")

    # Call the Tavily MCP tool with the query and max_results
    result = await search_tool.ainvoke(
        {
            "query": query,
            "max_results": max_results,
        }
    )

    return result


async def aviation_mcp_call(tool_name: str, tool_args: dict = None):
    tools = await client.get_tools()

    tool = next((tool for tool in tools if tool.name == tool_name), None)

    result = await tool.ainvoke(tool_args or {})

    return result


# ==========================================
# Weather MCP tools
# ==========================================

weather_tool = None
forecast_tool = None


async def initialize_weather_tools():
    global weather_tool
    global forecast_tool

    if weather_tool is not None and forecast_tool is not None:
        return

    if not WEATHER_SERVER_PATH.exists():
        raise FileNotFoundError(
            "Weather MCP server file was not found: " f"{WEATHER_SERVER_PATH}"
        )

    # Load only Weather.
    # Tavily and AviationStack will not be started.
    tools = await client.get_tools(server_name="weather")

    tools_by_name = {tool.name: tool for tool in tools}

    weather_tool = tools_by_name.get("get_current_weather")

    forecast_tool = tools_by_name.get("get_forecast")

    missing_tools = []

    if weather_tool is None:
        missing_tools.append("get_current_weather")

    if forecast_tool is None:
        missing_tools.append("get_forecast")

    if missing_tools:
        available_tools = ", ".join(tools_by_name.keys())

        raise RuntimeError(
            "Missing Weather MCP tools: "
            f"{', '.join(missing_tools)}. "
            f"Available tools: "
            f"{available_tools or 'none'}"
        )


async def weather_mcp_search(city: str):
    await initialize_weather_tools()

    result = await weather_tool.ainvoke({"city": city})

    return result


async def forecast_mcp_search(city: str):
    await initialize_weather_tools()

    result = await forecast_tool.ainvoke({"city": city})

    return result


# ==========================================
# llm
# ==========================================

llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")


# ==========================================
# Destination extractor
# ==========================================


def extract_destination(query: str):
    prompt = f"""
    Extract only the destination city or country.

    Query:
    {query}

    Return only destination name.
    """

    response = llm.invoke(prompt)

    return response.content[0].get("text", "")
