@echo off
chcp 65001 >nul
title TABDIL - Fix Tesseract PATH
cd /d "%~dp0"

echo ============================================================
echo   TABDIL - رفع خطای tesseract is not installed
echo ============================================================
echo.

echo [INFO] بررسی مسیر Tesseract...

set "TESS_EXE=C:\Program Files\Tesseract-OCR\tesseract.exe"
if exist "%TESS_EXE%" (
    echo [OK] پیدا شد: %TESS_EXE%
    goto :found
)

set "TESS_EXE=C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
if exist "%TESS_EXE%" (
    echo [OK] پیدا شد: %TESS_EXE%
    goto :found
)

set "TESS_EXE=%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"
if exist "%TESS_EXE%" (
    echo [OK] پیدا شد: %TESS_EXE%
    goto :found
)

echo [X] Tesseract پیدا نشد!
echo     Install-Tesseract.bat را اجرا کنید
pause
exit /b 1

:found
echo.
echo [INFO] تنظیم PATH و ذخیره مسیر...

:: ذخیره مسیر برای برنامه
echo %TESS_EXE% > "%~dp0TABDIL\tesseract_path.txt"
echo %TESS_EXE% > "%~dp0tesseract_path.txt"
echo %TESS_EXE% > "%USERPROFILE%\.tabdil_tesseract_path.txt"

echo [OK] مسیر ذخیره شد در:
echo      %~dp0TABDIL\tesseract_path.txt
echo      %~dp0tesseract_path.txt
echo      %USERPROFILE%\.tabdil_tesseract_path.txt

echo.
echo [INFO] افزودن به PATH موقت...

set "TESS_DIR=%~dp0TABDIL\tessdata"
if not exist "%TESS_DIR%" mkdir "%TESS_DIR%"

:: تست با venv
if exist ".venv\Scripts\python.exe" (
    echo [INFO] تست با venv...
    .venv\Scripts\python.exe -c "import pytesseract; pytesseract.pytesseract.tesseract_cmd = r'%TESS_EXE%'; print(pytesseract.image_to_string(r'%~dp0..\IMG_20260909_094503.jpg', lang='eng', config='--psm 6')[:100])"
) else (
    python -c "import pytesseract; pytesseract.pytesseract.tesseract_cmd = r'%TESS_EXE%'; print('test')"
)

echo.
echo [INFO] حالا Test-Tesseract.bat را اجرا کنید
echo [INFO] و سپس برنامه اصلی Run-TABDIL.bat
echo.

pause
