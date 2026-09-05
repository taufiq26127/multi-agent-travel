import os
from dotenv import load_dotenv
from tavily import TavilyClient

# Load environment variables from .env file
load_dotenv()

client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY"),
)


def tavily_search(query: str):
    """
    Perform a search using the Tavily API.

    Args:
        query (str): The search query.
        max_results (int): The maximum number of results to return.

    Returns:
        str: A formatted string containing the search results.
    """

    response = client.search(
        query=query,
        max_results=5,
    )

    results = []

    for i, r in enumerate(response["results"], 1):
        title = r.get("title", "Unknown Title")
        url = r.get("url", "")
        snippet = r.get("content", "")
        if len(snippet) > 300:
            snippet = snippet[:300].rsplit(" ", 1)[0] + "..."

        results.append(f"{i}. {title}\nURL: {url}\nSnippet: {snippet}\n")

    return "\n".join(results)
