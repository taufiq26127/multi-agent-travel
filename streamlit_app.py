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
st.caption("Buat rencana perjalanan lengkap dengan bantuan AI.")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"streamlit_{uuid.uuid4().hex}"

with st.form("travel_form"):
    query = st.text_area(
        "Ceritakan perjalanan yang Anda inginkan",
        placeholder=(
            "Contoh: Rencanakan perjalanan 5 hari ke Bali dari Jakarta, "
            "termasuk penerbangan dan hotel."
        ),
        height=120,
    )
    submitted = st.form_submit_button("Buat rencana perjalanan", type="primary")

if submitted:
    query = query.strip()
    if not query:
        st.warning("Silakan masukkan permintaan perjalanan terlebih dahulu.")
    else:
        with st.spinner("Sedang menyiapkan rencana perjalanan..."):
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
                    "Tidak dapat terhubung ke backend. "
                    f"Pastikan FastAPI berjalan di {API_URL}."
                )
                st.caption(str(exc))
            else:
                st.markdown("**Penerbangan**")
                st.write(result["flight_results"] or "Tidak ada data penerbangan.")
                st.markdown("**Hotel**")
                st.write(result["hotel_results"] or "Tidak ada data hotel.")
                st.write("**Cuaca**")
                st.write(result["weather_results"] or "Tidak ada data cuaca.")
                st.markdown("**Itinerary**")
                st.write(result["itinerary"] or "Tidak ada itinerary.")

                with st.expander("Lihat detail data pencarian"):
                    st.markdown(result["answer"])

                st.caption(f"Thread: {result['thread_id']}")
