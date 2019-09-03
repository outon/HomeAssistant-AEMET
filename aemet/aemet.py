"""AEMET: classes needed to retrieve weather data
and forecast from AEMET (Agencia Estatal de Metereologia)
"""

# from scipy import spatial
import math
import json
import logging
import os
from datetime import timedelta, datetime
from operator import itemgetter

import requests
from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
    ATTR_WEATHER_HUMIDITY,
    ATTR_WEATHER_PRESSURE,
    ATTR_WEATHER_TEMPERATURE,
)
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE, ATTR_ATTRIBUTION
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import Throttle
from requests.exceptions import ConnectionError, HTTPError, Timeout
from vincenty import vincenty


_LOGGER = logging.getLogger(__name__)
DEFAULT_CACHE_DIR = "aemet"

# Possible HTTP responses from AEMET API
HTTP_OK = 200
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429

# Additional attributes of the entity
ATTR_ELEVATION = "elevation"

# Data Attribution
ATTRIBUTION = "Data provided by AEMET. www.aemet.es"

# Additional Weather/Forecast attributes
ATTR_FORECAST_SNOW = "snow"
ATTR_WEATHER_HUMIDITY_LOW = "humidity_min"
ATTR_WEATHER_DEW_POINT = "dew_point"

# Predefined time between updates
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)


