import os
import uuid
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
import json
import psycopg
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver
from typing import TypedDict, Annotated
from langchain_google_genai import ChatGoogleGenerativeAI

# from mcp_client_test import tavily_mcp_search
from mcp_client import tavily_mcp_search, aviation_mcp_call

# from tools.tavily_tool import tavily_search
# from tools.flight_tool import search_flights


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


# load environment variables from .env file
load_dotenv()

# set the SSL certificate file and request CA bundle to use certifi's certificate
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()


# get database connection parameters from environment variables
def get_database_url():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set.")

    # not in use for now, but can be used if needed in the future
    # if "sslmode" not in database_url:
    #     seperator = "&" if "?" in database_url else "?"
    #     # Append sslmode=require to the database URL if not present
    #     database_url = f"{database_url}{seperator}sslmode=require"
    return database_url


# load the GOOGLE_API_KEY from environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set.")


# ==========================
# LLM
# ==========================
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    api_key=GOOGLE_API_KEY,
)


# ==========================
# state
# =========================
class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_results: str
    hotel_results: str
    itinerary: str
    llm_calls: int


# =========================
# Flight Agent
# =========================

# def flight_agent(state: TravelState):
#     query = state["user_query"]
#     flight_data = search_flights(query)

#     return {
#         "flight_results": flight_data,
#         "messages": [AIMessage(content="Flight results fetched.")],
#         "llm_calls": state.get("llm_calls", 0) + 1,
#     }


FLIGHT_AGENT_PROMPT = """
    You are a travel flight agent expert.

    User Query:
    {query}

    Airport Information:
    {airport_data}

    Airline Information:
    {airline_data}

    Generate:
    1. Likely deparature airport
    2. Likely arrival airport
    3. Airlines serving this route
    4. Typical flight duration
    5. Estimated airface range
    6. Peak season pricing warning
    7. Booking advice

    Return concise travel guidance dont give too much details, just give the most important information for the user to plan their trip about airports and flights and dont give recommendations about hotels or other aspects of the trip just focus on the flight information.
"""


def flight_agent(state: TravelState):
    query = state["user_query"]

    try:
        airports = asyncio.run(aviation_mcp_call("list_airports"))

        airlines = asyncio.run(aviation_mcp_call("list_airlines"))

        prompt = FLIGHT_AGENT_PROMPT.format(
            query=query,
            airport_data=str(airports)[:3000],
            airline_data=str(airlines)[:3000],
        )

        response = llm.invoke(
            [
                SystemMessage(content="You are an expert travel flight agent."),
                HumanMessage(content=prompt),
            ]
        )

        flights_data = _message_text(response.content)
    except Exception as e:
        flights_data = (
            f"Flight information could not be retrieved due to an error: {str(e)}"
        )

    return {
        "flight_results": flights_data,
        "messages": [AIMessage(content="Flight recommendations fetched.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# =========================
# Hotel Agent
# =========================


def hotel_agent(state: TravelState):
    print("\n INSIDE HOTEL AGENT \n")

    query = f"Best hotels for {state['user_query']}"

    try:
        hotels_data = asyncio.run(tavily_mcp_search(query))

        print("\n[DEBUG] Raw hotels_data:", hotels_data)

        # bongkar wrapper MCP kalau bentuknya list [{'type': 'text', 'text': '...'}]
        if isinstance(hotels_data, list) and len(hotels_data) > 0:
            first_item = hotels_data[0]
            if isinstance(first_item, dict) and "text" in first_item:
                hotels_data = json.loads(first_item["text"])

        results = hotels_data.get("results", [])

        hotel_lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "Unknown Title")
            url = r.get("url", "")
            snippet = r.get("content", "")
            if len(snippet) > 300:
                snippet = snippet[:300].rsplit(" ", 1)[0] + "..."
            hotel_lines.append(f"{i}. {title}\nURL: {url}\nSnippet: {snippet}\n")

        hotel_results = (
            "\n".join(hotel_lines) if hotel_lines else "Tidak ada hotel ditemukan."
        )

    except Exception as e:
        hotel_results = (
            f"Hotel information could not be retrieved due to an error: {str(e)}"
        )

    return {
        "hotel_results": hotel_results,
        "messages": [AIMessage(content="Hotel information fetched.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# =========================
# Itinerary Agent
# =========================


def itinerary_agent(state: TravelState):
    prompt = f"""
Create a complete travel itinerary.

User Query:
{state['user_query']}

Flight Results:
{state['flight_results']}

Hotel Results:
{state['hotel_results']}

Make the itinerary practical, budget-aware, and easy to follow.
"""

    response = llm.invoke(
        [
            SystemMessage(content="You are an expert travel planner."),
            HumanMessage(content=prompt),
        ]
    )

    return {
        "itinerary": _message_text(response.content),
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# =========================
# Final Response Agent
# =========================


def final_agent(state: TravelState):
    final_prompt = f"""
Generate the final travel response for the user.

User Request:
{state['user_query']}

Flights:
{state['flight_results']}

Hotels:
{state['hotel_results']}

Itinerary:
{state['itinerary']}

Format the final answer beautifully using these sections:

1. Trip Summary
2. Flight Information
3. Hotel Suggestions
4. Day-by-Day Itinerary
5. Estimated Budget
6. Final Recommendations

Important:
- Be clear and practical.
- Mention that live flight API may not provide ticket prices if pricing is unavailable.
- Keep the response useful for real travel planning.
"""

    response = llm.invoke(
        [
            SystemMessage(
                content="You are a professional AI travel booking assistant."
            ),
            HumanMessage(content=final_prompt),
        ]
    )

    return {"messages": [response], "llm_calls": state.get("llm_calls", 0) + 1}


# =========================
# Build Graph
# =========================

graph = StateGraph(TravelState)

graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)

graph.add_edge(START, "flight_agent")
graph.add_edge("flight_agent", "hotel_agent")
graph.add_edge("hotel_agent", "itinerary_agent")
graph.add_edge("itinerary_agent", "final_agent")
graph.add_edge("final_agent", END)


# =========================
# PostgreSQL Checkpointer
# =========================
DATABASE_URL = get_database_url()

_conn = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)

checkpointer = PostgresSaver(_conn)
checkpointer.setup()

travel_graph = graph.compile(checkpointer=checkpointer)

# =========================
# Function for FastAPI
# =========================


def run_travel_agent(user_input: str, thread_id: str | None = None):
    if not thread_id:
        thread_id = f"user_{uuid.uuid4().hex}"

    config = {"configurable": {"thread_id": thread_id}}

    result = travel_graph.invoke(
        {
            "messages": [HumanMessage(content=user_input)],
            "user_query": user_input,
            "flight_results": "",
            "hotel_results": "",
            "itinerary": "",
            "llm_calls": 0,
        },
        config=config,
    )

    final_answer = _message_text(result["messages"][-1].content)

    return {
        "thread_id": thread_id,
        "answer": final_answer,
        "flight_results": result.get("flight_results", ""),
        "hotel_results": result.get("hotel_results", ""),
        "itinerary": result.get("itinerary", ""),
        "llm_calls": result.get("llm_calls", 0),
    }
