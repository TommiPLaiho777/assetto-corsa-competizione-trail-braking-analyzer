@echo off
cd /d "%~dp0"
echo [ADVANCED TRAIL BRAKING 0.2.5 - EXPERIMENTAL READ-ONLY LIVE]
echo CAUTION: ACC live compatibility is NOT YET VERIFIED on your Windows PC.
echo 1. Close ALL older Trail Braking windows.
echo 2. START ACC WITHOUT THIS APP and enter a loaded practice session.
echo 3. ONLY THEN start this app. Exit immediately if any game instability.
echo No Windows reboot required and no changes to Rhino automation jobs.
echo.
if not exist ".venv\Scripts\python.exe" (
  echo Please run install_windows.bat first.
  pause
  exit /b 1
)
choice /M "ACC is stable AND already on track. Start read-only test"
if errorlevel 2 exit /b 0
".venv\Scripts\python.exe" main.py --live
if errorlevel 1 pause
