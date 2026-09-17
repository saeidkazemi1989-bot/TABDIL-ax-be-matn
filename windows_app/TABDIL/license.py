# -*- coding: utf-8 -*-
"""سیستم لایسنس یک ماهه برای TABDIL

- لایسنس بر اساس تاریخ انقضا + امضای HMAC ساده
- فایل لایسنس: license.key در کنار برنامه و همچنین در %APPDATA% و HOME
- اگر لایسنس وجود نداشته باشد، تریال 30 روزه خودکار ساخته می شود
- برای تمدید، فایل لایسنس جدید را در کنار برنامه قرار دهید

فرمت لایسنس: base64(json) + '.' + signature
json: {"exp": "2026-10-17", "type": "full", "days": 30, "created": "2026-09-17", "hwid": "..."}
signature: sha256(secret + json_b64).hexdigest()[:32]

برای تولید لایسنس جدید، از تابع generate_license استفاده کنید یا اسکریپت generate_license.py
"""
import os
import sys
import json
import base64
import hashlib
import datetime
from pathlib import Path

SECRET = "TABDIL-2024-SECRET-KEY-FOR-LICENSE-!@#"
APP_NAME = "TABDIL"

def app_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _license_paths():
    base = app_base_dir()
    here = os.path.dirname(os.path.abspath(__file__))
    home = os.path.expanduser("~")
    appdata = os.environ.get("APPDATA", home)
    return [
        os.path.join(base, "license.key"),
        os.path.join(base, "TABDIL", "license.key"),
        os.path.join(here, "license.key"),
        os.path.join(appdata, "TABDIL", "license.key"),
        os.path.join(home, ".tabdil_license"),
        os.path.join(home, ".tabdil", "license.key"),
    ]

def _get_hwid():
    """شناسه سخت‌افزار ساده - ترکیبی از نام کامپیوتر و یوزر"""
    try:
        import platform
        raw = f"{platform.node()}-{platform.machine()}-{os.environ.get('USERNAME','')}-{os.environ.get('COMPUTERNAME','')}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    except Exception:
        return "unknown-hwid"

def _sign(data_b64: str) -> str:
    return hashlib.sha256((SECRET + data_b64).encode()).hexdigest()[:32]

def generate_license(days=30, license_type="full", extra_info=None):
    """یک لایسنس جدید تولید می کند و محتوای آن را برمی گرداند"""
    now = datetime.datetime.now()
    exp = now + datetime.timedelta(days=days)
    payload = {
        "exp": exp.strftime("%Y-%m-%d"),
        "exp_full": exp.strftime("%Y-%m-%d %H:%M:%S"),
        "created": now.strftime("%Y-%m-%d"),
        "days": days,
        "type": license_type,
        "hwid": _get_hwid(),
        "app": APP_NAME,
        "version": "1.0",
    }
    if extra_info:
        payload.update(extra_info)
    
    json_str = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    b64 = base64.b64encode(json_str.encode('utf-8')).decode('ascii')
    sig = _sign(b64)
    license_content = f"{b64}.{sig}"
    return license_content, payload

def save_license(license_content: str, path=None):
    """لایسنس را در مسیرهای استاندارد ذخیره می کند"""
    if path is None:
        # ذخیره در دو جای اصلی
        paths = _license_paths()[:2]
    else:
        paths = [path]
    
    saved = []
    for p in paths:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(license_content)
            saved.append(p)
        except Exception as e:
            print(f"Failed to save license to {p}: {e}")
    return saved

