@echo off
chcp 65001 >nul
title TABDIL - Download Models from GitHub
cd /d "%~dp0"

echo ============================================================
echo   TABDIL - Download PaddleOCR models from GitHub
echo   No Baidu needed - uses GitHub which works in Iran
echo ============================================================
echo.

if exist ".venv\Scripts\python.exe" goto :check_paddle
echo .venv not found - run Install.bat first
pause
exit /b 1

:check_paddle
set "PY=.venv\Scripts\python.exe"
%PY% -c "import paddleocr" >nul 2>&1
if not errorlevel 1 goto :prepare
echo PaddleOCR not installed - run Install-PaddleOCR.bat first
pause
exit /b 1

:prepare
echo Checking cache
%PY% -c "import pathlib; whl=pathlib.Path.home()/'.paddleocr'/'whl'; print('Cache at', whl)"

echo.
echo This will download 3 models about 16 MB from GitHub Releases
echo   - Multilingual det
echo   - arabic rec v4
echo   - ch cls
echo.

REM Check if models already exist locally
set "SRC=%~dp0paddle_models"
if exist "%SRC%\det\ml\Multilingual_PP-OCRv3_det_infer\inference.pdmodel" (
  if exist "%SRC%\rec\arabic\arabic_PP-OCRv4_rec_infer\inference.pdmodel" (
    if exist "%SRC%\cls\ch\ch_ppocr_mobile_v2.0_cls_infer\inference.pdmodel" (
      echo [OK] Models already exist in paddle_models folder
      echo      Skipping download, verifying...
      goto :verify
    )
  )
)

set "DEST=%USERPROFILE%\.paddleocr\whl"
mkdir "%DEST%\det\ml" >nul 2>&1
mkdir "%DEST%\rec\arabic" >nul 2>&1
mkdir "%DEST%\cls\ch" >nul 2>&1
mkdir "paddle_models\det\ml" >nul 2>&1
mkdir "paddle_models\rec\arabic" >nul 2>&1
mkdir "paddle_models\cls\ch" >nul 2>&1

echo [2/4] Downloading from GitHub - if you already have tar files, put them in paddle_models and run Setup-PaddleModels-Local.bat

