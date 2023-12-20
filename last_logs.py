from insolAPI.WebAPI import API
import simplejson as json
import pandas as pd
import pendulum as pdl
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings
from tqdm import tqdm
import sys
from tabulate import tabulate
from pytz import timezone



def last_logs(dict_instal, list_sensor, api):
    time_args = dict(
        start=pdl.yesterday().subtract(weeks=1).to_datetime_string(),
        stop=(pdl.now()).to_datetime_string(),
        timezone = timezone('Europe/Zurich')
    )


    logs_joined = {}
    dict_list_theoretical = {}
    for instal in tqdm(dict_instal):
        logs_joined[instal] = {}
        dict_list_theoretical[instal] = []
        sensor_number = 0
        for sensor_type in api.SensorsTypes:
            if str(sensor_type).split(".")[1] in list_sensor:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=UserWarning)
                    logs_joined[instal][list_sensor[sensor_number]] = api.get_sensor_channels_logs_joined(**time_args,sensor_type=sensor_type, install=dict_instal[instal]["id"])
                    sensor_number += 1
                    try:
                        theoretical_sensor = api.get_sensor_channels(sensor_type=sensor_type, install=dict_instal[instal]["id"])
                        theoretical_sensor = theoretical_sensor[theoretical_sensor["deleted_at"].isna()].sensor_name.unique()
                        dict_list_theoretical[instal].extend(theoretical_sensor)
                    except:
                        pass

    unique_sensors = {}
    logs_joined_unique = {}
    last_log = {}
    for instal in dict_instal:
        # print(instal)
        unique_sensors[instal] = []
        for sensor_type in logs_joined[instal]:
            try:
                unique_sensors[instal].extend(logs_joined[instal][sensor_type]["sensor_name"].unique())
            except :
                pass
        unique_sensors[instal] = list(set(unique_sensors[instal]))
        logs_joined_unique[instal] = {}
        for sensor_type in logs_joined[instal]:
            for unique_sensor in unique_sensors[instal]:
                try:
                    if unique_sensor in logs_joined[instal][sensor_type]["sensor_name"].unique():
                        logs_joined_unique[instal][unique_sensor] = logs_joined[instal][sensor_type].loc[logs_joined[instal][sensor_type]["sensor_name"] == unique_sensor]
                        logs_joined_unique[instal][unique_sensor].index = logs_joined_unique[instal][unique_sensor].index.round('min')
                        logs_joined_unique[instal][unique_sensor] = logs_joined_unique[instal][unique_sensor].loc[~logs_joined_unique[instal][unique_sensor].index.duplicated(keep='first')]
                except :
                    pass

        for sensor in logs_joined_unique[instal]:
            logs_joined_unique[instal][sensor] = logs_joined_unique[instal][sensor].dropna(subset=[logs_joined_unique[instal][sensor].columns[1]])

        last_log[instal] = {}
        for sensor in dict_list_theoretical[instal]:
            try:
                last_log[instal][sensor] = logs_joined_unique[instal][sensor].index[-1]
            except:
                last_log[instal][sensor] = "> 1 week"
            try:
                if last_log[instal][sensor] > pdl.now().subtract(minutes=10):
                    last_log[instal][sensor] = "Online"
            except:
                pass

    #sort the sensors by the last log
    for instal in last_log:
        last_log[instal] = {k: v for k, v in sorted(last_log[instal].items(), key=lambda item: item[1])}

    for i in last_log:
        print(i)
        # last_log[i] = {k: v for k, v in sorted(last_log[instal].items(), key=lambda item: item[1])}
        print(tabulate(last_log[i].items(), headers=["Sensor", "Last log"], tablefmt="psql"))
        print("\n")