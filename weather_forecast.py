import requests
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import numpy as np
import os
import datetime
import sys
import pendulum as pdl
from insolAPI.WebAPI import API

"""
Parameters and response: https://openweathermap.org/forecast5
"""

#show_plot is the first argument of the script if htere is one, else it is False
if len(sys.argv) > 1:
    SHOW_PLOT = sys.argv[1]
else:
    SHOW_PLOT = False


class Color:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def get_weather_forecast(api_key, city_name):
    base_url = "http://api.openweathermap.org/data/2.5/forecast"
    params = {
        'appid': api_key,
        'cnt': '20',
        'units': 'metric'
    }
    if city_name == "Conthey":
        params["lat"] = '46.210646'
        params["lon"] = '7.30504'
    elif city_name == "Bioschmid":
        params["lat"] = '47.250876'
        params["lon"] = '8.238644'

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

        update_request_count()
        return data

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None



def plot_weather_forecast(weather_data, city_name):
    forecast_date = []
    forecast_temp = []
    forecast_snow = []
    forecast_rain = []
    forecast_wind = []
    forecast_pop = []

    for forecast in weather_data["list"]:
        forecast_date.append(forecast["dt_txt"])
        forecast_temp.append(forecast["main"]["temp"])
        forecast_wind.append(forecast["wind"]["speed"])
        forecast_pop.append(forecast["pop"])
        try:
            forecast_snow.append(forecast["snow"]["3h"])
        except:
            forecast_snow.append(0)
        try:
            forecast_rain.append(forecast["rain"]["3h"])
        except:
            forecast_rain.append(0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=forecast_date, y=forecast_temp,
                        mode='lines+markers',
                        name='Temperature', line=dict(color='orange', width=2)))
    fig.add_trace(go.Scatter(x=forecast_date, y=forecast_snow,
                        mode='lines+markers',
                        name='Snow', line=dict(color='lightblue', width=2)))
    fig.add_trace(go.Scatter(x=forecast_date, y=forecast_rain,
                        mode='lines+markers',
                        name='Rain', line=dict(color='darkcyan', width=2)))
    fig.add_trace(go.Scatter(x=forecast_date, y=forecast_wind,
                        mode='lines+markers',
                        name='Wind', line=dict(color='darkred', width=2)))
    fig.add_trace(go.Bar(x=forecast_date, y=forecast_pop, name='Precipitation Probability', marker_color='lightgrey'))

    # Update layout for better visualization
    fig.update_layout(title="Weather Forecast for " + city_name + "",
                    xaxis_title="Date",
                    yaxis_title="Values",
                    legend=dict(x=1, y=1, traceorder='normal'),
                    # Background color of the entire graph area,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)')

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')

    fig.show()


def alert_user(weather_data):
    # alert_snow = False
    # Alert the user if the temperature is above a certain threshold
    time_of_alert = []
    alert_list = []
    will_it_snow = False
    strong_wind = False
    for forecast in weather_data['list']:
        try:
            if bool(forecast['snow']['3h']):
                alert_list.append("Snow fall")
                alert_list.append(forecast["dt_txt"])
            # time_of_alert.append(forecast['dt_txt'])
        except:
            pass
        if forecast['wind']['speed'] > 10:
            alert_list.append("Strong wind > 10 m/s")
            alert_list.append(forecast["dt_txt"])
    return alert_list



def update_request_count():
    file_name = "count_requests.csv"

    # Check if the file exists
    if os.path.exists(file_name):
        # Read the last line and get the count
        with open(file_name, "r") as file:
            lines = file.readlines()
            if lines:
                last_line = lines[-1].strip()
                count = int(last_line.split(',')[1]) + 1
            else:
                count = 1
            # add the number of requests made during the last hour
            last_hour = datetime.datetime.now() - datetime.timedelta(hours=1)
            count_last_hour = 1
            for line in lines:
                if datetime.datetime.strptime(line.split(',')[4].strip(), "%Y-%m-%d %H:%M:%S") >= last_hour:
                    count_last_hour = count_last_hour + 1
    else:
        # If the file doesn't exist, create it and set count to 1
        count = 1
        count_last_hour = 1

    # Get the current timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Write the new line to the file
    with open(file_name, "a") as file:
        file.write(f"Total,{count},last hour,{count_last_hour},{timestamp}\n")



def log_reports(alerts, loc):
    file_name = "log_reports.csv"

    # Get the current timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Open the file in append mode (create if it doesn't exist)
    with open(file_name, "a") as file:
        # Write a new line with timestamp and alerts
        file.write(f"{loc},{timestamp}, {', '.join(alerts)}\n")



if __name__ == "__main__":
    # Replace 'YOUR_API_KEY' with your actual OpenWeatherMap API key
    api_key = '47b3b8c2f8061c46d61d01f2cbf28557'

    locations = ["Conthey", "Bioschmid"]
    weather_data = {}

    for loc in locations:
        weather_data[loc] = get_weather_forecast(api_key, loc)
        if SHOW_PLOT: plot_weather_forecast(weather_data[loc], loc)
        alerts = alert_user(weather_data[loc])
        for i in range(0, len(alerts), 2):
            print(Color.RED + f"{loc}: {alerts[i]} at {alerts[i+1]} \n" + Color.RESET)
        log_reports(alerts, loc)