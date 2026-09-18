# عیب‌یابی TABDIL (فارسی)

## ۱) برنامه باز نمی‌شود یا سریع بسته می‌شود

1. فایل `Check-Installation.bat` را اجرا کنید.
2. اگر خطای `numpy` یا `cv2` یا `No module named` دیدید:
   - پوشه `.venv` را حذف کنید
   - دوباره `Install.bat` را اجرا کنید
3. اگر همچنان باز نشد:
   - در پوشه `windows_app` یک CMD باز کنید (در نوار آدرس cmd تایپ کنید)
   - دستور زیر را بزنید:
     ```
     .venv\Scripts\python.exe run_app.py
     ```
   - متن خطا را کپی کنید و بفرستید.

## ۲) خطا: Tesseract پیدا نشد

این خطایی است که شما دیدید: `[X] Tesseract NOT found` و دیالوگ "موتور OCR آماده نیست".

**علت:** winget نصب را انجام می‌دهد ولی گاهی PATH آپدیت نمی‌شود یا نصب با خطای دسترسی ناقص می‌ماند.

**راه‌حل مرحله‌ای:**

۱) **نصب خودکار جدید:**
   - فایل `Install-Tesseract.bat` را اجرا کنید (جدید - هم winget هم دانلود مستقیم را امتحان می‌کند)
   - اگر پیام UAC (اجازه ادمین) آمد، Yes بزنید
   - بعد `Check-Installation.bat` را اجرا کنید

