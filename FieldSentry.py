# FieldSentry.py is a script that checks the status of the sensors, weather and screens of the installations
from insolAPI.WebAPI import API
import simplejson as json
import pandas as pd
import pendulum as pdl
from tqdm import tqdm
import warnings
import requests
import plotly.graph_objects as go
import os
import datetime
import sys
from tabulate import tabulate
from pytz import timezone
import last_logs as ll


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
    0: "",
    1: "Auto",
    2: "Manual",
    3: "Emergency",
    4: "Protection",
    5: "Demo",
    6: "Remote",
}



def read_json_config():
    """
    Read the config.json file and return the api key
    Parameters and response: https://openweathermap.org/forecast5
    """
    with open("config/config.json") as f:
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
    params = {"appid": api_data[0], "cnt": "20", "units": "metric"}

    params["lat"] = dict_instal[city_name]["latitude"]
    params["lon"] = dict_instal[city_name]["longitude"]

    try:
        response = requests.get(api_data[1], params=params)
        response.raise_for_status()
        data = response.json()

        update_request_count()
        return data

    except Exception as ex:
        # print(f" \n Error: {ex}")
        #generate an empty dict to avoid errors
        error_dict = {'list': [{'dt': 0,
                    'main': {'temp': 0,
                        'feels_like': 0,
                        'temp_min': 0,
                        'temp_max': 0,
                        'pressure': 0,
                        'sea_level': 0,
                        'grnd_level': 0,
                        'humidity': 0,
                        'temp_kf': 0},
                    'weather': [{'id': 0,
                        'main': 'Rain',
                        'description': 'light rain',
                        'icon': '10d'}],
                    'clouds': {'all': 0},
                    'wind': {'speed': 0, 'deg': 0, 'gust': 0},
                    'visibility': 0,
                    'pop': 0,
                    'rain': {'3h': 0},
                    'sys': {'pod': 'd'},
                    'dt_txt': '9999-01-01 00:00:00'}]}
        return error_dict  # noqa: E501



def plot_weather_forecast(weather_data, city_name):
    """
    If called, plot the weather forecast for the next 2 days
    """
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
    # if forecast["dt"] == 0:
    #     print("\nError: no weather data available")
    return alert_list



def update_request_count():
    """
    update the number of requests made to the API, and the number of requests made during the last hour
    """
    file_name = "reports/count_requests.csv"

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



def save_alerts_to_csv(df):
    """
    update the csv file with the alerts
    """
    df['Timestamp'] = datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')

    #replace \n with a ","
    df = df.replace('\n', ', ', regex=True)

    cols = df.columns.tolist()
    df = df[[cols[-1]] + cols[:-1]]


    #check if the file exists
    if not os.path.exists("reports/log_reports.csv"):
        df.to_csv("reports/log_reports.csv", index=False, header=True) # add the header if the file doesn't exist
    else:
        df.to_csv("reports/log_reports.csv", mode='a', header=False, index=False)
        with open("reports/log_reports.csv", "a") as file:
            file.write("\n")



def list_to_string(lst):
    """
    Convert a list to a string, to be able to print it
    """
    try:
        return "\n".join(map(str, lst))
    except Exception as e:
        pass



def process_screen_data(df):
    """
    logics to process the screen data
    """
    df = df[['screen_id', 'state', 'name']]
    screen_names = df['name'].unique()
    list_states = []
    for screen_name in screen_names:
        df_screen_tmp = df[df['name'] == screen_name]
        df_screen_tmp = df.sort_index(ascending=False)
        state = df_screen_tmp['state'][0]
        if state != 1:
            list_states.append(f"{screen_name}: {dict_screen_mode[state]}")
    if screen_names.size == 0:
        list_states.append("No logs for 2d+")
    return list_states


