@echo off
chcp 65001 >nul
title TABDIL - Install Tesseract OCR
cd /d "%~dp0"

echo ============================================================
echo   TABDIL - Install Tesseract OCR
echo   If msstore timeout 12002 happens, fallback to direct download
echo   or local installer file
echo ============================================================
echo.

set "TESS_EXE="
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set "TESS_EXE=C:\Program Files\Tesseract-OCR\tesseract.exe"
if not defined TESS_EXE if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" set "TESS_EXE=C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
if not defined TESS_EXE if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" set "TESS_EXE=%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"

if defined TESS_EXE goto :already

echo Tesseract not found - trying to install
echo.

REM ---------- Check for local installer manually downloaded ----------
echo [0/3] Checking for local installer file in this folder
set "LOCAL_INSTALLER="
if exist "%~dp0tesseract-ocr-w64-setup-5.5.0.20241111.exe" set "LOCAL_INSTALLER=%~dp0tesseract-ocr-w64-setup-5.5.0.20241111.exe"
if not defined LOCAL_INSTALLER if exist "%~dp0tesseract-ocr-w64-setup*.exe" set "LOCAL_INSTALLER=%~dp0tesseract-ocr-w64-setup-5.5.0.20241111.exe"
if not defined LOCAL_INSTALLER if exist "%~dp0tesseract-setup.exe" set "LOCAL_INSTALLER=%~dp0tesseract-setup.exe"
if not defined LOCAL_INSTALLER if exist "%TEMP%\tesseract-setup.exe" set "LOCAL_INSTALLER=%TEMP%\tesseract-setup.exe"

if not defined LOCAL_INSTALLER goto :winget_try

echo Found local installer: %LOCAL_INSTALLER%
echo Running installer - please accept UAC if asked
"%LOCAL_INSTALLER%" /SILENT
timeout /t 8 >nul
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" goto :direct_ok
echo Silent install may need more time, trying with UI
"%LOCAL_INSTALLER%"
timeout /t 5 >nul
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" goto :direct_ok
echo Local installer finished but not found at default path - checking PATH
where tesseract >nul 2>&1
if not errorlevel 1 goto :winget_ok
goto :manual

:winget_try
where winget >nul 2>&1
if errorlevel 1 goto :direct

echo [1/3] Trying winget with --source winget to avoid msstore timeout
winget install -e --id UB-Mannheim.TesseractOCR --source winget --accept-package-agreements --accept-source-agreements
if not errorlevel 1 goto :check_winget
echo        First try failed, trying without source filter
winget install -e --id UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements

:check_winget
timeout /t 3 >nul
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" goto :winget_ok
where tesseract >nul 2>&1
if not errorlevel 1 goto :winget_ok
echo winget finished but tesseract.exe not found - trying direct download
goto :direct

:winget_ok
echo [OK] Installed via winget
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
where tesseract >nul 2>&1
if not errorlevel 1 tesseract --version
goto :success

:direct
echo.
echo [2/3] Trying direct download from GitHub
echo        This uses GitHub which works in Iran
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$url='https://github.com/UB-Mannheim/tesseract/releases/download/v5.5.0.20241111/tesseract-ocr-w64-setup-5.5.0.20241111.exe'; $out=Join-Path $env:TEMP 'tesseract-setup.exe'; Write-Host 'Downloading Tesseract installer from GitHub...'; try { Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing -TimeoutSec 180; Write-Host 'Downloaded'; exit 0 } catch { Write-Host 'Failed:' $_.Exception.Message; exit 1 }"

if errorlevel 1 goto :manual
if not exist "%TEMP%\tesseract-setup.exe" goto :manual

echo.
echo Installer downloaded - running silent install, please accept UAC if asked
"%TEMP%\tesseract-setup.exe" /SILENT
timeout /t 8 >nul
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" goto :direct_ok

echo Silent install may need more time or admin rights
echo Trying with UI
"%TEMP%\tesseract-setup.exe"
timeout /t 5 >nul
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" goto :direct_ok
goto :manual

:direct_ok
echo [OK] Installed via direct download
"C:\Program Files\Tesseract-OCR\tesseract.exe" --version
del "%TEMP%\tesseract-setup.exe" >nul 2>&1
goto :success

:manual
echo.
echo [3/3] Automatic install failed
echo.
echo Please install manually - you already downloaded the file:
echo.
echo 1. If you downloaded tesseract-ocr-w64-setup-5.5.0.20241111.exe
echo    Put it in same folder as Install-Tesseract.bat:
echo    %~dp0
echo    Then run Install-Tesseract.bat again - it will detect and use it
echo.
echo 2. Or double-click the exe directly and install to:
echo    C:\Program Files\Tesseract-OCR\
echo    Keep default options, make sure Persian + English checked
echo.
echo 3. After install, run Check-Installation.bat to verify
echo 4. If app still says not found, it will ask to browse for tesseract.exe
echo.
echo Link: https://github.com/UB-Mannheim/tesseract/wiki
echo Direct: https://github.com/UB-Mannheim/tesseract/releases/download/v5.5.0.20241111/tesseract-ocr-w64-setup-5.5.0.20241111.exe
echo.
pause
exit /b 1

:already
echo [OK] Tesseract already installed at %TESS_EXE%
"%TESS_EXE%" --version
echo.
pause
exit /b 0

:success
echo.
echo ============================================================
echo   Tesseract installed successfully
echo   Run Run-TABDIL.bat - light engine should be OK
echo   For diagnostics run Check-Installation.bat
echo ============================================================
pause
exit /b 0
