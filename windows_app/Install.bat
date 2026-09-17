@echo off
chcp 65001 >nul
title TABDIL - Installer
cd /d "%~dp0"

echo ============================================================
echo   TABDIL - Image to Excel / Word   Installer
echo ============================================================
echo   If winget shows msstore timeout 12002, fallback to
echo   direct download will be used automatically.
echo   Supports local installer files in this folder.
echo ============================================================
echo.

REM ---------- Find Python ----------
set "PYEXE="

py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3.12"

if defined PYEXE goto :found_py
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3.11"

:found_py
if defined PYEXE goto :found_py2
py -3.10 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3.10"

:found_py2
if defined PYEXE goto :found_py3
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

:found_py3
if defined PYEXE goto :found_py4
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

:found_py4
if defined PYEXE goto :found_py5
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"

:found_py5
if defined PYEXE goto :python_ok
where python >nul 2>&1
if not errorlevel 1 set "PYEXE=python"

if defined PYEXE goto :python_ok

echo [1/5] Compatible Python not found - trying to install
REM Check local installer first
if exist "%~dp0python-3.11.9-amd64.exe" goto :python_local
if exist "%~dp0python-3.11*.exe" goto :python_local
if exist "%TEMP%\python-setup.exe" goto :python_local2

where winget >nul 2>&1
if errorlevel 1 goto :python_direct

echo        Trying winget with --source winget to avoid msstore timeout
winget install -e --id Python.Python.3.11 --source winget --scope user --accept-package-agreements --accept-source-agreements
if not errorlevel 1 goto :python_check_winget
echo        First try failed, trying without source filter
winget install -e --id Python.Python.3.11 --scope user --accept-package-agreements --accept-source-agreements

:python_check_winget
timeout /t 3 >nul
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if defined PYEXE goto :python_ok
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3.11"
if defined PYEXE goto :python_ok
goto :python_direct

:python_local
echo        Found local Python installer in this folder
if exist "%~dp0python-3.11.9-amd64.exe" set "PY_INSTALLER=%~dp0python-3.11.9-amd64.exe"
if not defined PY_INSTALLER if exist "%~dp0python-3.11*.exe" set "PY_INSTALLER=%~dp0python-3.11.9-amd64.exe"
goto :python_run_installer

:python_local2
set "PY_INSTALLER=%TEMP%\python-setup.exe"
goto :python_run_installer

