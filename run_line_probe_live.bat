@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Install dependencies first with install_windows.bat
  pause
  exit /b 1
)
if "%~1"=="" (
  echo Drag your ACC fastlane.ai onto this .bat or run:
  echo run_line_probe_live.bat "C:\path\to\fastlane.ai"
  pause
  exit /b 2
)
echo WARNING: EXPERIMENTAL READ-ONLY GRAPHICS PROBE - NO HUD CHANGES.
echo Launch ACC and wait until the car is ON TRACK before continuing.
pause
".venv\Scripts\python.exe" line_probe_text.py --fastlane "%~1" --live --seconds 90
pause
