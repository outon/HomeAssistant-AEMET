""" Description of existing AEMET weather sensors:

For weather stations:
    alt   : Altitude of the station in meters
    dmax  : Maximum wind direction recorded in the 60 minutes prior to the time indicated by 'fint' (degrees)
    dv    : Average wind direction, in the 10-minute period preceding the date indicated by 'fint' (degrees)
    fint  : Date end time of the observation period, this is data from the period of the hour preceding that indicated by this field (UTC time)
    hr    : Instantaneous relative humidity of the air corresponding to the date given by 'fint' (%)
    idema : Automatic weather station weather indicator
    lat   : Latitude of the weather station (degrees)
    lon   : Longitude of weather station (degrees)
    nieve : Snow layer thickness measured in the 10 minutes prior to the date indicated by 'fint' (cm)
    prec  : Accumulated precipitation, measured by the rain gauge, during the previous 60 minutes at the time indicated by the observation period 'fint' (mm, equivalent to l/m2)
    pres  : Instantaneous pressure at the level at which the barometer is installed and corresponding to the date given by 'fint' (hPa)
    ta    : Instantaneous air temperature corresponding to the date given by 'fint' (degrees Celsius)
    tamax : Maximum air temperature, the maximum value of the 60 instantaneous 'ta' values measured in the 60-minute period preceding the time indicated by the observation period 'fint' (degrees Celsius)
    tamin : Minimum air temperature, the minimum value of the 60 instantaneous 'ta' values measured in the 60-minute period preceding the time indicated by the observation period 'fint' (degrees Celsius)
    tpr   : Calculated dew point temperature corresponding to the 'fint' date (degrees Celsius)
    ubi   : Station location. Station name
    vis   : Visibility, average of the visibility measurement corresponding to the 10 minutes prior to the date given by 'fint' (Km)
    vmax  : Maximum wind speed, maximum value of the wind maintained 3 seconds and recorded in the 60 minutes preceding the time indicated by the observation period 'fint' (m/s)
    vv    : Average wind speed, average scalar of samples acquired every 0.25 or 1 second in the 10-minute period preceding that indicated by 'fint' (m/s)

Information for cities:
    altitud :      Altitude of the town in meters
    id :           City Code designated by INE (Instituto nacional de estadistica)
    latitud_dec:   Latitude of the town (degrees)
    longitud_dec": Longitude of the town (degrees)
    nombre :       Name of town

    other sensors exists, but are not of our interest.
"""

from datetime import timedelta

DEFAULT_CACHE_DIR = "aemet"

# Weather/Forecast attributes
ATTR_CONDITION_CLASS = "condition_class"
ATTR_FORECAST = "forecast"
ATTR_FORECAST_CONDITION = "condition"
ATTR_FORECAST_HUMIDITY = "humidity"
ATTR_FORECAST_PRECIPITATION = "precipitation"
ATTR_FORECAST_SNOW = "snow"
ATTR_FORECAST_TEMP = "temperature"
ATTR_FORECAST_TEMP_LOW = "templow"
ATTR_FORECAST_THERMAL_SENSATION = "thermal_sensation"
ATTR_FORECAST_TIME = "datetime"
ATTR_FORECAST_UV_INDEX = "UV index"
ATTR_FORECAST_WIND_BEARING = "wind_bearing"
ATTR_FORECAST_WIND_SPEED = "wind_speed"
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
    # SENSOR:                    [jsonpath,               field]
    "precipitation probability": ["probPrecipitacion[*]", "value"],
    "snow level": ["cotaNieveProv.[*]", "value"],
    ATTR_WEATHER_DESCRIPTION: ["estadoCielo[*]", "descripcion"],
    ATTR_FORECAST_CONDITION: ["estadoCielo[*]", "value"],
    ATTR_FORECAST_WIND_BEARING: ["viento[*]", "direccion"],
    ATTR_FORECAST_WIND_SPEED: ["viento[*]", "velocidad"],
    "maximum gust": ["rachaMax[*]", "value"],
    ATTR_FORECAST_TEMP: ["temperatura", "maxima"],
    ATTR_FORECAST_TEMP_LOW: ["temperatura", "minima"],
    "thermal sensation maximum": ["sensTermica", "maxima"],
    "thermal sensation minimum": ["sensTermica", "minima"],
    ATTR_FORECAST_HUMIDITY: ["humedadRelativa", "maxima"],
    "humidity min": ["humedadRelativa", "minima"],
    ATTR_FORECAST_UV_INDEX: ["uvMax", ""],
}

