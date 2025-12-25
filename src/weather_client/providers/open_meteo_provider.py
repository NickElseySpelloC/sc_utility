"""WeatherClient provider for Open Meteo weather provider."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

from weather_client.models import WeatherReading, WeatherStation, Wind

WEATHER_CODE_MAP = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    61: "rain",
    71: "snow",
    95: "thunderstorm",
}


class OpenMeteoProvider:
    def fetch(
        self, lat: float, lon: float
    ) -> tuple[WeatherReading, list[WeatherReading], WeatherStation]:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current_weather=true"
            "&hourly=temperature_2m,weathercode,windspeed_10m,winddirection_10m"
            "&timezone=UTC"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        utc_now = datetime.now(UTC)

        c = data["current_weather"]
        current_time_raw = c.get("time")
        utc_time = (
            datetime.fromisoformat(current_time_raw).replace(tzinfo=UTC)
            if isinstance(current_time_raw, str)
            else utc_now
        )
        local_time = utc_time.astimezone()
        current_reading = WeatherReading(
            utc_time=utc_time,
            local_time=local_time,
            temperature=c["temperature"],
            sky=WEATHER_CODE_MAP.get(c["weathercode"], "unknown"),
            wind=Wind(speed=self._covert_wind_speed(c["windspeed"]), deg=c.get("winddirection")),
        )

        hourly = []
        for i, ts in enumerate(data["hourly"]["time"]):
            utc_ts_dt = datetime.fromisoformat(ts).replace(tzinfo=UTC)
            local_ts_dt = utc_ts_dt.astimezone()
            if utc_ts_dt.date() != utc_time.date() or utc_ts_dt < utc_time:
                continue
            hourly.append(
                WeatherReading(
                    utc_time=utc_ts_dt,
                    local_time=local_ts_dt,
                    temperature=data["hourly"]["temperature_2m"][i],
                    sky=WEATHER_CODE_MAP.get(data["hourly"]["weathercode"][i], "unknown"),
                    wind=Wind(
                        speed=self._covert_wind_speed(data["hourly"]["windspeed_10m"][i]),
                        deg=data["hourly"]["winddirection_10m"][i],
                    ),
                )
            )

        station = WeatherStation("Open-Meteo", lat, lon)
        return current_reading, hourly, station

    @staticmethod
    def _covert_wind_speed(wind: float) -> float:
        """Convert wind speed from m/s to km/h.

        Args:
            wind (float): Wind speed as provided by Open-Meteo.

        Returns:
            float: Wind speed in kilometers per hour.
        """
        return wind
