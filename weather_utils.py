import requests
import os
from dotenv import load_dotenv
import pandas as pd
from requests.exceptions import RequestException
import logging

load_dotenv()

ACCUWEATHER_API_KEY = '7g72B7FfwEJqsrGmlSCYWKKofFw6Xz4y'
BASE_URL = "http://dataservice.accuweather.com"
logging.basicConfig(level=logging.INFO)


def get_location_key(city_name):
    url = f"{BASE_URL}/locations/v1/cities/search?apikey={ACCUWEATHER_API_KEY}&q={city_name}"
    try:
      response = requests.get(url)
      response.raise_for_status()
      data = response.json()
      if data:
          return data[0]['Key']
      return None
    except RequestException as e:
        logging.error(f"Error during get_location_key for {city_name}: {e}")
        return None


def get_daily_forecast(location_key, days=1):
    url = f"{BASE_URL}/forecasts/v1/daily/5day/{location_key}?apikey={ACCUWEATHER_API_KEY}&language=ru&details=true&metric=true"
    try:
      response = requests.get(url)
      response.raise_for_status()
      data = response.json()
      
      if 'DailyForecasts' not in data:
          return None
      
      forecasts = data['DailyForecasts'][:days]
      
      formatted_data = []
      for forecast in forecasts:
          date = forecast['Date']
          
          max_temp = forecast['Temperature']['Maximum']['Value']
          min_temp = forecast['Temperature']['Minimum']['Value']
          
          wind_speed = forecast['Day'].get('Wind', {}).get('Speed', {}).get('Value', 0)

          # Precipitation probability
          day_probability = forecast['Day'].get('PrecipitationProbability', 0)
          night_probability = forecast['Night'].get('PrecipitationProbability', 0)
          prec_probability = max(day_probability, night_probability)
          
          formatted_data.append({
              'Date': date,
              'Max_Temp': max_temp,
              'Min_Temp': min_temp,
              'Wind_Speed': wind_speed,
              'PrecipitationProbability': prec_probability
          })
      
      return pd.DataFrame(formatted_data)
    except RequestException as e:
        logging.error(f"Error during get_daily_forecast for location {location_key}: {e}")
        return None