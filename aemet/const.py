""" Description of existing AEMET weather sensors:

For weather stations:
    alt   : Altitude of the station in meters
    dmax  : Maximum wind direction recorded in the 60 minutes prior to
            the time indicated by 'fint' (degrees)
    dv    : Average wind direction, in the 10-minute period preceding
            the date indicated by 'fint' (degrees)
    fint  : Date end time of the observation period, this is data from
            the period of the hour preceding that indicated by this
            field (UTC time)
    hr    : Instantaneous relative humidity of the air corresponding to
            the date given by 'fint' (%)
    idema : Automatic weather station weather indicator
    lat   : Latitude of the weather station (degrees)
    lon   : Longitude of weather station (degrees)
    nieve : Snow layer thickness measured in the 10 minutes prior to the
            date indicated by 'fint' (cm)
    prec  : Accumulated precipitation, measured by the rain gauge,
            during the previous 60 minutes at the time indicated by the
            observation period 'fint' (mm, equivalent to l/m2)
    pres  : Instantaneous pressure at the level at which the barometer is
            installed and corresponding to the date given by 'fint' (hPa)
    ta    : Instantaneous air temperature corresponding to the date given
            by 'fint' (degrees Celsius)
    tamax : Maximum air temperature, the maximum value of the 60 instantaneous
            'ta' values measured in the 60-minute period preceding the time
            indicated by the observation period 'fint' (degrees Celsius)
    tamin : Minimum air temperature, the minimum value of the 60 instantaneous
            'ta' values measured in the 60-minute period preceding the time
            indicated by the observation period 'fint' (degrees Celsius)
    tpr   : Calculated dew point temperature corresponding to the 'fint' date
            (degrees Celsius)
    ubi   : Station location. Station name
    vis   : Visibility, average of the visibility measurement corresponding to
            the 10 minutes prior to the date given by 'fint' (Km)
    vmax  : Maximum wind speed, maximum value of the wind maintained 3 seconds
            and recorded in the 60 minutes preceding the time indicated by the
            observation period 'fint' (m/s)
    vv    : Average wind speed, average scalar of samples acquired every 0.25
            or 1 second in the 10-minute period preceding that indicated by
            'fint' (m/s)

Information for cities:
    altitud :     Altitude of the town in meters
    id :          City Code designated by INE (Instituto nacional de estadistica)
    latitud_dec:  Latitude of the town (degrees)
    longitud_dec: Longitude of the town (degrees)
    nombre :      Name of town

    other sensors exists, but are not of our interest.
"""

from datetime import timedelta

DEFAULT_NAME = "AEMET"
DEFAULT_CACHE_DIR = "aemet"
FORECAST_MODE = ["hourly", "daily"]
DEFAULT_FORECAST_MODE = "daily"

# Configuration options
CONF_API_KEY = "api_key"
CONF_ELEVATION = "elevation"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_MODE = "mode"
CONF_NAME = "name"

CONF_CACHE_DIR = "cache_dir"
CONF_SET_WEATHER_STATION = "weather_station"
CONF_SET_CITY = "city"
CONF_EXPERIMENTAL = "experimental"
# CONF_SCAN_INTERVAL = "scan_interval"

# Weather/Forecast attributes
ATTR_CONDITION_CLASS = "condition_class"
ATTR_FORECAST = "forecast"
ATTR_FORECAST_DESCRIPTION = "description"
ATTR_FORECAST_CONDITION = "condition"
ATTR_FORECAST_HUMIDITY = "humidity"
ATTR_FORECAST_HUMIDITY_MIN = "humidity min"
ATTR_FORECAST_PRECIPITATION = "precipitation"
ATTR_FORECAST_SNOW = "snow"
ATTR_FORECAST_TEMP = "temperature"
ATTR_FORECAST_TEMP_LOW = "templow"
ATTR_FORECAST_THERMAL_SENSATION = "thermal_sensation"
ATTR_FORECAST_TIME = "datetime"
ATTR_FORECAST_UV_INDEX = "UV index"
ATTR_FORECAST_WIND_BEARING = "wind_bearing"
ATTR_FORECAST_WIND_SPEED = "wind_speed"
ATTR_FORECAST_WIND_GUST = "maximum gust"

