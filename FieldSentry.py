# FieldSentry

# %% --------------------------------------- Imports ------------------------------------
from insolAPI.WebAPI import API
import simplejson as json
import pandas as pd
import pendulum as pdl
from tqdm import tqdm
import warnings
import requests
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import numpy as np
import os
import datetime
import sys
from tabulate import tabulate


SHOW_PLOT = False


list_sensor = [
    "PAR",
    "IRRAD",
    "GII",
    "DNI",
    "DHI",
    "TEMP",
    "HUMI",
    "RAIN",
    "RAIN_TYPE",
    "RAIN_ACCUMULATED",
    "WIND",
    "WIND_DIR",
    "VIRTUAL",
    "LEAF_TEMP"
]


dict_screen_mode = {
    1: "A",
    2: "M",
    3: "E",
    4: "P",
    5: "D",
    6: "R",
}

time_args = dict(
    start=pdl.now().subtract(hours=2, minutes=30).to_datetime_string(),
    stop=pdl.now().subtract(hours=2).to_datetime_string(),
    timezone="UTC",
)


installation_path = "C:/Users/Insolight/Desktop/InsolReports/Installations/"
with open(installation_path + "/local.json") as f:
    local_data = json.load(f)

# with open("C:/Users/Insolight/OneDrive - Insolight/Documents-OD/weather_forecast/config.json") as f:
#     config_data = json.load(f)


class Color:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


dict_instal_logs = {}  # type: dict
dict_sensor_channel_id = {}  # type: dict
diff_logs = {}  # type: dict
dict_logs_joined = {}  # type: dict
dict_channel_id = {}  # type: dict
dict_missing_sensors = {}  # type: dict
weather_data = {}
dict_alerts = {}
dict_time_of_snow = {} # type: dict
dict_time_of_wind = {} # type: dict
dict_time_high_T = {} # type: dict
dict_alert_time = {} # type: dict


# %% --------------------------------------- Weather ------------------------------------

"""
Parameters and response: https://openweathermap.org/forecast5
"""
def read_json_config(path):
    """
    Read the config.json file and return the api key
    """
    with open(path + "/config.json") as f:
        config_data = json.load(f)

    installations = {}

    # Iterate through locations
    locations = config_data['locations']
    for location in locations:
        # Store details in a dictionary
        location_details = {
            'id': location['id'],
            'name': location['name'],
            'latitude': location['latitude'],
            'longitude': location['longitude'],
            'wind_threshold': location['wind_threshold'],
            'high_temperature_threshold': location['high_temperature_threshold'],
            'has_a_screen': location['has_a_screen'],
        }
        installations[location['name']] = location_details
    return installations, [config_data['api_key'], config_data['api_url']]



def format_timestamp(original_timestamp_str):
    original_timestamp = datetime.datetime.strptime(original_timestamp_str, '%Y-%m-%d %H:%M:%S')
    formatted_timestamp_str = original_timestamp.strftime('%Hh %d-%m-%Y')
    return formatted_timestamp_str

def format_timestamps_in_dict(input_dict):
    formatted_dict = {}
    for key, sub_dict in input_dict.items():
        formatted_dict[key] = {}
        for event, timestamps in sub_dict.items():
            formatted_timestamps = [format_timestamp(ts) for ts in timestamps]
            formatted_dict[key][event] = formatted_timestamps
    return formatted_dict


