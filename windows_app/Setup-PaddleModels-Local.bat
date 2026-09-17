@echo off
chcp 65001 >nul
title TABDIL - Setup PaddleOCR Models from Local Folder
cd /d "%~dp0"

echo ============================================================
echo   Setup PaddleOCR models from local paddle_models folder
echo   Use this if you manually downloaded the 3 tar files
echo ============================================================
echo.

set "SRC=%~dp0paddle_models"
set "DEST=%USERPROFILE%\.paddleocr\whl"

if exist "%SRC%" goto :check_files
echo [X] Folder not found: %SRC%
echo     Creating it...
mkdir "%SRC%" >nul 2>&1
echo     Please put your 3 tar files inside:
echo     %SRC%
echo     Files needed:
echo     - Multilingual_PP-OCRv3_det_infer.tar
echo     - arabic_PP-OCRv4_rec_infer.tar
echo     - ch_ppocr_mobile_v2.0_cls_infer.tar
echo     See file: راهنمای-نصب-دستی.txt
pause
exit /b 1

:check_files
echo Source: %SRC%
echo Dest:   %DEST%
echo.

REM Also check if tar files were downloaded directly in this folder and move them
if exist "%~dp0*.tar" (
  echo Found tar files in main folder - moving to paddle_models
  move /Y "%~dp0*.tar" "%SRC%\" >nul 2>&1
)

echo [1/3] Checking local models
dir /b "%SRC%\*.tar" 2>nul
dir /s /b "%SRC%\*.pdmodel" 2>nul
if not errorlevel 1 goto :has_models
echo No .pdmodel found - looking for tar files to extract
goto :extract

:has_models
echo Found some pdmodel files
goto :extract

:extract
echo.
echo Extracting tar files if any
set "PS1=%TEMP%\tabdil_extract.ps1"
echo $src='%SRC%' > "%PS1%"
echo Write-Host "Searching tar files in $src" >> "%PS1%"
echo $tars=Get-ChildItem -Path $src -Filter *.tar -Recurse -ErrorAction SilentlyContinue >> "%PS1%"
echo if ^($tars.Count -eq 0^) { Write-Host "No tar files found, checking existing folders" } else { >> "%PS1%"
echo   foreach ^($tar in $tars^) { >> "%PS1%"
echo     Write-Host "Extracting $($tar.FullName)" >> "%PS1%"
echo     try { tar -xf $tar.FullName -C $src } catch { Write-Host "tar failed for $($tar.FullName): $($_.Exception.Message)" } >> "%PS1%"
echo   } >> "%PS1%"
echo } >> "%PS1%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
del "%PS1%" >nul 2>&1

:copy
echo.
echo [2/3] Copying to PaddleOCR cache
mkdir "%DEST%\det\ml" >nul 2>&1
mkdir "%DEST%\rec\arabic" >nul 2>&1
mkdir "%DEST%\cls\ch" >nul 2>&1

