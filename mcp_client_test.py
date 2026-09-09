import json
import os
import asyncio
from urllib.parse import urlencode
import certifi
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

# Set the SSL certificate file and request CA bundle to use certifi's certificate
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# Load environment variables from .env file
load_dotenv()

# Load the TAVILY_API_KEY from environment variables
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Initialize the MultiServerMCPClient
client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": "https://mcp.tavily.com/mcp/?"
            + urlencode({"tavilyApiKey": TAVILY_API_KEY or ""}),
        }
    }
)


# Asynchronous function to get all tools from the client
async def get_all_tools():
    tools = await client.get_tools()

    print("Available tools:")

    for tool in tools:
        print(f"- {tool.name}: {tool.description}")


# Global variable to store the tavily_search tool
tavily_search_tool = None


# Asynchronous function to get the tavily_search tool from the client
async def get_tavily_search_tool():
    global tavily_search_tool
    tools = await client.get_tools()
    tavily_search_tool = next(
        (tool for tool in tools if tool.name == "tavily_search"), None
    )

    if tavily_search_tool:
        print(f"Found tool: {tavily_search_tool.name}")
    else:
        print("tavily_search tool not found.")


# Asynchronous function to perform a search using the tavily_search tool
async def tavily_mcp_search(query):
    if tavily_search_tool is None:
        await get_tavily_search_tool()

    response = await tavily_search_tool.ainvoke(
        {
            "query": query,
            "max_results": 5,
        }
    )

    # response berbentuk: [{"type": "text", "text": "<json string>", "id": "..."}]
    if not response or not isinstance(response, list):
        return "Tidak ada hasil pencarian ditemukan."

    raw_text = response[0].get("text", "")

    try:
        data = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return "Gagal memparsing hasil pencarian."

    items = data.get("results", [])

    if not items:
        return "Tidak ada hasil pencarian ditemukan."

    results = []
    for i, r in enumerate(items, 1):
        title = r.get("title", "Unknown Title")
        url = r.get("url", "")
        snippet = r.get("content", "")
        if len(snippet) > 300:
            snippet = snippet[:300].rsplit(" ", 1)[0] + "..."

        results.append(f"{i}. {title}\nURL: {url}\nSnippet: {snippet}\n")

    return "\n".join(results)
