# -*- coding: utf-8 -*-
"""تولید لایسنس یک ماهه برای مشتری"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from TABDIL.license import generate_license, save_license
import datetime

def main():
    print("="*60)
    print("  TABDIL - تولید لایسنس یک ماهه")
    print("="*60)
    print()
    
    # تاریخ امروز
    now = datetime.datetime.now()
    print(f"تاریخ امروز: {now.strftime('%Y-%m-%d')}")
    
    # تولید لایسنس 30 روزه
    days = 30
    # اگر آرگومان داده شده، از آن استفاده کن
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except:
            pass
    
    print(f"تولید لایسنس {days} روزه...")
    license_content, payload = generate_license(days=days, license_type="full", extra_info={"customer": "default"})
    
    print()
    print(f"تاریخ انقضا: {payload['exp']}")
    print(f"نوع: {payload['type']}")
    print()
    print("محتوای لایسنس:")
    print("-"*60)
    print(license_content)
    print("-"*60)
    print()
    
    # ذخیره
    saved = save_license(license_content)
    print(f"لایسنس ذخیره شد در:")
    for p in saved:
        print(f"  - {p}")
    
    # همچنین یک فایل متنی برای ارسال به مشتری
    license_file = os.path.join(os.path.dirname(__file__), f"license_{payload['exp']}.txt")
    with open(license_file, 'w', encoding='utf-8') as f:
        f.write(f"TABDIL License - Valid until {payload['exp']}\n")
        f.write(f"Generated: {payload['created']}\n")
        f.write(f"Days: {days}\n")
        f.write("\n")
        f.write(license_content)
    
    print()
    print(f"فایل متنی هم ساخته شد: {license_file}")
    print()
    print("برای فعالسازی در سیستم مشتری:")
    print("1. فایل license.key را کنار برنامه (پوشه windows_app) قرار دهید")
    print("2. یا محتوای بالا را در فایل license.key کپی کنید")
    print()
    print("="*60)

if __name__ == "__main__":
    main()