class AemetAPI:
    """Connects to AEMET OpenData API services to retrieve weather forecast."""

    API_BASE_URL = "https://opendata.aemet.es/opendata/api"
    API_MASTER_RECORDS = {
        "ciudades": "/maestro/municipios",
        "estaciones": "/observacion/convencional/todas",  # To retrieve all known station we should retrieve
        # its currently weather data as there not exists any
        # way to retrieve them without its data
    }
    API_WEATHER = {
        "estacion": "/observacion/convencional/datos/estacion/{}",
        "estaciones": "/observacion/convencional/todas",
    }
    API_FORECAST = {
        "horaria": "/prediccion/especifica/municipio/horaria/{}",
        "diaria": "/prediccion/especifica/municipio/diaria/{}",
    }
    _ICONS_CONDITIONS = (
        "http://www.aemet.es/imagenes_gcd/eltiempo/prediccion/comun/ayuda/{}.png"
    )

    def __init__(self, api_key, cache_dir=DEFAULT_CACHE_DIR):
        _LOGGER.debug("Creating instance of AemetAPI, using parameters")
        _LOGGER.debug("api_key\t%s[...]%s", api_key[:20], api_key[-20:])
        _LOGGER.debug("cache_dir\t%s", cache_dir)

        self._api_key = api_key
        self._cache_dir = cache_dir
        self._init_cache(cache_dir)

    @staticmethod
    def _init_cache(cache_dir):
        """Init cache folder."""
        try:
            if not os.path.isdir(cache_dir):
                _LOGGER.debug("Create cache dir %s.", cache_dir)
                os.mkdir(cache_dir)
        except OSError as err:
            raise HomeAssistantError("Can't init cache dir {}".format(err))

    def _get_url_method(self, api_url):
        base_length = len(self.API_BASE_URL)
        api_method = api_url[base_length:]
        method = None
        for k, v in {
            **self.API_MASTER_RECORDS,
            **self.API_WEATHER,
            **self.API_FORECAST,
        }.items():
            if v == api_method:
                method = k
                break
        return method

    def aemet_load_from_file(self, api_url):
        """Load data cached locally."""
        file = None

        file = self._get_url_method(api_url)

        if file is None:
            raise HomeAssistantError("Can't find API method for {}".format(api_url))
        filename = os.path.join(self._cache_dir, file + ".json")
        try:
            with open(filename, "r") as infile:
                data = json.load(infile)
        except OSError:
            _LOGGER.info("Can't find cache file %s", filename)
            return None
        return data

    def save_to_file(self, file, data):
        """Save data to a cache file.
        :param file: name of file
        :param data: json to be stored
        """
        filename = os.path.join(self._cache_dir, file + ".json")
        try:
            with open(filename, "w") as outfile:
                json.dump(data, outfile, indent=2)
        except OSError:
            _LOGGER.info("Can't write on cache file %s", file)

    @staticmethod
    def _api_request(data_url: str, api_key: str = None):
        """Load data from AEMET.
        :param data_url: API call url
        :param api_key: API private key
        :return: json with AEMET response
        """

        _LOGGER.debug("Loading data from %s", data_url)

        params = {"api_key": api_key}
        try:
            if api_key is None:
                response = requests.get(data_url)
            else:
                response = requests.get(data_url, params=params)
        except (ConnectionError, HTTPError, Timeout, ValueError) as error:
            _LOGGER.error("Unable to retrieve data from AEMET. %s", error)
            return []
        aemet_response = response.json()

        return aemet_response

    def api_call(self, api_url: str, cached: bool = False):
        """Call to AEMET OpenData API services."""

        _LOGGER.debug("api_url: %s", api_url)
        _LOGGER.debug("api_key: %s[...]%s", self._api_key[:20], self._api_key[-20:])

        if cached:
            _LOGGER.debug("Loading cache data...")

            aemet_data = self.aemet_load_from_file(api_url)

            if aemet_data is not None:
                return aemet_data
        _LOGGER.debug("Loading non-cached data...")

        """Exceptions to this API model:
            when retrieving data for 'municipios' 
            we should do a direct api call, not an staged one."""
        method = self._get_url_method(api_url)
        direct_call = (method in ['ciudades'])

        if not direct_call:
            # Get staged data
            _LOGGER.debug("Loading staged data...")

            aemet_response = self._api_request(api_url, api_key=self._api_key)

            estado = aemet_response.get("estado")
            descripcion = aemet_response.get("descripcion", "No description provided")

            if estado is None:
                _LOGGER.error("Could not retrieve data from AEMET")
                raise
            elif estado == HTTP_UNAUTHORIZED:  # 401
                _LOGGER.error("Unauthorized. Error %s, %s", estado, descripcion)
                raise ValueError("Invalid api key")
            elif estado == HTTP_NOT_FOUND:  # 404
                _LOGGER.error("Not found. Error %s, %s", estado, descripcion)
                raise ConnectionError
            elif estado == HTTP_TOO_MANY_REQUESTS:  # 429
                _LOGGER.info("Too many requests. Error %s, %s", estado, descripcion)
                raise ConnectionRefusedError
            elif estado != HTTP_OK:
                _LOGGER.info(
                    "Could not retrieve data from AEMET. Error %s, %s",
                    estado,
                    descripcion,
                )
                raise HTTPError

            datos = aemet_response.get("datos")
            # metadatos = aemet_response.get('metadatos')

            # Get final data
            aemet_data = self._api_request(datos, api_key=self._api_key)
        else:
            # There exists at least one API call that do not use staged data, but direct call.
            _LOGGER.debug("Loading direct data...")

            aemet_data = self._api_request(api_url, api_key=self._api_key)
        return aemet_data


