import asyncio
import os
import json
from dotenv import load_dotenv
from pathlib import Path
from langchain.messages import (
    AnyMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
)
from mcp_client import (
    forecast_mcp_search,
    get_all_tools,
    aviation_mcp_call,
    weather_mcp_search,
)
from langchain_google_genai import ChatGoogleGenerativeAI

if __name__ == "__main__":

    def _message_text(content) -> str:
        """Normalize LangChain message content for API and UI consumers."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("text")
            ]
            return "\n".join(parts)
        return str(content)

    result = _message_text(asyncio.run(forecast_mcp_search("Jakarta")))
    print(result)
