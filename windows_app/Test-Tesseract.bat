@echo off
chcp 65001 >nul
title TABDIL - Test Tesseract Direct
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    echo Running with venv...
    .venv\Scripts\python.exe Test-Tesseract-Direct.py %*
) else (
    echo Running with system python...
    python Test-Tesseract-Direct.py %*
)
pause