class AemetMasterRecord:
    _ENTITIES = ["ciudades", "estaciones"]

    def __init__(
        self,
        entityclass: str,
        api_client: AemetAPI = None,
        weather_station: str = None,
        city: str = None,
        experimental: bool = False,
    ):
        _LOGGER.debug("Creating instance of AemetMasterRecord, using parameters")
        _LOGGER.debug("entity\t%s", entityclass)
        _LOGGER.debug("api\t%s", api_client)

        self.data = None

        if entityclass not in self._ENTITIES:
            raise ValueError
        self._entityClass = entityclass

        if weather_station is not None and entityclass == "estaciones":
            self.nearest = weather_station
        elif city is not None and entityclass == "ciudades":
            self.nearest = city
        else:
            self.nearest = None
        self.api_client = api_client
        self._location_tree = None

        # Default method to search
        self._nearest_location = (
            self._nearest_location_iterate
        )  # Compatible with RPI, slower
        # if experimental:
        #     self._nearest_location = (
        #         self._nearest_location_kdtree
        #     )  # Not tested in a RPI, faster

    def _write_master_data(self, force=False):
        if self.data is None:
            return
        last_saved = datetime.strptime(
            self.data.get("saved", datetime.now()), "%Y-%m-%dT%H:%M:%S"
        )
        elapsed = datetime.now() - last_saved
        if elapsed < timedelta(minutes=5) or force:
            self.api_client.save_to_file(self._entityClass, self.data)

    # def _nearest_location_kdtree(self, location: tuple) -> tuple:
    #     """Find nearest point in a list of points to a given location using KDTree.
    #
    #     This function is faster but cannot use it in a rpi environment due to limitations using scipy package.
    #
    #     :param location: reference location to find closest point
    #     :return: distance and closest point to location"""
    #
    #     def cartesian(latitude, longitude, elevation=0):
    #         """Convert to radians"""
    #         latitude = latitude * (math.pi / 180)
    #         longitude = longitude * (math.pi / 180)
    #
    #         R = (6378137.0 + elevation) / 1000.0  # relative to centre of the earth
    #         X = R * math.cos(latitude) * math.cos(longitude)
    #         Y = R * math.cos(latitude) * math.sin(longitude)
    #         Z = R * math.sin(latitude)
    #         return (X, Y, Z)
    #
    #     def find_closest(list_locations, location):
    #
    #         if self._location_tree is None:
    #             places = []  # create a list of points with cartesian coordinates
    #             for points in list_locations:
    #                 coordinates = (
    #                     float(points["latitud"]),
    #                     float(points["longitud"]),
    #                     float(points["altitud"]),
    #                 )
    #                 cartesian_coord = cartesian(*coordinates)
    #                 places.append(cartesian_coord)
    #
    #             self._location_tree = spatial.KDTree(
    #                 places
    #             )  # create a KDTree with those points
    #
    #         cartesian_coord = cartesian(*location)
    #         closest = self._location_tree.query([cartesian_coord], p=2)
    #         distance = closest[0][0]
    #         location_index = closest[1][0]
    #         return distance, location_index
    #
    #     if self.data is None:
    #         return None, None
    #
    #     list_locations = self.data[self._entityClass]
    #     (distance, index) = find_closest(list_locations, location)
    #
    #     return distance, list_locations[index]

    def _nearest_location_iterate(self, location: tuple):
        """Find nearest city or weather station given my current location
        :type location: tuple
        :param location: my current location
        :return: dictionary with information of cit or weather station
        """

        def distance(point1: tuple, point2: tuple):
            """Calculate the distance in kilometers between two points using vincenty function
            :param point1: coordinates (latitude, longitude) of point 1
            :param point2: coordinates (latitude, longitude) of point 1
            :return: distance in kilometers between two points
            """
            if None in (point1, point2):
                return None
            result = vincenty(point1, point2)
            if result is None:
                return None
            return result

        def nearest_location(list_locations, location):

            nearest_codigo = None
            nearest_distance = None

            places = []
            nearest = None
            for point in list_locations:
                coordinates = (float(point["latitud"]), float(point["longitud"]))
                point_distance = distance(coordinates, location)
                if nearest_distance is None or point_distance < nearest_distance:
                    nearest_distance = point_distance
                    nearest_codigo = point["codigo"]
                places.append([point["codigo"], point_distance])
            for point in list_locations:
                if point["codigo"] == nearest_codigo:
                    nearest = point
                    break
            return nearest_distance, nearest

        if self.data is None:
            return None, None

        list_locations = self.data[self._entityClass]
        (distance, closest_location) = nearest_location(list_locations, location)

        return distance, closest_location

    def update_distance(self, location, force=False):
        """Get nearest place to given location."""
        if isinstance(self.nearest, str):
            nearest = self.nearest
            self.nearest = None
            for v in self.data.get(self._entityClass):
                if v.get("codigo") == nearest:
                    self.nearest = v
                    break
            if isinstance(self.nearest, str):
                raise ValueError("Weather station or City code is not valid")

        if self.nearest is None or force:
            (distance, self.nearest) = self._nearest_location(location)

        distance = vincenty(
            location, (self.nearest["latitud"], self.nearest["longitud"])
        )
        """
        If the distance to my location is more than 25 km, the city must not be in Spain.

        On the website http://www.geomidpoint.com/random/ we can obtain up to 2000 random points 
        in a radius of 600 km around the centre of Spain (usually Cerro de los Ángeles, Madrid).

        We calculate the distance from those random points to the nearest city and on 
        website http://www.copypastemap.com/ we can trace those points with colors depending on the distance.

        All points further than 25 km from a city are outside the Spanish border."""

        if distance > 25.0 and self._entityClass == "ciudades":
            self.nearest = None

        """This is not true when looking for a weather station. The farthest points of 40 km 
        are the most likely to be outside the Spanish border. But there are places 
        between 25 and 40 km within Spain."""

        if distance > 40.0 and self._entityClass == "estaciones":
            self.nearest = None

    def _clean_master_data(self, data):
        """Cleans data received from AEMET."""
        if isinstance(data, dict):
            last_saved = data.get("saved")

            if last_saved is not None:
                """We only save curated, so there is no need to clean data again"""
                return data
        MAP_FIELDS = {
            "idema": "codigo",
            "ubi": "nombre",
            "lat": "latitud",
            "lon": "longitud",
            "alt": "altitud",
            "id": "codigo",
            "nombre": "nombre",
            "latitud_dec": "latitud",
            "longitud_dec": "longitud",
            "altitud": "altitud",
        }

        FLOAT_FIELDS = ["latitud", "longitud", "altitud"]

        clean_data = []
        for entity in data:
            clean_entity = {
                MAP_FIELDS[k]: v for k, v in entity.items() if k in MAP_FIELDS
            }
            clean_entity["codigo"] = (
                clean_entity["codigo"][2:]
                if clean_entity["codigo"].startswith("id")
                else clean_entity["codigo"]
            )
            clean_entity = {
                k: (float(v) if k in FLOAT_FIELDS else v)
                for k, v in clean_entity.items()
            }
            clean_data.append(clean_entity)
        final_data = {
            "saved": datetime.now().replace(microsecond=0).isoformat(),
            self._entityClass: clean_data,
        }

        return final_data

    def _get_master_data(self, cached=False):
        """Get master data: List of cities or Weather stations"""
        _LOGGER.debug("Get master data for: %s ", self._entityClass)

        endpoint_url = "{}{}".format(
            self.api_client.API_BASE_URL,
            self.api_client.API_MASTER_RECORDS.get(self._entityClass),
        )
        raw_data = self.api_client.api_call(endpoint_url, cached=cached)

        return raw_data

    def update(self, api_client: AemetAPI = None):
        _LOGGER.debug("Updating AEMET Master Records.")

        if api_client is not None:
            self.api_client = api_client
        if self.api_client is None:
            raise NotImplementedError
        if self.data is None:
            raw_data = self._get_master_data(cached=True)
            if isinstance(raw_data, list):
                self.data = self._clean_master_data(raw_data)
            else:
                self.data = raw_data
            self._location_tree = (
                None
            )  # Remove KDTree as we have loaded a new set of data
        else:
            last_saved = datetime.strptime(self.data.get("saved"), "%Y-%m-%dT%H:%M:%S")
            elapsed = datetime.now() - last_saved
            if timedelta(days=7) < elapsed:
                raw_data = self._get_master_data(cached=False)
                self.data = self._clean_master_data(raw_data)
        self._write_master_data()


