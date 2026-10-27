@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Install Python dependencies first with install_windows.bat.
  pause
  exit /b 1
)
if "%~1"=="" (
  echo Drag the original ACC Nurburgring 24h fastlane.ai file onto this BAT.
  echo The game file is validated and its path is stored; original file is not changed.
  pause
  exit /b 2
)
".venv\Scripts\python.exe" download_corner_metadata.py --fastlane "%~1"
if errorlevel 1 (
  echo Failed to register game file. Check that it is Nurburgring 24h fastlane.ai.
  pause
  exit /b 1
)
echo Done! Restart Advanced Trail Braking --live after ACC is on track.
pause
