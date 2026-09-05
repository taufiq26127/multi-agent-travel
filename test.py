from tools.tavily_tool import tavily_search
from tools.flight_tool import search_flights

# res = tavily_search("best hotel in the indonesia?")
# print(res)

res = search_flights("plan 7 days trip to japan from indonesia")
print(res)
