from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pyowm.commons.exceptions import UnauthorizedError

from weather_client.providers.owm_provider import OWMProvider


class _FakeResponse:
    def __init__(self, payload, *, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error_msg = f"HTTP {self.status_code} Error"
            raise RuntimeError(error_msg)

    def json(self):
        return self._payload


def test_owm_provider_falls_back_to_free_endpoints_on_unauthorized(mocker):
    provider = OWMProvider("dummy")
    mocker.patch.object(
        provider._mgr,  # noqa: SLF001
        "one_call",
        side_effect=UnauthorizedError("Invalid API Key provided"),
    )

    now = datetime(2025, 12, 21, 4, 0, tzinfo=UTC)
    mocker.patch("weather_client.providers.owm_provider.datetime", wraps=datetime)
    mocker.patch("weather_client.providers.owm_provider.datetime.now", return_value=now)

    current_payload = {
        "dt": int(now.timestamp()),
        "main": {"temp": 20.5},
        "weather": [{"description": "clear sky"}],
        "wind": {"speed": 3.2, "deg": 180},
    }

    forecast_payload = {
        "list": [
            {
                "dt": int(now.timestamp()) + 3 * 3600,
                "main": {"temp": 21.0},
                "weather": [{"description": "few clouds"}],
                "wind": {"speed": 2.8, "deg": 170},
            }
        ]
    }

    get = mocker.patch(
        "weather_client.providers.owm_provider.requests.get",
        side_effect=[
            _FakeResponse(current_payload),
            _FakeResponse(forecast_payload),
        ],
    )

    current, hourly, station = provider.fetch(-33.86, 151.21)

    assert station.source == "OpenWeatherMap (free)"
    assert current.temperature == 20.5
    assert hourly
    assert hourly[0].temperature == 21.0
    assert get.call_count == 2


def test_owm_provider_free_endpoint_http_error_raises(mocker):
    provider = OWMProvider("dummy")
    mocker.patch.object(provider._mgr, "one_call", side_effect=UnauthorizedError("nope"))  # noqa: SLF001
    mocker.patch(
        "weather_client.providers.owm_provider.requests.get",
        return_value=_FakeResponse({}, status_code=401),
    )

    with pytest.raises(RuntimeError):
        provider.fetch(-33.86, 151.21)
