"""AEMET: Custom Weather Component to retrieve weather data
and forecast from AEMET (Agencia Estatal de Metereologia)

This component makes use of AEMET opendata REST API service to
retrieve weather data and forecast.

* Current weather data obtained by automatic weather stations.
* Weather forecast data is provided by Cities or Towns.

To retrieve this data we need to know the station id or the
city code that we obtain from the geographical location of
our Home Assistant or we define manually.

The received data are reformatted so that they can be used by
Home Assistant.

Note: Currently data is obtained from weather station, all
missing information is obtained from weather forecast.
"""
