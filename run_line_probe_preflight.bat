@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run install_windows.bat
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m unittest tests.test_line_reference_research -v
pause