class AemetForecast:
    """Get the latest data from AEMET."""

    _FORECAST_MODE = ["diaria", "horaria"]
    _MAP_FIELDS = {
        "descripcion": "description",
        "dv": ATTR_FORECAST_WIND_BEARING,
        "viento_Direccion": ATTR_FORECAST_WIND_BEARING,
        "vientoAndRachaMax_Direccion": ATTR_FORECAST_WIND_BEARING,
        "alt": "altitude",
        "idema": "weather_station",
        "fint": ATTR_FORECAST_TIME,
        "humedadRelativa_Maxima": ATTR_WEATHER_HUMIDITY,
        "humedadRelativa_Minima": "humidity min",
        "hr": ATTR_WEATHER_HUMIDITY,
        "humedadRelativa": ATTR_WEATHER_HUMIDITY,
        "estadoCielo": ATTR_FORECAST_CONDITION,
        "uvMax": "UV index",
        "lat": ATTR_LATITUDE,
        "lon": ATTR_LONGITUDE,
        "nieve": ATTR_FORECAST_SNOW,
        "ubi": "location",
        "ocaso": "sunset",
        "orto": "sunrise",
        "prec": ATTR_FORECAST_PRECIPITATION,
        "precipitacion": ATTR_FORECAST_PRECIPITATION,
        "pres": ATTR_WEATHER_PRESSURE,
        "probPrecipitacion": "precipitation_probability",
        "tpr": ATTR_WEATHER_DEW_POINT,
        "sensTermica_Maxima": "sensacion termica maxima",
        "sensTermica_Minima": "sensacion termica minima",
        "sensTermica": "sensacion termica",
        "temperatura_Maxima": ATTR_WEATHER_TEMPERATURE,
        "temperatura_Minima": ATTR_FORECAST_TEMP_LOW,
        "ta": ATTR_WEATHER_TEMPERATURE,
        "temperatura": ATTR_WEATHER_TEMPERATURE,
        "value": "valor",
        "vv": ATTR_FORECAST_WIND_SPEED,
        "viento_Velocidad": ATTR_FORECAST_WIND_SPEED,
        "vientoAndRachaMax_Velocidad": ATTR_FORECAST_WIND_SPEED,
        "vis": "visibility",
        "periodo": "periodo",
    }
    _FLOAT_SENSORS = (
        ATTR_WEATHER_HUMIDITY,
        ATTR_FORECAST_SNOW,
        ATTR_FORECAST_PRECIPITATION,
        "sensacion termica",
        ATTR_WEATHER_TEMPERATURE,
        ATTR_FORECAST_WIND_SPEED,
    )

    def __init__(self, forecastmode, city=None, api_client=None):
        """Initialize the data object."""
        _LOGGER.debug("Creating instance of AemetForecast, using parameters")
        _LOGGER.debug("forecast\t%s", forecastmode)
        _LOGGER.debug("city\t%s", city)
        _LOGGER.debug("api\t%s", api_client)

        self.data = None
        self.nearest = city

        if forecastmode not in self._FORECAST_MODE:
            raise ValueError
        self._forecastmode = forecastmode
        self.api_client = api_client

    def _refactor_forecast(self, raw_data):
        """Cleans data received from AEMET related with Weather Forecast."""

        def _periodo(variable, fecha):
            if "periodo" not in variable:
                intervalo = "{}T00:00:00".format(fecha)
            else:
                ini_periodo = variable["periodo"][:2]
                fin_periodo = variable["periodo"][-2:]
                if ini_periodo == fin_periodo:
                    intervalo = "{}T{}:00:00".format(fecha, ini_periodo)
                elif ini_periodo == "00" and fin_periodo == "24":
                    intervalo = "{}T00:00:00".format(fecha)
                else:
                    intervalo = "{}T{}:00:00 & {}".format(
                        fecha, ini_periodo, fin_periodo
                    )
            return intervalo

        def inner_transform(data, sensor, fields, append=False, replace=False):
            interval = _periodo(data, fecha)
            if interval not in transformed_data:
                transformed_data[interval] = {}
            for field in fields:
                name = field if replace else sensor
                name = "{}_{}".format(name, field.capitalize()) if append else name

                name = self._MAP_FIELDS.get(name)
                if name is None:
                    return
                resultado = data.get(field)
                if resultado is None:
                    pass
                elif isinstance(resultado, list):
                    if resultado[0] != "":
                        transformed_data[interval][name] = resultado[0]
                else:
                    if resultado != "":
                        transformed_data[interval][name] = resultado

        def transform(data, sensors, fields, append=False, replace=False):
            for sensor in sensors:
                sensor_data = data.get(sensor)
                if sensor_data is None:
                    continue
                if isinstance(sensor_data, list):
                    for lista_datos in sensor_data:
                        inner_transform(lista_datos, sensor, fields, append, replace)
                else:
                    lista_datos = sensor_data
                    inner_transform(lista_datos, sensor, fields, append, replace)

        version = str(raw_data[0]["version"])
        if version != "1.0":
            _LOGGER.info("Version %s of AEMET schema is not supported", version)
            return None
        copyright = raw_data[0]["origen"]
        header = {
            "city": raw_data[0]["nombre"],
            "province": raw_data[0]["provincia"],
            "processing date": raw_data[0]["elaborado"],
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "API version": version,
            "copyrigth": copyright,
        }

        transformed_data = {}
        if self._forecastmode == "diaria":
            #    list of sensor,      list of field,     append, replace
            schema_definition = [
                (["estadoCielo"], ["value"], False, False),
                (["estadoCielo"], ["descripcion"], False, True),
                (["temperatura"], ["maxima"], False, False),
                (["temperatura"], ["minima"], True, False),
                (["humedadRelativa"], ["maxima"], False, False),
                (["humedadRelativa"], ["minima"], True, False),
                (["viento"], ["direccion"], True, False),
                (["viento"], ["velocidad"], True, False),
            ]
        else:
            #    list of sensor,      list of field,    append, replace
            schema_definition = [
                (["estadoCielo"], ["value"], False, False),
                (["estadoCielo"], ["descripcion"], False, True),
                (["temperatura"], ["value"], False, False),
                (["precipitacion"], ["value"], False, False),
                (["nieve"], ["value"], False, False),
                (["sensTermica"], ["value"], False, False),
                (["humedadRelativa"], ["value"], False, False),
                (["vientoAndRachaMax"], ["direccion"], True, False),
                (["vientoAndRachaMax"], ["velocidad"], True, False),
            ]
        for forecast in raw_data[0]["prediccion"]["dia"]:
            fecha = forecast.get("fecha")
            for schema in schema_definition:
                transform(forecast, *schema)
        # Moves all dates which are an interval to its initial hour
        for key, value in transformed_data.items():
            if len(key) > 19:
                fecha = "{}T00:00:00".format(key[:10])
                horas = "{}-{}".format(key[11:13], key[-2:])
                transformed_data[fecha][horas] = value
        # Insert key of dict as an attribute
        for key, value in transformed_data.items():
            if len(key) == 19:
                value[ATTR_FORECAST_TIME] = key
        # Convert all float sensors to float value
        for value in transformed_data.values():
            for sensor in self._FLOAT_SENSORS:
                valor = value.get(sensor)
                if valor is not None:
                    try:
                        value[sensor] = float(valor)
                    except:
                        continue
        # Keep only data with specific key length, transform it to a list and sort it.
        sorted_data = [v for k, v in transformed_data.items() if len(k) == 19]
        sorted_data = sorted(sorted_data, key=itemgetter(ATTR_FORECAST_TIME))

        final_data = {"information": header, "data": sorted_data}
        return final_data

    def _load_forecast_data(self, city):
        """Get station data"""
        endpoint_url = "{}{}".format(
            self.api_client.API_BASE_URL,
            self.api_client.API_FORECAST[self._forecastmode].format(city),
        )
        raw_data = self.api_client.api_call(endpoint_url)
        return raw_data

    def _update_forecast(self):
        if self.nearest is None:
            raise ValueError
        codigo = self.nearest.get("codigo")
        city = self.nearest.get("nombre")

        _LOGGER.debug("Updating weather forecast for city %s", city)

        raw_data = self._load_forecast_data(codigo)
        clean_data = None

        if raw_data is None:
            _LOGGER.info("No weather forecast received from AEMET")
        else:
            clean_data = self._refactor_forecast(raw_data)
        return clean_data

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self, nearest=None, api_client=None):
        if nearest is not None:
            self.nearest = nearest
        if api_client is not None:
            self.api_client = api_client
        # if None in (self.nearest, self.api_client):
        #     raise ValueError
        # Update weather forecast
        try:
            data = self._update_forecast()
        except ValueError:
            _LOGGER.info("No data retrieved")
            return False

        self.data = {
            self._forecastmode: data,
            "saved": (datetime.now().replace(microsecond=0).isoformat()),
        }

        self.api_client.save_to_file(self._forecastmode, self.data)


