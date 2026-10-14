import logging
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
logger = logging.getLogger(__name__)
# httpx logs full request URLs at INFO, including WeatherAPI's query-string key.
logging.getLogger("httpx").setLevel(logging.WARNING)
port = int(os.getenv("PORT", 8085))
mcp = FastMCP("weather", host="0.0.0.0", port=port)

# Constants
WEATHERAPI_BASE = "https://api.weatherapi.com/v1"
USER_AGENT = "weather-app/1.0"

def weather_api_key() -> str | None:
    value = os.getenv("WEATHERAPI_KEY", "").strip()
    if not value or value == "replace_with_your_weatherapi_key":
        return None
    return value

async def make_weather_request(endpoint: str, params: dict[str, str]) -> dict[str, Any] | None:
    """Make a request to the WeatherAPI with proper error handling."""
    api_key = weather_api_key()
    if not api_key:
        logger.error("WEATHERAPI_KEY is not configured")
        return None
        
    headers = {
        "User-Agent": USER_AGENT,
    }
    url = f"{WEATHERAPI_BASE}/{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url, headers=headers, params={**params, "key": api_key}, timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("WeatherAPI returned HTTP %s", e.response.status_code)
            return None
        except httpx.RequestError as e:
            logger.error("WeatherAPI request failed: %s", e)
            return None

@mcp.tool()
async def get_current_weather(city: str) -> str:
    """Get current weather conditions for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney")
    """
    params = {
        "q": city,
        "aqi": "no"
    }
    
    data = await make_weather_request("current.json", params)

    if not data:
        if not weather_api_key():
            return f"❌ WeatherAPI key not configured. Please set WEATHERAPI_KEY environment variable with your API key from weatherapi.com"
        return f"Unable to fetch current weather data for {city}. Please check the city name and API key configuration."

    current = data["current"]
    location = data["location"]
    
    return f"""
Current Weather for {location['name']}, {location['region']}, {location['country']}:

Temperature: {current['temp_c']}°C ({current['temp_f']}°F)
Feels like: {current['feelslike_c']}°C ({current['feelslike_f']}°F)
Condition: {current['condition']['text']}
Humidity: {current['humidity']}%
Wind: {current['wind_kph']} km/h ({current['wind_mph']} mph) {current['wind_dir']}
Pressure: {current['pressure_mb']} mb
UV Index: {current['uv']}
Visibility: {current['vis_km']} km

Last updated: {current['last_updated']}
"""

@mcp.tool()
async def get_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney", "Melbourne")
        days: Number of days to forecast (1-3)
    """
    if not 1 <= days <= 3:
        return "Forecast days must be between 1 and 3."
    
    params = {
        "q": city,
        "days": str(days),
        "aqi": "no",
        "alerts": "no"
    }
    
    data = await make_weather_request("forecast.json", params)

    if not data:
        if not weather_api_key():
            return f"❌ WeatherAPI key not configured. Please set WEATHERAPI_KEY environment variable with your API key from weatherapi.com"
        return f"Unable to fetch forecast data for {city}. Please check the city name and API key configuration."

    location = data["location"]
    forecast_days = data["forecast"]["forecastday"]
    
    forecasts = []
    forecasts.append(f"Weather Forecast for {location['name']}, {location['region']}, {location['country']}:")
    
    for day in forecast_days:
        day_data = day["day"]
        date = day["date"]
        
        forecast = f"""
{date}:
High: {day_data['maxtemp_c']}°C ({day_data['maxtemp_f']}°F)
Low: {day_data['mintemp_c']}°C ({day_data['mintemp_f']}°F)
Condition: {day_data['condition']['text']}
Chance of Rain: {day_data['daily_chance_of_rain']}%
Max Wind: {day_data['maxwind_kph']} km/h
UV Index: {day_data['uv']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

@mcp.tool()
async def health_check() -> str:
    """Health check endpoint for deployment verification."""
    key_status = "configured" if weather_api_key() else "missing"
    return f"Weather MCP Server is running. WEATHERAPI_KEY: {key_status}."

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Weather MCP server at http://0.0.0.0:%s/mcp", port)
    mcp.run(transport="streamable-http")
