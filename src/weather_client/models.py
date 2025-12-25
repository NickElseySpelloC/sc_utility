"""Data models for WeatherClient."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Wind:
    speed: float
    deg: float | None
    units: str = "km/h"


@dataclass
class WeatherReading:
    utc_time: datetime
    local_time: datetime
    temperature: float
    sky: str
    wind: Wind


@dataclass
class WeatherStation:
    source: str
    latitude: float
    longitude: float
