@echo off

set conda_environment=insolinsights

rem Activate the Conda environment
call conda activate %conda_environment%

python FieldSentry.py

rem Deactivate the Conda environment (optional)
call conda deactivate

cmd /k
