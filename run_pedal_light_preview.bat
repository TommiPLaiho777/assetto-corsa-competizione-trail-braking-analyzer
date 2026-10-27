@echo off
cd /d "%~dp0"
echo [PEDAL OVERLAP LIGHT] OFFLINE UI preview. ACC must remain CLOSED.
echo This test NEVER attaches to ACC and NEVER creates a named memory section.
if not exist ".venv\Scripts\python.exe" (
 echo Run install_windows.bat first.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" pedal_light_preview.py
if errorlevel 1 pause