class AemetWeather:
    """Get the latest data from AEMET."""

    _MAP_FIELDS = {
        "descripcion": "description",
        "dv": ATTR_FORECAST_WIND_BEARING,
        "viento_Direccion": ATTR_FORECAST_WIND_BEARING,
        "vientoAndRachaMax_Direccion": ATTR_FORECAST_WIND_BEARING,
        "alt": "altitude",
        "idema": "weather_station",
        "fint": ATTR_FORECAST_TIME,
        "humedadRelativa_Maxima": ATTR_WEATHER_HUMIDITY,
        "humedadRelativa_Minima": "humidity min",
        "hr": ATTR_WEATHER_HUMIDITY,
        "humedadRelativa": ATTR_WEATHER_HUMIDITY,
        "estadoCielo": ATTR_FORECAST_CONDITION,
        "uvMax": "UV index",
        "lat": ATTR_LATITUDE,
        "lon": ATTR_LONGITUDE,
        "nieve": ATTR_FORECAST_SNOW,
        "ubi": "location",
        "ocaso": "sunset",
        "orto": "sunrise",
        "prec": ATTR_FORECAST_PRECIPITATION,
        "precipitacion": ATTR_FORECAST_PRECIPITATION,
        "pres": ATTR_WEATHER_PRESSURE,
        "probPrecipitacion": "precipitation_probability",
        "tpr": ATTR_WEATHER_DEW_POINT,
        "sensTermica_Maxima": "sensacion termica maxima",
        "sensTermica_Minima": "sensacion termica minima",
        "sensTermica": "sensacion termica",
        "temperatura_Maxima": ATTR_WEATHER_TEMPERATURE,
        "temperatura_Minima": ATTR_FORECAST_TEMP_LOW,
        "ta": ATTR_WEATHER_TEMPERATURE,
        "temperatura": ATTR_WEATHER_TEMPERATURE,
        "value": "valor",
        "vv": ATTR_FORECAST_WIND_SPEED,
        "viento_Velocidad": ATTR_FORECAST_WIND_SPEED,
        "vientoAndRachaMax_Velocidad": ATTR_FORECAST_WIND_SPEED,
        "vis": "visibility",
        "periodo": "periodo",
    }
    _FLOAT_SENSORS = (
        ATTR_WEATHER_HUMIDITY,
        ATTR_FORECAST_SNOW,
        ATTR_FORECAST_PRECIPITATION,
        "sensacion termica",
        ATTR_WEATHER_TEMPERATURE,
        ATTR_FORECAST_WIND_SPEED,
    )

    def __init__(self, station=None, api_client=None):
        """Initialize the data object."""
        _LOGGER.debug("Creating instance of AemetWeather, using parameters")
        _LOGGER.debug("station\t%s", station)
        _LOGGER.debug("api\t%s", api_client)

        self.data = None
        self.nearest = station
        self.api_client = api_client

    def _remap_keys(self, data):
        """Remap AEMET field names to HA field names. Those fields not in MAP_FIELDS will be removed."""
        translated = {}
        for key, value in data.items():
            if key in self._MAP_FIELDS:
                mapped_key = self._MAP_FIELDS[key]
                translated[mapped_key] = value
        return translated

    def _clean_currently_data(self, raw_data):

        # Sort data by time to keep latest.
        sorted_data = sorted(raw_data, key=itemgetter("fint"))
        remapped_data = self._remap_keys(sorted_data[-1])

        delete = ("location", "weather_station", "latitude", "longitude", "altitude")

        # In station_info we store data that is removed from weather data
        station_info = {info: remapped_data[info] for info in delete}
        station_info[ATTR_ATTRIBUTION] = ATTRIBUTION

        clean_data = {k: v for k, v in remapped_data.items() if k not in delete}

        return {"information": station_info, "data": clean_data}

    def _load_current_data(self, station_id):
        """Get station data"""
        _LOGGER.debug("Loading data from station %s", station_id)
        endpoint_url = "{}{}".format(
            self.api_client.API_BASE_URL,
            self.api_client.API_WEATHER["estacion"].format(station_id),
        )
        raw_data = self.api_client.api_call(endpoint_url)

        return raw_data

    def _update_currently(self):
        if self.nearest is None:
            raise ValueError("Nearest weather station or city not defined")
        station_id = self.nearest.get("codigo")

        _LOGGER.debug("Updating meteorological data from station %s", station_id)

        raw_data = self._load_current_data(station_id)
        clean_data = None
        # Transform data
        if raw_data is None:
            _LOGGER.info("No meteorological data received from AEMET")
        else:
            clean_data = self._clean_currently_data(raw_data)
        return clean_data

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self, nearest=None, api_client=None):
        if nearest is not None:
            self.nearest = nearest
        if api_client is not None:
            self.api_client = api_client
        # Update current weather
        try:
            data = self._update_currently()
        except ValueError:
            _LOGGER.info("No data retrieved")
            return False

        self.data = {
            "currently": data,
            "saved": (datetime.now().replace(microsecond=0).isoformat()),
        }

        self.api_client.save_to_file("currently", self.data)