set "PS1=%TEMP%\tabdil_dl.ps1"
echo $baseUrl='https://github.com/saeidkazemi1989-bot/TABDIL-ax-be-matn/releases/download/paddle-models' > "%PS1%"
echo $destRoot='%DEST%' >> "%PS1%"
echo $localRoot='%~dp0paddle_models' >> "%PS1%"
echo $srcRoot='%~dp0paddle_models' >> "%PS1%"
echo $models=@( >> "%PS1%"
echo   @{name='Multilingual_PP-OCRv3_det_infer.tar'; url="$baseUrl/Multilingual_PP-OCRv3_det_infer.tar"; dest="$destRoot/det/ml/Multilingual_PP-OCRv3_det_infer"; localDest="$localRoot/det/ml/Multilingual_PP-OCRv3_det_infer"}, >> "%PS1%"
echo   @{name='arabic_PP-OCRv4_rec_infer.tar'; url="$baseUrl/arabic_PP-OCRv4_rec_infer.tar"; dest="$destRoot/rec/arabic/arabic_PP-OCRv4_rec_infer"; localDest="$localRoot/rec/arabic/arabic_PP-OCRv4_rec_infer"}, >> "%PS1%"
echo   @{name='ch_ppocr_mobile_v2.0_cls_infer.tar'; url="$baseUrl/ch_ppocr_mobile_v2.0_cls_infer.tar"; dest="$destRoot/cls/ch/ch_ppocr_mobile_v2.0_cls_infer"; localDest="$localRoot/cls/ch/ch_ppocr_mobile_v2.0_cls_infer"} >> "%PS1%"
echo ^) >> "%PS1%"
echo foreach ^($m in $models^) { >> "%PS1%"
echo   # Skip if already exists >> "%PS1%"
echo   if ^(Test-Path ^(Join-Path $m.dest 'inference.pdmodel'^)^) { Write-Host "Already exists: $($m.name) - skipping"; continue } >> "%PS1%"
echo   # Check if tar already exists locally >> "%PS1%"
echo   $localTar=Join-Path $srcRoot $m.name >> "%PS1%"
echo   $tarPath=Join-Path $env:TEMP $m.name >> "%PS1%"
echo   if ^(Test-Path $localTar^) { >> "%PS1%"
echo     Write-Host "Found local tar: $localTar - using it" >> "%PS1%"
echo     Copy-Item -Force $localTar $tarPath >> "%PS1%"
echo   } else { >> "%PS1%"
echo     Write-Host "`nDownloading $($m.name)..." >> "%PS1%"
echo     try { >> "%PS1%"
echo       Invoke-WebRequest -Uri $m.url -OutFile $tarPath -UseBasicParsing -TimeoutSec 180 >> "%PS1%"
echo       Write-Host "Downloaded to $tarPath" >> "%PS1%"
echo     } catch { >> "%PS1%"
echo       Write-Host "FAILED: $($_.Exception.Message) - try manual download, see راهنمای-نصب-دستی.txt" -ForegroundColor Red >> "%PS1%"
echo       continue >> "%PS1%"
echo     } >> "%PS1%"
echo   } >> "%PS1%"
echo   try { >> "%PS1%"
echo     $destDir=$m.dest; $localDestDir=$m.localDest >> "%PS1%"
echo     if ^(Test-Path $destDir^) { Remove-Item -Recurse -Force $destDir } >> "%PS1%"
echo     if ^(Test-Path $localDestDir^) { Remove-Item -Recurse -Force $localDestDir } >> "%PS1%"
echo     New-Item -ItemType Directory -Force -Path $destDir ^| Out-Null >> "%PS1%"
echo     New-Item -ItemType Directory -Force -Path $localDestDir ^| Out-Null >> "%PS1%"
echo     tar -xf $tarPath -C ^(Split-Path $destDir -Parent^) >> "%PS1%"
echo     Copy-Item -Recurse -Force -Path "$destDir/*" -Destination $localDestDir -ErrorAction SilentlyContinue >> "%PS1%"
echo     Write-Host "OK: $($m.name)" >> "%PS1%"
echo     Remove-Item -Force $tarPath -ErrorAction SilentlyContinue >> "%PS1%"
echo   } catch { >> "%PS1%"
echo     Write-Host "Extract FAILED: $($_.Exception.Message)" -ForegroundColor Red >> "%PS1%"
echo   } >> "%PS1%"
echo } >> "%PS1%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
del "%PS1%" >nul 2>&1

:verify
echo.
echo [3/4] Verifying
%PY% -c "import pathlib; whl=pathlib.Path.home()/'.paddleocr'/'whl'; print('det:', (whl/'det'/'ml'/'Multilingual_PP-OCRv3_det_infer'/'inference.pdmodel').exists()); print('rec:', (whl/'rec'/'arabic'/'arabic_PP-OCRv4_rec_infer'/'inference.pdmodel').exists()); print('cls:', (whl/'cls'/'ch'/'ch_ppocr_mobile_v2.0_cls_infer'/'inference.pdmodel').exists())"

echo.
echo [4/4] Testing PaddleOCR init
%PY% - <<PYEOF
import os
os.environ["TQDM_DISABLE"]="1"
from TABDIL.ocr import _find_local_paddle_models
local = _find_local_paddle_models()
print(f"Local models: {local}")
try:
    from paddleocr import PaddleOCR
    kwargs={"lang":"arabic","show_log":False}
    if "det_model_dir" in local:
        kwargs["det_model_dir"]=local["det_model_dir"]
    if "rec_model_dir" in local:
        kwargs["rec_model_dir"]=local["rec_model_dir"]
    if "cls_model_dir" in local:
        kwargs["cls_model_dir"]=local["cls_model_dir"]
    ocr = PaddleOCR(**kwargs)
    print("PaddleOCR init OK - offline works")
except Exception as e:
    print(f"Init failed: {e}")
    print("See PADDLE_MODELS_MANUAL.md and راهنمای-نصب-دستی.txt for manual method")
PYEOF

echo.
echo ============================================================
echo   Done - if models downloaded, PaddleOCR works without VPN
echo   If download failed, manually download 3 tars and run
echo   Setup-PaddleModels-Local.bat - see راهنمای-نصب-دستی.txt
echo ============================================================
pause
