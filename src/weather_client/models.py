"""Data models for WeatherClient."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Temperature:
    reading: float
    high: float | None = None
    low: float | None = None
    feels_like: float | None = None
    units: str = "C"


@dataclass
class SkyCondition:
    title: str                          # A short title for the sky condition (e.g., "Clear", "Cloudy", "Rain").
    description: str                    # A more detailed description of the sky condition (e.g., "Clear sky", "Overcast clouds", "Light rain").
    icon_code: str | None = None        # A code representing the sky condition, which can be used to look up an appropriate icon, e.g., 10d
    icon_png_url: str | None = None     # A URL to a PNG image representing the sky condition.
    cloud_cover: int | None = None      # The percentage of cloud cover (0 to 1)
    visibility: int | None = None       # The visibility in meters.
    uv_index: float | None = None       # The UV index as a percentage (0 to 1)


@dataclass
class Wind:
    speed: float
    deg: float | None
    gust: float | None = None
    units: str = "km/h"


@dataclass
class WeatherReading:
    utc_time: datetime
    local_time: datetime
    temperature: Temperature
    sky: SkyCondition
    wind: Wind
    summary: str | None = None          # A brief text summary of the weather conditions (e.g., "Light rain", "Partly cloudy").
    precip_probability: float | None = None
    rain: float | None = None
    pressure: float | None = None
    humidity: float | None = None
    dew_point: float | None = None
    sunrise: datetime | None = None
    sunset: datetime | None = None


@dataclass
class WeatherStation:
    source: str
    latitude: float
    longitude: float
    timezone_name: str | None = None
    timezone_offset: int | None = None


@dataclass
class WeatherData:
    current: WeatherReading        # The current weather reading.
    hourly: list[WeatherReading]   # A list of hourly weather readings for the next 48 hours (or as provided by the source).
    daily: list[WeatherReading]    # A list of daily weather readings for the next 7 days (or as provided by the source). May be empty.
    station: WeatherStation        # The weather station providing the data.
    as_at: datetime                # The timestamp when the data was last updated.
