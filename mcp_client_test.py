import os
import asyncio
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
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}",
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

    result = await tavily_search_tool.ainvoke({"query": query})

    return result
    # print("Search result:")
    # print(result)
