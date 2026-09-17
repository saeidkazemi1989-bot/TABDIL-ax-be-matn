# -*- coding: utf-8 -*-
"""لایه انتزاعی موتورهای OCR:
  - TesseractEngine : سبک و آفلاین (پیش‌فرض)
  - PaddleEngine   : دقیق‌تر، نصب اختیاری (PaddleOCR با مدل عربی/فارسی)
  بهبود برای دست‌نویس: استفاده از image_to_string برای حفظ معنی، PSM بهینه، گروه‌بندی با line_num
"""
import os
import glob
import shutil
import threading
import sys
import re

import numpy as np

from .table import Word, words_from_tesseract_data
from .util import TESSDATA_DIR, clean_ocr_word


# ---------------------------------------------------------------- Tesseract

class TesseractEngine:
    name = "tesseract"
    display_name = "Tesseract (سبک و آفلاین)"

    def __init__(self):
        import pytesseract  # نصب‌شده با requirements
        self._pytesseract = pytesseract
        exe = self._find_exe()
        if exe:
            pytesseract.pytesseract.tesseract_cmd = exe
        os.environ.setdefault("TESSDATA_PREFIX", TESSDATA_DIR)
        self._lock = threading.Lock()

    @staticmethod
    def _find_exe():
        try:
            from .util import get_saved_tesseract_path
            saved = get_saved_tesseract_path()
            if saved and os.path.exists(saved):
                return saved
        except Exception:
            pass
        env = os.environ.get("TESSERACT_CMD")
        if env and os.path.exists(env):
            return env
        found = shutil.which("tesseract")
        if found:
            return found
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""),
                         r"Programs\Tesseract-OCR\tesseract.exe"),
            os.path.join(os.environ.get("PROGRAMDATA", ""),
                         r"chocolatey\bin\tesseract.exe"),
            os.path.join(os.environ.get("USERPROFILE", ""),
                         r"AppData\Local\Tesseract-OCR\tesseract.exe"),
            r"C:\Tools\Tesseract-OCR\tesseract.exe",
            r"C:\tesseract\tesseract.exe",
        ]
        here = os.path.dirname(os.path.abspath(__file__))
        candidates += [
            os.path.join(here, "tesseract", "tesseract.exe"),
            os.path.join(os.path.dirname(here), "tesseract", "tesseract.exe"),
            os.path.join(here, "..", "tesseract", "tesseract.exe"),
            os.path.join(os.path.dirname(here), "..", "tesseract", "tesseract.exe"),
            os.path.join(here, "..", "..", "tesseract", "tesseract.exe"),
        ]
        for pat in (r"C:\Program Files\Tesseract-OCR*\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR*\tesseract.exe"):
            candidates += glob.glob(pat)
        for c in candidates:
            if c and os.path.exists(c):
                return c
        return None

    @classmethod
    def is_available(cls):
        try:
            import pytesseract  # noqa: F401
        except Exception:
            return False, "کتابخانه pytesseract نصب نشده است. فایل Install.bat را اجرا کنید."
        exe = cls._find_exe()
        if not exe:
            return False, (
                "برنامه Tesseract روی ویندوز پیدا نشد.\n\n"
                "راه‌حل‌ها:\n"
                "۱) فایل Install-Tesseract.bat را اجرا کنید (نصب خودکار با winget یا دانلود).\n"
                "۲) یا دستی نصب کنید: https://github.com/UB-Mannheim/tesseract/wiki\n"
                "   مسیر پیش‌فرض: C:\\Program Files\\Tesseract-OCR\\tesseract.exe\n"
                "۳) اگر قبلاً نصب کرده‌اید ولی برنامه پیدا نمی‌کند، در پیام بعدی مسیر tesseract.exe را دستی انتخاب کنید.\n"
                "۴) برای عیب‌یابی Check-Installation.bat را اجرا کنید."
            )
        if not os.path.exists(os.path.join(TESSDATA_DIR, "fas.traineddata")):
            return False, "فایل زبان فارسی (fas.traineddata) کنار برنامه پیدا نشد. پوشه TABDIL/tessdata را چک کنید."
        try:
            import subprocess
            subprocess.run([exe, "--version"], capture_output=True, timeout=5)
        except Exception:
            pass
        return True, exe

    def _recognize_psm(self, gray_img, lang, psm, oem=3, extra_config=""):
        config = f'--tessdata-dir "{TESSDATA_DIR}" --oem {oem} --psm {psm} {extra_config}'
        with self._lock:
            data = self._pytesseract.image_to_data(
                gray_img, lang=lang, config=config,
                output_type=self._pytesseract.Output.DICT,
            )
        return data

    def _recognize_string(self, gray_img, lang, psm, oem=3, extra_config=""):
        config = f'--tessdata-dir "{TESSDATA_DIR}" --oem {oem} --psm {psm} {extra_config}'
        with self._lock:
            text = self._pytesseract.image_to_string(
                gray_img, lang=lang, config=config
            )
        return text

    def recognize(self, gray_img, lang="fas+eng", table_mode=True):
        if table_mode:
            # جدول: PSM 6 بهترین است
            data = self._recognize_psm(gray_img, lang, 6, oem=3)
            words = words_from_tesseract_data(data)
            conf = float(np.mean([w.conf for w in words])) if words else 0.0
            return words, conf
        else:
            # دست‌نویس/متن: استراتژی جدید - استفاده از image_to_string برای حفظ معنی
            # و image_to_data برای اطمینان و موقعیت
            
            # برای دست‌نویس فارسی، فقط فارسی بهتر از فارسی+انگلیسی است
            # اگر lang fas+eng است و متن فارسی به نظر می رسد، fas را هم امتحان کن
            langs_to_try = [lang]
            if lang == "fas+eng":
                langs_to_try.append("fas")
                langs_to_try.append("eng")  # شاید انگلیسی هم باشد
            
            best_words = []
            best_lines = []
            best_score = -1
            best_text = ""
            
            # کانفیگ‌های مختلف برای دست‌نویس
            configs = [
                (6, 1, "-c preserve_interword_spaces=1"),  # PSM 6, LSTM only, حفظ فاصله - بهترین برای پاراگراف فارسی
                (6, 3, "-c preserve_interword_spaces=1"),
                (4, 1, "-c preserve_interword_spaces=1"),  # PSM 4 برای ستون تکی
                (4, 3, ""),
                (3, 1, ""),  # خودکار
                (3, 3, ""),
                (11, 1, ""), # متن پراکنده
                (12, 1, ""),
            ]
            
            for try_lang in langs_to_try:
                for psm, oem, extra in configs:
                    try:
                        # اول متن کامل را بگیر - این معنی را بهتر حفظ می کند
                        text = self._recognize_string(gray_img, try_lang, psm, oem, extra)
                        if not text or not text.strip():
                            continue
                        
                        # حالا data برای کلمات و اطمینان
                        data = self._recognize_psm(gray_img, try_lang, psm, oem, extra)
                        words = words_from_tesseract_data(data)
                        if not words:
                            # اگر کلمه‌ای پیدا نشد ولی متن هست، از متن استفاده کن
                            # یک Word ساختگی برای هر خط
                            lines = [l.strip() for l in text.split('\n') if l.strip()]
                            if lines:
                                # امتیاز بر اساس طول متن
                                score = len(text) * 0.5
                                if score > best_score:
                                    best_score = score
                                    best_text = text
                                    best_lines = lines
                                    best_words = words
                            continue
                        
                        # امتیازدهی
                        good = [w for w in words if w.conf >= 30]
                        medium = [w for w in words if w.conf >= 15]
                        total_chars = sum(len(w.text) for w in words)
                        avg_conf = float(np.mean([w.conf for w in words])) if words else 0
                        good_avg = float(np.mean([w.conf for w in good])) if good else 0
                        
                        # برای دست‌نویس، تعداد خطوط و طول متن مهم است
                        # متن مستقیم از image_to_string معمولاً بهتر است
                        text_len = len(text.strip())
                        line_count = len([l for l in text.split('\n') if l.strip()])
                        
                        # امتیاز ترکیبی
                        # برای دست‌نویس فارسی، متنی که از image_to_string می آید و طولانی است، بهتر است
                        score = (
                            len(good) * 8 + 
                            len(medium) * 2 + 
                            good_avg * 0.4 + 
                            avg_conf * 0.2 +
                            min(text_len / 8, 30) +
                            line_count * 2
                        )
                        
                        # اگر زبان فارسی است و متن فارسی دارد، امتیاز بیشتر
                        persian_chars = len(re.findall(r'[ء-ی]', text))
                        if persian_chars > text_len * 0.3:
                            score += 10
                        
                        if score > best_score:
                            best_score = score
                            best_words = words
                            best_text = text
                            # خطوط را از text بگیر، نه از clustering
                            best_lines = [l.strip() for l in text.split('\n') if l.strip()]
                            
                    except Exception as e:
                        continue
            
            # اگر بهترین متن را از image_to_string گرفتیم، آن را به Word تبدیل کن برای سازگاری
            # اما برای حفظ معنی، خطوط را از best_text می گیریم
            # در نهایت، words را برمی گردانیم ولی در app.py از best_lines استفاده خواهیم کرد
            # برای فعلاً، اگر best_text وجود دارد، کلمات را از آن بسازیم
            if best_text and not best_words:
                # از متن، کلمات ساختگی بساز
                # این برای حالت fallback است
                pass
            
            # اگر هنوز کلمه‌ای نداریم، از بهترین استفاده کن
            if not best_words and best_lines:
                # کلمات ساختگی از خطوط
                words = []
                y = 0
                for line in best_lines:
                    # هر خط را به کلمات تقسیم کن
                    for x_idx, w_text in enumerate(line.split()):
                        words.append(Word(x=x_idx*100, y=y, w=80, h=20, text=w_text, conf=50))
                    y += 30
                conf = 50.0
                return words, conf
            
            conf = float(np.mean([w.conf for w in best_words])) if best_words else 0.0
            
            # نکته مهم: برای دست‌نویس، اگر best_text داریم، آن را به عنوان خطوط در نظر بگیر
            # اما چون تابع باید words برگرداند، words را برمی گردانیم
            # و در table.py build_paragraph_lines را بهبود می دهیم که از Tesseract line grouping استفاده کند
            # برای الان، یک ویژگی اضافه می کنیم: اگر best_text طولانی است، آن را در words ذخیره می کنیم
            # به صورت یک Word خاص که کل متن را دارد
            
            # برای حفظ معنی، بهترین کار این است که best_text را به عنوان مرجع نگه داریم
            # و در build_paragraph_lines از آن استفاده کنیم
            # فعلاً، اگر best_lines وجود دارد، یک Word برای هر خط با موقعیت درست بسازیم
            if best_lines and len(best_lines) > 1:
                # اگر best_lines از image_to_string بهتر است، از آن استفاده کن
                # کلمات را بر اساس best_lines بازسازی کن
                reconstructed_words = []
                y_pos = 0
                for line_idx, line_text in enumerate(best_lines):
                    # هر خط را به کلمات تقسیم کن و موقعیت بده
                    x_pos = 1000  # شروع از راست برای فارسی
                    for word_text in line_text.split():
                        if not word_text.strip():
                            continue
                        reconstructed_words.append(
                            Word(x=x_pos, y=y_pos, w=len(word_text)*20, h=20, 
                                 text=word_text, conf=60)
                        )
                        x_pos -= len(word_text)*20 + 20  # به چپ حرکت کن برای فارسی
                    y_pos += 35
                
                # اگر reconstructed بهتر است (تعداد کلمات بیشتر یا معنی بهتر)، از آن استفاده کن
                if len(reconstructed_words) > len(best_words) * 0.5:
                    # ترکیب: کلمات اصلی + بازسازی شده را مقایسه کن
                    # برای دست‌نویس، بازسازی از image_to_string معمولاً بهتر است
                    if len(best_text) > sum(len(w.text) for w in best_words):
                        best_words = reconstructed_words
            
            return best_words, conf

    def recognize_with_lines(self, gray_img, lang="fas+eng"):
        """برای دست‌نویس: مستقیم خطوط را از Tesseract بگیر - بهترین برای حفظ معنی"""
        best_lines = []
        best_conf = 0
        
        configs = [
            (6, 1, "-c preserve_interword_spaces=1"),
            (6, 3, "-c preserve_interword_spaces=1"),
            (4, 1, ""),
            (3, 1, ""),
        ]
        
        for psm, oem, extra in configs:
            try:
                text = self._recognize_string(gray_img, lang, psm, oem, extra)
                if not text or not text.strip():
                    continue
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if not lines:
                    continue
                
                # امتیاز بر اساس طول و فارسی بودن
                total_chars = sum(len(l) for l in lines)
                persian_chars = len(re.findall(r'[ء-ی]', text))
                score = total_chars + persian_chars * 0.5 + len(lines) * 5
                
                if score > best_conf:
                    best_conf = score
                    best_lines = lines
            except:
                continue
        
        return best_lines

    def quick_conf(self, gray_img, lang="fas+eng"):
        import cv2
        h, w = gray_img.shape[:2]
        s = min(1.0, 1000.0 / max(h, w))
        small = cv2.resize(gray_img, None, fx=s, fy=s,
                           interpolation=cv2.INTER_AREA) if s < 1.0 else gray_img
        config = f'--tessdata-dir "{TESSDATA_DIR}" --oem 3 --psm 11'
        try:
            with self._lock:
                data = self._pytesseract.image_to_data(
                    small, lang=lang, config=config,
                    output_type=self._pytesseract.Output.DICT)
            confs = [float(c) for c in data.get("conf", [])
                     if self._good_conf(c)]
            return float(np.mean(confs)) if confs else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _good_conf(c):
        try:
            return float(c) >= 0
        except (TypeError, ValueError):
            return False

    def osd_degrees(self, gray_img):
        import cv2
        import re
        h, w = gray_img.shape[:2]
        s = min(1.0, 1400.0 / max(h, w))
        small = cv2.resize(gray_img, None, fx=s, fy=s,
                           interpolation=cv2.INTER_AREA) if s < 1.0 else gray_img
        try:
            with self._lock:
                out = self._pytesseract.image_to_osd(
                    small,
                    config=f'--tessdata-dir "{TESSDATA_DIR}"',
                    lang="osd")
            m = re.search(r"Rotate:\s*(\d+)", out)
            mc = re.search(r"Orientation confidence:\s*([0-9.eE+-]+)", out)
            deg = int(m.group(1)) if m else None
            conf = float(mc.group(1)) if mc else None
            return deg, conf
        except Exception:
            return None, None


