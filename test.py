from tools.tavily_tool import tavily_search
from tools.flight_tool import search_flights
from backend import run_travel_agent

# res = tavily_search("best hotel in the indonesia?")
# print(res)

# res = search_flights("plan 7 days trip to japan from indonesia")
# print(res)
user_query = "rencanakan perjalanan ke bali selama 5 hari dari jakarta, indonesia, termasuk penerbangan dan hotel"

response = run_travel_agent(user_input=user_query)

print("Final Response:")
print(response["answer"])