if __name__ == "__main__":
    try:
        with open("config/api_credits_path.json") as f:
            installation_path = json.load(f)["path"]

        # installation_path = "C:/Users/Insolight/Desktop/InsolReports/Installations/"
        with open(installation_path + "local.json") as f:
            local_data = json.load(f)

        api = API(local_data["API_user"], local_data["API_pwd"], dev_space=False)
        api.get_sensor_channels(sensor_type=api.SensorsTypes.TEMP, install=23)
        print("✅ Successfully connected to the API\nCollecting data...\n")
    except Exception as e:
        print(f"❌ {e}")
        print("\nExiting...")
        sys.stdout.flush()
        sys.exit(0)

    time_args = dict(
    start=pdl.now().subtract(days=0, hours=0, minutes=30).to_datetime_string(),
    stop=pdl.now().subtract(days=0, hours=0).to_datetime_string(),
    timezone=timezone('Europe/Zurich'),
    )
    time_args_screens = dict(
        start=pdl.now().subtract(days=2, hours=2, minutes=30).to_datetime_string(),
        stop=pdl.now().subtract(days=0, hours=2).to_datetime_string(),
        timezone=timezone('Europe/Zurich'),
    )

    # declarations of the dictionaries
    dict_instal_json, api_data = read_json_config()
    dict_instal_logs = {}  # type: dict
    dict_sensor_channel_id = {}  # type: dict
    diff_logs = {}  # type: dict
    dict_logs_joined = {}  # type: dict
    dict_channel_id = {}  # type: dict
    dict_missing_sensors = {}  # type: dict
    dict_weather_data = {} # type: dict
    dict_alerts = {} # type: dict
    dict_time_of_snow = {} # type: dict
    dict_time_of_wind = {} # type: dict
    dict_time_high_T = {} # type: dict
    dict_alert_time = {} # type: dict
    dict_screen_states = {} # type: dict

    #main loop
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
        list_screen_states = []


        # get the weather forecast for each installation
        dict_weather_data[instal] = get_weather_forecast(dict_instal_json, api_data, instal)
        if SHOW_PLOT:
            plot_weather_forecast(dict_weather_data[instal], instal)
        dict_alerts[instal] = alert_user(dict_weather_data[instal], dict_instal_json[instal])

        for i in range(0, len(dict_alerts[instal]), 2):
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
                dict_df_screen[instal] = api.get_screens_logs_joined(**time_args_screens, install=dict_instal_json[instal]["id"])
                list_screen_states = process_screen_data(dict_df_screen[instal])
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
                            dict_sensor_channel_id[instal][list_sensor[sensor_number]][dict_sensor_channel_id[instal][list_sensor[sensor_number]]["deleted_at"].isna()].index.tolist()
                        )
                except Exception as e:
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
        df_report.loc[instal, ("Screen mode")] = dict_screen_states[instal]
    df_report = df_report.reset_index(drop=True)

    #make a copy of the report dataframe to convert the lists to strings, so that it can be printed
    df_report_string = df_report.copy()

    # convert the lists to strings
    for col in df_report_string.columns:
        if col == "Installation":
            continue
        df_report_string[col] = df_report_string[col].apply(list_to_string)


    save_alerts_to_csv(df_report_string.copy())

    no_weather_data = ""
    loc_no_weather = ""
    for instal in dict_instal_json:
        if dict_weather_data[instal]["list"][0]["dt"] == 0:
            no_weather_data = "\n⚠️ no weather data available for "
            loc_no_weather = loc_no_weather + instal + ", "
    if len(no_weather_data) > 0:
        print(no_weather_data + loc_no_weather[:-2] + "\n")


    print(tabulate(df_report_string, headers="keys", tablefmt="grid", showindex=False))
    text_file = open("reports/output.txt", "w")
    text_file.write(str(pdl.now().strftime("%Y-%m-%d %Hh%M")) + "\n\n")
    text_file.write(tabulate(df_report_string, headers="keys", tablefmt="grid", showindex=False))
    text_file.write("\n\n")
    text_file.close()

    show_last_log = input("\nDo you want to see the last log? (y/n) ")
    if show_last_log == "y":
        ll.last_logs(dict_instal_json, list_sensor, api)
    else:
        print("\nExiting...")
