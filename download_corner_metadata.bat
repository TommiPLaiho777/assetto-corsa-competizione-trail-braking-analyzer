@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Install Python dependencies first with install_windows.bat.
  pause
  exit /b 1
)
echo Downloading optional Nürburgring corner metadata from the independent RaceIQ project.
echo This does not change ACC or the existing Mini HUD timing.
".venv\Scripts\python.exe" download_corner_metadata.py --download
if errorlevel 1 (
  echo Download failed. Check internet connection and try again; no live data changes.
  pause
  exit /b 1
)
echo Download completed. Next: drag your ACC fastlane.ai onto configure_fastlane.bat
pause
