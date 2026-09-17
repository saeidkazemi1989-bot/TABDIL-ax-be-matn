@echo off
chcp 65001 >nul
title TABDIL - Check Installation
cd /d "%~dp0"

echo ============================================================
echo   TABDIL - Installation Diagnostics
echo ============================================================
echo.

if exist ".venv\Scripts\python.exe" goto :venv_ok
echo [X] Virtual environment NOT found at .venv
echo     Run Install.bat first
goto :end

:venv_ok
echo [OK] Virtual environment found
set "PY=.venv\Scripts\python.exe"

echo.
echo --- Python version ---
%PY% -c "import sys; print(sys.version)"

echo.
echo --- Core packages ---
%PY% -c "import numpy, cv2, PIL, customtkinter, pytesseract; print('numpy', numpy.__version__); print('cv2', cv2.__version__); print('Pillow', PIL.__version__); print('customtkinter', customtkinter.__version__); print('pytesseract OK')"
if errorlevel 1 goto :core_fail
echo [OK] Core packages OK
goto :opencv_check

:core_fail
echo [X] Core packages check failed
goto :opencv_check

:opencv_check
echo.
echo --- OpenCV / Numpy conflict check ---
%PY% -c "import numpy, cv2; print('numpy', numpy.__version__, '| cv2', cv2.__version__)"
%PY% -m pip list | findstr /i opencv
%PY% -m pip list | findstr /i numpy

echo.
echo --- Tesseract OCR ---
set "TESS_FOUND=0"
where tesseract >nul 2>&1
if errorlevel 1 goto :tess_progfiles
echo [OK] Tesseract found in PATH
tesseract --version
set "TESS_FOUND=1"
goto :tess_after

:tess_progfiles
if not exist "C:\Program Files\Tesseract-OCR\tesseract.exe" goto :tess_x86
echo [OK] Tesseract found at C:\Program Files\Tesseract-OCR\tesseract.exe
"C:\Program Files\Tesseract-OCR\tesseract.exe" --version
set "TESS_FOUND=1"
goto :tess_after

:tess_x86
if not exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" goto :tess_local
echo [OK] Tesseract found at C:\Program Files ^(x86^)\Tesseract-OCR\tesseract.exe
"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" --version
set "TESS_FOUND=1"
goto :tess_after

:tess_local
if not exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" goto :tess_bundled
echo [OK] Tesseract found at LOCALAPPDATA
"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" --version
set "TESS_FOUND=1"
goto :tess_after

:tess_bundled
if not exist "tesseract\tesseract.exe" goto :tess_custom1
echo [OK] Tesseract found at tesseract\tesseract.exe
"%~dp0tesseract\tesseract.exe" --version
set "TESS_FOUND=1"
goto :tess_after

:tess_custom1
if not exist "TABDIL\tesseract_path.txt" goto :tess_custom2
echo [INFO] Custom path file exists: TABDIL\tesseract_path.txt
type "TABDIL\tesseract_path.txt"
echo.

:tess_custom2
if not exist "tesseract_path.txt" goto :tess_final
echo [INFO] Custom path file exists: tesseract_path.txt
type "tesseract_path.txt"
echo.

:tess_final
if "%TESS_FOUND%"=="1" goto :tess_after
echo [X] Tesseract NOT found
echo     Solutions:
echo     1. Run Install-Tesseract.bat
echo     2. Or install manually from https://github.com/UB-Mannheim/tesseract/wiki
echo     3. App will ask to browse for tesseract.exe if needed

:tess_after
echo.
echo --- Tessdata Persian ---
if exist "TABDIL\tessdata\fas.traineddata" goto :tessdata_ok
echo [X] fas.traineddata missing
goto :paddle_check

:tessdata_ok
echo [OK] fas.traineddata bundled

:paddle_check
echo.
echo --- PaddleOCR optional ---
%PY% -c "import paddleocr; print('paddleocr', paddleocr.__version__)" 2>nul
if not errorlevel 1 goto :paddle_ok
echo [INFO] PaddleOCR not installed - optional, Tesseract works offline
goto :app_check

:paddle_ok
%PY% -c "import paddleocr, paddle, numpy, cv2; print('paddleocr', paddleocr.__version__); print('paddle', paddle.__version__); print('numpy', numpy.__version__); print('cv2', cv2.__version__)"
%PY% -c "import pathlib; home=pathlib.Path.home(); p=home/'.paddleocr'; print('Model folder exists:', p.exists(), 'at', p)"
%PY% -c "import paddleocr" 2>nul
if not errorlevel 1 goto :paddle_import_ok
echo [X] PaddleOCR import failed - version mismatch
echo     Try Fix-OpenCV-Conflict.bat or Install-PaddleOCR.bat again
goto :app_check

:paddle_import_ok
echo [OK] PaddleOCR import OK
echo      If models not downloaded yet, run Download-PaddleModels-GitHub.bat

:app_check
echo.
echo --- App import test ---
%PY% -c "import TABDIL.app, TABDIL.ocr, TABDIL.preprocess, TABDIL.table; print('[OK] All TABDIL modules import OK')"
if not errorlevel 1 goto :diag_done
echo [X] TABDIL modules import failed

:diag_done
echo.
echo ============================================================
echo   Diagnostics complete
echo   If Tesseract is OK, app should work in light mode
echo   For accurate mode, ensure PaddleOCR models downloaded
echo ============================================================

:end
pause
