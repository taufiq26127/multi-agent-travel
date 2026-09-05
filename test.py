from tools.tavily_tool import tavily_search
from tools.flight_tool import search_flights
from backend import run_travel_agent

# res = tavily_search("best hotel in the indonesia?")
# print(res)

# res = search_flights("plan 7 days trip to japan from indonesia")
# print(res)
user_query = "Plan a 3 days trip to thailand from indonesia"

response = run_travel_agent(user_input=user_query, thread_id="test-user")

print("Final Response:")
print(response["answer"])
