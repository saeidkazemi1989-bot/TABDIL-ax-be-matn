# -*- coding: utf-8 -*-
"""ابزارهای عمومی: مسیرها، نرمال‌سازی متن فارسی، فونت و ..."""
import os
import sys
import re

APP_NAME = "TABDIL"
OUTPUT_FONT = "Calibri"  # طبق خواسته کاربر: همه خروجی‌ها با فونت Calibri


def app_base_dir() -> str:
    """مسیر ریشه برنامه (هم در حالت اجرای عادی، هم در حالت فایل exe ساخته‌شده با PyInstaller)."""
    if getattr(sys, "frozen", False):  # PyInstaller
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_dir(relative: str) -> str:
    """مسیر فایل‌های همراه برنامه (tessdata و assets).

    در حالت exe فایل‌های add-data داخل پوشه موقت _MEIPASS قرار می‌گیرند و
    یک کپی هم کنار exe ممکن است باشد.
    """
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, relative))
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(here, relative))
    base = app_base_dir()
    candidates.append(os.path.join(base, "TABDIL", relative))
    candidates.append(os.path.join(base, relative))
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]


TESSDATA_DIR = resource_dir(os.path.join("tessdata"))
ASSETS_DIR = resource_dir(os.path.join("assets"))

# ارقام فارسی و عربی -> لاتین
_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_LATIN_DIGITS = "0123456789"
_DIGIT_TABLE = str.maketrans(_PERSIAN_DIGITS + _ARABIC_DIGITS,
                             _LATIN_DIGITS + _LATIN_DIGITS)


def to_latin_digits(text: str) -> str:
    return text.translate(_DIGIT_TABLE)


def normalize_persian(text: str) -> str:
    """نرمال‌سازی ملایم حروف فارسی (بدون دست زدن به کدهای لاتین و اعداد)."""
    if not text:
        return ""
    # ي و ى -> ی ، ك -> ک
    text = text.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    # حذف نشانه‌های جهت‌نما (LRM/RLM) ولی حفظ نیم‌فاصله
    text = text.replace("‎", "").replace("‏", "")
    return text


def clean_ocr_word(text: str) -> str:
    text = normalize_persian(text or "")
    # حذف کاراکترهای کنترلی و فشرده‌سازی فاصله
    text = re.sub(r"[\t\r\n\x00-\x08\x0b\x0c]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


_NUMERIC_RE = re.compile(r"^[\w\s\.\-\:/,()\+]{1,}$", re.UNICODE)
_PERSIAN_LETTER_RE = re.compile(r"[ء-ی]")
_ANY_DIGIT_RE = re.compile(r"[0-9۰-۹٠-٩]")


def maybe_latinize_numeric_cell(text: str) -> str:
    """اگر محتوای سلول عمدتاً عدد/کد لاتین بود، ارقام فارسی آن را لاتین می‌کند."""
    t = (text or "").strip()
    if not t or not _ANY_DIGIT_RE.search(t):
        return t
    has_persian_letters = bool(_PERSIAN_LETTER_RE.search(t))
    digits = len(re.findall(r"[0-9۰-۹٠-٩]", t))
    if not has_persian_letters and digits >= max(2, len(t.replace(" ", "")) * 0.35):
        return to_latin_digits(t)
    return t


def safe_sheet_name(name: str, fallback: str = "Sheet") -> str:
    name = re.sub(r"[\\/\?\*\[\]\:]", "_", name or "").strip()
    name = name[:28] or fallback
    return name


def split_stem(filename: str) -> str:
    return os.path.splitext(os.path.basename(filename))[0]


# -------------------- Tesseract path config --------------------
def _config_candidates() -> list[str]:
    base = app_base_dir()
    here = os.path.dirname(os.path.abspath(__file__))
    return [
        os.path.join(base, "tesseract_path.txt"),
        os.path.join(base, "TABDIL", "tesseract_path.txt"),
        os.path.join(here, "tesseract_path.txt"),
        os.path.join(os.path.expanduser("~"), ".tabdil_tesseract_path.txt"),
    ]


def get_saved_tesseract_path() -> str | None:
    """اگر کاربر قبلاً مسیر tesseract.exe را دستی انتخاب کرده، آن را بخوان."""
    for cfg in _config_candidates():
        try:
            if os.path.exists(cfg):
                with open(cfg, "r", encoding="utf-8") as f:
                    p = f.read().strip().strip('"').strip("'")
                    if p and os.path.exists(p):
                        return p
        except Exception:
            continue
    return None


def save_tesseract_path(path: str):
    path = path.strip().strip('"').strip("'")
    for cfg in _config_candidates()[:2]:  # save in two main places
        try:
            os.makedirs(os.path.dirname(cfg), exist_ok=True)
            with open(cfg, "w", encoding="utf-8") as f:
                f.write(path)
        except Exception:
            continue
