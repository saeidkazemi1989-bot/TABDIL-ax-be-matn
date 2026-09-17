@echo off
chcp 65001 >nul
title TABDIL
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto :start

echo First run - starting installation
call "%~dp0Install.bat"

:start
echo Starting TABDIL
".venv\Scripts\pythonw.exe" "run_app.py"
if not errorlevel 1 goto :end

echo.
echo App closed with error - running with console for details
echo If you see numpy/cv2 mismatch, run Install.bat again
echo If you see PaddleOCR download errors, need VPN or use Tesseract
echo.
".venv\Scripts\python.exe" "run_app.py"
echo.
echo If problem persists, run Check-Installation.bat and send output
pause

:end
