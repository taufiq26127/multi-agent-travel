import os
import uuid

import requests
import streamlit as st

API_URL = os.getenv("TRAVEL_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="MCP Traveler",
    page_icon="✈️",
    layout="centered",
)

st.title("✈️ MCP Traveler")
st.caption("Build your travel plan with the help of MCP and OpenWeather API.")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"streamlit_{uuid.uuid4().hex}"

with st.form("travel_form"):
    query = st.text_area(
        "Describe the travel you want to plan",
        placeholder=(
            "Example: Plan a 5-day trip to Bali from Jakarta, "
            "including flights and hotels."
        ),
        height=120,
    )
    submitted = st.form_submit_button("Make Travel Plan", type="primary")

if submitted:
    query = query.strip()
    if not query:
        st.warning("Please enter a travel request first.")
    else:
        with st.spinner("Waiting for the travel plan..."):
            try:
                response = requests.post(
                    f"{API_URL.rstrip('/')}/travel",
                    json={"query": query, "thread_id": st.session_state.thread_id},
                    timeout=180,
                )
                response.raise_for_status()
                result = response.json()
                st.session_state.thread_id = result["thread_id"]
            except requests.RequestException as exc:
                st.error(
                    "Unable to connect to the backend. "
                    f"Please ensure FastAPI is running at {API_URL}."
                )
                st.caption(str(exc))
            else:
                st.success("Travel plan generated successfully!")
                st.markdown(result["answer"])

                with st.expander("Lihat detail data pencarian"):
                    st.markdown("**Flights**")
                    st.write(result["flight_results"] or "No flight data available.")
                    st.markdown("**Hotel**")
                    st.write(result["hotel_results"] or "No hotel data available.")
                    st.write("**Weather**")
                    st.write(result["weather_results"] or "No weather data available.")
                    st.markdown("**Itinerary**")
                    st.write(result["itinerary"] or "No itinerary available.")

                st.caption(f"Thread: {result['thread_id']}")
