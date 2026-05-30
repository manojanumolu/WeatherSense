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
st.markdown("""
<style>
header[data-testid="stHeader"]   { display: none !important; }
[data-testid="stToolbar"]        { display: none !important; }
[data-testid="stDecoration"]     { display: none !important; }
[data-testid="stStatusWidget"]   { display: none !important; }
footer                           { display: none !important; }
#MainMenu                        { display: none !important; }
.stDeployButton                  { display: none !important; }
.stApp, .stMain, .main,
section.main, .block-container,
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewContainer"] > section {
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
    overflow: hidden !important;
}
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
    api_key = None

# ── City from URL query param ─────────────────────────────────────────────────
city = st.query_params.get("city", "").strip()

# ── Load base HTML ────────────────────────────────────────────────────────────
html_path    = Path(__file__).parent / "index.html"
html_content = html_path.read_text(encoding="utf-8")

# Always hide the demo switcher pills — live app shows real data only
html_content = html_content.replace(
    "</head>",
    "<style>#demoSwitch{display:none!important}"
    ".topbar{margin-bottom:4px!important}</style></head>",
)

# ── Scripts injected at end of <body> ─────────────────────────────────────────

def make_scripts(api_key_js):
    """Return the </body>-replacement string with nav + autocomplete scripts."""
    return f"""
<script>
/* ── City navigation: always active (search works in both demo and live) ── */
(function () {{
  function goCity() {{
    var city = (document.getElementById('search') || {{}}).value || '';
    city = city.trim();
    if (!city) return;
    var base;
    try {{ base = (window.parent || window).location.href.split('?')[0]; }}
    catch (e) {{ base = window.location.href.split('?')[0]; }}
    var dest = base + '?city=' + encodeURIComponent(city);
    try {{ (window.parent || window).location.href = dest; }}
    catch (e) {{ window.location.href = dest; }}
  }}

  var btn = document.getElementById('getWeather');
  if (btn) {{
    btn.addEventListener('click', function (e) {{
      e.stopImmediatePropagation();
      goCity();
    }}, true);
  }}

  var inp = document.getElementById('search');
  if (inp) {{
    inp.addEventListener('keydown', function (e) {{
      if (e.key === 'Enter') {{ e.stopImmediatePropagation(); goCity(); }}
    }}, true);
  }}

  /* ── City autocomplete via OWM Geocoding API ── */
  if (inp && '{api_key_js}') {{
    var dl = document.createElement('datalist');
    dl.id = 'city-suggestions';
    inp.setAttribute('list', 'city-suggestions');
    inp.setAttribute('autocomplete', 'off');
    document.body.appendChild(dl);

    var timer = null;
    inp.addEventListener('input', function () {{
      clearTimeout(timer);
      var q = inp.value.trim();
      if (q.length < 2) {{ dl.innerHTML = ''; return; }}
      timer = setTimeout(function () {{
        fetch('https://api.openweathermap.org/geo/1.0/direct?q='
              + encodeURIComponent(q) + '&limit=5&appid={api_key_js}')
          .then(function (r) {{ return r.json(); }})
          .then(function (data) {{
            dl.innerHTML = (data || []).map(function (c) {{
              var label = c.name;
              if (c.state) label += ', ' + c.state;
              label += ', ' + c.country;
              return '<option value="' + label + '">';
            }}).join('');
          }})
          .catch(function () {{}});
      }}, 320);
    }});
  }}
}})();
</script>
</body>"""


# ── Build HTML to serve ───────────────────────────────────────────────────────
ak = api_key or ""

if not api_key:
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
            .replace("</body>", make_scripts(ak))
        )
    else:
        not_found_banner = f"""
<div style="position:fixed;top:18px;left:50%;transform:translateX(-50%);
            z-index:99999;background:rgba(255,68,68,.18);
            border:1px solid rgba(255,68,68,.45);backdrop-filter:blur(16px);
            border-radius:14px;padding:13px 22px;color:#fff;
            font-family:Outfit,sans-serif;font-size:14px;
            display:flex;align-items:center;gap:10px;white-space:nowrap;">
  ❌ No results for <strong style="margin:0 4px">{city}</strong> — check spelling and try again.
</div>"""
        display_html = html_content.replace("</body>",
            not_found_banner + make_scripts(ak).replace("</body>", ""))

else:
    # No city yet — show mock demo; search button will navigate to ?city=
    display_html = html_content.replace("</body>", make_scripts(ak))

# ── Render — fills 100 % of viewport via the CSS above ───────────────────────
st.components.v1.html(display_html, height=800, scrolling=True)
