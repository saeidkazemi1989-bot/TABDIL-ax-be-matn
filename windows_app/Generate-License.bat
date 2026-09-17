@echo off
chcp 65001 >nul
title TABDIL - Generate License
cd /d "%~dp0"

echo ============================================================
echo   TABDIL - Generate 1-Month License
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo .venv not found - running Install.bat first
  call "%~dp0Install.bat"
)

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo Generating 30-day license...
%PY% generate_license.py 30

echo.
echo Done - license files created:
dir /b license*.key license*.txt 2>nul

echo.
echo ============================================================
echo   License generated for 30 days
echo   File license.key is ready to use
echo   Give it to customer along with app
echo ============================================================
pause
