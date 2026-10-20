@echo off
cd /d "%~dp0"
echo [ADVANCED TRAIL BRAKING 0.2.4] Private Python environment
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher missing. Install Python 3.11 or 3.12 x64 first.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 (
    echo Could not create private environment. No system packages changed.
    pause
    exit /b 1
  )
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed. Other Python environments unchanged.
  pause
  exit /b 1
)
echo.
echo Installation complete. Run run_windows.bat for safe offline demo.
pause
