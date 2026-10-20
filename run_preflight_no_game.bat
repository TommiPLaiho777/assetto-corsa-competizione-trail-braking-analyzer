@echo off
cd /d "%~dp0"
echo [0.2.4.1] Offline safety checks - ACC should be CLOSED.
if not exist ".venv\Scripts\python.exe" (
  echo Run install_windows.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 (
  echo FAILED. Do NOT attempt live ACC integration.
  pause
  exit /b 1
)
echo All offline checks passed. This does not prove Windows/ACC live compatibility.
pause