def get_weather_forecast(dict_instal, api_data, city_name):
    """
    Request the weather forecast for the next 2 days, every 3 hours
    """
    # base_url = "http://api.openweathermap.org/data/2.5/forecast"
    params = {"appid": api_data[0], "cnt": "20", "units": "metric"}

    params["lat"] = dict_instal[city_name]["latitude"]
    params["lon"] = dict_instal[city_name]["longitude"]

    try:
        response = requests.get(api_data[1], params=params)
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
    fig.add_trace(
        go.Scatter(
            x=forecast_date,
            y=forecast_temp,
            mode="lines+markers",
            name="Temperature",
            line=dict(color="orange", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=forecast_date,
            y=forecast_snow,
            mode="lines+markers",
            name="Snow",
            line=dict(color="lightblue", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=forecast_date,
            y=forecast_rain,
            mode="lines+markers",
            name="Rain",
            line=dict(color="darkcyan", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=forecast_date,
            y=forecast_wind,
            mode="lines+markers",
            name="Wind",
            line=dict(color="darkred", width=2),
        )
    )
    fig.add_trace(
        go.Bar(
            x=forecast_date,
            y=forecast_pop,
            name="Precipitation Probability",
            marker_color="lightgrey",
        )
    )

    # Update layout for better visualization
    fig.update_layout(
        title="Weather Forecast for " + city_name + "",
        xaxis_title="Date",
        yaxis_title="Values",
        legend=dict(x=1, y=1, traceorder="normal"),
        # Background color of the entire graph area,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(0,0,0,0.1)")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(0,0,0,0.1)")

    fig.show()


def alert_user(weather_data, dict_events):
    """
    Set the threshold for the alerts, and which alerts to send
    """
    alert_list = []
    for forecast in weather_data["list"]:
        try:
            if bool(forecast["snow"]["3h"]):
                alert_list.append("Snow fall")
                alert_list.append(forecast["dt_txt"])
        except:
            pass
        if forecast["wind"]["speed"] > dict_events["wind_threshold"]:
            alert_list.append("Strong wind")
            alert_list.append(forecast["dt_txt"])
        if forecast["main"]["temp"] > dict_events["high_temperature_threshold"]:
            alert_list.append("High temperature")
            alert_list.append(forecast["dt_txt"])
        #to add a new alert, add the condition here. Also need to change the main
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
                count = int(last_line.split(",")[1]) + 1
            else:
                count = 1
            # add the number of requests made during the last hour
            last_hour = datetime.datetime.now() - datetime.timedelta(hours=1)
            count_last_hour = 1
            for line in lines:
                if (
                    datetime.datetime.strptime(
                        line.split(",")[4].strip(), "%Y-%m-%d %H:%M:%S"
                    )
                    >= last_hour
                ):
                    count_last_hour = count_last_hour + 1
    else:
        # If the file doesn't exist, create it and set count to 1
        count = 1
        count_last_hour = 1

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(file_name, "a") as file:
        file.write(f"Total,{count},last hour,{count_last_hour},{timestamp}\n")


def log_reports(alerts, loc):
    """
    Write the report in a csv file, with the location, the timestamp and the alerts
    """
    file_name = "log_reports.csv"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(file_name, "a") as file:
        file.write(f"{loc},{timestamp}, {', '.join(alerts)}\n")


def save_alerts_to_csv(df):
    # current_timestamp =
    # new_df = df.copy()
    df['Timestamp'] = datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')

    cols = df.columns.tolist()
    df = df[[cols[-1]] + cols[:-1]]

    #check if the file exists
    if not os.path.exists("log_reports.csv"):
        df.to_csv("log_reports.csv", index=False, header=True) # add the header if the file doesn't exist
    else:
        df.to_csv("log_reports.csv", mode='a', header=False, index=False)
        #add a blank line
        with open("log_reports.csv", "a") as file:
            file.write("\n")



def list_to_string(lst):
    try:
        return "\n".join(map(str, lst))
    except Exception as e:
        pass



def process_screen_data(df):
    df = df[['screen_id', 'state', 'name']]
    screen_names = df['name'].unique()
    list_screen_states = []
    for screen_name in screen_names:
        df_screen_tmp = df[df['name'] == screen_name]
        df_screen_tmp = df.sort_index(ascending=False)
        state = df_screen_tmp['state'][0]
        # print(f"{screen_name}: {dict_screen_mode[state]}")
        list_screen_states.append([screen_name, dict_screen_mode[state]])
        print(list_screen_states)
    return list_screen_states


if __name__ == "__main__":

    api = API(local_data["API_user"], local_data["API_pwd"], dev_space=False)
    dict_instal_json, api_data = read_json_config("C:/Users/Insolight/OneDrive - Insolight/Documents-OD/FieldSentry")

    for instal in tqdm(dict_instal_json):
        list_channel_id = [] # type: list
        list_sensor_logging = [] # type: list
        dict_logs_joined[instal] = {}
        dict_sensor_channel_id[instal] = {}
        sensor_number = 0
        dict_alert_time[instal] = {"Snow fall": [], "Strong wind": [], "High temperature": []}
        list_snow_time = []
        list_wind_time = []
        list_highT_time = []
        dict_df_screen = {}
        dict_screen_states = {}


        # get the weather forecast for each installation
        weather_data[instal] = get_weather_forecast(dict_instal_json, api_data, instal)
        if SHOW_PLOT:
            plot_weather_forecast(weather_data[instal], instal)
        dict_alerts[instal] = alert_user(weather_data[instal], dict_instal_json[instal])

        for i in range(0, len(dict_alerts[instal]), 2):
            # print(Color.RED + f"{loc}: {dict_alerts[loc][i]} at {dict_alerts[loc][i+1]} \n" + Color.RESET)
            if dict_alerts[instal][i] == "Snow fall":
                list_snow_time.append(dict_alerts[instal][i + 1])
                dict_alert_time[instal]["Snow fall"].append(dict_alerts[instal][i + 1])
            if dict_alerts[instal][i] == "Strong wind":
                list_wind_time.append(dict_alerts[instal][i + 1])
                dict_alert_time[instal]["Strong wind"].append(dict_alerts[instal][i + 1])
            if dict_alerts[instal][i] == "High temperature":
                list_highT_time.append(dict_alerts[instal][i + 1])
                dict_alert_time[instal]["High temperature"] = dict_alerts[instal][i + 1]

        #screen data
        if dict_instal_json[instal]["has_a_screen"]:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=UserWarning)
                dict_df_screen[instal] = api.get_screens_logs_joined(**time_args, install=dict_instal_json[instal]["id"])
                list_screen_states = process_screen_data(dict_df_screen[instal])
        else:
            list_screen_states = []
        dict_screen_states[instal] = list_screen_states


        # get all the sensors and channels for each installation
        for sensor_type in api.SensorsTypes:
            if str(sensor_type).split(".")[1] in list_sensor:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", category=UserWarning)

                        dict_logs_joined[instal][
                            list_sensor[sensor_number]
                        ] = api.get_sensor_channels_logs_joined(
                            **time_args,
                            sensor_type=sensor_type,
                            install=dict_instal_json[instal]["id"],
                        )
                        list_sensor_logging.extend(
                            dict_logs_joined[instal][
                                list_sensor[sensor_number]
                            ].sensor_channel_id.unique()
                        )
                except:
                    pass
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=UserWarning)

                    dict_sensor_channel_id[instal][
                        list_sensor[sensor_number]
                    ] = api.get_sensor_channels(
                        sensor_type=sensor_type, install=dict_instal_json[instal]["id"]
                    )
                    list_channel_id.extend(
                        dict_sensor_channel_id[instal][list_sensor[sensor_number]][
                            dict_sensor_channel_id[instal][list_sensor[sensor_number]][
                                "deleted_at"
                            ].isnull()
                        ].index.to_list()
                    )
            except:
                pass
            sensor_number += 1

        dict_instal_logs[instal] = list_sensor_logging  # dict with the list of sensors logging for each installation
        dict_channel_id[instal] = list_channel_id       # dict with the list of channels for each installation


        # substraction, result is the list of sensors that are not logging, and not deleted from the config
        diff_logs[instal] = list(
            set(dict_channel_id[instal]) - set(dict_instal_logs[instal])
        )

        #try to identify the missing sensors from the channel list
        for sensor_id in diff_logs[instal]:
            for sensor in list_sensor:
                try:
                    dict_missing_sensors[sensor_id] = [
                        instal,
                        dict_sensor_channel_id[instal][sensor]
                        .loc[sensor_id]
                        .address,
                        dict_sensor_channel_id[instal][sensor]
                        .loc[sensor_id]
                        .sensor_name,
                        dict_sensor_channel_id[instal][sensor]
                        .loc[sensor_id]
                        .channel_name,
                    ]
                    # print(Color.RED + f"{sensor_id}: {dict_missing_sensors[sensor_id]}" + Color.RESET)
                except:
                    pass

    df_missing_sensors = pd.DataFrame.from_dict(
        dict_missing_sensors,
        orient="index",
        columns=["installation", "address", "sensor_name", "channel_name"],
    )
    df_missing_sensors = df_missing_sensors.drop_duplicates(subset=["sensor_name"])

    columns = ["Installation", "Sensor ID", "Sensor Name", "Snow fall", "Strong wind", "High temp", "Screen mode"]
    df_report = pd.DataFrame(columns=columns)

    dict_alert_time = format_timestamps_in_dict(dict_alert_time)

    # fill the report with the missing sensors dict, with one line per installation, and a list of the missing sensors
    for instal in dict_instal_json:
        df_report.loc[instal, ("Installation")] = instal
        df_report.loc[instal, ("Sensor ID")] = df_missing_sensors[
            df_missing_sensors["installation"] == instal
        ].address.to_list()
        df_report.loc[instal, ("Sensor Name")] = df_missing_sensors[
            df_missing_sensors["installation"] == instal
        ].sensor_name.to_list()
        df_report.loc[instal, ("Snow fall")] = dict_alert_time[instal]["Snow fall"]
        df_report.loc[instal, ("Strong wind")] = dict_alert_time[instal]["Strong wind"]
        df_report.loc[instal, ("High temp")] = dict_alert_time[instal]["High temperature"]
    df_report = df_report.reset_index(drop=True)

    #make a copy of the report dataframe to convert the lists to strings, so that it can be printed
    df_report_string = df_report.copy()

    # convert the lists to strings
    for col in df_report_string.columns:
        if col == "Installation":
            continue
        df_report_string[col] = df_report_string[col].apply(list_to_string)


    save_alerts_to_csv(df_report)

    print(tabulate(df_report_string, headers="keys", tablefmt="grid", showindex=False))