def _parse_license(content: str):
    """لایسنس را پارس و اعتبارسنجی امضا می کند"""
    try:
        content = content.strip()
        if '.' not in content:
            return None, "فرمت لایسنس نامعتبر است"
        b64, sig = content.rsplit('.', 1)
        expected_sig = _sign(b64)
        if sig != expected_sig:
            # برای سازگاری با لایسنس های قدیمی ساده، اگر امضا اشتباه بود ولی JSON معتبر بود، قبول کن
            # اما برای امنیت، بهتر است سخت گیر باشیم - اینجا فقط هشدار می دهیم
            # برای این نسخه، امضا را چک می کنیم ولی اگر فایل از ما باشد، درست است
            # اگر کسی دستی تاریخ را عوض کند، امضا نمی خورد
            pass  # اجازه می دهیم با اخطار ادامه یابد - در نسخه نهایی باید return None کنیم
            # برای نسخه فعلی، برای جلوگیری از دستکاری، چک می کنیم
            # اگر می خواهید سخت گیر باشید، این خط را فعال کنید:
            # return None, "امضای لایسنس نامعتبر است"
            # فعلا برای سادگی، فقط اگر طول امضا درست نباشد خطا می دهیم
            if len(sig) != 32:
                return None, "امضای لایسنس نامعتبر است"
            # اگر امضا اشتباه بود ولی ما می خواهیم جلوی دستکاری را بگیریم:
            if sig != expected_sig:
                return None, "لایسنس دستکاری شده است"
        
        json_str = base64.b64decode(b64.encode('ascii')).decode('utf-8')
        payload = json.loads(json_str)
        return payload, None
    except Exception as e:
        return None, f"خطا در خواندن لایسنس: {e}"

def check_license():
    """
    لایسنس را چک می کند
    برمی گرداند: (is_valid: bool, days_left: int, message: str, payload: dict)
    """
    # اول همه مسیرها را چک کن
    for path in _license_paths():
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if not content:
                    continue
                payload, err = _parse_license(content)
                if err:
                    # فایل خراب است، برو بعدی
                    continue
                if not payload:
                    continue
                
                # چک تاریخ انقضا
                exp_str = payload.get("exp")
                if not exp_str:
                    continue
                
                try:
                    exp_date = datetime.datetime.strptime(exp_str, "%Y-%m-%d")
                except ValueError:
                    try:
                        exp_date = datetime.datetime.strptime(payload.get("exp_full", exp_str), "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        continue
                
                now = datetime.datetime.now()
                # تاریخ انقضا تا آخر روز معتبر است
                exp_date_end = exp_date.replace(hour=23, minute=59, second=59)
                delta = exp_date_end - now
                days_left = delta.days
                # اگر امروز منقضی شده ولی هنوز ساعت داریم، 0 روز مانده
                if delta.total_seconds() > 0:
                    if days_left < 0:
                        days_left = 0
                    msg = f"لایسنس معتبر است - {days_left} روز باقی مانده (تا {exp_str})"
                    return True, days_left, msg, payload
                else:
                    # منقضی شده، برو بعدی شاید لایسنس جدیدتری باشد
                    continue
            except Exception:
                continue
    
    # هیچ لایسنس معتبری پیدا نشد - چک کن آیا تریال قبلی وجود داشته؟
    # برای اولین اجرا، تریال 30 روزه بساز
    return False, 0, "لایسنس یافت نشد یا منقضی شده است", None

def ensure_trial_license(days=30):
    """اگر لایسنسی وجود نداشته باشد، تریال 30 روزه می سازد"""
    valid, days_left, msg, payload = check_license()
    if valid:
        return True, days_left, msg, payload
    
    # تریال بساز
    license_content, payload = generate_license(days=days, license_type="trial")
    saved = save_license(license_content)
    if saved:
        return True, days, f"لایسنس آزمایشی {days} روزه ساخته شد - تا {payload['exp']} معتبر است", payload
    else:
        return False, 0, "نمی توان لایسنس آزمایشی ساخت", None

def get_license_status_text():
    """متن وضعیت لایسنس برای نمایش در UI"""
    valid, days_left, msg, payload = check_license()
    if valid:
        exp = payload.get("exp", "?") if payload else "?"
        ltype = payload.get("type", "trial") if payload else "trial"
        if ltype == "trial":
            return f"🟢 آزمایشی: {days_left} روز مانده (تا {exp})"
        else:
            return f"🟢 لایسنس: {days_left} روز مانده (تا {exp})"
    else:
        return "🔴 لایسنس منقضی شده یا یافت نشد"

# برای تست مستقیم
if __name__ == "__main__":
    print("Checking license...")
    valid, days_left, msg, payload = check_license()
    print(f"Valid: {valid}, Days left: {days_left}, Msg: {msg}")
    if payload:
        print(f"Payload: {payload}")
    
    if not valid:
        print("\nGenerating 30-day trial license...")
        content, payload = generate_license(days=30, license_type="trial")
        print(f"License: {content[:50]}...")
        print(f"Payload: {payload}")
        saved = save_license(content)
        print(f"Saved to: {saved}")
