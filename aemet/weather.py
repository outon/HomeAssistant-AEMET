"""AEMET: Custom Weather Component for AEMET (Agencia Estatal de Metereologia)"""

import logging
from datetime import datetime, timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.weather import (
    ATTR_FORECAST,
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
    ATTR_WEATHER_ATTRIBUTION,
    ATTR_WEATHER_HUMIDITY,
    ATTR_WEATHER_OZONE,
    ATTR_WEATHER_PRESSURE,
    ATTR_WEATHER_TEMPERATURE,
    ATTR_WEATHER_VISIBILITY,
    ATTR_WEATHER_WIND_BEARING,
    ATTR_WEATHER_WIND_SPEED,
    PLATFORM_SCHEMA,
    WeatherEntity,
)
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_ELEVATION,
    CONF_MODE,
    CONF_NAME,
    TEMP_CELSIUS,
    PRECISION_TENTHS,
)
from homeassistant.util import Throttle

from .aemet import AemetData

MAP_CONDITION = {
    "11": "sunny",
    "11n": "clear-night",
    "12": "partlycloudy",
    "12n": "partlycloudy",
    "13": "partlycloudy",
    "13n": "partlycloudy",
    "14": "cloudy",
    "14n": "cloudy",
    "15": "cloudy",
    "16": "cloudy",
    "17": "Nubes altas",
    "17n": "Nubes altas noche",
    "23": "rainy",
    "23n": "rainy",
    "24": "rainy",
    "24n": "rainy",
    "25": "rainy",
    "26": "rainy",
    "33": "snowy",
    "33n": "snowy",
    "34": "snowy",
    "34n": "snowy",
    "35": "snowy",
    "36": "snowy",
    "36n": "snowy",
    "43": "partlycloudy",
    "43n": "partlycloudy",
    "44": "cloudy",
    "45": "cloudy",
    "46": "cloudy",
    "51": "lightning",
    "52": "lightning",
    "53": "lightning",
    "54": "lightning",
    "61": "lightning-rainy",
    "62": "lightning-rainy",
    "63": "lightning-rainy",
    "64": "lightning-rainy",
    "71": "partlycloudy",
    "72": "snowy",
    "73": "snowy",
    "74": "snowy",
}
WIND_DIRECTIONS = {
    "C": None,  # C = Calm
    "N": "N",
    "NNE": "NNE",
    "NE": "NE",
    "ENE": "ENE",
    "E": "E",
    "ESE": "ESE",
    "SE": "SE",
    "SSE": "SSE",
    "S": "S",
    "SSO": "SSW",
    "SO": "SW",
    "OSO": "WSW",
    "O": "W",
    "ONO": "WNW",
    "NO": "NW",
    "NNO": "NNW",
}

DEFAULT_NAME = "AEMET"
_LOGGER = logging.getLogger(__name__)
DEFAULT_CACHE_DIR = "aemet"

