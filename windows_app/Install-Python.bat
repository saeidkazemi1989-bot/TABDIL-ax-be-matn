@echo off
chcp 65001 >nul
title TABDIL - Install Python 3.11
cd /d "%~dp0"

echo ============================================================
echo   TABDIL - Install Python 3.11 Direct Download
echo   Use this if winget shows msstore timeout 12002
echo ============================================================
echo.

set "PYEXE="
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3.11"
if not defined PYEXE (
  py -3.12 -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PYEXE=py -3.12"
)
if not defined PYEXE (
  py -3.10 -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PYEXE=py -3.10"
)
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if defined PYEXE goto :already

echo Python not found - checking for local installer
set "LOCAL_PY="
if exist "%~dp0python-3.11.9-amd64.exe" set "LOCAL_PY=%~dp0python-3.11.9-amd64.exe"
if not defined LOCAL_PY if exist "%~dp0python-3.11*.exe" set "LOCAL_PY=%~dp0python-3.11.9-amd64.exe"
if not defined LOCAL_PY if exist "%TEMP%\python-setup.exe" set "LOCAL_PY=%TEMP%\python-setup.exe"

if defined LOCAL_PY goto :install_local

echo [1/2] Downloading Python 3.11.9 from python.org
powershell -NoProfile -ExecutionPolicy Bypass -Command "$url='https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'; $out=Join-Path $env:TEMP 'python-setup.exe'; Write-Host 'Downloading...'; try { Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing -TimeoutSec 180; Write-Host 'Downloaded'; exit 0 } catch { Write-Host 'Failed:' $_.Exception.Message; exit 1 }"

if not errorlevel 1 goto :dl_ok
echo Download failed - trying alternative
powershell -NoProfile -ExecutionPolicy Bypass -Command "$url='https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'; $out=Join-Path $env:TEMP 'python-setup.exe'; try { (New-Object System.Net.WebClient).DownloadFile($url, $out); Write-Host 'Downloaded'; exit 0 } catch { Write-Host 'Failed:' $_.Exception.Message; exit 1 }"

:dl_ok
if exist "%TEMP%\python-setup.exe" goto :install
echo.
echo *** Download failed - install manually from https://www.python.org/downloads/
echo *** Put python-3.11.9-amd64.exe in this folder and run again
echo *** %~dp0
pause
exit /b 1

:install_local
echo Found local installer: %LOCAL_PY%
set "PY_INSTALLER=%LOCAL_PY%"
goto :run_install

:install
set "PY_INSTALLER=%TEMP%\python-setup.exe"

:run_install
echo.
echo [2/2] Installing Python 3.11.9 quiet install
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
timeout /t 10 >nul

echo Checking
py -3.11 -c "import sys; print('Python', sys.version)" 2>nul
if not errorlevel 1 goto :success_ok
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" goto :success_ok
where python >nul 2>&1
if not errorlevel 1 goto :success_ok

echo Installation may need a moment - run Check-Installation.bat
pause
exit /b 0

:already
echo [OK] Python already installed: %PYEXE%
%PYEXE% -c "import sys; print(sys.version)"
pause
exit /b 0

:success_ok
echo [OK] Python 3.11 installed
del "%TEMP%\python-setup.exe" >nul 2>&1
goto :success

:success
echo.
echo ============================================================
echo   Python installed successfully
echo   Now run Install.bat to set up TABDIL environment
echo ============================================================
pause
exit /b 0
