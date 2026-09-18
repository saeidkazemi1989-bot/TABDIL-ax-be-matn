@echo off
chcp 65001 >nul
title TABDIL - Install PaddleOCR
cd /d "%~dp0"

echo ============================================================
echo   Installing PaddleOCR - optional high-accuracy engine
echo   Download size about 1 GB. Python 3.10-3.12 required.
echo   Fixes opencv 5.x / numpy 2.x conflicts automatically.
echo ============================================================
echo.

if exist ".venv\Scripts\python.exe" goto :check_ver
echo Virtual environment not found - run Install.bat first
pause
exit /b 1

:check_ver
set "PY=.venv\Scripts\python.exe"
%PY% -c "import sys; v=sys.version_info[:2]; sys.exit(0 if v[0]==3 and 10 <= v[1] <= 12 else 1)"
if not errorlevel 1 goto :pip_up
echo.
echo *** Unsupported Python version - need 3.10-3.12
echo *** Delete .venv folder and run Install.bat again
pause
exit /b 1

:pip_up
%PY% -c "import sys; print('Using Python', sys.version.split()[0])"
%PY% -m pip install --upgrade pip --disable-pip-version-check

echo.
echo [1/5] Cleaning old OpenCV packages including 5.x
%PY% -m pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless opencv-contrib-python-headless >nul 2>&1
%PY% -m pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless opencv-contrib-python-headless >nul 2>&1

echo.
echo [2/5] Installing numpy 1.26.4 compatible with paddleocr 2.8.1
%PY% -m pip install --only-binary=:all: --force-reinstall "numpy==1.26.4" --disable-pip-version-check
if not errorlevel 1 goto :paddle
echo *** Failed to install numpy 1.26.4
pause
exit /b 1

:paddle
echo.
echo [3/5] Installing paddlepaddle 2.x
%PY% -m pip install --only-binary=:all: "paddlepaddle>=2.6.0,<3.0" --disable-pip-version-check
if not errorlevel 1 goto :paddle_ok
echo PyPI failed - trying official PaddlePaddle index
%PY% -m pip install paddlepaddle==2.6.2 -f https://www.paddlepaddle.org.cn/whl/windows/mkl/avx/stable.html --disable-pip-version-check
if not errorlevel 1 goto :paddle_ok
echo *** paddlepaddle install failed - check internet
echo *** Lightweight Tesseract engine works without this step
pause
exit /b 1

:paddle_ok
echo.
echo [4/5] Installing paddleocr 2.8.1
%PY% -m pip install --only-binary=:all: --no-deps "paddleocr==2.8.1" --disable-pip-version-check
if not errorlevel 1 goto :deps
echo *** paddleocr install failed - check internet
pause
exit /b 1

:deps
echo Installing paddleocr dependencies without pulling opencv 5.x
%PY% -m pip install --only-binary=:all: --no-deps shapely scikit-image imgaug pyclipper lmdb tqdm rapidfuzz cython pyyaml beautifulsoup4 fonttools fire requests lxml --disable-pip-version-check 2>nul
%PY% -m pip install --only-binary=:all: shapely scikit-image imgaug pyclipper lmdb tqdm rapidfuzz cython pyyaml beautifulsoup4 fonttools fire requests lxml --disable-pip-version-check

echo.
echo [5/5] Fixing OpenCV - removing 5.x and installing 4.11.0.86
%PY% -m pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless opencv-contrib-python-headless >nul 2>&1
%PY% -m pip install --only-binary=:all: --force-reinstall "numpy==1.26.4" --disable-pip-version-check
%PY% -m pip install --only-binary=:all: --no-deps --force-reinstall "opencv-contrib-python==4.11.0.86" --disable-pip-version-check
if not errorlevel 1 goto :verify
echo contrib failed, trying headless
%PY% -m pip install --only-binary=:all: --no-deps --force-reinstall "opencv-python-headless==4.11.0.86" --disable-pip-version-check

:verify
echo.
echo Verifying
%PY% -c "import numpy, cv2; print('numpy', numpy.__version__, '| cv2', cv2.__version__)"
if not errorlevel 1 goto :verify2
echo Verification failed - fixing again
%PY% -m pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless opencv-contrib-python-headless >nul 2>&1
%PY% -m pip install --only-binary=:all: --force-reinstall "numpy==1.26.4" --disable-pip-version-check
%PY% -m pip install --only-binary=:all: --no-deps --force-reinstall "opencv-contrib-python==4.11.0.86" --disable-pip-version-check

:verify2
%PY% -c "import paddle; print('paddle', paddle.__version__)"
%PY% -c "import paddleocr; print('paddleocr', paddleocr.__version__)"

echo.
echo ============================================================
echo   Done
echo   In app select engine: accurate PaddleOCR
echo   First conversion downloads models - several minutes
echo   If in Iran, need VPN for first download from Baidu
echo   Or run Download-PaddleModels-GitHub.bat - no Baidu needed
echo   If VPN does not work, use light engine Tesseract offline
echo ============================================================
pause
exit /b 0
