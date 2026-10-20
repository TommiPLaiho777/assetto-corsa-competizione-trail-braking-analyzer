@echo off
cd /d "%~dp0"
echo [ADVANCED TRAIL BRAKING 0.2.4.1 – OFFLINE RAW REPLAY]
echo ACC is not accessed.
if not exist ".venv\Scripts\python.exe" (
  echo Run install_windows.bat first.
  pause
  exit /b 1
)
if not exist "data\raw_braking_events.jsonl" (
  echo No 0.2.4 raw events yet. Drive with 0.2.4 to create the file.
  pause
  exit /b 0
)
".venv\Scripts\python.exe" replay_raw.py "data\raw_braking_events.jsonl" --out "calibration_reports\replay_0241.csv"
if errorlevel 1 pause
