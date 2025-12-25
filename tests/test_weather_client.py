from __future__ import annotations

from datetime import UTC, datetime

from weather_client import WeatherClient
from weather_client.models import WeatherReading, WeatherStation, Wind
from weather_client.providers.open_meteo_provider import OpenMeteoProvider
from weather_client.providers.owm_provider import OWMProvider


def test_client_falls_back_to_open_meteo(mocker):
    utc_time = datetime(2025, 12, 20, 12, 0, tzinfo=UTC)
    expected = (
        WeatherReading(
            utc_time=utc_time,
            local_time=utc_time.astimezone(),
            temperature=20.0,
            sky="clear sky",
            wind=Wind(speed=3.0, deg=180.0),
        ),
        [],
        WeatherStation(source="Open-Meteo", latitude=-33.86, longitude=151.21),
    )

    mocker.patch.object(OWMProvider, "fetch", side_effect=RuntimeError("boom"))
    open_meteo_fetch = mocker.patch.object(OpenMeteoProvider, "fetch", return_value=expected)

    client = WeatherClient(-33.86, 151.21, owm_api_key="dummy")
    assert client.get_weather() == expected
    open_meteo_fetch.assert_called_once()


def test_client_uses_owm_when_available(mocker):
    utc_time = datetime(2025, 12, 20, 12, 0, tzinfo=UTC)

    expected = (
        WeatherReading(
            utc_time=utc_time,
            local_time=utc_time.astimezone(),
            temperature=22.0,
            sky="sunny",
            wind=Wind(speed=2.0, deg=None),
        ),
        [],
        WeatherStation(source="OpenWeatherMap One Call API", latitude=-33.86, longitude=151.21),
    )

    owm_fetch = mocker.patch.object(OWMProvider, "fetch", return_value=expected)
    mocker.patch.object(OpenMeteoProvider, "fetch", side_effect=AssertionError("should not call"))

    client = WeatherClient(-33.86, 151.21, owm_api_key="dummy")
    assert client.get_weather() == expected
    owm_fetch.assert_called_once()
