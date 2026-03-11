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
from pprint import pprint

# Allow running this example directly from a src/ layout checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from weather_client import WeatherClient

api_key = os.environ.get("OWM_API_KEY_V3")
client = WeatherClient(
    latitude=-33.7234659,
    longitude=151.0965371,
    owm_api_key=api_key,
)

weather_data = client.get_weather(first_choice="owm")

print("\n\nWeather data for Sydney, Australia (lat: -33.86, lon: 151.21)")
print(f"Using APU key: {api_key}")
print("Current weather:")
pprint(weather_data.current, indent=4)
print(f"Station: {weather_data.station}")

print(len(weather_data.hourly), "hourly points")
for hour in weather_data.hourly[:4]:  # Print the first 4 hourly forecasts
    pprint(hour, indent=4)

print(len(weather_data.daily), "daily points")
for day in weather_data.daily[:4]:  # Print the first 4 daily forecasts
    pprint(day, indent=4)
