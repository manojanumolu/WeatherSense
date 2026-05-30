import json
from pathlib import Path

import streamlit as st

from weather_api import build_data_object

st.set_page_config(
    page_title="WeatherSense",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Erase every pixel of Streamlit chrome ────────────────────────────────────
# The WeatherSense HTML is the entire UI; Streamlit is only the data layer.
st.markdown("""
<style>
/* Header / toolbar / footer */
header[data-testid="stHeader"]   { display: none !important; }
[data-testid="stToolbar"]        { display: none !important; }
[data-testid="stDecoration"]     { display: none !important; }
[data-testid="stStatusWidget"]   { display: none !important; }
footer                           { display: none !important; }
#MainMenu                        { display: none !important; }
.stDeployButton                  { display: none !important; }

/* Remove every gap / padding around the component */
.stApp, .stMain, .main,
section.main, .block-container,
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewContainer"] > section {
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
    overflow: hidden !important;
}

/* Stretch the iframe to fill the entire browser viewport */
iframe {
    position: fixed !important;
    inset: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    border: none !important;
    z-index: 9999 !important;
}
</style>
""", unsafe_allow_html=True)

# ── API key ───────────────────────────────────────────────────────────────────
try:
    api_key = st.secrets["OWM_API_KEY"]
except Exception:
    # Can't use st.error (hidden by CSS), so serve an error overlay inside HTML
    api_key = None

# ── City from URL query param (?city=London) ──────────────────────────────────
# The WeatherSense "Get Weather" button in LIVE_MODE navigates to ?city=...
# which causes Streamlit to re-render and fetch fresh data.
city = st.query_params.get("city", "").strip()

# ── Load base HTML ────────────────────────────────────────────────────────────
html_path    = Path(__file__).parent / "index.html"
html_content = html_path.read_text(encoding="utf-8")

# ── Script injected at end of <body> when in LIVE_MODE ───────────────────────
# Overrides the "Get Weather" button (and Enter key) to navigate the parent
# window to ?city=<input value>, which triggers a Streamlit data-fetch cycle.
LIVE_NAV_SCRIPT = """
<script>
(function () {
  function goCity() {
    var city = (document.getElementById('search') || {}).value || '';
    city = city.trim();
    if (!city) return;
    var base;
    try { base = (window.parent || window).location.href.split('?')[0]; }
    catch (e) { base = window.location.href.split('?')[0]; }
    var dest = base + '?city=' + encodeURIComponent(city);
    try { (window.parent || window).location.href = dest; }
    catch (e) { window.location.href = dest; }
  }

  // Capture button click before the existing listener fires
  var btn = document.getElementById('getWeather');
  if (btn) {
    btn.addEventListener('click', function (e) {
      if (window.LIVE_MODE) { e.stopImmediatePropagation(); goCity(); }
    }, true);
  }

  // Also capture Enter in the search box
  var inp = document.getElementById('search');
  if (inp) {
    inp.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && window.LIVE_MODE) {
        e.stopImmediatePropagation();
        goCity();
      }
    }, true);
  }
})();
</script>
</body>"""

# ── Build the HTML to serve ───────────────────────────────────────────────────
if not api_key:
    # Overlay the API-key error on top of the mock dashboard
    error_overlay = """
<div style="position:fixed;inset:0;z-index:99999;
            background:rgba(10,10,26,.92);display:flex;
            align-items:center;justify-content:center;font-family:Outfit,sans-serif;">
  <div style="background:rgba(255,255,255,.1);backdrop-filter:blur(18px);
              border:1px solid rgba(255,255,255,.2);border-radius:20px;
              padding:40px 48px;max-width:480px;text-align:center;color:#fff;">
    <div style="font-size:2.5rem;margin-bottom:16px;">🔑</div>
    <h2 style="margin:0 0 12px;font-weight:800;">API Key Required</h2>
    <p style="color:rgba(255,255,255,.7);line-height:1.6;margin:0 0 20px">
      Create <code style="background:rgba(255,255,255,.15);padding:2px 8px;
      border-radius:6px">.streamlit/secrets.toml</code> and add:<br><br>
      <code style="background:rgba(255,255,255,.15);padding:6px 14px;
      border-radius:8px;font-size:13px">OWM_API_KEY = "your_key_here"</code>
    </p>
    <p style="color:rgba(255,255,255,.5);font-size:13px;margin:0">
      Get a free key at openweathermap.org/api
    </p>
  </div>
</div>
</body>"""
    display_html = html_content.replace("</body>", error_overlay)

elif city:
    data = build_data_object(city, api_key)
    if data:
        json_str = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
        display_html = (
            html_content
            .replace(
                "const LIVE_MODE = false; // replaced by app.py injection",
                "const LIVE_MODE = true;",
            )
            .replace(
                "let currentData = MOCK_DATA_PRESETS.sunny; // TODO: REPLACE WITH API CALL",
                f"let currentData = {json_str};",
            )
            .replace("</body>", LIVE_NAV_SCRIPT)
        )
    else:
        # City not found — show mock UI with an error banner
        not_found = f"""
<div style="position:fixed;top:20px;left:50%;transform:translateX(-50%);
            z-index:99999;background:rgba(255,68,68,.15);
            border:1px solid rgba(255,68,68,.4);backdrop-filter:blur(16px);
            border-radius:14px;padding:14px 24px;color:#fff;
            font-family:Outfit,sans-serif;font-size:14px;
            display:flex;align-items:center;gap:10px;">
  ❌ Could not find weather for <strong>{city}</strong> — check the city name.
</div>
</body>"""
        display_html = (
            html_content
            .replace("</body>", not_found + LIVE_NAV_SCRIPT.replace("</body>", ""))
        )

else:
    # No city yet — show mock demo with LIVE_NAV_SCRIPT so search works
    display_html = html_content.replace("</body>", LIVE_NAV_SCRIPT)

# ── Render — fills 100 % of the viewport via the CSS above ───────────────────
st.components.v1.html(display_html, height=800, scrolling=False)
