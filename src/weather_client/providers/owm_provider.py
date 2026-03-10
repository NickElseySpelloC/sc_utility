"""WeatherClient provider for OpenWeatherMap (OWM) API.

Refer to the documentation for details on the endpoints used:
https://nickelseyspelloc.github.io/sc_utility/reference/weather_client/

"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests
from pyowm import OWM
from pyowm.commons.exceptions import APIRequestError, UnauthorizedError
from pyowm.weatherapi30.weather import Weather

from weather_client.models import (
    SkyCondition,
    Temperature,
    WeatherData,
    WeatherReading,
    WeatherStation,
    Wind,
)


class OWMProvider:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._owm = OWM(api_key)
        self._mgr = self._owm.weather_manager()

    def fetch(self, lat: float, lon: float) -> WeatherData:
        """Fetch weather data from OpenWeatherMap.

        Args:
            lat (float): Latitude of the location.
            lon (float): Longitude of the location.

        Raises:
            RuntimeError: If the OWM API key is not set or if the request fails.
            NotImplementedError: If the OWM API key does not have access to the One Call API.

        Returns:
            A WeatherData object containing the current reading, list of hourly readings, and weather station info.
        """
        try:
            one_call = self._mgr.one_call(lat=lat, lon=lon, units="celsius")
        except UnauthorizedError as e:
            # Many "free" OpenWeatherMap keys don't have access to One Call.
            # Fall back to free-tier endpoints (current + 5-day/3-hour forecast).
            error_msg = "Not implemented"
            raise NotImplementedError(error_msg) from e
            # return self._fetch_free(lat, lon)
        except APIRequestError as e:
            error_msg = f"OpenWeatherMap request failed: {e}"
            raise RuntimeError(error_msg) from e

        local_tz = datetime.now().astimezone().tzinfo
        utc_now = datetime.now(UTC)
        time_now = datetime.now(tz=local_tz)
        current = one_call.current
        hourly = one_call.forecast_hourly or []
        daily = one_call.forecast_daily or []

        # Build up the current reading. The One Call API doesn't provide high/low or feels-like for the current weather, so those will be None.
        current_sky = SkyCondition(
            title=current.status,
            description=current.detailed_status,
            icon_code=current.weather_icon_name,
            icon_png_url=self._get_icon_url(current.weather_icon_name),
            cloud_cover=current.clouds / 100 if current.clouds is not None else None,
            visibility=current.visibility_distance,
            uv_index=current.uvi / 100 if current.uvi is not None else None)

        current_reading = WeatherReading(
            utc_time=utc_now,
            local_time=utc_now.astimezone(),
            temperature=Temperature(reading=current.temperature("celsius")["temp"]),
            sky=current_sky,
            wind=Wind(
                speed=self._covert_wind_speed(current.wind()["speed"]),
                deg=current.wind().get("deg"),
                gust=self._covert_wind_speed(current.wind().get("gust", 0.0)) if "gust" in current.wind() else None,
            ),
            summary=current.detailed_status,
            precip_probability=current.precipitation_probability if current.precipitation_probability is not None else None,
            rain=self._get_rain(current, "all"),
            pressure=current.pressure["press"] if current.pressure else None,
            humidity=current.humidity / 100 if current.humidity is not None else None,
            dew_point=current.dewpoint("celsius") if current.dewpoint else None,
            sunrise=self._convert_unix_time_to_datetime(current.sunrise_time("unix")) if current.sunrise_time() else None,
            sunset=self._convert_unix_time_to_datetime(current.sunset_time("unix")) if current.sunset_time() else None,
        )

        # Build up the hourly reading
        hourly: list[WeatherReading] = []
        for hour in one_call.forecast_hourly or []:
            utc_timestamp = self._convert_unix_time_to_datetime(hour.ref_time)
            local_timestamp = self._convert_unix_time_to_datetime(hour.ref_time, get_local=True)
            if local_timestamp < time_now:
                continue

            hour_sky = SkyCondition(
                title=hour.status,
                description=hour.detailed_status,
                icon_code=hour.weather_icon_name,
                icon_png_url=self._get_icon_url(hour.weather_icon_name),
                cloud_cover=hour.clouds / 100 if hour.clouds is not None else None,
                visibility=hour.visibility_distance,
                uv_index=hour.uvi / 100 if hour.uvi is not None else None)

            hourly.append(
                WeatherReading(
                    utc_time=utc_timestamp,
                    local_time=local_timestamp,
                    temperature=Temperature(
                        reading=hour.temperature("celsius")["temp"],
                        feels_like=hour.temperature("celsius").get("feels_like")),
                    sky=hour_sky,
                    wind=Wind(speed=self._covert_wind_speed(hour.wind()["speed"]), deg=hour.wind().get("deg")),
                )
            )

        daily: list[WeatherReading] = []

        station = WeatherStation("OpenWeatherMap One Call API", lat, lon)

        # Build the final response object.
        return_data = WeatherData(current=current_reading, hourly=hourly, daily=daily, station=station, as_at=datetime.now(tz=local_tz))
        return return_data

    # def _fetch_free(self, lat: float, lon: float) -> WeatherData:
    #     """Use free-tier endpoints: current weather + 5 day / 3 hour forecast.

    #     Args:
    #         lat (float): Latitude of the location.
    #         lon (float): Longitude of the location.

    #     Returns:
    #         tuple[WeatherReading, list[WeatherReading], WeatherStation]: Current reading, hourly forecast, and station info.
    #     """

    #     def _as_float(value: Any, *, field: str) -> float:
    #         try:
    #             return float(value)
    #         except (TypeError, ValueError) as e:
    #             error_msg = f"OpenWeatherMap response missing/invalid {field}"
    #             raise RuntimeError(error_msg) from e

    #     current_url = "https://api.openweathermap.org/data/2.5/weather"
    #     forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
    #     params = {"lat": lat, "lon": lon, "appid": self._api_key, "units": "metric"}

    #     current_resp = requests.get(current_url, params=params, timeout=10)
    #     current_resp.raise_for_status()
    #     current_data: dict[str, Any] = current_resp.json()

    #     utc_now = datetime.now(UTC)
    #     dt_raw = current_data.get("dt")
    #     dt_unix = int(dt_raw) if isinstance(dt_raw, (int, float)) else int(utc_now.timestamp())
    #     utc_current_time = datetime.fromtimestamp(dt_unix, tz=UTC)
    #     current_weather = (current_data.get("weather") or [{}])[0] or {}
    #     current_wind = current_data.get("wind") or {}
    #     # Convert the wind speed from m/s to km/h
    #     if "speed" in current_wind:
    #         current_wind["speed"] = self._covert_wind_speed(_as_float(current_wind["speed"], field="wind.speed"))
    #     current_main = current_data.get("main") or {}

    #     current_reading = WeatherReading(
    #         utc_time=utc_current_time,
    #         local_time=utc_current_time.astimezone(),
    #         temperature=_as_float(current_main.get("temp"), field="main.temp"),
    #         temperature_high=_as_float(current_main.get("temp_max"), field="main.temp_max"),
    #         temperature_low=_as_float(current_main.get("temp_min"), field="main.temp_min"),
    #         feels_like=_as_float(current_main.get("feels_like"), field="main.feels_like"),
    #         sky=str(current_weather.get("description") or "unknown"),
    #         wind=Wind(
    #             speed=_as_float(current_wind.get("speed", 0.0), field="wind.speed"),
    #             deg=(float(current_wind["deg"]) if "deg" in current_wind else None),
    #             gusts=_as_float(current_wind["gust"], field="wind.gust") if "gust" in current_wind else None,
    #         ),
    #     )

    #     forecast_resp = requests.get(forecast_url, params=params, timeout=10)
    #     forecast_resp.raise_for_status()
    #     forecast_data: dict[str, Any] = forecast_resp.json()

    #     hourly: list[WeatherReading] = []
    #     for item in forecast_data.get("list", []):
    #         utc_ts = datetime.fromtimestamp(int(item.get("dt", 0)), tz=UTC)
    #         if utc_ts < utc_now:    # Issue 35
    #             continue

    #         weather = (item.get("weather") or [{}])[0] or {}
    #         wind = item.get("wind") or {}
    #         main = item.get("main") or {}

    #         hourly.append(
    #             WeatherReading(
    #                 utc_time=utc_ts,
    #                 local_time=utc_ts.astimezone(),
    #                 temperature=_as_float(main.get("temp"), field="forecast.main.temp"),
    #                 temperature_high=_as_float(main.get("temp_max"), field="forecast.main.temp_max"),
    #                 temperature_low=_as_float(main.get("temp_min"), field="forecast.main.temp_min"),
    #                 feels_like=_as_float(main.get("feels_like"), field="forecast.main.feels_like"),
    #                 sky=str(weather.get("description") or "unknown"),
    #                 wind=Wind(
    #                     speed=_as_float(wind.get("speed", 0.0), field="forecast.wind.speed"),
    #                     deg=(float(wind["deg"]) if "deg" in wind else None),
    #                     gusts=_as_float(wind["gust"], field="forecast.wind.gust") if "gust" in wind else None,
    #                 ),
    #             )
    #         )

    #     station = WeatherStation("OpenWeatherMap (free)", lat, lon)
    #     return current_reading, hourly, station

    @staticmethod
    def _covert_wind_speed(wind: float) -> float:
        """Convert wind speed from m/s to km/h.

        Args:
            wind (float): Wind speed in meters per second.

        Returns:
            float: Wind speed in kilometers per hour.
        """
        return wind * 3.6

    @staticmethod
    def _get_rain(rain_data: list[Weather] | Weather | None, key: str) -> float | None:
        """Extract the rain volume from the OWM response.

        The OWM API may provide rain data in different formats (e.g., "1h" for last hour, "3h" for last 3 hours).
        This method will attempt to extract the most recent rain volume available.

        Args:
            rain_data (list[Weather] | Weather | None): The "rain" field from the OWM API response. Might be None.
            key (str): The key to look for in the rain data (e.g., "1h" or "3h").

        Returns:
            float: The rain volume in mm, or None if no rain data is available.
        """
        if not rain_data:
            return None
        if isinstance(rain_data, list):
            src_weather = rain_data[0]
        elif isinstance(rain_data, Weather):
            src_weather = rain_data
        else:
            return None

        rain = src_weather.rain
        if rain and key in rain:
            return float(rain[key])
        return None

    @staticmethod
    def _get_icon_url(icon_code: str | None) -> str | None:
        """Get the URL for an OpenWeatherMap icon code.

        OWM icons can be retrieved at https://openweathermap.org/payload/api/media/file/<icon_code>.png

        Args:
            icon_code (str): The OWM icon code (e.g., "10d").

        Returns:
            str: The URL to the corresponding PNG icon, or None if the icon code is not provided.
        """
        if not icon_code:
            return None
        return f"https://openweathermap.org/payload/api/media/file/{icon_code}.png"

    @staticmethod
    def _convert_unix_time_to_datetime(unix_time: int, get_local: bool = False) -> datetime:
        """Convert a Unix timestamp to a timezone-aware datetime object in UTC.

        Args:
            unix_time (int): The Unix timestamp to convert.
            get_local (bool): Whether to convert the time to the local timezone.

        Returns:
            datetime: The converted datetime object.
        """
        dt = datetime.fromtimestamp(unix_time, tz=UTC)
        if get_local:
            dt = dt.astimezone()
        return dt