ATTR_WEATHER_ATTRIBUTION = "attribution"
ATTR_WEATHER_CONDITION = "condition"
ATTR_WEATHER_DESCRIPTION = "description"
ATTR_WEATHER_DEW_POINT = "dew_point"
ATTR_WEATHER_HUMIDITY = "humidity"
ATTR_WEATHER_HUMIDITY_LOW = "humidity_min"
ATTR_WEATHER_OZONE = "ozone"
ATTR_WEATHER_PRECIPITATION = "precipitation"
ATTR_WEATHER_PRESSURE = "pressure"
ATTR_WEATHER_SNOW = "snow"
ATTR_WEATHER_TEMPERATURE = "temperature"
ATTR_WEATHER_TEMP_LOW = "templow"
ATTR_WEATHER_THERMAL_SENSATION = "thermal_sensation"
ATTR_WEATHER_TIME = "datetime"
ATTR_WEATHER_VISIBILITY = "visibility"
ATTR_WEATHER_WIND_BEARING = "wind_bearing"
ATTR_WEATHER_WIND_SPEED = "wind_speed"

# Units
TEMP_CELSIUS = "°C"
TEMP_FAHRENHEIT = "°F"

PRESSURE_PA = "Pa"
PRESSURE_HPA = "hPa"
PRESSURE_BAR = "bar"
PRESSURE_MBAR = "mbar"
PRESSURE_INHG = "inHg"
PRESSURE_PSI = "psi"

# Location Attributes
ATTR_LOCATION = "location"
ATTR_LATITUDE = "latitude"
ATTR_LONGITUDE = "longitude"
ATTR_ELEVATION = "elevation"
ATTR_CODE = "code"

# Data Attribution
ATTR_ATTRIBUTION = "attribution"
ATTRIBUTION = "Data provided by AEMET. www.aemet.es"

# Possible HTTP responses from AEMET API
HTTP_OK = 200
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429

FIELD_MAPPINGS = dict(
    alt=ATTR_ELEVATION,
    altitud=ATTR_ELEVATION,
    dv=ATTR_WEATHER_WIND_BEARING,
    fint=ATTR_WEATHER_TIME,
    hr=ATTR_WEATHER_HUMIDITY,
    id=ATTR_CODE,
    idema=ATTR_CODE,
    lat=ATTR_LATITUDE,
    latitud_dec=ATTR_LATITUDE,
    lon=ATTR_LONGITUDE,
    longitud_dec=ATTR_LONGITUDE,
    nieve=ATTR_WEATHER_SNOW,
    nombre=ATTR_LOCATION,
    prec=ATTR_WEATHER_PRECIPITATION,
    pres=ATTR_WEATHER_PRESSURE,
    ta=ATTR_WEATHER_TEMPERATURE,
    tamin=ATTR_WEATHER_TEMP_LOW,
    tpr=ATTR_WEATHER_DEW_POINT,
    ubi=ATTR_LOCATION,
    vis=ATTR_WEATHER_VISIBILITY,
    vv=ATTR_WEATHER_WIND_SPEED,
)

DAILY_SENSORS_CONVERT = {
    # SENSOR:                        [jsonpath,               field]
    "precipitation probability":     ["probPrecipitacion[*]", "value"],
    "snow level":                    ["cotaNieveProv.[*]",    "value"],
    ATTR_WEATHER_DESCRIPTION:        ["estadoCielo[*]",       "descripcion"],
    ATTR_FORECAST_CONDITION:         ["estadoCielo[*]",       "value"],
    ATTR_FORECAST_WIND_BEARING:      ["viento[*]",            "direccion"],
    ATTR_FORECAST_WIND_SPEED:        ["viento[*]",            "velocidad"],
    ATTR_FORECAST_WIND_GUST:         ["rachaMax[*]",          "value"],
    ATTR_FORECAST_TEMP:              ["temperatura",          "maxima"],
    ATTR_FORECAST_TEMP_LOW:          ["temperatura",          "minima"],
    "thermal sensation maximum":     ["sensTermica",          "maxima"],
    "thermal sensation minimum":     ["sensTermica",          "minima"],
    ATTR_FORECAST_HUMIDITY:          ["humedadRelativa",      "maxima"],
    ATTR_FORECAST_HUMIDITY_MIN:      ["humedadRelativa",      "minima"],
    ATTR_FORECAST_UV_INDEX:          ["uvMax",                ""],
}

