"""
Weather client example script.

This script demonstrates usage of the WeatherClient to fetch current weather,
hourly forecasts, and station information for Sydney, Australia coordinates.

Environment Variables:
    OWM_API_KEY: OpenWeatherMap API key required for weather data access.
                 This environment variable must be set before running the script.

The script fetches weather data for coordinates (-33.86, 151.21) representing
Sydney and prints current conditions, station info, and the number of hourly
forecast data points available.
"""
import os
import sys
from pathlib import Path

# Allow running this example directly from a src/ layout checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from weather_client import WeatherClient

api_key = os.environ.get("OWM_API_KEY")
client = WeatherClient(
    latitude=-33.7234659,
    longitude=151.0965371,
    owm_api_key=api_key,
)

current, hourly, station = client.get_weather()
# current, hourly, station = client.get_open_meteo_weather()

print("\n\nWeather data for Sydney, Australia (lat: -33.86, lon: 151.21)")
print(f"Using APU key: {api_key}")
print(f"Current weather: {current}")
print(f"Station: {station}")
print(len(hourly), "hourly points")
