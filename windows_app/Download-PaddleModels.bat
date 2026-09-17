@echo off
chcp 65001 >nul
title TABDIL - Download PaddleOCR Models
cd /d "%~dp0"

echo ============================================================
echo   TABDIL - Download PaddleOCR models - first-time setup
echo   This needs VPN in Iran - models are from Baidu servers
echo ============================================================
echo.

if exist ".venv\Scripts\python.exe" goto :check_paddle
echo Virtual environment not found - run Install.bat first
pause
exit /b 1

:check_paddle
set "PY=.venv\Scripts\python.exe"
%PY% -c "import paddleocr" >nul 2>&1
if not errorlevel 1 goto :status
echo PaddleOCR not installed - run Install-PaddleOCR.bat first
pause
exit /b 1

:status
echo Checking current model status
%PY% -c "import os; home=os.path.expanduser('~'); import pathlib; p=pathlib.Path(home)/'.paddleocr'; print('Exists:', p.exists(), 'at', p)"
echo.
echo This will download 200-400 MB of models
echo If you are in Iran, please turn on VPN before continuing
echo.
set /p VPN="VPN is ON? y/n: "
if /i "%VPN%"=="y" goto :dl
echo Please turn on VPN and run again
pause
exit /b 0

:dl
echo.
echo [1/2] Downloading detection + recognition models for arabic
echo This may take several minutes
%PY% - <<PYEOF
import os, sys
if getattr(sys, "stdout", None) is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if getattr(sys, "stderr", None) is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
os.environ["TQDM_DISABLE"]="0"
try:
    from paddleocr import PaddleOCR
    print("Initializing PaddleOCR lang=arabic - downloading if needed")
    ocr = PaddleOCR(lang="arabic", show_log=True, use_angle_cls=True)
    print("Arabic model ready")
    print("Initializing English model")
    ocr_en = PaddleOCR(lang="en", show_log=True, use_angle_cls=True)
    print("English model ready")
    print("All models downloaded successfully")
except Exception as e:
    print(f"Failed: {e}")
    print("1. Make sure VPN is ON")
    print("2. Delete .paddleocr and .paddlex folders and retry")
    print("3. Or use Tesseract engine offline")
    sys.exit(1)
PYEOF

if not errorlevel 1 goto :test
echo.
echo *** Model download failed - try with VPN or use Tesseract offline
pause
exit /b 1

:test
echo.
echo [2/2] Testing OCR on dummy image
%PY% - <<PYEOF
import numpy as np, cv2
from paddleocr import PaddleOCR
ocr = PaddleOCR(lang="arabic", show_log=False)
dummy = np.ones((100, 400, 3), dtype=np.uint8) * 255
cv2.putText(dummy, "TEST", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
try:
    result = ocr.ocr(dummy, cls=True)
    print("OCR test passed")
except Exception as e:
    print(f"OCR test warning: {e}")
PYEOF

echo.
echo ============================================================
echo   Done - Models are ready. You can now use accurate PaddleOCR
echo   engine in app without VPN anymore
echo ============================================================
pause