HOURLY_SENSORS_CONVERT = {
    # SENSOR:                        [jsonpath,               field]
    ATTR_FORECAST_CONDITION:         ["estadoCielo[*]",       "value"],
    ATTR_FORECAST_DESCRIPTION:       ["estadoCielo[*]",       "descripcion"],
    ATTR_FORECAST_PRECIPITATION:     ["precipitacion[*]",     "value"],
    ATTR_FORECAST_SNOW:              ["nieve[*]",             "value"],
    ATTR_FORECAST_TEMP:              ["temperatura[*]",       "value"],
    ATTR_FORECAST_THERMAL_SENSATION: ["sensTermica[*]",       "value"],
    ATTR_FORECAST_HUMIDITY:          ["humedadRelativa[*]",   "value"],
    ATTR_FORECAST_WIND_BEARING:      ["vientoAndRachaMax[*]", "direccion"],
    ATTR_FORECAST_WIND_SPEED:        ["vientoAndRachaMax[*]", "velocidad"],
}

FLOAT_SENSORS = (
    ATTR_FORECAST_HUMIDITY,
    ATTR_FORECAST_SNOW,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_THERMAL_SENSATION,
    ATTR_FORECAST_TEMP,
)

MAP_CONDITION = {
    "11":  "sunny",                # Despejado
    "11n": "clear-night",          # Despejado Noche
    "12":  "partlycloudy",         # Poco nuboso
    "13":  "partlycloudy",         # Intervalos nubosos
    "14":  "cloudy",               # Nuboso
    "15":  "cloudy",               # Muy nuboso
    "15n": "cloudy",
    "16":  "cloudy",               # Cubierto
    "16n": "cloudy",
    "17":  "cloudy",               # Nubes altas
    "23":  "rainy",                # Intervalos nubosos con lluvia
    "24":  "rainy",                # Nuboso con lluvia
    "25":  "rainy",                # Muy nuboso con lluvia
    "25n": "rainy",
    "26":  "rainy",                # Cubierto con lluvia
    "26n": "rainy",
    "27":  "pouring",              # Chubascos
    "33":  "snowy",                # Intervalos nubosos con nieve
    "34":  "snowy",                # Nuboso con nieve
    "35":  "snowy",                # Muy nuboso con nieve
    "36":  "snowy",                # Cubierto con nieve
    "43":  "partlycloudy",         # Intervalos nubosos con lluvia escasa
    "44":  "partlycloudy",         # Nuboso con lluvia escasa
    "45":  "cloudy",               # Muy nuboso con lluvia escasa
    "46":  "cloudy",               # Cubierto con lluvia escasa
    "46n": "cloudy",
    "51":  "lightning",            # Intervalos nubosos con tormenta
    "52":  "lightning",            # Nuboso con tormenta
    "53":  "lightning",            # Muy nuboso con tormenta
    "54":  "lightning",            # Cubierto con tormenta
    "61":  "lightning-rainy",      # Intervalos nubosos con tormenta y lluvia escasa
    "62":  "lightning-rainy",      # Nuboso con tormenta y lluvia escasa
    "63":  "lightning-rainy",      # Muy nuboso con tormenta y lluvia escasa
    "64":  "lightning-rainy",      # Cubierto con tormenta y lluvia escasa
    "71":  "partlycloudy",         # Intervalos nubosos con nieve escasa
    "72":  "snowy",                # Nuboso con nieve escasa
    "73":  "snowy",                # Muy nuboso con nieve escasa
    "74":  "snowy",                # Cubierto con nieve escasa
    "81":  "fog",                  # Niebla
    "81n": "fog",
    "82":  "fog",                  # Bruma - Neblina
    "82n": "fog",
    "83":  "calima",               # Calima
}

ICONS_URL = "www.aemet.es/imagenes_gcd/_iconos_municipios/{}.png"

WIND_DIRECTIONS = {
    "C":     None,
    "N":      0.0,
    "NNE":   22.5,
    "NE":    45.0,
    "ENE":   67.5,
    "E":     90.0,
    "ESE":  112.5,
    "SE":   135.0,
    "SSE":  157.5,
    "S":    180.0,
    "SSW":  202.5,
    "SW":   225.0,
    "WSW":  247.5,
    "W":    270.0,
    "WNW":  292.5,
    "NW":   315.0,
    "NNW":  337.5,
}

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=10)
