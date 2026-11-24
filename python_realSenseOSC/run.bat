@echo off
rem Quick launcher for Windows (double-click)
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv || goto :err
  .venv\Scripts\pip install -r requirements.txt || goto :err
)
.venv\Scripts\python realsense_osc.py %*
if errorlevel 1 goto :err
exit /b 0
:err
pause