set "PS2=%TEMP%\tabdil_copy.ps1"
echo $src='%SRC%' > "%PS2%"
echo $dest='%DEST%' >> "%PS2%"
echo Write-Host "Source: $src" >> "%PS2%"
echo Write-Host "Dest: $dest" >> "%PS2%"
echo function Copy-Model($pattern, $target) { >> "%PS2%"
echo   $found=Get-ChildItem -Path $src -Directory -Recurse ^| Where-Object { $_.Name -like $pattern -and ^(Test-Path ^(Join-Path $_.FullName 'inference.pdmodel'^)^) } ^| Select-Object -First 1 >> "%PS2%"
echo   if ^($found^) { >> "%PS2%"
echo     Write-Host "Copying $($found.FullName) to $target" >> "%PS2%"
echo     New-Item -ItemType Directory -Force -Path $target ^| Out-Null >> "%PS2%"
echo     Copy-Item -Recurse -Force -Path "$($found.FullName)/*" -Destination $target >> "%PS2%"
echo     return $true >> "%PS2%"
echo   } >> "%PS2%"
echo   return $false >> "%PS2%"
echo } >> "%PS2%"
echo $ok1=Copy-Model "*Multilingual*det*" "$dest/det/ml/Multilingual_PP-OCRv3_det_infer" >> "%PS2%"
echo $ok2=Copy-Model "*arabic*rec*" "$dest/rec/arabic/arabic_PP-OCRv4_rec_infer" >> "%PS2%"
echo if ^(-not $ok2^) { $ok2=Copy-Model "*arabic*" "$dest/rec/arabic/arabic_PP-OCRv4_rec_infer" } >> "%PS2%"
echo $ok3=Copy-Model "*ch*cls*" "$dest/cls/ch/ch_ppocr_mobile_v2.0_cls_infer" >> "%PS2%"
echo if ^(-not $ok3^) { $ok3=Copy-Model "*cls*" "$dest/cls/ch/ch_ppocr_mobile_v2.0_cls_infer" } >> "%PS2%"
echo # direct structure copy if already in correct place >> "%PS2%"
echo if ^(Test-Path "$src/det/ml/Multilingual_PP-OCRv3_det_infer/inference.pdmodel"^) { New-Item -Force -ItemType Directory -Path "$dest/det/ml/Multilingual_PP-OCRv3_det_infer" ^| Out-Null; Copy-Item -Recurse -Force -Path "$src/det/ml/Multilingual_PP-OCRv3_det_infer/*" -Destination "$dest/det/ml/Multilingual_PP-OCRv3_det_infer"; $ok1=$true } >> "%PS2%"
echo if ^(Test-Path "$src/rec/arabic/arabic_PP-OCRv4_rec_infer/inference.pdmodel"^) { New-Item -Force -ItemType Directory -Path "$dest/rec/arabic/arabic_PP-OCRv4_rec_infer" ^| Out-Null; Copy-Item -Recurse -Force -Path "$src/rec/arabic/arabic_PP-OCRv4_rec_infer/*" -Destination "$dest/rec/arabic/arabic_PP-OCRv4_rec_infer"; $ok2=$true } >> "%PS2%"
echo if ^(Test-Path "$src/rec/arabic/arabic_PP-OCRv3_rec_infer/inference.pdmodel"^) { New-Item -Force -ItemType Directory -Path "$dest/rec/arabic/arabic_PP-OCRv3_rec_infer" ^| Out-Null; Copy-Item -Recurse -Force -Path "$src/rec/arabic/arabic_PP-OCRv3_rec_infer/*" -Destination "$dest/rec/arabic/arabic_PP-OCRv3_rec_infer"; $ok2=$true } >> "%PS2%"
echo if ^(Test-Path "$src/cls/ch/ch_ppocr_mobile_v2.0_cls_infer/inference.pdmodel"^) { New-Item -Force -ItemType Directory -Path "$dest/cls/ch/ch_ppocr_mobile_v2.0_cls_infer" ^| Out-Null; Copy-Item -Recurse -Force -Path "$src/cls/ch/ch_ppocr_mobile_v2.0_cls_infer/*" -Destination "$dest/cls/ch/ch_ppocr_mobile_v2.0_cls_infer"; $ok3=$true } >> "%PS2%"
echo Write-Host "Copy results: det=$ok1 rec=$ok2 cls=$ok3" >> "%PS2%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS2%"
del "%PS2%" >nul 2>&1

echo.
echo [3/3] Verifying
if exist "%DEST%\det\ml\Multilingual_PP-OCRv3_det_infer\inference.pdmodel" (
  echo [OK] det model ready
) else (
  echo [X] det model missing - need Multilingual_PP-OCRv3_det_infer
)

if exist "%DEST%\rec\arabic\arabic_PP-OCRv4_rec_infer\inference.pdmodel" (
  echo [OK] rec arabic v4 ready
) else (
  if exist "%DEST%\rec\arabic\arabic_PP-OCRv3_rec_infer\inference.pdmodel" (
    echo [OK] rec arabic v3 ready
  ) else (
    echo [X] rec arabic missing - need arabic_PP-OCRv4_rec_infer
  )
)

if exist "%DEST%\cls\ch\ch_ppocr_mobile_v2.0_cls_infer\inference.pdmodel" (
  echo [OK] cls model ready
) else (
  echo [X] cls model missing - need ch_ppocr_mobile_v2.0_cls_infer
)

echo.
echo Also checking local paddle_models folder for app offline use
if exist "%SRC%\det\ml\Multilingual_PP-OCRv3_det_infer\inference.pdmodel" echo [OK] local det ready
if exist "%SRC%\rec\arabic\arabic_PP-OCRv4_rec_infer\inference.pdmodel" echo [OK] local rec ready
if exist "%SRC%\cls\ch\ch_ppocr_mobile_v2.0_cls_infer\inference.pdmodel" echo [OK] local cls ready

echo.
echo ============================================================
echo   Done - Now run Check-Installation.bat
echo   PaddleOCR should work offline without Baidu
echo   If still missing, put tar files in:
echo   %SRC%
echo   and run this bat again
echo ============================================================
pause
