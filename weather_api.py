import requests
import streamlit as st
from datetime import datetime, timedelta
from collections import defaultdict


BASE_URL = "https://api.openweathermap.org/data/2.5"
GEO_URL  = "https://api.openweathermap.org/geo/1.0"


# ── formatting ────────────────────────────────────────────────────────────────

def _fmt_hour(dt):
    h = dt.hour % 12 or 12
    return f"{h}{'AM' if dt.hour < 12 else 'PM'}"

def _fmt_time(dt):
    h = dt.hour % 12 or 12
    return f"{h}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"

def _fmt_date(dt):
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    days   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    return f"{days[dt.weekday()]}, {months[dt.month-1]} {dt.day}"


# ── state / icon / emoji ──────────────────────────────────────────────────────

def determine_state(weather_id, is_night):
    if is_night and 800 <= weather_id <= 802:
        return "night"
    wgrp = weather_id // 100
    if wgrp == 2:  return "stormy"
    if wgrp in (3, 5):  return "rainy"
    if wgrp == 6:  return "snowy"
    if weather_id in (803, 804):  return "rainy"
    return "sunny"

def determine_icon(weather_id, is_night):
    if weather_id == 800:
        return "clear-night" if is_night else "clear-day"
    if weather_id in (801, 802):
        return "few-clouds-night" if is_night else "few-clouds"
    if weather_id in (803, 804):
        return "few-clouds"
    wgrp = weather_id // 100
    if wgrp == 2:  return "storm"
    if wgrp in (3, 5):  return "rain"
    if wgrp == 6:  return "snow"
    if wgrp == 7:  return "fog"
    return "few-clouds"

def weather_emoji(weather_id, is_night):
    if weather_id == 800:  return "🌙" if is_night else "☀️"
    if weather_id == 801:  return "🌤️"
    if weather_id in (802, 803):  return "⛅"
    if weather_id == 804:  return "☁️"
    wgrp = weather_id // 100
    if wgrp == 2:  return "⛈️"
    if wgrp == 3:  return "🌦️"
    if weather_id in (500, 501):  return "🌧️"
    if wgrp == 5:  return "🌦️"
    if wgrp == 6:  return "🌨️"
    if wgrp == 7:  return "🌫️"
    return "🌡️"


# ── API key validation ────────────────────────────────────────────────────────

def validate_api_key(api_key):
    """Returns 'valid', 'invalid', or 'network_error'."""
    try:
        r = requests.get(
            f"{BASE_URL}/weather",
            params={"q": "London", "appid": api_key, "units": "metric"},
            timeout=8,
        )
        if r.status_code in (401, 403):
            return "invalid"
        if r.status_code == 200:
            return "valid"
        return "network_error"
    except Exception:
        return "network_error"


# ── geocoding ─────────────────────────────────────────────────────────────────

