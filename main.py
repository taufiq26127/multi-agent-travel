from typing import Any
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

import nest_asyncio

nest_asyncio.apply()

from backend import run_travel_agent


class TravelRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Permintaan perjalanan pengguna")
    thread_id: str | None = Field(
        default=None,
        description="ID percakapan untuk melanjutkan konteks perjalanan",
    )


class TravelResponse(BaseModel):
    thread_id: str
    answer: str
    flight_results: Any
    hotel_results: Any
    itinerary: Any
    llm_calls: int


app = FastAPI(
    title="MCP Traveler API",
    description="API perencana perjalanan berbasis AI",
    version="1.0.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/travel", response_model=TravelResponse)
async def create_travel_plan(request: TravelRequest) -> TravelResponse:
    try:
        result = await run_in_threadpool(
            run_travel_agent,
            user_input=request.query.strip(),
            thread_id=request.thread_id,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return TravelResponse(**result)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