ATTRIBUTION = "Data provided by AEMET (www.aemet.es)"
ATTR_WEATHER_DESCRIPTION = "description"
FORECAST_MODE = ["hourly", "daily"]


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_LONGITUDE): cv.longitude,
        vol.Optional(CONF_ELEVATION): cv.small_float,
        vol.Optional(CONF_MODE, default="hourly"): vol.In(FORECAST_MODE),
        vol.Optional("cache_dir", default=DEFAULT_CACHE_DIR): cv.string,
        vol.Optional("weather_station"): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the AEMET weather entities."""
    _LOGGER.debug("Setting up plataform %s", DEFAULT_NAME)

    latitude = config.get(CONF_LATITUDE, hass.config.latitude)
    longitude = config.get(CONF_LONGITUDE, hass.config.longitude)
    elevation = config.get(CONF_ELEVATION, hass.config.elevation)
    name = config.get(CONF_NAME)
    api_key = config.get(CONF_API_KEY)

    mode = config.get(CONF_MODE)

    cache_dir = config.get("cache_dir")

    weather_station = config.get("weather_station")

    aemet = AemetData(
        latitude,
        longitude,
        elevation,
        api_key=api_key,
        cache_dir=cache_dir,
        weather_station=weather_station,
    )

    add_entities([AemetWeather(name, aemet, mode)], True)
    _LOGGER.debug(
        "Entity %s[%s] created for location (%s, %s)", name, mode, latitude, longitude
    )


class AemetWeather(WeatherEntity):
    """Representation of a weather entity."""

    def __init__(self, name, aemet, mode):
        """Initialize AEMET weather."""
        _LOGGER.debug("Creating instance of AemetWeather, using parameters")
        _LOGGER.debug("name\t%s", name)
        _LOGGER.debug("aemet\t%s", aemet)
        _LOGGER.debug("mode\t%s", mode)

        self._name = name

        assert isinstance(aemet, AemetData)
        self._aemet = aemet
        self._mode = mode

        self._aemet_data = None
        self._aemet_currently = None
        self._aemet_hourly = None
        self._aemet_daily = None

    @property
    def state(self):
        return self.condition

    @property
    def state_attributes(self):
        """Return the state attributes."""
        data = {ATTR_WEATHER_TEMPERATURE: self.temperature}

        humidity = self.humidity
        if humidity is not None:
            data[ATTR_WEATHER_HUMIDITY] = humidity

        ozone = self.ozone
        if ozone is not None:
            data[ATTR_WEATHER_OZONE] = ozone

        pressure = self.pressure
        if pressure is not None:
            data[ATTR_WEATHER_PRESSURE] = pressure

        wind_bearing = self.wind_bearing
        if wind_bearing is not None:
            data[ATTR_WEATHER_WIND_BEARING] = wind_bearing

        wind_speed = self.wind_speed
        if wind_speed is not None:
            data[ATTR_WEATHER_WIND_SPEED] = wind_speed

        visibility = self.visibility
        if visibility is not None:
            data[ATTR_WEATHER_VISIBILITY] = visibility

        attribution = self.attribution
        if attribution is not None:
            data[ATTR_WEATHER_ATTRIBUTION] = attribution

        if self.forecast is not None:
            forecast = []
            for forecast_entry in self.forecast:
                forecast_entry = dict(forecast_entry)
                forecast_entry[ATTR_FORECAST_TEMP] = forecast_entry[ATTR_FORECAST_TEMP]

                if ATTR_FORECAST_TEMP_LOW in forecast_entry:
                    forecast_entry[ATTR_FORECAST_TEMP_LOW] = forecast_entry[
                        ATTR_FORECAST_TEMP_LOW
                    ]

                forecast.append(forecast_entry)

            data[ATTR_FORECAST] = forecast

        return data

    @property
    def attribution(self):
        """Return the attribution."""
        if self._aemet_data is not None:
            return self._aemet_data["daily"]["information"].get(
                ATTR_WEATHER_ATTRIBUTION
            )

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def temperature(self):
        """Return the temperature."""
        value = self._aemet_currently.get(ATTR_WEATHER_TEMPERATURE)
        if value is None:
            value = self._aemet_forecast_current_hour.get(ATTR_WEATHER_TEMPERATURE)
        return value

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def humidity(self):
        """Return the humidity."""
        value = self._aemet_currently.get(ATTR_WEATHER_HUMIDITY)
        if value is None:
            value = self._aemet_forecast_current_hour.get(ATTR_WEATHER_HUMIDITY)
        return value

    @property
    def wind_speed(self):
        """Return the wind speed."""
        value = self._aemet_currently.get(ATTR_WEATHER_WIND_SPEED)
        if value is None:
            value = self._aemet_forecast_current_hour.get(ATTR_WEATHER_WIND_SPEED)
        return value

    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        value = self._aemet_currently.get(ATTR_WEATHER_WIND_BEARING)
        if value is None:
            value = self._aemet_forecast_current_hour.get(ATTR_WEATHER_WIND_BEARING)
        return WIND_DIRECTIONS.get(value)

    @property
    def ozone(self):
        """Return the ozone level."""
        value = self._aemet_currently.get(ATTR_WEATHER_OZONE)
        if value is None:
            value = self._aemet_forecast_current_hour.get(ATTR_WEATHER_OZONE)
        return value

    @property
    def pressure(self):
        """Return the pressure."""
        value = self._aemet_currently.get(ATTR_WEATHER_PRESSURE)
        if value is None:
            value = self._aemet_forecast_current_hour.get(ATTR_WEATHER_PRESSURE)
        return value

    @property
    def visibility(self):
        """Return the visibility."""
        value = self._aemet_currently.get(ATTR_WEATHER_VISIBILITY)
        if value is None:
            value = self._aemet_forecast_current_hour.get(ATTR_WEATHER_VISIBILITY)
        return value

    @property
    def precision(self):
        return PRECISION_TENTHS

    @property
    def condition(self):
        """Return the weather condition."""
        condition = self._aemet_currently.get("condition")
        if condition is None:
            condition = self._aemet_forecast_current_hour.get(
                "condition", "desconocido"
            )
        return MAP_CONDITION.get(condition)

    @property
    def forecast(self):
        """Return the forecast array."""

        fc = []

        if self._mode == "daily":
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            for entry in self._aemet_daily:
                forecast_time = datetime.strptime(
                    entry.get(ATTR_FORECAST_TIME), "%Y-%m-%dT%H:%M:%S"
                )
                if forecast_time >= today:
                    data = {
                        ATTR_FORECAST_TIME: entry.get(ATTR_FORECAST_TIME),
                        ATTR_FORECAST_TEMP: entry.get(ATTR_FORECAST_TEMP),
                        ATTR_FORECAST_TEMP_LOW: entry.get(ATTR_FORECAST_TEMP_LOW),
                        ATTR_FORECAST_PRECIPITATION: entry.get(
                            ATTR_FORECAST_PRECIPITATION
                        ),
                        ATTR_FORECAST_WIND_SPEED: entry.get(ATTR_FORECAST_WIND_SPEED),
                        ATTR_FORECAST_WIND_BEARING: entry.get(ATTR_FORECAST_WIND_SPEED),
                        ATTR_FORECAST_CONDITION: MAP_CONDITION.get(
                            entry.get(ATTR_FORECAST_CONDITION)
                        ),
                    }

                    if data[ATTR_FORECAST_CONDITION] is None:
                        hour = datetime.now().hour
                        inicio = int(hour / 6) * 6
                        fin = int(hour / 6 + 1) * 6
                        data[ATTR_FORECAST_CONDITION] = MAP_CONDITION.get(
                            entry.get("{}-{}".format(inicio, fin)).get(
                                ATTR_FORECAST_CONDITION
                            )
                        )
                        data[ATTR_FORECAST_WIND_SPEED] = entry.get(
                            "{}-{}".format(inicio, fin)
                        ).get(ATTR_FORECAST_WIND_SPEED)
                        data[ATTR_FORECAST_WIND_BEARING] = entry.get(
                            "{}-{}".format(inicio, fin)
                        ).get(ATTR_FORECAST_WIND_BEARING)

                    fc.append(data)
        else:
            now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

            for entry in self._aemet_hourly:
                forecast_time = datetime.strptime(
                    entry.get(ATTR_FORECAST_TIME), "%Y-%m-%dT%H:%M:%S"
                )
                if forecast_time >= now:
                    data = {
                        ATTR_FORECAST_TIME: entry.get(ATTR_FORECAST_TIME),
                        ATTR_FORECAST_TEMP: entry.get(ATTR_FORECAST_TEMP),
                        ATTR_FORECAST_PRECIPITATION: entry.get(
                            ATTR_FORECAST_PRECIPITATION
                        ),
                        ATTR_FORECAST_CONDITION: MAP_CONDITION.get(
                            entry.get(ATTR_FORECAST_CONDITION)
                        ),
                    }
                    fc.append(data)

        return fc

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from AEMET."""
        _LOGGER.debug("Get the latest data from AEMET for %s ", self._name)
        self._aemet.update()

        self._aemet_data = self._aemet.data
        self._aemet_hourly = self._aemet.hourly.data.get("horaria").get("data")
        self._aemet_daily = self._aemet.daily.data.get("diaria").get("data")
        self._aemet_currently = self._aemet.currently.data.get("currently").get("data")

        now = datetime.now().replace(minute=0, second=0, microsecond=0).isoformat()

        for prediccion in self._aemet_hourly:
            if now == prediccion[ATTR_FORECAST_TIME]:
                self._aemet_forecast_current_hour = prediccion
                break