def geocode_location(location, api_key):
    try:
        r = requests.get(
            f"{GEO_URL}/direct",
            params={"q": location, "limit": 1, "appid": api_key},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if data:
            g = data[0]
            parts = [g.get("name", "")]
            if g.get("state"):
                parts.append(g["state"])
            parts.append(g.get("country", ""))
            return g["lat"], g["lon"], ", ".join(p for p in parts if p)
        return None, None, None
    except Exception:
        return None, None, None


# ── weather fetchers ──────────────────────────────────────────────────────────

def _weather_by_coords(lat, lon, api_key):
    try:
        r = requests.get(f"{BASE_URL}/weather",
                         params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
                         timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def _weather_by_name(location, api_key):
    try:
        r = requests.get(f"{BASE_URL}/weather",
                         params={"q": location, "appid": api_key, "units": "metric"},
                         timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def get_forecast(lat, lon, api_key):
    try:
        r = requests.get(f"{BASE_URL}/forecast",
                         params={"lat": lat, "lon": lon, "cnt": 40,
                                 "appid": api_key, "units": "metric"},
                         timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def get_aqi(lat, lon, api_key):
    try:
        r = requests.get(f"{BASE_URL}/air_pollution",
                         params={"lat": lat, "lon": lon, "appid": api_key},
                         timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def get_uvi(lat, lon, api_key):
    try:
        r = requests.get(f"{BASE_URL}/uvi",
                         params={"lat": lat, "lon": lon, "appid": api_key},
                         timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ── main builder ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def build_data_object(location, api_key):
    """Returns a data dict on success, or None on failure."""
    try:
        from recommendations import get_recommendations

        # ── 1. Resolve location → lat/lon ──────────────────────────────────
        lat, lon, geo_display = geocode_location(location, api_key)
        current = None

        if lat is not None:
            current = _weather_by_coords(lat, lon, api_key)

        if current is None:
            current = _weather_by_name(location, api_key)
            if current:
                lat = current["coord"]["lat"]
                lon = current["coord"]["lon"]
                geo_display = None

        if not current:
            return None

        # ── 2. Timezone offset (OWM returns seconds east of UTC) ────────────
        tz_offset = current.get("timezone", 0)

        def _local(ts):
            """Convert UTC Unix timestamp → local datetime using OWM's tz offset."""
            return datetime.utcfromtimestamp(ts + tz_offset)

        # ── 3. Night detection ──────────────────────────────────────────────
        now_ts     = current.get("dt", 0)
        sunrise_ts = current.get("sys", {}).get("sunrise", 0)
        sunset_ts  = current.get("sys", {}).get("sunset", 0)
        is_night   = not (sunrise_ts <= now_ts <= sunset_ts)

        weather_id = current["weather"][0]["id"]

        # ── 4. Hourly: next 12 × 3-h forecast slots ────────────────────────
        forecast_data = get_forecast(lat, lon, api_key)
        hourly = []
        if forecast_data and "list" in forecast_data:
            for entry in forecast_data["list"][:12]:
                dt  = _local(entry["dt"])
                wid = entry["weather"][0]["id"]
                h   = dt.hour
                hourly.append({
                    "t":    _fmt_hour(dt),
                    "temp": round(entry["main"]["temp"]),
                    "rain": round(entry.get("pop", 0) * 100),
                    "e":    weather_emoji(wid, h < 6 or h >= 20),
                })

        # ── 5. 5-day forecast ───────────────────────────────────────────────
        forecast = []
        if forecast_data and "list" in forecast_data:
            days_map = defaultdict(list)
            for entry in forecast_data["list"]:
                day_key = _local(entry["dt"]).strftime("%Y-%m-%d")
                days_map[day_key].append(entry)

            today       = _local(now_ts).strftime("%Y-%m-%d")
            future_days = sorted(d for d in days_map if d > today)[:5]
            if len(future_days) < 5:
                future_days = sorted(days_map.keys())[:5]

            for dk in future_days:
                entries = days_map[dk]
                dt      = datetime.strptime(dk, "%Y-%m-%d")
                temps   = [e["main"]["temp"] for e in entries]
                pops    = [e.get("pop", 0) * 100 for e in entries]
                midday  = min(entries,
                              key=lambda e: abs(_local(e["dt"]).hour - 12))
                wid  = midday["weather"][0]["id"]
                desc = midday["weather"][0]["description"]
                forecast.append({
                    "day":  dt.strftime("%a"),
                    "e":    weather_emoji(wid, False),
                    "desc": desc,
                    "hi":   round(max(temps)),
                    "lo":   round(min(temps)),
                    "rain": round(max(pops)),
                })

        # ── 6. AQI ─────────────────────────────────────────────────────────
        aqi_data  = get_aqi(lat, lon, api_key)
        aqi_level = 1
        poll = {"CO": 0, "NO": 0, "NO2": 0, "O3": 0, "PM25": 0, "PM10": 0}
        if aqi_data and "list" in aqi_data and aqi_data["list"]:
            item = aqi_data["list"][0]
            aqi_level = item["main"]["aqi"]
            c = item.get("components", {})
            poll = {
                "CO":   round(c.get("co",    0), 1),
                "NO":   round(c.get("no",    0), 1),
                "NO2":  round(c.get("no2",   0), 1),
                "O3":   round(c.get("o3",    0), 1),
                "PM25": round(c.get("pm2_5", 0), 1),
                "PM10": round(c.get("pm10",  0), 1),
            }

        # ── 7. UV ──────────────────────────────────────────────────────────
        uvi_data  = get_uvi(lat, lon, api_key)
        uv_index  = round(uvi_data["value"]) if uvi_data and "value" in uvi_data else 0

        # ── 8. Sunrise / sunset / daylight (all in local time) ──────────────
        sunrise_dt = _local(sunrise_ts) if sunrise_ts else datetime.utcnow()
        sunset_dt  = _local(sunset_ts)  if sunset_ts  else datetime.utcnow()
        daylight_s = max(0, sunset_ts - sunrise_ts)

        # ── 9. City display name ────────────────────────────────────────────
        owm_name = current.get("name", "")
        country  = current.get("sys", {}).get("country", "")
        city_str = geo_display or (f"{owm_name}, {country}" if country else owm_name)

        # ── 10. Assemble ────────────────────────────────────────────────────
        wind_kmh = round(current.get("wind", {}).get("speed", 0) * 3.6)
        now_dt   = _local(now_ts)
        recs     = get_recommendations(current, forecast_data, aqi_level, uv_index)

        return {
            "state": determine_state(weather_id, is_night),
            "icon":  determine_icon(weather_id, is_night),
            "city":  city_str,
            "date":  _fmt_date(now_dt),
            "time":  _fmt_time(now_dt),
            "desc":  current["weather"][0]["description"],
            "temp":  round(current["main"]["temp"]),
            "feels": round(current["main"]["feels_like"]),
            "stats": {
                "humidity":   current["main"]["humidity"],
                "wind":       wind_kmh,
                "pressure":   current["main"]["pressure"],
                "visibility": round(current.get("visibility", 10000) / 1000, 1),
                "clouds":     current.get("clouds", {}).get("all", 0),
            },
            "recs":     recs,
            "hourly":   hourly,
            "forecast": forecast,
            "aqi":  {"level": aqi_level, "poll": poll},
            "uv":   {
                "index":    uv_index,
                "sunrise":  _fmt_time(sunrise_dt),
                "sunset":   _fmt_time(sunset_dt),
                "daylight": f"{daylight_s // 3600}h {(daylight_s % 3600) // 60:02d}m",
            },
        }
    except Exception:
        return None
