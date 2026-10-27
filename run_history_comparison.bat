@echo off
cd /d "%~dp0"
echo [ADVANCED TRAIL BRAKING 0.2.4 - OFFLINE SCORE COMPARISON]
echo This does not open ACC or access game memory.
if not exist ".venv\Scripts\python.exe" (
  echo Please run install_windows.bat first.
  pause
  exit /b 1
)
if exist "data\braking_history.jsonl" (
  ".venv\Scripts\python.exe" calibration_report.py "data\braking_history.jsonl" --out "calibration_reports\my_live_runs"
) else (
  echo No new 0.2.4 live events yet. Generating reference-only report.
)
".venv\Scripts\python.exe" calibration_report.py "reference_history\braking_history_20261020_003335.jsonl" --out "calibration_reports\reference_20261020"
if errorlevel 1 (
  echo The offline report encountered an error.
  pause
  exit /b 1
)
echo Reports saved in calibration_reports\. Source logs are not modified.
pause
