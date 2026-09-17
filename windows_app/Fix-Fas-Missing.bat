@echo off
chcp 65001 >nul
title TABDIL - Fix Persian Model
cd /d "%~dp0"

echo ============================================================
echo   TABDIL - رفع مشکل فارسی
echo   اگر خروجی خالی میده، این فایل را اجرا کنید
echo ============================================================
echo.

set "BUNDLED=%~dp0TABDIL\tessdata\fas.traineddata"
set "SYSTEM1=C:\Program Files\Tesseract-OCR\tessdata\fas.traineddata"
set "SYSTEM2=C:\Program Files (x86)\Tesseract-OCR\tessdata\fas.traineddata"

echo [INFO] بررسی فایل‌های موجود:
echo.
if exist "%BUNDLED%" (
    echo [OK] Bundled: %BUNDLED%
    dir "%BUNDLED%" | findstr /i fas
) else (
    echo [X] Bundled missing: %BUNDLED%
)
echo.
if exist "%SYSTEM1%" (
    echo [OK] System: %SYSTEM1%
    dir "%SYSTEM1%" | findstr /i fas
) else (
    echo [X] System missing: %SYSTEM1%
)
echo.
if exist "%SYSTEM2%" (
    echo [OK] System x86: %SYSTEM2%
) else (
    echo [X] System x86 missing: %SYSTEM2%
)

echo.
echo --- تلاش کپی از سیستمی به bundled ---
if exist "%SYSTEM1%" (
    if not exist "%~dp0TABDIL\tessdata" mkdir "%~dp0TABDIL\tessdata"
    copy /Y "%SYSTEM1%" "%BUNDLED%"
    echo [OK] کپی از System به Bundled انجام شد
) else if exist "%SYSTEM2%" (
    if not exist "%~dp0TABDIL\tessdata" mkdir "%~dp0TABDIL\tessdata"
    copy /Y "%SYSTEM2%" "%BUNDLED%"
    echo [OK] کپی از System x86 به Bundled انجام شد
) else (
    echo [X] هیچ فایل سیستمی پیدا نشد
)

echo.
echo --- تست سریع ---
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -c "from TABDIL.ocr import TesseractEngine; from TABDIL.util import TESSDATA_DIR; import os; print('TESSDATA_DIR:', TESSDATA_DIR); print('fas exists:', os.path.exists(os.path.join(TESSDATA_DIR, 'fas.traineddata'))); from TABDIL.ocr import _get_tessdata_candidates; print('candidates:', _get_tessdata_candidates())"
) else (
    python -c "from TABDIL.ocr import TesseractEngine; from TABDIL.util import TESSDATA_DIR; import os; print('TESSDATA_DIR:', TESSDATA_DIR); print('fas exists:', os.path.exists(os.path.join(TESSDATA_DIR, 'fas.traineddata')))"
)

echo.
echo [INFO] حالا Test-Tesseract.bat را اجرا کنید
echo.

pause
