import asyncio
import os
import json
from dotenv import load_dotenv
from langchain.messages import (
    AnyMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
)

from backend import _message_text
from mcp_client import get_all_tools, aviation_mcp_call
from langchain_google_genai import ChatGoogleGenerativeAI

if __name__ == "__main__":

    load_dotenv()

    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
    )

    user_query = "Rencanakan perjalanan 5 hari ke Amerika Serikat dari Jakarta."

    FLIGHT_AGENT_PROMPT = """
    You are a travel flight agent expert.

    User Query:
    {query}

    Airport Information:
    {airport_data}

    Airline Information:
    {airline_data}

    Generate:
    1. Likely departure airport
    2. Likely arrival airport
    3. Airlines serving this route
    4. Typical flight duration
    5. Estimated airfare range
    6. Peak season pricing warning
    7. Booking advice

    Return concise travel guidance
"""

    def extract_mcp_data(mcp_result):
        """Bongkar wrapper [{'type': 'text', 'text': '[json]'}] jadi list dict asli."""
        if not mcp_result:
            return []
        first_item = mcp_result[0]
        if isinstance(first_item, dict) and "text" in first_item:
            try:
                return json.loads(first_item["text"])
            except json.JSONDecodeError:
                return []
        return mcp_result

    def format_airports(airports, limit=300):
        airports = extract_mcp_data(airports)
        lines = []
        for a in airports[:limit]:
            name = a.get("airport_name", "Unknown")
            iata = a.get("iata_code", "-")
            icao = a.get("icao_code", "-")
            country = a.get("country_name") or "Unknown country"
            tz = a.get("timezone", "-")
            gmt = a.get("gmt", "-")
            lines.append(
                f"- {name} (IATA: {iata}, ICAO: {icao}), located in {country}, "
                f"timezone {tz} (GMT{gmt})."
            )
        return "\n".join(lines)

    def format_airlines(airlines, limit=300):
        airlines = extract_mcp_data(airlines)
        lines = []
        for al in airlines[:limit]:
            name = al.get("airline_name", al.get("name", "Unknown"))
            iata = al.get("iata_code", "-")
            icao = al.get("icao_code", "-")
            country = al.get("country_name") or "Unknown country"
            lines.append(f"- {name} (IATA: {iata}, ICAO: {icao}), based in {country}.")
        return "\n".join(lines)

    def flight_agent(query, llm):
        print("\n INSIDE FLIGHT AGENT \n")

        try:
            airports = asyncio.run(aviation_mcp_call("list_airports"))
            airlines = asyncio.run(aviation_mcp_call("list_airlines"))

            airport_text = format_airports(airports)
            airline_text = format_airlines(airlines)

            print("\n[DEBUG] airport_text:\n", airport_text)
            print("\n[DEBUG] airline_text:\n", airline_text)

            prompt = FLIGHT_AGENT_PROMPT.format(
                query=query,
                airport_data=airport_text,
                airline_data=airline_text,
            )

            response = llm.invoke(
                [
                    SystemMessage(content="You are an expert travel flight agent."),
                    HumanMessage(content=prompt),
                ]
            )

            result_text = _message_text(response.content)
        except Exception as e:
            result_text = (
                f"Flight information could not be retrieved due to an error: {str(e)}"
            )

        return {"flight_results": result_text}

    flights_data = flight_agent(user_query, llm)

    print("\n FLIGHT AGENT RESPONSE: ", flights_data["flight_results"])
