## Python environment

The script must be run from within the environment `insolinsights`

## To do before first execution

### Instal librairies

`conda activate insolinsights`

`pip install -r requirements.txt`

### Change the path to the local json file
In the `config/api_credits_path.json` file, change the path to where the "local.json" file is located (usually in the InsolReports/Scripts folder) so that the API can access the credits.

## How to run

- Double click on `FieldSentry.bat`. This will open a command prompt, and the result will be displayed here

OR

- Run directly from within a python IDE

OR

- Run the notebook named `Field_Sentry.ipynb`

## Editing the configuration

### Addition of an installation
Open the file `"config/config.json"` and add a new installation on the same template as the already existing ones

### Modification of weather alarm trigger levels
Open the file `"config/config.json"` and change the wind or high temperature levels

## Outout of the script
- The results of the main table are reported in a csv file named `log_reports.csv`, each time the script is executed. Go to the end of the file to see the last report.
- The main table presents the report for the weather, the sensors and the screens, with one row per installation.
	- The weather is checked for two days in the future.
	- The sensors are checked for the last 30 minutes. A sensor will be detected as faulty if it hasn't logged during the last half hour.
	- The screens are checked for the last two days. If the state is "auto" then nothing is displayed. All other states are displayed.
- After the main table you will be asked if you want to see the last log for each sensor. This will take about 1 minute to display. The result is displayed with one table per installation, one line per sensor, and the time of the last log if it is not up to date, and the time it has been offline for the last week. You have the choice to save these tables to an excel sheet. /!\ You might need to change the type of the columns to "Time" in excel to read properly the values.