# ------------------------------------------------------------------ Paddle

def _paddle_model_root():
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".paddleocr"),
        os.path.join(home, ".paddlex"),
        os.path.join(home, ".paddle", "ocr"),
    ]
    return candidates

def _local_paddle_model_candidates():
    from .util import app_base_dir
    base = app_base_dir()
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, "paddle_models"),
        os.path.join(base, "TABDIL", "paddle_models"),
        os.path.join(here, "paddle_models"),
        os.path.join(here, "..", "paddle_models"),
        os.path.join(os.path.dirname(base), "paddle_models"),
    ]
    return candidates

def _paddle_models_exist():
    for root in _paddle_model_root():
        if os.path.exists(root):
            for dirpath, dirnames, filenames in os.walk(root):
                if any(f.endswith((".pdparams", ".pdmodel", ".onnx", ".json")) for f in filenames):
                    return True
    for local in _local_paddle_model_candidates():
        if os.path.exists(local):
            for dirpath, dirnames, filenames in os.walk(local):
                if any(f.endswith((".pdparams", ".pdmodel")) for f in filenames):
                    return True
    return False

def _find_local_paddle_models():
    result = {}
    for root in _local_paddle_model_candidates():
        if not os.path.exists(root):
            continue
        if "det_model_dir" not in result:
            for sub in [
                os.path.join(root, "det", "ml", "Multilingual_PP-OCRv3_det_infer"),
                os.path.join(root, "det", "ml"),
                os.path.join(root, "Multilingual_PP-OCRv3_det_infer"),
                os.path.join(root, "det"),
            ]:
                if os.path.exists(os.path.join(sub, "inference.pdmodel")):
                    result["det_model_dir"] = sub
                    break
                if os.path.basename(sub) == "det":
                    for dirpath, dirnames, filenames in os.walk(sub):
                        if "inference.pdmodel" in filenames and "det" in dirpath.lower():
                            result["det_model_dir"] = dirpath
                            break
        if "rec_model_dir" not in result:
            for sub in [
                os.path.join(root, "rec", "arabic", "arabic_PP-OCRv4_rec_infer"),
                os.path.join(root, "rec", "arabic"),
                os.path.join(root, "arabic_PP-OCRv4_rec_infer"),
                os.path.join(root, "arabic_PP-OCRv3_rec_infer"),
                os.path.join(root, "rec"),
            ]:
                if os.path.exists(os.path.join(sub, "inference.pdmodel")):
                    result["rec_model_dir"] = sub
                    break
                if os.path.basename(sub) == "rec":
                    for dirpath, dirnames, filenames in os.walk(sub):
                        if "inference.pdmodel" in filenames and ("arabic" in dirpath.lower() or "rec" in dirpath.lower()):
                            if "arabic" in dirpath.lower():
                                result["rec_model_dir"] = dirpath
                                break
                    if "rec_model_dir" in result:
                        break
        if "cls_model_dir" not in result:
            for sub in [
                os.path.join(root, "cls", "ch", "ch_ppocr_mobile_v2.0_cls_infer"),
                os.path.join(root, "cls", "ch"),
                os.path.join(root, "ch_ppocr_mobile_v2.0_cls_infer"),
                os.path.join(root, "cls"),
            ]:
                if os.path.exists(os.path.join(sub, "inference.pdmodel")):
                    result["cls_model_dir"] = sub
                    break
                if os.path.basename(sub) == "cls":
                    for dirpath, dirnames, filenames in os.walk(sub):
                        if "inference.pdmodel" in filenames and "cls" in dirpath.lower():
                            result["cls_model_dir"] = dirpath
                            break
    home = os.path.expanduser("~")
    whl_root = os.path.join(home, ".paddleocr", "whl")
    if os.path.exists(whl_root):
        if "det_model_dir" not in result:
            cand = os.path.join(whl_root, "det", "ml", "Multilingual_PP-OCRv3_det_infer")
            if os.path.exists(os.path.join(cand, "inference.pdmodel")):
                result["det_model_dir"] = cand
        if "rec_model_dir" not in result:
            for ver in ["arabic_PP-OCRv4_rec_infer", "arabic_PP-OCRv3_rec_infer"]:
                cand = os.path.join(whl_root, "rec", "arabic", ver)
                if os.path.exists(os.path.join(cand, "inference.pdmodel")):
                    result["rec_model_dir"] = cand
                    break
        if "cls_model_dir" not in result:
            cand = os.path.join(whl_root, "cls", "ch", "ch_ppocr_mobile_v2.0_cls_infer")
            if os.path.exists(os.path.join(cand, "inference.pdmodel")):
                result["cls_model_dir"] = cand
    return result