:python_direct
echo        winget failed - trying direct download from python.org
REM Check local again
if exist "%~dp0python-3.11.9-amd64.exe" (
  set "PY_INSTALLER=%~dp0python-3.11.9-amd64.exe"
  goto :python_run_installer
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$url='https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'; $out=Join-Path $env:TEMP 'python-setup.exe'; Write-Host 'Downloading Python 3.11.9...'; try { Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing -TimeoutSec 180; Write-Host 'Downloaded'; exit 0 } catch { Write-Host 'Failed:' $_.Exception.Message; exit 1 }"
if exist "%TEMP%\python-setup.exe" set "PY_INSTALLER=%TEMP%\python-setup.exe"
if not defined PY_INSTALLER goto :python_manual

:python_run_installer
echo        Installing Python from %PY_INSTALLER%
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
timeout /t 8 >nul
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3.11"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if defined PYEXE goto :python_ok
goto :python_manual

:python_manual
echo.
echo *** Automatic Python install failed
echo *** Please install manually:
echo *** 1. Download from https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
echo ***    Put file in this folder: %~dp0
echo ***    Then run Install.bat again - it will auto-detect
echo *** 2. Or download from python.org and during install TICK Add to PATH
echo *** 3. Or run Install-Python.bat
pause
exit /b 1

:python_ok
echo [1/5] Python OK - %PYEXE%
%PYEXE% -c "import sys; print('Python version:', sys.version.split()[0])"

REM ---------- Venv ----------
if not exist ".venv\Scripts\python.exe" goto :create_venv

REM Check venv python version is 3.10-3.12
".venv\Scripts\python.exe" -c "import sys; v=sys.version_info[:2]; sys.exit(0 if v[0]==3 and 10 <= v[1] <= 12 else 1)"
if not errorlevel 1 goto :venv_exists
echo Recreating venv with supported Python version
rmdir /s /q .venv

:create_venv
echo [2/5] Creating virtual environment
%PYEXE% -m venv .venv
if not errorlevel 1 goto :venv_exists
echo Failed, trying without pip
%PYEXE% -m venv .venv --without-pip
".venv\Scripts\python.exe" -m ensurepip 2>nul

:venv_exists
echo [2/5] Installing packages - please wait
".venv\Scripts\python.exe" -m pip install --upgrade pip --disable-pip-version-check
if errorlevel 1 echo Warning pip upgrade failed

".venv\Scripts\python.exe" -m pip install -r requirements.txt --disable-pip-version-check
if not errorlevel 1 goto :verify_core
echo *** Package install failed - check internet
pause
exit /b 1

:verify_core
echo [3/5] Verifying core packages
".venv\Scripts\python.exe" -c "import numpy, cv2; print('numpy', numpy.__version__, '| cv2', cv2.__version__)"
if not errorlevel 1 goto :tesseract_check
echo Fixing versions
".venv\Scripts\python.exe" -m pip install --force-reinstall "numpy==1.26.4" --disable-pip-version-check
".venv\Scripts\python.exe" -m pip install --no-deps --force-reinstall "opencv-python-headless==4.11.0.86" --disable-pip-version-check

:tesseract_check
echo [4/5] Checking Tesseract OCR
set "TESS_FOUND=0"
where tesseract >nul 2>&1
if not errorlevel 1 set "TESS_FOUND=1"
if "%TESS_FOUND%"=="0" if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set "TESS_FOUND=1"
if "%TESS_FOUND%"=="0" if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" set "TESS_FOUND=1"
if "%TESS_FOUND%"=="0" if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" set "TESS_FOUND=1"

if "%TESS_FOUND%"=="1" goto :tess_ok
echo [4/5] Tesseract not found - trying install
REM Check local installer first
if exist "%~dp0tesseract-ocr-w64-setup-5.5.0.20241111.exe" goto :tesseract_direct
if exist "%~dp0tesseract-ocr-w64-setup*.exe" goto :tesseract_direct
where winget >nul 2>&1
if errorlevel 1 goto :tesseract_direct

echo        Trying winget with --source winget
winget install -e --id UB-Mannheim.TesseractOCR --source winget --accept-package-agreements --accept-source-agreements
if not errorlevel 1 goto :tess_check2
echo        Trying winget without source filter
winget install -e --id UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements

:tess_check2
timeout /t 5 >nul
where tesseract >nul 2>&1
if not errorlevel 1 set "TESS_FOUND=1"
if "%TESS_FOUND%"=="0" if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set "TESS_FOUND=1"
if "%TESS_FOUND%"=="1" goto :tess_ok

:tesseract_direct
echo        winget failed or local installer found - running Install-Tesseract.bat
call "%~dp0Install-Tesseract.bat"
where tesseract >nul 2>&1
if not errorlevel 1 set "TESS_FOUND=1"
if "%TESS_FOUND%"=="0" if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set "TESS_FOUND=1"

if "%TESS_FOUND%"=="0" goto :tess_missing
echo [4/5] Tesseract OK
goto :shortcut

:tess_missing
echo        Tesseract still not found - you can still use app
echo        App will ask to browse for tesseract.exe if needed
echo        Or install manually from https://github.com/UB-Mannheim/tesseract/wiki
goto :shortcut

:tess_ok
echo [4/5] Tesseract OK - already installed

:shortcut
echo [5/5] Creating desktop shortcut
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\TABDIL.lnk'); $s.TargetPath='%~dp0Run-TABDIL.bat'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%~dp0TABDIL\assets\logo.ico,0'; $s.Description='TABDIL'; $s.Save()" 2>nul

echo.
echo ============================================================
echo   Done
echo   Run Run-TABDIL.bat or desktop icon
echo   To verify run Check-Installation.bat
echo.
echo   If msstore timeout 12002 happened
echo   It is normal in Iran - fallback to direct download used
echo   If still not installed
echo   - Put installer exe in this folder and run again
echo   - Run Install-Python.bat
echo   - Run Install-Tesseract.bat
echo.
echo   If Tesseract still NOT found
echo   App will ask to browse for tesseract.exe manually
echo.
echo   Optional accurate engine
echo   Run Install-PaddleOCR.bat
echo   Or Download-PaddleModels-GitHub.bat - no Baidu needed
echo ============================================================
pause
exit /b 0