۲) **نصب دستی (اگر روش ۱ نشد):**
   - بروید به: https://github.com/UB-Mannheim/tesseract/wiki
   - فایل `tesseract-ocr-w64-setup-5.5.0.20241111.exe` را دانلود و نصب کنید
   - مسیر پیش‌فرض را تغییر ندهید: `C:\Program Files\Tesseract-OCR\`
   - بعد از نصب ویندوز را یک بار Restart کنید (برای آپدیت PATH)

۳) **انتخاب دستی مسیر (جدید):**
   - اگر Tesseract نصب است ولی برنامه پیدا نمی‌کند، کافی است در برنامه روی "شروع تشخیص" بزنید
   - برنامه از شما می‌پرسد: "مسیر tesseract.exe را دستی انتخاب کنید؟"
   - Yes بزنید و فایل `C:\Program Files\Tesseract-OCR\tesseract.exe` را انتخاب کنید
   - مسیر ذخیره می‌شود و دیگر نیازی به انتخاب مجدد نیست (در فایل `tesseract_path.txt`)

۴) **بررسی:**
   - `Check-Installation.bat` باید `[OK] Tesseract found` نشان دهد
   - در CMD این را تست کنید: `where tesseract` یا `"C:\Program Files\Tesseract-OCR\tesseract.exe" --version`

## ۳) موتور دقیق (PaddleOCR) هنگ می‌کند یا خطای دانلود می‌دهد

این رایج‌ترین مشکل در ایران است.

**علت:** مدل‌ها از سرور Baidu دانلود می‌شوند که در ایران فیلتر/کند است.

**راه‌حل:**

- VPN روشن کنید
- فایل `Download-PaddleModels.bat` را اجرا کنید
- منتظر بمانید تا دانلود تمام شود (چند دقیقه)
- بعد از آن دیگر نیاز به VPN نیست

**اگر دانلود ناقص شد:**

پوشه‌های زیر را حذف کنید:
```
C:\Users\<نام شما>\.paddleocr
C:\Users\<نام شما>\.paddlex
```
و دوباره با VPN تلاش کنید.

**اگر VPN ندارید:**

در برنامه موتور را روی `سبک (Tesseract)` بگذارید — کاملاً آفلاین است و برای جدول‌های تایپی دقت عالی دارد.

## ۴) خطای نسخه‌ها: numpy / opencv ناسازگار

مثال‌های واقعی که کاربران گزارش کرده‌اند:
```
paddleocr 2.8.1 requires opencv-contrib-python, which is not installed.
opencv-python 5.0.0.93 requires numpy>=2; python_version >= "3.9", but you have numpy 1.26.4 which is incompatible.
paddleocr 2.8.1 requires numpy<2.0, but you have numpy 2.4.6
opencv-python-headless 4.14 requires numpy>=2
```

**این خطا به VPN ربط ندارد!** مشکل نسخه کتابخانه‌هاست - بعضی بسته‌ها مثل scikit-image آخرین opencv 5.x را می‌کشند که با numpy 1.x ناسازگار است.

**راه‌حل سریع (جدید):**

- فایل `Fix-OpenCV-Conflict.bat` را اجرا کنید - همه opencv های 5.x را حذف و نسخه سازگار 4.11.0.86 را نصب می‌کند
- یا `Install-PaddleOCR.bat` جدید را اجرا کنید (خودش در آخر نسخه‌ها را فیکس می‌کند)

**راه‌حل دستی:**
```bat
.venv\Scripts\python.exe -m pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless opencv-contrib-python-headless
.venv\Scripts\python.exe -m pip install --force-reinstall numpy==1.26.4
.venv\Scripts\python.exe -m pip install --no-deps opencv-contrib-python==4.11.0.86
```

**چرا opencv-contrib-python؟**
- paddleocr در metadata خود `opencv-contrib-python` می‌خواهد، نه headless
- اگر headless نصب کنید pip هشدار می‌دهد ولی کار می‌کند
- برای رفع هشدار، نسخه جدید اسکریپت `opencv-contrib-python==4.11.0.86` نصب می‌کند که هم نیاز paddleocr را برطرف می‌کند و هم با numpy 1.26.4 سازگار است

## ۵) خطای `No models are available for lang='arabic'`

شما PaddleOCR نسخه ۳ نصب کرده‌اید که مدل عربی ندارد.

**راه‌حل:**

- `Install-PaddleOCR.bat` جدید را اجرا کنید که نسخه 2.8.1 نصب می‌کند
- یا:
  ```
  .venv\Scripts\python.exe -m pip install --only-binary=:all: --force-reinstall paddleocr==2.8.1 paddlepaddle>=2.6.0,<3.0
  ```

## ۶) خطای `NoneType has no attribute write` (tqdm)

این باگ قبلاً برطرف شده. اگر همچنان دیدید:

- مطمئن شوید `run_app.py` جدید را دارید (شامل fix برای pythonw.exe)
- `Install.bat` را دوباره اجرا کنید

## ۷) خروجی Excel/Word خالی یا به‌هم‌ریخته

- عکس را با نور یکنواخت و بدون سایه بگیرید
- گزینه «بهبود کیفیت» را روشن بگذارید
- نوع صفحه را دستی انتخاب کنید: «جدولی تایپی» برای جدول، «متن/دست‌نویس» برای یادداشت
- نتیجه قبل از ذخیره قابل ویرایش است — سلول‌ها را اصلاح کنید

## ۸) فونت خروجی Calibri نیست

همه خروجی‌ها با Calibri ساخته می‌شوند (طبق درخواست). اگر در Word فونت دیگری می‌بینید:

- مطمئن شوید فونت Calibri روی ویندوز نصب است (به‌صورت پیش‌فرض هست)
- فایل را در Word باز کنید و فونت را چک کنید — ممکن است Word فونت جایگزین نشان دهد ولی فایل اصلی Calibri است

## تماس

اگر هیچ‌کدام جواب نداد، خروجی `Check-Installation.bat` را بفرستید.

## ۹) خطای winget: `Failed when searching source: msstore` و `WinHttpSendRequest: 12002`

این خطایی است که شما دیدید:
```
Failed when searching source: msstore
An unexpected error occurred while executing the command:
WinHttpSendRequest: 12002: The operation timed out
0x80072ee2 : unknown error
```

**علت:** winget به صورت پیش‌فرض دو منبع دارد: `winget` و `msstore` (فروشگاه مایکروسافت). منبع `msstore` در ایران بسیار کند یا فیلتر است و تایم‌اوت 12002 می‌دهد. این به برنامه TABDIL ربط ندارد - مشکل شبکه ویندوز است.

**راه‌حل (جدید - خودکار):**

نسخه جدید `Install.bat` و `Install-Tesseract.bat` به صورت خودکار این مشکل را دور می‌زنند:
- اول با `--source winget` تلاش می‌کنند (بدون msstore)
- اگر باز هم نشد، مستقیم از python.org و GitHub دانلود می‌کنند (بدون winget)

**راه‌حل دستی:**

۱) **برای Python:**
   - فایل `Install-Python.bat` را اجرا کنید - مستقیم از python.org دانلود می‌کند (بدون msstore)
   - یا دستی از https://www.python.org/downloads/release/python-3119/ نصب کنید

۲) **برای Tesseract:**
   - فایل `Install-Tesseract.bat` را اجرا کنید - مستقیم از GitHub دانلود می‌کند
   - یا دستی از https://github.com/UB-Mannheim/tesseract/wiki نصب کنید

۳) **غیرفعال کردن موقت msstore (اختیاری):**
   ```bat
   winget source disable --name msstore
   Install.bat
   winget source enable --name msstore
   ```
   یا همیشه با `--source winget` نصب کنید:
   ```bat
   winget install --id Python.Python.3.11 --source winget
   winget install --id UB-Mannheim.TesseractOCR --source winget
   ```

۴) **اگر winget کلاً کار نمی‌کند:**
   - همه نصب‌ها را دستی انجام دهید (لینک‌ها بالا)
   - بعد `Install.bat` را اجرا کنید - اگر Python پیدا کند، بقیه را بدون winget نصب می‌کند

