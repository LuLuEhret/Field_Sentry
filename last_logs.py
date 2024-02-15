import pandas as pd
import pendulum as pdl
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import warnings
from tqdm import tqdm
from tabulate import tabulate
from pytz import timezone
import numpy as np
import datetime


def print_progress_bar(percentage, length=10):
    # print(percentage)
    if np.isnan(percentage):
        percentage = 1
    if percentage > 1:
        percentage = 1
    block = int(round(length * percentage))
    progress = "[" + "#" * block + "-" * (length - block) + "]"
    # print(f"\r{progress}", end="", flush=True)
    return progress


def last_logs(dict_instal, list_sensor, api):
    time_args = dict(
        start=pdl.now().subtract(weeks=1).to_datetime_string(),
        stop=(pdl.now()).to_datetime_string(),
        timezone = timezone('Europe/Zurich')
    )

    logs_joined = {}
    dict_list_theoretical = {}
    unique_sensors = {}
    logs_joined_unique = {}
    last_log = {}
    time_diff = {}
    print("\nCollecting data...\n")
    for instal in tqdm(dict_instal):
        logs_joined[instal] = {}
        dict_list_theoretical[instal] = []
        sensor_number = 0
        if dict_instal[instal]["id"] == "xx":
            continue
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

    print("\nProcessing data...\n")
    for instal in dict_instal:
        unique_sensors[instal] = []
        time_diff[instal] = {}
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


        for sensor in dict_list_theoretical[instal]:
            try:
                logs_joined_unique[instal][sensor] = logs_joined_unique[instal][sensor].dropna(subset=[logs_joined_unique[instal][sensor].columns[1]])
                time_serie = logs_joined_unique[instal][sensor].index.tz_localize(None)
                now = pd.to_datetime(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                now_serie = pd.Series(data=now, index=[now])

                time_serie.to_series()
                time_serie = pd.Series(time_serie)

                series = [time_serie, now_serie]
                time_series = pd.concat(series, ignore_index=True)
                time_difference = time_series.diff()
                time_difference = time_difference[time_difference > pd.Timedelta(minutes=2)].sum()
                time_diff[instal][sensor] = time_difference
            except:
                time_diff[instal][sensor] = pd.NaT

        last_log[instal] = {}
        for sensor in dict_list_theoretical[instal]:
            try:
                last_log[instal][sensor] = logs_joined_unique[instal][sensor].index[-1].strftime("%Y-%m-%d %Hh%M")
            except:
                last_log[instal][sensor] = "> 1 week"
            try:
                if logs_joined_unique[instal][sensor].index[-1] > pdl.now().subtract(minutes=10):
                    last_log[instal][sensor] = "Online"
            except:
                pass

    #make a df with the last log and the time difference for each sensor
    dict_df = {}
    for instal in last_log:
        dict_df[instal] = pd.DataFrame.from_dict(last_log[instal], orient="index", columns=["Last log"])
        dict_df[instal]["Time offline (1w)"] = dict_df[instal].index.map(time_diff[instal])
        try:
            dict_df[instal]["% offline"] = dict_df[instal]["Time offline (1w)"].apply(lambda x: print_progress_bar(x.total_seconds() / (7 * 24 * 60 * 60)))
        except:
            pass

    # #sort the sensors by the last log
    # for instal in last_log:
    #     last_log[instal] = {k: v for k, v in sorted(last_log[instal].items(), key=lambda item: item[1])}


    for instal, df in dict_df.items():
        # Sort the DataFrame by the "Last log" column
        df_sorted = df.sort_values(by=["Last log", "Time offline (1w)"], ascending=[True, False])

        print(f"{instal}")
        table = tabulate(df_sorted, headers="keys", tablefmt="psql", showindex=True)
        print(table)
        print("\n")

        with open("reports/output.txt", "a", encoding="utf-8") as text_file:
            text_file.write(f"{instal}\n")
            text_file.write(tabulate(df_sorted, headers="keys", tablefmt="psql", showindex=True))
            text_file.write("\n\n")

    print("Report saved as 'output.txt'\nEnd of script\n")

    # saving = input("Save table to excel file? (y/n)")
    # if saving == "y":
    #     writer = pd.ExcelWriter('reports/last_log.xlsx', engine='openpyxl')
    #     for instal, df in dict_df.items():
    #         df.to_excel(writer, sheet_name=instal)
    #     writer.close()
    #     print("File saved as 'last_log.xlsx'")