class AemetData:
    """Get the latest data from AEMET."""

    def __init__(
        self,
        latitude: float,
        longitude: float,
        elevation: float = 0.0,
        api_key: str = None,
        cache_dir: str = DEFAULT_CACHE_DIR,
        weather_station: str = None,
        city: str = None,
        experimental: bool = False,
    ):
        """Initialize the data object."""
        _LOGGER.debug("Creating instance of AemetData, using parameters")
        _LOGGER.debug("location\t(%s, %s, %s)", latitude, longitude, elevation)
        _LOGGER.debug("api_key\t%s[...]%s", api_key[:20], api_key[-20:])
        _LOGGER.debug("cache_dir\t%s", cache_dir)
        _LOGGER.debug("Weather Station\t%s", weather_station)

        self.api_client = None
        self._api_key = api_key
        self._cache_dir = cache_dir

        if api_key is not None:
            self.api_client = AemetAPI(api_key, cache_dir)
        self.location = (latitude, longitude, elevation)

        self.weather_stations = AemetMasterRecord(
            "estaciones",
            self.api_client,
            weather_station=weather_station,
            experimental=experimental,
        )
        self.cities = AemetMasterRecord(
            "ciudades", self.api_client, city=city, experimental=experimental
        )

        self.currently = AemetWeather(api_client=self.api_client)
        self.hourly = AemetForecast("horaria", api_client=self.api_client)
        self.daily = AemetForecast("diaria", api_client=self.api_client)

        self.data = None

        self.__experimental = experimental

    def update_location(self, latitude, longitude, elevation=0):

        if None in (latitude, longitude):
            raise ValueError
        self.location = (latitude, longitude, elevation)

        self.cities.update_distance(self.location, force=True)
        self.weather_stations.update_distance(self.location, force=True)

        self.currently.nearest = self.weather_stations.nearest
        self.hourly.nearest = self.cities.nearest
        self.daily.nearest = self.cities.nearest

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        if not isinstance(self.api_client, AemetAPI):
            raise ValueError
        _LOGGER.debug("Updating AEMET data.")

        # Update current weather
        self.weather_stations.update()
        self.weather_stations.update_distance(self.location)
        self.currently.update(
            nearest=self.weather_stations.nearest, api_client=self.api_client
        )

        # Update weather forecast
        self.cities.update()
        self.cities.update_distance(self.location)
        self.hourly.update(nearest=self.cities.nearest, api_client=self.api_client)
        self.daily.update(nearest=self.cities.nearest, api_client=self.api_client)

        self.data = {
            "currently": self.currently.data.get("currently", None)
            if self.currently.data is not None
            else None,
            "hourly": self.hourly.data.get("horaria", None)
            if self.hourly.data is not None
            else None,
            "daily": self.daily.data.get("diaria", None)
            if self.daily.data is not None
            else None,
            "saved": (datetime.now().replace(microsecond=0).isoformat()),
        }

        self.api_client.save_to_file("data", self.data)
