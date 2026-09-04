import asyncio
from mcp_client_test import tavily_mcp_search, get_all_tools, get_tavily_search_tool

if __name__ == "__main__":
    # Run the asynchronous function to get all tools
    query = "latest news football about real madrid"
    asyncio.run(tavily_mcp_search(query))
