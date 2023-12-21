## Python environment

insolinsights

## To do before first execution

### Instal librairies

- tabulate  
- tqdm  

`conda activate insolinsights`    
`pip install tabulate`  
`pip install tqdm`  

### Change the path to the local json file 
In the file `config/api_credits_path.json`, change the path to where is located the file named "local.json" (usually in the folder InsolReports/Scripts)

## How to run

Double click on `FieldSentry.bat`, or run directly from within a python IDE

## Editing the configuration

### Addition of an installation
Open the file `"config/config.json"` and add a new installation on the same template as the already existing ones

### Modification of weather alarm trigger levels
Open the file `"config/config.json"` and change the wind or high temperature levels

## Results
- The results of the main table are reported in a csv file named `log_reports.csv`, each time the script is executed. 
- The main table presents the report for the weather, the sensors and the screens, with one row per installation. 
	- The weather is checked for two days in the future. 
	- The sensors are checked for the last 30 minutes. A sensor will be detected as faulty if it hasn't logged during the last half hour. 
	- The screens are checked for the last two days. If the state is "auto" then nothing is displayed. All other states are displayed. 
