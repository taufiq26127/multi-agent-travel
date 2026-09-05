import os
import certifi
import asyncio
import operator
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain.messages import (
    AnyMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
)
from typing import TypedDict, Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from mcp_client_test import tavily_mcp_search

# load environment variables from .env file
load_dotenv()

# Set the SSL certificate file and request CA bundle to use certifi's certificate
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# Load the GOOGLE_API_KEY from environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set.")


# Initialize the ChatGoogleGenerativeAI model with the specified model name
llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")


# state
class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    hotel_results: str
    llm_call: int


# hotel agent
def hotel_agent(state: TravelState):
    query = f"best hotels in {state['user_query']}"
    hotel_results = asyncio.run(tavily_mcp_search(query))
    return {
        "hotel_results": hotel_results,
        "messages": [AIMessage(content=f"Hotel information fetched.")],
        "llm_call": state.get("llm_call", 0) + 1,
    }