class PaddleEngine:
    name = "paddle"
    display_name = "PaddleOCR (دقیق‌تر)"

    _shared = {}
    _lock = threading.Lock()

    def __init__(self, lang="arabic"):
        self._ensure_streams()
        os.environ.setdefault("TQDM_DISABLE", "1")
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        with PaddleEngine._lock:
            if "ocr" not in PaddleEngine._shared:
                PaddleEngine._shared["ocr"] = self._build(lang)
        self.ocr = PaddleEngine._shared["ocr"]

    @staticmethod
    def _ensure_streams():
        try:
            if getattr(sys, "stdout", None) is None:
                sys.stdout = open(os.devnull, "w", encoding="utf-8")
        except Exception:
            pass
        try:
            if getattr(sys, "stderr", None) is None:
                sys.stderr = open(os.devnull, "w", encoding="utf-8")
        except Exception:
            pass
        try:
            if getattr(sys, "__stdout__", None) is None:
                sys.__stdout__ = sys.stdout
            if getattr(sys, "__stderr__", None) is None:
                sys.__stderr__ = sys.stderr
        except Exception:
            pass

    @staticmethod
    def _build(lang):
        from paddleocr import PaddleOCR
        import inspect
        try:
            import paddleocr as _p
            ver = getattr(_p, "__version__", "0") or "0"
            major = int(ver.split(".")[0])
        except Exception:
            major = 2
        if major >= 3:
            raise RuntimeError(
                "نسخه نصب‌شده PaddleOCR نسخه ۳ است و مدل عربی/فارسی را با این "
                "برنامه پشتیبانی نمی‌کند.\n"
                "لطفاً فایل Install-PaddleOCR.bat را دوباره اجرا کنید تا نسخه سازگار (2.8.1) نصب شود.\n"
                "اگر همچنان خطا داشتید، پوشه .venv را حذف و دوباره Install.bat و سپس Install-PaddleOCR.bat را اجرا کنید.")

        try:
            import numpy as _np
            import cv2 as _cv2
            _cv_ver = _cv2.__version__
            if _np.__version__.startswith("1.") and (_cv_ver.startswith("4.14") or _cv_ver.startswith("4.15") or _cv_ver.startswith("5.")):
                raise RuntimeError(
                    f"ناسازگاری نسخه‌ها: numpy {_np.__version__} با opencv {_cv_ver} سازگار نیست.\n"
                    "این خطا به VPN ربط ندارد - مشکل نسخه کتابخانه‌هاست.\n"
                    "لطفاً Fix-OpenCV-Conflict.bat یا Install-PaddleOCR.bat را دوباره اجرا کنید.")
        except RuntimeError:
            raise
        except Exception:
            pass

        local_models = _find_local_paddle_models()
        kwargs = dict(lang=lang, show_log=False, use_angle_cls=True)
        if local_models:
            if "det_model_dir" in local_models:
                kwargs["det_model_dir"] = local_models["det_model_dir"]
            if "rec_model_dir" in local_models:
                kwargs["rec_model_dir"] = local_models["rec_model_dir"]
            if "cls_model_dir" in local_models:
                kwargs["cls_model_dir"] = local_models["cls_model_dir"]

        try:
            sig = inspect.signature(PaddleOCR.__init__)
            params = sig.parameters
            if "use_angle_cls" not in params:
                kwargs.pop("use_angle_cls")
            if "show_log" not in params:
                kwargs.pop("show_log")
            if "text_detection_model_dir" in params:
                kwargs.setdefault("use_doc_orientation_classify", False)
                kwargs.setdefault("use_doc_unwarping", False)
        except Exception:
            pass

        try:
            return PaddleOCR(**kwargs)
        except Exception as e:
            err = str(e).lower()
            if any(k in err for k in ["download", "urlopen", "timeout", "connection", "ssl", "bcebos", "http", "404", "403"]):
                raise RuntimeError(
                    "دانلود مدل‌های PaddleOCR با خطا مواجه شد.\n\n"
                    "این مدل‌ها از سرور Baidu (paddleocr.bj.bcebos.com) دانلود می‌شوند که در ایران اغلب فیلتر یا بسیار کند است.\n\n"
                    "راه‌حل‌های بدون VPN (جدید):\n"
                    "۱) فایل Download-PaddleModels-GitHub.bat را اجرا کنید - مدل‌ها از گیت‌هاب (قابل دسترس در ایران) دانلود می‌شوند.\n"
                    "۲) فایل PADDLE_MODELS_MANUAL.md را بخوانید - لینک‌های مستقیم + آموزش قرار دادن دستی مدل‌ها در پوشه paddle_models/\n"
                    "۳) یا فعلاً از موتور سبک Tesseract استفاده کنید (موتور 'سبک' کاملاً آفلاین است).\n\n"
                    "راه‌حل با VPN:\n"
                    "- با VPN فایل Download-PaddleModels.bat را اجرا کنید.\n"
                    "- اگر VPN جواب نمی‌دهد، مدل‌ها را دستی دانلود و در paddle_models/ قرار دهید.\n\n"
                    f"خطای اصلی: {e}"
                ) from e
            if "arabic" in err and "no models" in err:
                raise RuntimeError(
                    "مدل عربی/فارسی برای PaddleOCR نسخه ۳ پیدا نشد.\n"
                    "لطفاً نسخه 2.8.1 را نصب کنید: Install-PaddleOCR.bat را اجرا کنید.\n\n"
                    f"خطای اصلی: {e}"
                ) from e
            raise

    @classmethod
    def is_available(cls):
        try:
            import paddleocr  # noqa: F401
            import paddle  # noqa: F401
        except Exception as ex:
            return False, ("موتور دقیق PaddleOCR نصب نیست. برای نصب، فایل "
                           "Install-PaddleOCR.bat را اجرا کنید (حدود ۱ گیگابایت، "
                           "نیاز به اینترنت در اولین اجرا).\n"
                           f"جزئیات: {ex}")
        try:
            import paddleocr as _p
            ver = getattr(_p, "__version__", "0") or "0"
            major = int(ver.split(".")[0])
            if major >= 3:
                return False, ("نسخه PaddleOCR شما نسخه ۳ است که مدل عربی/فارسی را پشتیبانی نمی‌کند.\n"
                               "لطفاً Install-PaddleOCR.bat را دوباره اجرا کنید تا نسخه 2.8.1 نصب شود.")
        except Exception:
            pass
        try:
            import numpy as _np
            import cv2 as _cv2
            _cv_ver = _cv2.__version__
            if _np.__version__.startswith("1.") and (_cv_ver.startswith("4.14") or _cv_ver.startswith("4.15") or _cv_ver.startswith("5.") or _cv_ver >= "4.14"):
                return False, (f"ناسازگاری نسخه‌ها: numpy {_np.__version__} با opencv {_cv_ver}\n"
                               "این خطا به VPN ربط ندارد.\n"
                               "لطفاً Fix-OpenCV-Conflict.bat یا Install-PaddleOCR.bat را دوباره اجرا کنید.\n"
                               "نسخه درست: numpy 1.26.4 + opencv-contrib-python 4.11.0.86")
        except Exception:
            pass

        local = _find_local_paddle_models()
        if local and "rec_model_dir" in local and "det_model_dir" in local:
            return True, f"paddleocr (local models: {len(local)} found)"

        if not _paddle_models_exist():
            return True, "paddleocr (مدل‌ها در اولین اجرا دانلود می‌شوند - نیاز به VPN در ایران، یا از GitHub دانلود کنید: Download-PaddleModels-GitHub.bat)"
        return True, "paddleocr"

    def recognize(self, gray_img, lang="fas+eng", table_mode=True):
        import cv2
        img_bgr = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)
        words = []
        confs = []
        for box, text, score in self._run(img_bgr):
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            x, y = int(min(xs)), int(min(ys))
            w, h = int(max(xs) - x), int(max(ys) - y)
            if score < 0.3 and len(text.strip()) < 2:
                continue
            words.append(Word(x=x, y=y, w=max(1, w), h=max(1, h),
                              text=clean_ocr_word(text), conf=float(score) * 100.0))
            confs.append(float(score) * 100.0)
        return words, (float(np.mean(confs)) if confs else 0.0)

    def quick_conf(self, gray_img, lang="fas+eng"):
        try:
            return TesseractEngine().quick_conf(gray_img, lang)
        except Exception:
            return None

    def osd_degrees(self, gray_img):
        try:
            return TesseractEngine().osd_degrees(gray_img)
        except Exception:
            return None

    def _run(self, img_bgr):
        out = []
        try:
            result = self.ocr.ocr(img_bgr, cls=True)
        except TypeError:
            result = self.ocr.ocr(img_bgr)
        except Exception as e:
            err = str(e).lower()
            if any(k in err for k in ["download", "bcebos", "timeout", "connection"]):
                raise RuntimeError(
                    "خطا در دانلود مدل PaddleOCR (احتمالاً نیاز به VPN در ایران).\n"
                    "لطفاً Download-PaddleModels-GitHub.bat را امتحان کنید (بدون نیاز به Baidu) یا از موتور سبک استفاده کنید.\n\n"
                    f"خطای اصلی: {e}"
                ) from e
            raise
        if not result:
            return out

        first = result[0]
        if first is not None and hasattr(first, "rec_texts"):
            polys = getattr(first, "rec_polys", None) or getattr(first, "dt_polys", None)
            texts = getattr(first, "rec_texts", [])
            scores = getattr(first, "rec_scores", [1.0] * len(texts))
            for poly, text, score in zip(polys, texts, scores):
                out.append(([[float(p[0]), float(p[1])] for p in poly], text, float(score)))
            return out

        items = first if isinstance(first, list) else result
        for item in items or []:
            try:
                box, pair = item[0], item[1]
                if isinstance(pair, (tuple, list)):
                    text, score = pair[0], pair[1]
                else:
                    text, score = str(pair), 1.0
                out.append(([[float(p[0]), float(p[1])] for p in box], text, float(score)))
            except Exception:
                continue
        return out


ENGINES = {
    "tesseract": TesseractEngine,
    "paddle": PaddleEngine,
}


def get_engine(engine_name):
    cls = ENGINES.get(engine_name, TesseractEngine)
    return cls()
