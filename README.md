# HomeAssistant-AEMET

A Home Assistant custom-component that retrieves current information and weather forecasts published by [AEMET](http://www.aemet.es) (**A**gencia **e**statal de **met**eorología).

⚠️ As this is the Spanish governmental meteorological agency, only information on locations in Spain is published. ⚠️ 

The information is obtained from weather stations distributed throughout Spain.

To use this component in your Home Assistant you will need to obtain a personal/private API KEY from [AEMET Open Data](https://opendata.aemet.es).

🇪🇸 All information is in Spanish. 🇪🇸 

## Getting started

Place the files of `aemet` component at this location on your setup: 

* Hass.io: `/custom_components/aemet/`
* Hassbian / Other: `<config directory>/custom_components/aemet/`

And then restart Home Assistant to make sure the component loads.

Due to how `custom_components` are loaded, it is normal to see a `ModuleNotFoundError` error on first boot after adding this, to resolve it, restart Home-Assistant.

#### Example configuration.yaml

This configuration will load the component with your current location as defined at your Home Assistant. 
```yaml
weather:
  platform: aemet
  api_key: !secret aemet_api_key
```
You can add optional parameters to configure your component:
```yaml
weather:
  platform: aemet
  name: el_tiempo
  api_key: !secret aemet_api_key
  latitude: 40.4169019
  longitude: -3.7056721
``` 

#### Config options
The following table shows all the options that can be used to configure your component.

There is only one mandatory parameter `apy_key`, any other parameter is optional.

| key | required | default value | description
| --- | :---: | :---: | ---
| **api_key** | Yes | N/A | Your private api key from AEMET.
| **name** | No | aemet | Name of your component. If you have several instances of this component you need to have different names.
| **latitude** | No | Home Assistant Latitude | Latitude of your location
| **Longitude** | No | Home Assistant Longitude | Longitude of your location
| **elevation** | No | 0.0 | Elevation of your location.
| **mode** | No | daily | Type of forecast: `hourly` or `daily`
| **cache_dir** | No | aemet | Directory where to cache some files. Location is relative to your **config** directory, but you can use a full qualified path. e.g.   ```cache_dir: aemet``` and ```cache_dir: /config/aemet``` are equivalent

**Other config options**
(for experimental use, can be removed in future versions)

| key | required | default value | description
| --- | :---: | :---: | ---
| **weather_station** | No| N/A | Code of weather station to retrieve data instead of looking for the nearest one
| **city** | No | N/A | Code of city (as defined by INE on http://www.ine.es/daco/daco42/codmun/codmunmapa.htm) to retrieve data instead of looking for the nearest one
| **experimental** | No | `False` | If `true` the search for nearest weather station or city will be done by using a KDTree (requires `scipy` package). Some changes in aemet.py file should be done to uncomment some code. 

## How to obtain your API KEY

You should go to: https://opendata.aemet.es

On section "Obtención de API Key" you should click on "Solicitar"

![https://opendata.aemet.es](https://user-images.githubusercontent.com/6525261/64166305-17466500-ce47-11e9-9830-5ba1ff05fa80.png)

Once you enter your email in next screen you will receive an email from opendata_apikey@aemet.es to verify your email address and a link to request your api key.

![verification_mail](https://user-images.githubusercontent.com/6525261/64166881-52956380-ce48-11e9-9b34-71ab17e04987.png)

Finally after you confirm your request you will receive a second email with your API Key

![confirmation_mail](https://user-images.githubusercontent.com/6525261/64166429-6391a500-ce47-11e9-97ad-79126fe3306e.png))

## How data is processed

AEMET produces 3 types of data...

* Conventional observation with data from the last 24 hours
* Hourly forecast with the forecast of the next 72 hours
* Daily forecast up to 5 days.

All information is collected and preprocessed to match the way " Home Assistant " can work with it.

### Currently Weather

The "current" information is obtained from weather stations which are updated hourly, but depending on the station there will be some information or other available.

For example:
* Station 1111X (Santander CMT) has 9 sensors: "precipitation", "wind_speed", "wind_bearing", "pressure", "humidity", "templow", "temperature", "dew_point" and "visibility".

* Station 3194U (Madrid - C. Universitaria) has 6 sensors: "precipitation", "wind_speed", "wind_bearing", "humidity", "templow", "temperature".

* Station 3194Y (Pozuelo de Alarcon, Madrid) has 4 sensors: "precipitation", "humidity", "templow", "temperature".

If some information is not available but it is available in forescast data, then it is obtained from the hourly forecast information for the current time.

### Weather Forecast

Weather Forecast is obtained for Locations not directly from Weather Station.

AEMET produces forecast data for:

* Days D and D+1:  Some sensors get information for 6 hours interval, 12 hours interval and whole day.
* Days D+2 and D+3:  Some sensors get information for 12 hours interval and whole day.
* Day D+4:  Sensos get information for whole day.

We present information on daily basis except for current day that will present the information from 6 hour interval.
