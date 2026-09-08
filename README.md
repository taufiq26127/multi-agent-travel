# MCP Traveler

MCP Traveler adalah aplikasi perencana perjalanan berbasis AI. Pengguna cukup
menuliskan kebutuhan perjalanan dalam bahasa natural, lalu sistem mengumpulkan
informasi penerbangan, hotel, dan cuaca sebelum menyusun itinerary serta
rekomendasi akhir.

Proyek ini menggunakan:

- **LangGraph** untuk mengorkestrasi workflow agent secara berurutan.
- **Google Gemini** melalui `ChatGoogleGenerativeAI` untuk ekstraksi lokasi,
  analisis hasil pencarian, dan penyusunan itinerary.
- **Model Context Protocol (MCP)** untuk menghubungkan agent dengan layanan
  Tavily, AviationStack, dan server cuaca lokal.
- **FastAPI** sebagai backend API.
- **Streamlit** sebagai antarmuka web.
- **PostgreSQL** sebagai checkpointer LangGraph agar konteks berdasarkan
  `thread_id` dapat dilanjutkan.

## Arsitektur singkat

```text
Streamlit UI
     |
     v
FastAPI (/travel)
     |
     v
LangGraph Travel Workflow
     |
     +--> AviationStack MCP ----> data bandara dan maskapai
     +--> Tavily MCP ------------> hasil pencarian hotel
     +--> Weather MCP lokal -----> cuaca saat ini dan prakiraan
     |
     v
PostgreSQL Checkpointer
```

## Workflow masing-masing agent

Workflow dijalankan secara sinkron dan berurutan. Output agent sebelumnya
disimpan di `TravelState` dan menjadi input agent berikutnya.

```mermaid
flowchart TD
    A([START]) --> B[Flight Agent]
    B --> C[Hotel Agent]
    C --> D[Weather Agent]
    D --> E[Itinerary Agent]
    E --> F[Final Response Agent]
    F --> G([END])
```

### 1. Flight Agent

Implementasi: `flight_agent` di `backend.py`.

Alur:

1. Membaca `user_query`.
2. Memanggil AviationStack MCP melalui `list_airports`.
3. Memanggil AviationStack MCP melalui `list_airlines`.
4. Mengirim data tersebut ke Gemini.
5. Menghasilkan informasi bandara keberangkatan/kedatangan, maskapai yang
   melayani rute, estimasi durasi, kisaran tarif, peringatan musim ramai, dan
   saran pemesanan.
6. Menyimpan hasil ke `state["flight_results"]`.

Agent ini memberikan panduan penerbangan. Harga tiket bersifat estimasi dan
tidak selalu tersedia dari API live.

### 2. Hotel Agent

Implementasi: `hotel_agent` di `backend.py`.

Alur:

1. Membentuk query `Best hotels for <user_query>`.
2. Memanggil tool `tavily_search` melalui Tavily MCP.
3. Mengambil maksimal lima hasil pencarian.
4. Menormalisasi hasil MCP dan menampilkan judul, URL, serta snippet setiap
   hotel.
5. Menyimpan hasil ke `state["hotel_results"]`.

Tavily digunakan sebagai mesin pencarian web; hasilnya bukan inventori
pemesanan atau konfirmasi ketersediaan kamar.

### 3. Weather Agent

Implementasi: `weather_agent` di `backend.py`.

Alur:

1. Meminta Gemini mengekstrak nama kota atau negara tujuan dari `user_query`.
2. Memanggil `get_current_weather` pada Weather MCP lokal.
3. Memanggil `get_forecast` pada Weather MCP lokal.
4. Menggabungkan cuaca saat ini dan lima entri prakiraan pertama.
5. Menyimpan hasil ke `state["weather_results"]`.

### 4. Itinerary Agent

Implementasi: `itinerary_agent` di `backend.py`.

Alur:

1. Membaca query pengguna.
2. Membaca hasil penerbangan, hotel, dan cuaca dari state.
3. Meminta Gemini menyusun itinerary lengkap yang praktis, mudah diikuti,
   dan mempertimbangkan anggaran.
4. Menyimpan hasil per hari ke `state["itinerary"]`.

### 5. Final Response Agent

Implementasi: `final_agent` di `backend.py`.

Alur:

1. Menggabungkan permintaan pengguna, hasil penerbangan, hotel, cuaca, dan
   itinerary.
2. Meminta Gemini menyusun jawaban final yang mudah dibaca.
3. Jawaban diarahkan memiliki bagian Trip Summary, Flight Information, Hotel
   Suggestions, Day-by-Day Itinerary, Estimated Budget, dan Final
   Recommendations.
4. Jawaban terakhir dikembalikan sebagai `answer` pada response API.

## MCP server dan tool

Konfigurasi semua server berada di `mcp_client.py` dan dikelola oleh
`MultiServerMCPClient` dari `langchain-mcp-adapters`.

| MCP server      | Transport           | Sumber                        | Tool yang digunakan                   | Agent   |
| --------------- | ------------------- | ----------------------------- | ------------------------------------- | ------- |
| `tavily`        | Streamable HTTP     | `https://mcp.tavily.com/mcp/` | `tavily_search`                       | Hotel   |
| `aviationstack` | stdio melalui `uvx` | package `aviationstack-mcp`   | `list_airports`, `list_airlines`      | Flight  |
| `weather`       | stdio               | `custom_weather_mcp.py`       | `get_current_weather`, `get_forecast` | Weather |

### Weather MCP lokal

`custom_weather_mcp.py` membuat server `FastMCP("Weather MCP Server")` dan
menyediakan:

- `get_current_weather(city)`: memanggil OpenWeather dan mengembalikan suhu,
  suhu terasa, kelembapan, kondisi, serta kecepatan angin.
- `get_forecast(city)`: memanggil OpenWeather dan mengembalikan lima entri
  prakiraan pertama.

### Utility penerbangan lokal

`tools/flight_tool.py` berisi utilitas resolusi lokasi ke kode IATA
(database `airportsdata`, alias negara, dan `pycountry`) serta konstanta
AviationStack. Utility ini berguna untuk pengembangan/eksperimen, tetapi
workflow aktif di `backend.py` saat ini menggunakan tool MCP
`list_airports` dan `list_airlines` secara langsung.

## Struktur proyek

```text
.
├── backend.py              # TravelState, agent, LangGraph, PostgreSQL checkpointer
├── main.py                 # FastAPI app dan endpoint HTTP
├── mcp_client.py           # Konfigurasi client dan adapter semua MCP server
├── custom_weather_mcp.py   # MCP server cuaca lokal
├── streamlit_app.py        # UI Streamlit
├── mcp_client_test.py      # Contoh client Tavily MCP sederhana
├── tools/
│   └── flight_tool.py      # Utility resolusi lokasi/IATA
├── requirements.txt        # Daftar dependency pip
├── pyproject.toml          # Metadata dan dependency project
└── async.ipynb             # Eksperimen async
```

## Prasyarat

- Python **3.12 atau lebih baru**.
- PostgreSQL yang dapat diakses aplikasi.
- `uv`/`uvx` untuk menjalankan AviationStack MCP.
- API key: `GOOGLE_API_KEY`, `TAVILY_API_KEY`, `AVIATIONSTACK_API_KEY`, dan
  `OPENWEATHER_API_KEY`.
