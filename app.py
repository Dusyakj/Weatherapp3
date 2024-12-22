import requests
from weather_utils import BASE_URL, ACCUWEATHER_API_KEY

from flask import Flask, request, render_template
import dash
from dash import dcc
from dash import html
import plotly.graph_objects as go
import pandas as pd
from weather_utils import get_location_key, get_daily_forecast
import plotly.express as px
import logging
from requests.exceptions import RequestException


logging.basicConfig(level=logging.INFO)
server = Flask(__name__)

app = dash.Dash(__name__, server=server, url_base_pathname='/dashboard/')

app.layout = html.Div([
    html.H1("Графики погоды"),
    html.P("Введите данные на основной странице")
])

def create_weather_graphs(start_city, end_city, waypoints, days):
    all_cities = [start_city] + waypoints + [end_city]
    
    all_data = {}
    for city in all_cities:
        location_key = get_location_key(city)
        if location_key:
           forecast_df = get_daily_forecast(location_key, days)
           if forecast_df is not None:
              all_data[city] = forecast_df
           else:
               logging.warning(f"No forecast data for {city}")
        else:
             logging.warning(f"No location key for {city}")
           
    if not all_data:
        return ["No Data available"], None
        
    graphs = []
    for city, df in all_data.items():
      
        fig_temp = go.Figure(data=[
          go.Scatter(x=df['Date'], y=df['Max_Temp'], mode='lines+markers', name=f'{city} Max Temp'),
          go.Scatter(x=df['Date'], y=df['Min_Temp'], mode='lines+markers', name=f'{city} Min Temp')
        ])
        fig_temp.update_layout(title=f'Температура в {city}')
        graphs.append(dcc.Graph(figure=fig_temp))

        fig_wind = go.Figure(data=[
            go.Scatter(x=df['Date'], y=df['Wind_Speed'], mode='lines+markers', name=f'Скорость ветра {city}')
        ])
        fig_wind.update_layout(title=f'Скорость ветра в {city}')
        graphs.append(dcc.Graph(figure=fig_wind))

        fig_prec = go.Figure(data=[
            go.Scatter(x=df['Date'], y=df['PrecipitationProbability'], mode='lines+markers', name=f'Вероятность осадков {city}')
        ])
        fig_prec.update_layout(title=f'Вероятность осадков в {city}')
        graphs.append(dcc.Graph(figure=fig_prec))
      
    
    # Map creation
    
    lats = []
    lons = []

    for city in all_cities:
        location_key = get_location_key(city)
        if location_key:
            url = f"{BASE_URL}/locations/v1/{location_key}?apikey={ACCUWEATHER_API_KEY}" 
            try:
                response = requests.get(url)
                response.raise_for_status()
                location_data = response.json()
                if location_data and location_data.get('GeoPosition'): 
                    lats.append(location_data['GeoPosition']['Latitude'])
                    lons.append(location_data['GeoPosition']['Longitude'])
            except RequestException as e:
                logging.error(f"Error fetching data for {city}: {e}")
        else:
            logging.warning(f"No location key for {city}, can't get lat/lon data")

    map_fig = None
    if lats and lons:
        map_df = pd.DataFrame({'lat': lats, 'lon': lons, 'city': all_cities})
        map_fig = px.line_mapbox(map_df, lat="lat", lon="lon", zoom=3, hover_name='city') 
        map_fig.update_layout(mapbox_style="open-street-map")

    return graphs, map_fig


@server.route('/weather', methods=['POST'])
def weather_report():
    start_city = request.form['start_city']
    end_city = request.form['end_city']
    waypoints_str = request.form.get('waypoints', '')
    waypoints = [wp.strip() for wp in waypoints_str.split(',') if wp.strip()]
    days = int(request.form['days'])
    print(start_city, end_city, waypoints, days)
    graphs, map_fig = create_weather_graphs(start_city, end_city, waypoints, days)
    
    app.layout = html.Div([
            html.H1("Графики погоды"),
            html.Div(graphs) if graphs != ["No Data available"] else html.P("Нет данных"),
            html.H2("Маршрут на карте"),
            dcc.Graph(figure=map_fig) if map_fig else html.P("Нет данных")
        ])
    
    return render_template('dashboard.html', dash_url='/dashboard/')

@server.route('/', methods=['GET'])
def index():
    return render_template('index.html')

if __name__ == '__main__':
    server.run(debug=True, port=5000)