HOURLY_SENSORS_CONVERT = {
    ATTR_FORECAST_CONDITION: ["estadoCielo[*]", "value"],
    "description": ["estadoCielo[*]", "descripcion"],
    ATTR_FORECAST_PRECIPITATION: ["precipitacion[*]", "value"],
    ATTR_FORECAST_SNOW: ["nieve[*]", "value"],
    ATTR_FORECAST_TEMP: ["temperatura[*]", "value"],
    ATTR_FORECAST_THERMAL_SENSATION: ["sensTermica[*]", "value"],
    ATTR_FORECAST_HUMIDITY: ["humedadRelativa[*]", "value"],
    ATTR_FORECAST_WIND_BEARING: ["vientoAndRachaMax[*]", "direccion"],
    ATTR_FORECAST_WIND_SPEED: ["vientoAndRachaMax[*]", "velocidad"],
}

FLOAT_SENSORS = (
    ATTR_FORECAST_HUMIDITY,
    ATTR_FORECAST_SNOW,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_THERMAL_SENSATION,
    ATTR_FORECAST_TEMP,
)
MAP_CONDITION = {
    "11": "sunny",  # "Clear"
    "11n": "clear-night",  # "Clear"
    "12": "partlycloudy",  # "Little cloudy",
    "12n": "partlycloudy",  # "Little cloudy",
    "13": "partlycloudy",  # "Cloudy intervals",
    "13n": "partlycloudy",  # "Cloudy intervals",
    "14": "cloudy",  # "Cloudy",
    "14n": "cloudy",  # "Cloudy",
    "15": "cloudy",  # "Very cloudy",
    "16": "cloudy",  # "Covered",
    "17": "Nubes altas",  # "High clouds",
    "17n": "Nubes altas noche",  # "High clouds",
    "23": "rainy",  # "Cloudy intervals with rain",
    "23n": "rainy",  # "Cloudy intervals with rain",
    "24": "rainy",  # "Cloudy with rain",
    "24n": "rainy",  # "Cloudy with rain",
    "25": "rainy",  # "Very cloudy with rain",
    "26": "rainy",  # "Covered with rain",
    "33": "snowy",  # "Cloudy intervals with snow",
    "33n": "snowy",  # "Cloudy intervals with snow",
    "34": "snowy",  # "Cloudy with snow",
    "34n": "snowy",  # "Cloudy with snow",
    "35": "snowy",  # "Very cloudy with snow",
    "36": "snowy",  # "Covered with snow",
    "36n": "snowy",
    "43": "partlycloudy",  # "Cloudy intervals with little rain"
    "43n": "partlycloudy",  # "Cloudy intervals with little rain",
    "44": "cloudy",  # "Cloudy with scarce rain",
    "44n": "Cloudy with scarce rain",
    "45": "cloudy",  # "Very cloudy with little rain",
    "46": "cloudy",  # "Covered with scarce rain",
    "51": "lightning",  # "Cloudy storm intervals",
    "51n": "Cloud intervals with storm",
    "52": "lightning",  # "Cloudy with storm",
    "52n": "Cloudy with storm",
    "53": "lightning",  # "Very cloudy with storm",
    "54": "lightning",  # "Covered with storm",
    "61": "lightning-rainy",  # "Cloudy intervals with storm and scarce rain",
    "61n": "Cloudy intervals with storm and scarce rain",
    "62": "lightning-rainy",  # "Cloudy with storm and scarce rain",
    "62n": "Cloudy with storm and scarce rain",
    "63": "lightning-rainy",  # "Very cloudy with storm and little rain",
    "64": "lightning-rainy",  # "Covered with storm and scarce rain",
    "71": "partlycloudy",  # "Cloudy intervals with scarce snow",
    "71n": "Cloudy intervals with scarce snow",
    "72": "snowy",  # "Cloudy with scarce snow",
    "72n": "Cloudy with scarce snow",
    "73": "snowy",  # "Very cloudy with scarce snow",
    "74": "snowy",  # "Covered with scarce snow",
    "81": "Fog",
    "82": "Mist",
    "83": "Calima",
}

ICONS_URL = "www.aemet.es/imagenes_gcd/_iconos_municipios/{}.png"

WIND_DIRECTIONS = dict(C=None, N="N", NNE="NNE", NE="NE", ENE="ENE", E="E", ESE="ESE", SE="SE", SSE="SSE", S="S",
                       SSO="SSW", SO="SW", OSO="WSW", O="W", ONO="WNW", NO="NW", NNO="NNW")

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)
