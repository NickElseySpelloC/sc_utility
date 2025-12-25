"""WeatherClient main client module."""
from __future__ import annotations

from typing import TYPE_CHECKING

from weather_client.providers.open_meteo_provider import OpenMeteoProvider
from weather_client.providers.owm_provider import OWMProvider

if TYPE_CHECKING:
    from weather_client.models import WeatherReading, WeatherStation


class WeatherClient:
    def __init__(self, latitude: float, longitude: float, owm_api_key: str | None = None):
        """Initialize the WeatherClient.

        Args:
            latitude: Latitude of the location to fetch weather for.
            longitude: Longitude of the location to fetch weather for.
            owm_api_key: Optional OpenWeatherMap API key for enhanced data.
        """
        self.latitude = latitude
        self.longitude = longitude
        self._owm = OWMProvider(owm_api_key) if owm_api_key else None
        self._open_meteo = OpenMeteoProvider()

    def get_weather(
        self,
    ) -> tuple[WeatherReading, list[WeatherReading], WeatherStation]:
        """Fetch weather data from providers, falling back as needed.

        Returns:
            A tuple of (current reading, list of hourly readings, weather station info).
        """
        if self._owm:
            try:
                return self._owm.fetch(self.latitude, self.longitude)
            except Exception:  # noqa: BLE001, S110
                # Provider failures should fall back to Open-Meteo.
                # This includes cases where OWM One Call is not available for the key/tier.
                pass
        return self._open_meteo.fetch(self.latitude, self.longitude)

    def get_open_meteo_weather(
        self,
    ) -> tuple[WeatherReading, list[WeatherReading], WeatherStation]:
        """Fetch weather data from Open Meteo.

        Returns:
            A tuple of (current reading, list of hourly readings, weather station info).
        """
        return self._open_meteo.fetch(self.latitude, self.longitude)
