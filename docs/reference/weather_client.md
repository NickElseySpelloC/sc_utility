# WeatherClient

This class provides a simple wrapper for the OpenWeathermap (OWM) and Open Meteo weather providers. It returns the current and forecast weather for the designated location. 

The class will attempt to retrieve the weather data from the providers in this order:
1. OWM paid subscription (valid OWM "One Call" API Key required).
2. OWM free tier (valid OWM free server API Key required).
3. Open Meteo weather (no API key needed)

For the first two options, an OWM API key is required. You can obtain one at https://openweathermap.org.

In all instances the WeatherClient weather look methods (e.g. get_weather()) return a WeatherData dataclass:

```python
  {%
    include "../../src/weather_client/models.py"
  %}
```

::: weather_client.WeatherClient
