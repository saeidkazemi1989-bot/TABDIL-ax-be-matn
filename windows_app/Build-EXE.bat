@echo off
chcp 65001 >nul
title TABDIL - Build Windows EXE
cd /d "%~dp0"

echo ============================================================
echo   Building TABDIL.exe - one-folder build in dist\TABDIL
echo   Must be run ON WINDOWS. First run Install.bat if needed.
echo ============================================================
echo.

if exist ".venv\Scripts\python.exe" goto :build

echo Virtual environment not found - running Install.bat first
call "%~dp0Install.bat"

:build
".venv\Scripts\python.exe" -m pip install pyinstaller --disable-pip-version-check
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean TABDIL.spec
if not errorlevel 1 goto :done

echo.
echo *** Build failed
pause
exit /b 1

:done
echo.
echo ============================================================
echo   Done - app is at dist\TABDIL\TABDIL.exe
echo.
echo   NOTE: Tesseract OCR must also be installed on target PC
echo   Run Install.bat there or via winget:
echo     winget install -e --id UB-Mannheim.TesseractOCR --source winget
echo   Persian/English data is already bundled
echo.
echo   To make zip, compress dist\TABDIL
echo ============================================================
pause
