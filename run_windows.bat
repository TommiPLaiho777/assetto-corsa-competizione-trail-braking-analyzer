@echo off
cd /d "%~dp0"
echo [ADVANCED TRAIL BRAKING 0.3.5.2 - OFFLINE DEMO]
echo This mode NEVER connects to ACC and can run with ACC closed.
if not exist ".venv\Scripts\python.exe" (
  echo Please run install_windows.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py --demo
if errorlevel 1 pause
