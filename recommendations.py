"""
Smart weather recommendations engine.
Returns a list of rec dicts: { p, icon, title, msg }
sorted high → medium → low, max 5 items.
"""

from datetime import datetime


def get_recommendations(weather_data, forecast_data, aqi_level=1, uv_index=0):
    recs = {"high": [], "medium": [], "low": []}

    current  = weather_data or {}
    main     = current.get("main", {})
    wind     = current.get("wind", {})
    weather  = current.get("weather", [{}])[0]

    temp        = main.get("temp", 20)
    feels_like  = main.get("feels_like", temp)
    wind_kmh    = wind.get("speed", 0) * 3.6
    weather_id  = weather.get("id", 800)
    humidity    = main.get("humidity", 50)

    # Rain intensity (mm in last 3 h) from first forecast slot
    rain_mm = 0
    if forecast_data and "list" in forecast_data and forecast_data["list"]:
        first = forecast_data["list"][0]
        rain_mm = first.get("rain", {}).get("3h", 0)

    # ── HIGH priority ────────────────────────────────────────────────────────

    if temp > 35:
        recs["high"].append({
            "p": "high", "icon": "🌡️",
            "title": "Extreme Heat Warning",
            "msg": "Stay indoors between 11 AM–4 PM. Drink at least 3 litres of water throughout the day.",
        })

    if weather_id // 100 == 2:
        recs["high"].append({
            "p": "high", "icon": "⛈️",
            "title": "Thunderstorm Warning",
            "msg": "Stay indoors. Avoid open areas, trees, and bodies of water. Unplug sensitive electronics.",
        })

    if weather_id // 100 == 5 and (weather_id >= 502 or rain_mm > 10):
        recs["high"].append({
            "p": "high", "icon": "🌧️",
            "title": "Heavy Rain Alert",
            "msg": "Avoid unnecessary travel. Heavy rain expected — wait for conditions to improve.",
        })

    if weather_id // 100 == 6:
        recs["high"].append({
            "p": "high", "icon": "❄️",
            "title": "Snow Advisory",
            "msg": "Drive slowly and watch for black ice. Wear appropriate footwear and layers outdoors.",
        })

    if aqi_level == 5:
        recs["high"].append({
            "p": "high", "icon": "🚨",
            "title": "Hazardous Air Quality",
            "msg": "Avoid all outdoor activity. Keep windows closed and use air purifiers indoors.",
        })

    # ── MEDIUM priority ──────────────────────────────────────────────────────

    if wind_kmh > 40:
        recs["medium"].append({
            "p": "medium", "icon": "💨",
            "title": "High Wind Advisory",
            "msg": "Secure outdoor furniture and loose items. Avoid driving high-profile vehicles on exposed roads.",
        })

    if feels_like < 5:
        recs["medium"].append({
            "p": "medium", "icon": "🧥",
            "title": "Cold Weather Alert",
            "msg": "Wear thermal layers, gloves, and a hat. Limit prolonged time outdoors.",
        })

    if aqi_level == 4:
        recs["medium"].append({
            "p": "medium", "icon": "😷",
            "title": "Poor Air Quality",
            "msg": "Wear an N95 mask when outdoors. Sensitive groups should remain inside.",
        })

    # Light drizzle (3xx) or light rain under heavy threshold (5xx < 502)
    if weather_id // 100 == 3 or (weather_id // 100 == 5 and weather_id < 502):
        recs["medium"].append({
            "p": "medium", "icon": "☔",
            "title": "Rain Expected",
            "msg": "Carry an umbrella. Light rain may persist through the day.",
        })

    # ── LOW priority ─────────────────────────────────────────────────────────

    if humidity > 85:
        recs["low"].append({
            "p": "low", "icon": "💧",
            "title": "High Humidity",
            "msg": "Stay in air-conditioned spaces when possible. Drink plenty of water to stay comfortable.",
        })

    if uv_index > 6:
        recs["low"].append({
            "p": "low", "icon": "🕶️",
            "title": "High UV Index",
            "msg": f"UV index is {uv_index}. Apply SPF 30+ sunscreen and reapply every 2 hours outdoors.",
        })

    if aqi_level == 3:
        recs["low"].append({
            "p": "low", "icon": "😷",
            "title": "Air Quality Moderate",
            "msg": "Sensitive groups (children, elderly, asthmatics) should limit prolonged outdoor activity.",
        })

    # Perfect conditions
    if weather_id in (800, 801) and 18 <= temp <= 28 and wind_kmh < 20:
        recs["low"].append({
            "p": "low", "icon": "✅",
            "title": "Perfect Outdoor Conditions",
            "msg": "Great conditions for a walk, run, or picnic — make the most of the weather!",
        })

    combined = recs["high"] + recs["medium"] + recs["low"]
    return combined[:5]
