@echo off
chcp 65001 >nul
title TABDIL - Download Best Persian Model
cd /d "%~dp0"

echo ============================================================
echo   TABDIL - دانلود بهترین مدل فارسی Tesseract
echo   اگر خروجی خالی میده، این مدل دقیق‌تر را دانلود کنید
echo ============================================================
echo.

set "TESSDATA_DIR=%~dp0TABDIL\tessdata"
if not exist "%TESSDATA_DIR%" mkdir "%TESSDATA_DIR%"

echo [INFO] پوشه tessdata: %TESSDATA_DIR%
echo.

echo [1/3] تلاش دانلود با PowerShell (GitHub)...
powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata_best/raw/main/fas.traineddata' -OutFile '%TESSDATA_DIR%\fas.traineddata.best' -UseBasicParsing; Write-Host '[OK] دانلود best موفق'; } catch { Write-Host '[X] دانلود best شکست:' $_.Exception.Message } }"

if exist "%TESSDATA_DIR%\fas.traineddata.best" (
    echo.
    echo [OK] فایل best دانلود شد، جایگزین می‌شود...
    copy /Y "%TESSDATA_DIR%\fas.traineddata.best" "%TESSDATA_DIR%\fas.traineddata"
    del "%TESSDATA_DIR%\fas.traineddata.best"
    goto :check
)

echo.
echo [2/3] تلاش دانلود fast (سبک‌تر)...
powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata_fast/raw/main/fas.traineddata' -OutFile '%TESSDATA_DIR%\fas.traineddata.fast' -UseBasicParsing; Write-Host '[OK] دانلود fast موفق'; } catch { Write-Host '[X] دانلود fast شکست:' $_.Exception.Message } }"

if exist "%TESSDATA_DIR%\fas.traineddata.fast" (
    echo.
    echo [OK] فایل fast دانلود شد
    copy /Y "%TESSDATA_DIR%\fas.traineddata.fast" "%TESSDATA_DIR%\fas.traineddata"
    del "%TESSDATA_DIR%\fas.traineddata.fast"
    goto :check
)

echo.
echo [3/3] تلاش دانلود از tessdata اصلی...
powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata/raw/main/fas.traineddata' -OutFile '%TESSDATA_DIR%\fas.traineddata.main' -UseBasicParsing; Write-Host '[OK] دانلود main موفق'; } catch { Write-Host '[X] دانلود main شکست:' $_.Exception.Message } }"

if exist "%TESSDATA_DIR%\fas.traineddata.main" (
    copy /Y "%TESSDATA_DIR%\fas.traineddata.main" "%TESSDATA_DIR%\fas.traineddata"
    del "%TESSDATA_DIR%\fas.traineddata.main"
    goto :check
)

echo.
echo [X] همه دانلودها شکست خورد
echo     ممکن است اینترنت یا فیلتر باشد
echo     راه‌حل دستی:
echo     1. مرورگر را باز کنید
echo     2. به آدرس بروید: https://github.com/tesseract-ocr/tessdata_best
echo     3. فایل fas.traineddata را دانلود کنید
echo     4. در پوشه %TESSDATA_DIR% بریزید
echo.
goto :end

:check
echo.
echo --- بررسی فایل ---
dir "%TESSDATA_DIR%\fas.traineddata"
echo.
echo [INFO] همچنین در مسیر سیستمی Tesseract چک کنید:
if exist "C:\Program Files\Tesseract-OCR\tessdata\fas.traineddata" (
    echo [OK] C:\Program Files\Tesseract-OCR\tessdata\fas.traineddata وجود دارد
    dir "C:\Program Files\Tesseract-OCR\tessdata\fas.traineddata"
) else (
    echo [X] C:\Program Files\Tesseract-OCR\tessdata\fas.traineddata وجود ندارد
    echo     فایل را دستی کپی کنید:
    echo     copy "%TESSDATA_DIR%\fas.traineddata" "C:\Program Files\Tesseract-OCR\tessdata\"
)

echo.
echo [OK] تمام شد - حالا Test-Tesseract.bat را اجرا کنید
echo.

:end
pause
