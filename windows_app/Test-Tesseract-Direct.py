# -*- coding: utf-8 -*-
"""تست مستقیم Tesseract - برای دیباگ خروجی خالی"""
import os
import sys
import cv2

# اضافه کردن مسیر TABDIL
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

print("="*60)
print("TABDIL - تست مستقیم Tesseract")
print("="*60)

# چک pytesseract
try:
    import pytesseract
    print(f"[OK] pytesseract نصب است")
    print(f"     مسیر: {pytesseract.pytesseract.tesseract_cmd}")
except Exception as e:
    print(f"[X] pytesseract نصب نیست: {e}")
    print("    فایل Install.bat را اجرا کنید")
    input("Enter برای خروج...")
    sys.exit(1)

# پیدا کردن tesseract.exe
from TABDIL.ocr import TesseractEngine
from TABDIL.util import TESSDATA_DIR

exe = TesseractEngine._find_exe()
print(f"\n--- Tesseract exe ---")
if exe and os.path.exists(exe):
    print(f"[OK] پیدا شد: {exe}")
    try:
        import subprocess
        result = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=5)
        print(f"     {result.stdout.strip()}")
    except Exception as e:
        print(f"     خطا در اجرا: {e}")
else:
    print(f"[X] پیدا نشد!")
    print("    Install-Tesseract.bat را اجرا کنید")
    print(f"    TESSDATA_DIR: {TESSDATA_DIR}")

print(f"\n--- Tessdata ---")
print(f"مسیر: {TESSDATA_DIR}")
for lang_file in ["fas.traineddata", "eng.traineddata", "osd.traineddata"]:
    p = os.path.join(TESSDATA_DIR, lang_file)
    print(f"  {lang_file}: {'OK' if os.path.exists(p) else 'MISSING'} - {p}")

# تست روی عکس‌ها
print(f"\n--- تست OCR روی عکس‌ها ---")
test_images = []
# عکس‌های نمونه در پوشه‌های مختلف
for root in [".", "..", os.path.join("..", "..")]:
    for fname in ["IMG_20260909_094503.jpg", "IMG_20260909_094513.jpg", "sample.jpg"]:
        fp = os.path.join(root, fname)
        if os.path.exists(fp):
            test_images.append(fp)

# همچنین عکس‌های انتخابی کاربر از آرگومان
if len(sys.argv) > 1:
    for arg in sys.argv[1:]:
        if os.path.exists(arg):
            test_images.append(arg)

if not test_images:
    print("هیچ عکس نمونه پیدا نشد")
    print("یک عکس را به عنوان آرگومان بدهید یا در کنار این فایل بگذارید")
    # لیست فایل‌های jpg در مسیر
    import glob
    jpgs = glob.glob("*.jpg") + glob.glob("*.png") + glob.glob(os.path.join("..", "*.jpg"))
    if jpgs:
        print(f"عکس‌های موجود: {jpgs[:5]}")
        test_images = jpgs[:2]

for img_path in test_images[:3]:
    print(f"\n>>> تست: {img_path}")
    try:
        # خواندن
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            # با unicode
            from TABDIL.preprocess import imread_unicode
            img_color = imread_unicode(img_path)
            img = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
        print(f"    سایز: {img.shape}, میانگین: {img.mean():.1f}")
        
        # ذخیره دیباگ
        debug_dir = os.path.join(os.path.expanduser("~"), "Desktop", "TABDIL_debug")
        os.makedirs(debug_dir, exist_ok=True)
        
        # تست‌های مختلف
        configs = [
            ("fas+eng", 6, 3, ""),
            ("fas", 6, 3, ""),
            ("fas", 6, 1, "-c preserve_interword_spaces=1"),
            ("fas+eng", 3, 3, ""),
            ("eng", 6, 3, ""),
        ]
        
        for lang, psm, oem, extra in configs:
            try:
                cfg = f'--tessdata-dir "{TESSDATA_DIR}" --oem {oem} --psm {psm} {extra}'
                txt = pytesseract.image_to_string(img, lang=lang, config=cfg)
                txt_clean = txt.strip()
                print(f"    [{lang} PSM{psm} OEM{oem}] {len(txt_clean)} کاراکتر: {txt_clean[:80]!r}")
                if len(txt_clean) > 10:
                    print(f"        >>> موفق! متن: {txt_clean[:200]}")
                    break
            except Exception as e:
                print(f"    [{lang} PSM{psm}] خطا: {e}")
                # تلاش بدون tessdata-dir
                try:
                    cfg2 = f'--oem {oem} --psm {psm} {extra}'
                    txt = pytesseract.image_to_string(img, lang=lang, config=cfg2)
                    print(f"    [{lang} PSM{psm} بدون tessdata] {len(txt.strip())} کاراکتر")
                    if len(txt.strip()) > 10:
                        break
                except Exception as e2:
                    print(f"        بدون tessdata هم خطا: {e2}")
        
        # تست باینری
        print(f"    --- تست باینری OTSU ---")
        try:
            _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            txt = pytesseract.image_to_string(binary, lang="fas", config=f'--tessdata-dir "{TESSDATA_DIR}" --oem 3 --psm 6')
            print(f"    باینری: {len(txt.strip())} کاراکتر: {txt.strip()[:80]!r}")
            cv2.imwrite(os.path.join(debug_dir, f"test_binary_{os.path.basename(img_path)}"), binary)
        except Exception as e:
            print(f"    باینری خطا: {e}")
        
        # تست image_to_data
        print(f"    --- تست image_to_data ---")
        try:
            data = pytesseract.image_to_data(img, lang="fas", config=f'--tessdata-dir "{TESSDATA_DIR}" --oem 3 --psm 6', output_type=pytesseract.Output.DICT)
            n = len([t for t in data["text"] if t.strip()])
            print(f"    تعداد کلمات در data: {n}")
            if n > 0:
                for i in range(min(5, len(data["text"]))):
                    if data["text"][i].strip():
                        print(f"      {data['text'][i]} conf={data['conf'][i]}")
        except Exception as e:
            print(f"    data خطا: {e}")
            
    except Exception as e:
        import traceback
        print(f"    خطا کلی: {e}")
        traceback.print_exc()

print("\n" + "="*60)
print("تست تمام شد. پوشه دیباگ:")
print(os.path.join(os.path.expanduser("~"), "Desktop", "TABDIL_debug"))
print("اگر همه تست‌ها 0 کاراکتر دادند، Tesseract مشکل دارد")
print("Check-Installation.bat را اجرا کنید")
print("="*60)
input("Enter برای خروج...")
