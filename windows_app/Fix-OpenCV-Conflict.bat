@echo off
chcp 65001 >nul
title TABDIL - Fix OpenCV Conflict
cd /d "%~dp0"

echo ============================================================
echo   Fix OpenCV version conflict
echo   Fixes opencv 5.x requires numpy 2 and contrib missing
echo ============================================================
echo.

if exist ".venv\Scripts\python.exe" goto :status
echo [X] .venv not found - run Install.bat first
pause
exit /b 1

:status
set "PY=.venv\Scripts\python.exe"

echo Current status:
%PY% -c "import numpy, cv2; print('numpy', numpy.__version__, '| cv2', cv2.__version__)" 2>&1
%PY% -m pip list | findstr /i opencv

echo.
echo [1/4] Removing ALL opencv packages
%PY% -m pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless opencv-contrib-python-headless >nul 2>&1
%PY% -m pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless opencv-contrib-python-headless >nul 2>&1

echo [2/4] Re-installing numpy 1.26.4
%PY% -m pip install --only-binary=:all: --force-reinstall "numpy==1.26.4" --disable-pip-version-check
if not errorlevel 1 goto :opencv
echo *** Failed to install numpy 1.26.4
pause
exit /b 1

:opencv
echo [3/4] Installing opencv-contrib-python 4.11.0.86
%PY% -m pip install --only-binary=:all: --no-deps --force-reinstall "opencv-contrib-python==4.11.0.86" --disable-pip-version-check
if not errorlevel 1 goto :verify
echo Trying headless variant
%PY% -m pip install --only-binary=:all: --no-deps --force-reinstall "opencv-python-headless==4.11.0.86" --disable-pip-version-check

:verify
echo [4/4] Verifying
%PY% -c "import numpy, cv2; print('OK: numpy', numpy.__version__, '| cv2', cv2.__version__)"
if not errorlevel 1 goto :paddle
echo Still mismatch - trying again
%PY% -m pip install --only-binary=:all: --force-reinstall "numpy==1.26.4" --disable-pip-version-check
%PY% -m pip install --only-binary=:all: --no-deps --force-reinstall "opencv-contrib-python==4.11.0.86" --disable-pip-version-check

:paddle
%PY% -c "import paddleocr, paddle; print('paddleocr', paddleocr.__version__, 'OK')" 2>nul
if errorlevel 1 goto :no_paddle
echo [OK] PaddleOCR import works
goto :done

:no_paddle
echo [INFO] PaddleOCR not installed - run Install-PaddleOCR.bat

:done
echo.
echo ============================================================
echo   Done - this error is NOT related to VPN
echo   VPN only needed for PaddleOCR models from Baidu
echo   Now run Check-Installation.bat
echo ============================================================
pause
