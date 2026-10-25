"""Open-Meteo adapter. Store temperatures in Celsius; convert only when rendering."""
import json
import math
import ssl

import certifi
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ATTRIBUTION = "Weather: Open-Meteo.com (CC BY 4.0)"


def get_json(url, params):
    request = Request(url + "?" + urlencode(params), headers={"User-Agent": "InkyHome/0.1"})
    with urlopen(request, timeout=8, context=ssl.create_default_context(cafile=certifi.where())) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("Weather response is too large")
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("error"):
        raise ValueError("Weather provider returned an error")
    return data


def search_cities(query):
    data = get_json("https://geocoding-api.open-meteo.com/v1/search",
                    {"name": query, "count": 8, "language": "en", "format": "json"})
    cities = []
    for row in data.get("results", []):
        if not row.get("timezone"):
            continue
        cities.append({"name": row["name"], "region": row.get("admin1", ""),
                       "country": row.get("country", ""), "latitude": row["latitude"],
                       "longitude": row["longitude"], "timezone": row["timezone"]})
    return cities


def location_key(city):
    return f'{city["latitude"]:.5f},{city["longitude"]:.5f}'


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_city(city):
    if not isinstance(city, dict):
        raise ValueError("Choose a city from the search results")
    result = {}
    for key in ("name", "region", "country", "timezone"):
        value = city.get(key, "")
        if not isinstance(value, str) or len(value) > 120:
            raise ValueError("Invalid city details")
        result[key] = value
    if not result["name"]:
        raise ValueError("City needs a name")
    for key, limit in (("latitude", 90), ("longitude", 180)):
        value = city.get(key)
        if not number(value) or abs(value) > limit:
            raise ValueError("Invalid city coordinates")
        result[key] = float(value)
    try:
        ZoneInfo(result["timezone"])
    except (KeyError, ValueError):
        raise ValueError("City has an invalid timezone") from None
    return result


def normalize(data, city, now):
    current = data.get("current") or {}
    daily = data.get("daily") or {}
    hourly = data.get("hourly") or {}
    if not isinstance(current, dict) or not isinstance(daily, dict) or not isinstance(hourly, dict):
        raise ValueError("Invalid forecast response")
    days = []
    def item(section, key, index):
        values = section.get(key) or []
        value = values[index] if index < len(values) else None
        return value if number(value) else None
    for i, day in enumerate((daily.get("time") or [])[:4]):
        datetime.strptime(day, "%Y-%m-%d")
        days.append({"date": day, "high": item(daily, "temperature_2m_max", i),
                     "low": item(daily, "temperature_2m_min", i),
                     "rain": item(daily, "precipitation_probability_max", i),
                     "code": item(daily, "weather_code", i)})
    if not days:
        raise ValueError("Weather provider returned no forecast days")
    # Hourly probability closest to the current reading, rather than today's maximum.
    target = str(current.get("time", ""))[:13]
    index = next((i for i, value in enumerate(hourly.get("time", [])) if value[:13] == target), None)
    rain = item(hourly, "precipitation_probability", index) if index is not None else None
    return {"location_key": location_key(city), "fetched_at": now.isoformat(), "days": days,
            "temperature": current.get("temperature_2m") if number(current.get("temperature_2m")) else None,
            "feels_like": current.get("apparent_temperature") if number(current.get("apparent_temperature")) else None,
            "code": current.get("weather_code") if number(current.get("weather_code")) else None,
            "rain": rain}


class WeatherClient:
    def fetch(self, city, now):
        data = get_json("https://api.open-meteo.com/v1/forecast", {
            "latitude": city["latitude"], "longitude": city["longitude"],
            "current": "temperature_2m,apparent_temperature,weather_code",
            "hourly": "precipitation_probability",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": 4, "timezone": city["timezone"], "temperature_unit": "celsius"})
        return normalize(data, city, now)


class SampleWeatherClient:
    """Explicit opt-in fixture; never silently substitutes for a failed live fetch."""
    def fetch(self, city, now):
        today = now.astimezone(ZoneInfo(city["timezone"])).date()
        return {"location_key": location_key(city), "fetched_at": now.isoformat(),
                "temperature": 18, "feels_like": 17, "code": 2, "rain": 15,
                "days": [{"date": (today + timedelta(days=i)).isoformat(), "high": 20 + i,
                          "low": 12 + i, "rain": 15 + i * 10, "code": [2, 3, 61, 0][i]}
                         for i in range(4)]}


def condition(code):
    if code == 0: return "Clear skies"
    if code in (1, 2): return "Partly cloudy"
    if code == 3: return "Overcast"
    if code in (45, 48): return "Fog"
    if code in (51, 53, 55, 56, 57): return "Drizzle"
    if code in (61, 63, 65, 66, 67, 80, 81, 82): return "Rain"
    if code in (71, 73, 75, 77, 85, 86): return "Snow"
    if code in (95, 96, 99): return "Thunderstorms"
    return "Conditions unavailable"
