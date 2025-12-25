# WeatherClient

This class provides a simple wrapper for the OpenWeathermap and Open Meteo weather providers. It returns the current and forecast weather for the designated location. 

The class will attempt to retrieve the weather data from the providers in this order:
1. OWM paid subscription (OWM_API_KEY required.)
2. OWM free tier (OWM_API_KEY required.)
3. Open Meteo weather.

For the first two options, an OWM API key is required. You can obtain one at https://openweathermap.org.

The following data classes are used by this class:

```python
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
```

::: weather_client.WeatherClient
