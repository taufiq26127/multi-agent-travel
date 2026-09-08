import json
import os
import asyncio
import certifi
import shutil
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

# Set the SSL certificate file and request CA bundle to use certifi's certificate
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# Load environment variables from .env file
load_dotenv()

# Load the TAVILY_API_KEY from environment variables
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATION_STACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")

# Preserve the complete Windows environment when starting
# local stdio MCP servers.
AVIATION_ENV = os.environ.copy()
AVIATION_ENV["AVIATION_STACK_API_KEY"] = AVIATION_STACK_API_KEY or ""
UVX_COMMAND = shutil.which("uvx") or r"C:\Users\LENOVO\.local\bin\uvx.exe"


# ==========================================
# MCP client configuration
# ==========================================

client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": ("https://mcp.tavily.com/mcp/" f"?tavilyApiKey={TAVILY_API_KEY}"),
        },
        "aviationstack": {
            "transport": "stdio",
            "command": UVX_COMMAND,
            "args": ["--with", "mcp<2", "aviationstack-mcp"],
            "env": AVIATION_ENV,
        },
    }
)


# Asynchronous function to get all tools from the client
async def get_all_tools():
    tools = await client.get_tools()

    print("Available tools:")

    for tool in tools:
        print(f"- {tool.name}: {tool.description}")


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
