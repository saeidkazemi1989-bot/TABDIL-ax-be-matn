# دانلود دستی مدل‌های PaddleOCR (برای ایران بدون VPN)

اگر VPN شما جواب نمی‌دهد، می‌توانید مدل‌ها را **دستی** دانلود و در پوشه `paddle_models/` قرار دهید. برنامه به صورت خودکار آن‌ها را شناسایی می‌کند و دیگر از Baidu دانلود نمی‌کند.

## مدل‌های لازم برای زبان فارسی/عربی (PaddleOCR 2.8.1)

برنامه برای `lang=arabic` (که شامل فارسی `fa` هم می‌شود) به ۳ مدل نیاز دارد:

| مدل | لینک مستقیم Baidu (اصلی) | حجم تقریبی | توضیح |
|-----|---------------------------|------------|-------|
| **det** (تشخیص ناحیه متن) | https://paddleocr.bj.bcebos.com/PP-OCRv3/multilingual/Multilingual_PP-OCRv3_det_infer.tar | ~4 MB | چندزبانه |
| **rec arabic** (تشخیص حروف فارسی/عربی) | https://paddleocr.bj.bcebos.com/PP-OCRv4/multilingual/arabic_PP-OCRv4_rec_infer.tar | ~10 MB | مهم‌ترین |
| **cls** (تشخیص زاویه) | https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar | ~2 MB | چرخش |

**جایگزین v3 اگر v4 نشد:**
- https://paddleocr.bj.bcebos.com/PP-OCRv3/multilingual/arabic_PP-OCRv3_rec_infer.tar

## لینک‌های جایگزین بدون نیاز به Baidu (از گیت‌هاب)

چون Baidu در ایران فیلتر است، این مدل‌ها را روی گیت‌هاب هم قرار دادیم (قابل دسترس در ایران):

> **توجه:** این لینک‌ها بعد از آپلود مدل‌ها فعال می‌شوند. اگر هنوز کار نمی‌کنند، از روش دستی Baidu با دانلود منیجر استفاده کنید.

```
https://github.com/saeidkazemi1989-bot/TABDIL-ax-be-matn/releases/download/paddle-models/Multilingual_PP-OCRv3_det_infer.tar
https://github.com/saeidkazemi1989-bot/TABDIL-ax-be-matn/releases/download/paddle-models/arabic_PP-OCRv4_rec_infer.tar
https://github.com/saeidkazemi1989-bot/TABDIL-ax-be-matn/releases/download/paddle-models/ch_ppocr_mobile_v2.0_cls_infer.tar
```

اسکریپت `Download-PaddleModels-GitHub.bat` به صورت خودکار از همین لینک‌ها دانلود می‌کند.

**منابع دیگر (اگر گیت‌هاب هم کند بود):**
- HuggingFace Space که مدل‌ها را mirror کرده: https://huggingface.co/spaces/openfree/Compare-RAG-CHAT/tree/main/paddleocr/whl/rec/arabic
- ONNX نسخه‌ها (برای تبدیل): https://github.com/PT-Perkasa-Pilar-Utama/ppu-paddle-ocr-models/tree/main/recognition/multi/arabic/v5

## روش دستی (بدون نیاز به اسکریپت)

### مرحله ۱: دانلود
هر ۳ فایل بالا را دانلود کنید. اگر با مرورگر مستقیم نشد:
- از **IDM** یا **Free Download Manager** استفاده کنید
- یا لینک را در https://www.proxysite.com/ یا VPN مرورگر قرار دهید
- یا از یک VPS/سرور خارج استفاده کنید

### مرحله ۲: ساخت پوشه‌ها
در کنار `Install.bat` یک پوشه `paddle_models` بسازید با این ساختار:

```
windows_app/
├─ paddle_models/
│  ├─ det/
│  │  └─ ml/
│  │     └─ Multilingual_PP-OCRv3_det_infer/
│  │        ├─ inference.pdmodel
│  │        ├─ inference.pdiparams
│  │        └─ ...
│  ├─ rec/
│  │  └─ arabic/
│  │     └─ arabic_PP-OCRv4_rec_infer/
│  │        ├─ inference.pdmodel
│  │        ├─ inference.pdiparams
│  │        └─ ...
│  └─ cls/
│     └─ ch/
│        └─ ch_ppocr_mobile_v2.0_cls_infer/
│           ├─ inference.pdmodel
│           └─ ...
```

**روش ساده‌تر:** هر tar را با 7-Zip یا WinRAR باز کنید و پوشه داخلی‌اش را دقیقاً در مسیر بالا قرار دهید.

### مرحله ۳: اجرای اسکریپت نصب محلی

```bat
Setup-PaddleModels-Local.bat
```

این اسکریپت مدل‌ها را به `C:\Users\<شما>\.paddleocr\whl\...` کپی می‌کند تا PaddleOCR آن‌ها را پیدا کند.

### مرحله ۴: تست

```bat
Check-Installation.bat
```

باید ببینید:
```
[OK] PaddleOCR import OK
Model folder exists: True
```

و در برنامه موتور `دقیق (PaddleOCR)` را انتخاب کنید - دیگر نباید روی "در حال آماده‌سازی" بماند.

## اگر هیچ‌کدام نشد

از **موتور سبک Tesseract** استفاده کنید که:
- کاملاً آفلاین است
- نیازی به دانلود مدل ندارد
- برای جدول‌های تایپی فارسی دقت عالی دارد
- در ایران بدون هیچ مشکلی کار می‌کند

کافی است در برنامه موتور را روی `سبک (Tesseract)` بگذارید.

## آپلود مدل‌ها به گیت‌هاب (برای کمک به دیگران)

اگر شما موفق شدید مدل‌ها را دانلود کنید، لطفاً آن‌ها را به ریلیز گیت‌هاب آپلود کنید تا دیگران بدون VPN استفاده کنند:

1. بروید به: https://github.com/saeidkazemi1989-bot/TABDIL-ax-be-matn/releases
2. یک Release جدید با تگ `paddle-models` بسازید
3. ۳ فایل tar را آپلود کنید

یا فایل‌ها را برای ادمین بفرستید تا آپلود کند.
