"""WeatherClient provider for OpenWeatherMap (OWM) API."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests
from pyowm import OWM
from pyowm.commons.exceptions import APIRequestError, UnauthorizedError

from weather_client.models import WeatherReading, WeatherStation, Wind


class OWMProvider:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._owm = OWM(api_key)
        self._mgr = self._owm.weather_manager()

    def fetch(
        self, lat: float, lon: float
    ) -> tuple[WeatherReading, list[WeatherReading], WeatherStation]:
        try:
            one_call = self._mgr.one_call(lat=lat, lon=lon, units="celsius")
        except UnauthorizedError:
            # Many "free" OpenWeatherMap keys don't have access to One Call.
            # Fall back to free-tier endpoints (current + 5-day/3-hour forecast).
            return self._fetch_free(lat, lon)
        except APIRequestError as e:
            error_msg = f"OpenWeatherMap request failed: {e}"
            raise RuntimeError(error_msg) from e

        utc_now = datetime.now(UTC)
        current = one_call.current

        current_reading = WeatherReading(
            utc_time=utc_now,
            local_time=utc_now.astimezone(),
            temperature=current.temperature("celsius")["temp"],
            sky=current.detailed_status,
            wind=Wind(speed=self._covert_wind_speed(current.wind()["speed"]), deg=current.wind().get("deg")),
        )

        hourly: list[WeatherReading] = []
        for h in one_call.forecast_hourly or []:
            ref = h.reference_time("unix")
            if isinstance(ref, datetime):
                utc_ts = ref if ref.tzinfo is not None else ref.replace(tzinfo=UTC)
            else:
                utc_ts = datetime.fromtimestamp(int(ref), tz=UTC)
            if utc_ts.date() != utc_now.date() or utc_ts < utc_now:
                continue
            hourly.append(
                WeatherReading(
                    utc_time=utc_ts,
                    local_time=utc_ts.astimezone(),
                    temperature=h.temperature("celsius")["temp"],
                    sky=h.detailed_status,
                    wind=Wind(speed=self._covert_wind_speed(h.wind()["speed"]), deg=h.wind().get("deg")),
                )
            )

        station = WeatherStation("OpenWeatherMap One Call API", lat, lon)
        return current_reading, hourly, station

    def _fetch_free(  # noqa: PLR0914
        self, lat: float, lon: float
    ) -> tuple[WeatherReading, list[WeatherReading], WeatherStation]:
        """Use free-tier endpoints: current weather + 5 day / 3 hour forecast.

        Args:
            lat (float): Latitude of the location.
            lon (float): Longitude of the location.

        Returns:
            tuple[WeatherReading, list[WeatherReading], WeatherStation]: Current reading, hourly forecast, and station info.
        """

        def _as_float(value: Any, *, field: str) -> float:
            try:
                return float(value)
            except (TypeError, ValueError) as e:
                error_msg = f"OpenWeatherMap response missing/invalid {field}"
                raise RuntimeError(error_msg) from e

        current_url = "https://api.openweathermap.org/data/2.5/weather"
        forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {"lat": lat, "lon": lon, "appid": self._api_key, "units": "metric"}

        current_resp = requests.get(current_url, params=params, timeout=10)
        current_resp.raise_for_status()
        current_data: dict[str, Any] = current_resp.json()

        utc_now = datetime.now(UTC)
        dt_raw = current_data.get("dt")
        dt_unix = int(dt_raw) if isinstance(dt_raw, (int, float)) else int(utc_now.timestamp())
        utc_current_time = datetime.fromtimestamp(dt_unix, tz=UTC)
        current_weather = (current_data.get("weather") or [{}])[0] or {}
        current_wind = current_data.get("wind") or {}
        # Convert the wind speed from m/s to km/h
        if "speed" in current_wind:
            current_wind["speed"] = self._covert_wind_speed(_as_float(current_wind["speed"], field="wind.speed"))
        current_main = current_data.get("main") or {}

        current_reading = WeatherReading(
            utc_time=utc_current_time,
            local_time=utc_current_time.astimezone(),
            temperature=_as_float(current_main.get("temp"), field="main.temp"),
            sky=str(current_weather.get("description") or "unknown"),
            wind=Wind(
                speed=_as_float(current_wind.get("speed", 0.0), field="wind.speed"),
                deg=(float(current_wind["deg"]) if "deg" in current_wind else None),
            ),
        )

        forecast_resp = requests.get(forecast_url, params=params, timeout=10)
        forecast_resp.raise_for_status()
        forecast_data: dict[str, Any] = forecast_resp.json()

        hourly: list[WeatherReading] = []
        for item in forecast_data.get("list", []):
            utc_ts = datetime.fromtimestamp(int(item.get("dt", 0)), tz=UTC)
            if utc_ts.date() != utc_now.date() or utc_ts < utc_now:
                continue

            weather = (item.get("weather") or [{}])[0] or {}
            wind = item.get("wind") or {}
            main = item.get("main") or {}

            hourly.append(
                WeatherReading(
                    utc_time=utc_ts,
                    local_time=utc_ts.astimezone(),
                    temperature=_as_float(main.get("temp"), field="forecast.main.temp"),
                    sky=str(weather.get("description") or "unknown"),
                    wind=Wind(
                        speed=_as_float(wind.get("speed", 0.0), field="forecast.wind.speed"),
                        deg=(float(wind["deg"]) if "deg" in wind else None),
                    ),
                )
            )

        station = WeatherStation("OpenWeatherMap (free)", lat, lon)
        return current_reading, hourly, station

    @staticmethod
    def _covert_wind_speed(wind: float) -> float:
        """Convert wind speed from m/s to km/h.

        Args:
            wind (float): Wind speed in meters per second.

        Returns:
            float: Wind speed in kilometers per hour.
        """
        return wind * 3.6
