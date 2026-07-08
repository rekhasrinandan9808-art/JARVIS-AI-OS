"""
location/agent.py
LocationAgent -- device location + weather. Not one of the numbered 39
(matches the architecture doc, where location/ sits alongside the 39
agents, not inside them). Uses two free, no-API-key services:

  - IP geolocation: ip-api.com (free tier, no key, ~45 req/min)
  - Weather + geocoding: Open-Meteo (api.open-meteo.com, fully free, no key)

NOTE: this sandbox has no network access, so these HTTP calls are written
correctly but UNVERIFIED here. Test them on your actual machine.
"""

from __future__ import annotations
import json
import urllib.request
import urllib.parse
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


# Open-Meteo WMO weather codes -> human description
WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "depositing rime fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    71: "slight snow", 73: "moderate snow", 75: "heavy snow",
    80: "slight rain showers", 81: "moderate rain showers", 82: "violent rain showers",
    95: "thunderstorm", 96: "thunderstorm with slight hail", 99: "thunderstorm with heavy hail",
}


class LocationAgent(BaseAgent):
    name = "location"
    description = (
        "Reports this device's approximate location via IP geolocation, geocodes place "
        "names, and fetches current weather for any location. Uses free no-key APIs "
        "(ip-api.com, open-meteo.com) -- no accounts or billing required."
    )
    agent_id = 0  # not one of the numbered 39; see module docstring

    def _http_get_json(self, url: str, timeout: int = 10) -> dict:
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-AI-OS/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("my_location", "Get this device's approximate location via IP geolocation", {}),
            AgentCapability("geocode", "Convert a place name to lat/lon", {"place": "str"}),
            AgentCapability("weather", "Get current weather for a place name, or explicit lat/lon", {"place": "str (optional)", "lat": "float (optional)", "lon": "float (optional)"}),
            AgentCapability("weather_here", "Get current weather at this device's IP-geolocated position", {}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "my_location":
            data = self._http_get_json("http://ip-api.com/json/")
            if data.get("status") != "success":
                raise RuntimeError("IP geolocation failed: " + str(data.get("message", "unknown error")))
            return {
                "city": data.get("city"),
                "region": data.get("regionName"),
                "country": data.get("country"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "timezone": data.get("timezone"),
                "isp": data.get("isp"),
                "note": "Approximate -- derived from IP address, not GPS. Accuracy is city-level at best.",
            }

        if action == "geocode":
            place = params["place"]
            url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({"name": place, "count": 1})
            data = self._http_get_json(url)
            results = data.get("results") or []
            if not results:
                raise ValueError("No location found for '" + place + "'")
            r = results[0]
            return {
                "place": place,
                "name": r["name"],
                "country": r.get("country"),
                "lat": r["latitude"],
                "lon": r["longitude"],
                "timezone": r.get("timezone"),
            }

        if action in ("weather", "weather_here"):
            if action == "weather_here" or (not params.get("lat") and params.get("place") is None):
                loc = await self._run("my_location", {})
                lat, lon, label = loc["lat"], loc["lon"], loc["city"]
            elif params.get("place"):
                geo = await self._run("geocode", {"place": params["place"]})
                lat, lon, label = geo["lat"], geo["lon"], geo["name"]
            else:
                lat, lon, label = params["lat"], params["lon"], f"{params['lat']},{params['lon']}"

            url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "temperature_unit": "celsius",
            })
            data = self._http_get_json(url)
            current = data.get("current", {})
            code = current.get("weather_code")
            return {
                "location": label,
                "lat": lat, "lon": lon,
                "temperature_c": current.get("temperature_2m"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "wind_speed_kmh": current.get("wind_speed_10m"),
                "condition": WEATHER_CODES.get(code, "unknown (" + str(code) + ")"),
            }
