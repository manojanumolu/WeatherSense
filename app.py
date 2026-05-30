import json
from pathlib import Path

import streamlit as st

from weather_api import build_data_object

st.set_page_config(page_title="WeatherSense", page_icon="🌤️", layout="wide")

# ── API key ───────────────────────────────────────────────────────────────────
try:
    api_key = st.secrets["OWM_API_KEY"]
except Exception:
    st.error("⚠️ OpenWeatherMap API key not found.")
    st.info(
        """
**To run locally:**
1. Get a free API key at https://openweathermap.org/api
2. Create `.streamlit/secrets.toml` in this folder and add:
   ```
   OWM_API_KEY = "your_key_here"
   ```
3. Restart the app.

**To deploy on Streamlit Cloud:**
Go to your app → Settings → Secrets and add:
```
OWM_API_KEY = "your_key_here"
```
        """
    )
    st.stop()

# ── Minimal Streamlit UI ──────────────────────────────────────────────────────
st.markdown("### 🌤️ WeatherSense — Live Weather Dashboard")
col1, col2 = st.columns([4, 1])
with col1:
    location = st.text_input(
        "location",
        placeholder="Enter city, ZIP code, or lat,lon — then press Get Weather",
        label_visibility="collapsed",
    )
with col2:
    search_clicked = st.button(
        "🔍 Get Weather", type="primary", use_container_width=True
    )

# ── Load base HTML ────────────────────────────────────────────────────────────
html_path    = Path(__file__).parent / "index.html"
html_content = html_path.read_text(encoding="utf-8")

# ── Session state: persist last rendered HTML across Streamlit rerenders ──────
if "live_html" not in st.session_state:
    st.session_state.live_html = None

# ── Handle search ─────────────────────────────────────────────────────────────
if search_clicked and location.strip():
    query = location.strip()
    with st.spinner(f"Fetching weather for **{query}**…"):
        data = build_data_object(query, api_key)

    if data is None:
        st.error(
            f"❌ Could not fetch weather for **{query}**. "
            "Check the city name or ZIP code and try again."
        )
        st.session_state.live_html = None
    else:
        # Safely serialise to JSON — escape any accidental </script> sequences
        json_str = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

        modified = html_content.replace(
            "const LIVE_MODE = false; // replaced by app.py injection",
            "const LIVE_MODE = true;",
        ).replace(
            "let currentData = MOCK_DATA_PRESETS.sunny; // TODO: REPLACE WITH API CALL",
            f"let currentData = {json_str};",
        )
        st.session_state.live_html = modified

# ── Render HTML component ─────────────────────────────────────────────────────
display_html = st.session_state.live_html or html_content
st.components.v1.html(display_html, height=900, scrolling=True)
