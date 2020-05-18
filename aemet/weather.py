"""AEMET: Custom Weather Component for AEMET (Agencia Estatal de Metereologia)"""

import logging
from datetime import datetime

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.weather import PLATFORM_SCHEMA
from homeassistant.components.weather import WeatherEntity
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_ELEVATION,
    CONF_MODE,
    CONF_NAME,
)
from homeassistant.const import PRECISION_TENTHS
from homeassistant.util import Throttle

from .aemet import AemetData
from .const import *

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_LONGITUDE): cv.longitude,
        vol.Optional(CONF_ELEVATION): cv.small_float,
        vol.Optional(CONF_MODE, default=DEFAULT_FORECAST_MODE): vol.In(FORECAST_MODE),
        vol.Optional(CONF_CACHE_DIR, default=DEFAULT_CACHE_DIR): cv.string,
        vol.Optional(CONF_SET_WEATHER_STATION): cv.string,
        vol.Optional(CONF_SET_CITY): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_EXPERIMENTAL, default=False): cv.boolean,
    }
)


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
    city = config.get("city")
    experimental = config.get("experimental")

    aemet = AemetData(
        latitude,
        longitude,
        elevation,
        api_key=api_key,
        cache_dir=cache_dir,
        weather_station=weather_station,
        city=city,
        experimental=experimental,
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

        self._aemet_forecast_current_hour = None

    def retrieve_forecast_subday(self, data, field, intervalo=24):
        if self._mode == "daily":
            date = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
            forecast_date = datetime.strptime(
                data.get(ATTR_FORECAST_TIME), "%Y-%m-%dT%H:%M:%S"
            ).replace(hour=0, minute=0, second=0)

            if (
                    intervalo == 3 and date == forecast_date
            ):  # if today ... we can get info up to 6 hours interval
                return None
            if (
                    intervalo == 12 and date != forecast_date
            ):  # if not today ... we should get info for whole day
                return None
        else:
            if intervalo == 3:
                return None

        valor = self.retrieve_forecast_subday(data, field, int(intervalo / 2))
        if valor is not None:
            return valor
        else:
            hour = datetime.now().hour

            inicio = str(int(hour / intervalo) * intervalo).zfill(2)
            fin = str(int(hour / intervalo + 1) * intervalo).zfill(2)
            periodo = f"{inicio}-{fin}"

            campo = data.get(periodo, None)
            if campo is None:
                if intervalo == 24:
                    valor = data.get(field, None)
                    return valor
                return None
            else:
                valor = campo.get(field, None)
                return valor

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
        if self._aemet_data["currently"] is None:
            return None

        value = self._aemet_data["currently"]["data"].get(ATTR_WEATHER_TEMPERATURE)
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
        if self._aemet_data["currently"] is None:
            return None

        value = self._aemet_data["currently"]["data"].get(ATTR_WEATHER_HUMIDITY)
        if value is None:
            value = self._aemet_forecast_current_hour.get(ATTR_WEATHER_HUMIDITY)
        return value

    @property
    def wind_speed(self):
        """Return the wind speed."""
        if self._aemet_data["currently"] is None:
            return None

        value = self._aemet_data["currently"]["data"].get(ATTR_WEATHER_WIND_SPEED)
        if value is None:
            value = self._aemet_forecast_current_hour.get(ATTR_WEATHER_WIND_SPEED)
        return value

    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        if self._aemet_data["currently"] is None:
            return None

        value = self._aemet_data["currently"]["data"].get(ATTR_WEATHER_WIND_BEARING)
        if value is None:
            value = self._aemet_forecast_current_hour.get(ATTR_WEATHER_WIND_BEARING)

        if isinstance(value, str):
            valor = WIND_DIRECTIONS.get(value)
        else:
            valor = value

        return valor

    @property
    def ozone(self):
        """Return the ozone level."""
        if self._aemet_data["currently"] is None:
            return None

        value = self._aemet_data["currently"]["data"].get(ATTR_WEATHER_OZONE)
        if value is None:
            value = self._aemet_forecast_current_hour.get(ATTR_WEATHER_OZONE)
        return value

    @property
    def pressure(self):
        """Return the pressure."""
        if self._aemet_data["currently"] is None:
            return None

        value = self._aemet_data["currently"]["data"].get(ATTR_WEATHER_PRESSURE)
        if value is None:
            value = self._aemet_forecast_current_hour.get(ATTR_WEATHER_PRESSURE)
        return value

    @property
    def visibility(self):
        """Return the visibility."""
        if self._aemet_data["currently"] is None:
            return None

        value = self._aemet_data["currently"]["data"].get(ATTR_WEATHER_VISIBILITY)
        if value is None:
            value = self._aemet_forecast_current_hour.get(ATTR_WEATHER_VISIBILITY)
        return value

    @property
    def precision(self):
        return PRECISION_TENTHS

    @property
    def condition(self):
        """Return the weather condition."""
        if self._aemet_data["currently"] is None:
            return None

        condition = self._aemet_data["currently"]["data"].get("condition")
        if condition is None:
            condition = self._aemet_forecast_current_hour.get(
                "condition", "desconocido"
            )

        # Night conditions get an "n" appended, if not found lets try without that "n"
        return MAP_CONDITION.get(condition, MAP_CONDITION.get(condition[:2]))

    @property
    def forecast(self):
        """Return the forecast array."""

        fc = []

        if self._mode == "daily":
            if self._aemet_data["daily"] is None:
                return None

            date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            working_data = self._aemet_data["daily"]["data"]

        else:
            if self._aemet_data["hourly"] is None:
                return None

            date = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
            working_data = self._aemet_data["hourly"]["data"]

        for entry in working_data:
            forecast_time = datetime.strptime(
                entry.get(ATTR_FORECAST_TIME), "%Y-%m-%dT%H:%M:%S"
            )
            if forecast_time >= date:
                condition = self.retrieve_forecast_subday(entry, ATTR_FORECAST_CONDITION)
                data = {
                    ATTR_FORECAST_TIME: entry.get(ATTR_FORECAST_TIME),
                    ATTR_FORECAST_TEMP: entry.get(ATTR_FORECAST_TEMP),
                    ATTR_FORECAST_TEMP_LOW: entry.get(ATTR_FORECAST_TEMP_LOW),
                    ATTR_FORECAST_PRECIPITATION: entry.get(ATTR_FORECAST_PRECIPITATION),
                    ATTR_FORECAST_CONDITION: MAP_CONDITION.get(condition,
                        MAP_CONDITION.get(condition[:2], entry.get(ATTR_WEATHER_DESCRIPTION, "")),
                    ),
                    ATTR_FORECAST_WIND_SPEED: self.retrieve_forecast_subday(
                        entry, ATTR_FORECAST_WIND_SPEED
                    ),
                    ATTR_FORECAST_WIND_BEARING: WIND_DIRECTIONS.get(
                        self.retrieve_forecast_subday(
                            entry, ATTR_FORECAST_WIND_BEARING
                        ),
                        None,
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

        now = datetime.now().replace(minute=0, second=0, microsecond=0).isoformat()

        if self._aemet_data["hourly"] is not None:
            for prediccion in self._aemet_data["hourly"]["data"]:
                if now == prediccion[ATTR_FORECAST_TIME]:
                    self._aemet_forecast_current_hour = prediccion
                    break
