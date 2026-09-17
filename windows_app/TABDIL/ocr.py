# -*- coding: utf-8 -*-
"""لایه انتزاعی موتورهای OCR - نسخه متعادل: قوی برای تشخیص ولی سریع
  - TesseractEngine : سبک و آفلاین
  - PaddleEngine   : دقیق‌تر
  فیکس: تعادل بین سرعت و دقت - 4-6 تست به جای 16+ ولی کافی برای تشخیص
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


class TesseractEngine:
    name = "tesseract"
    display_name = "Tesseract (سبک و آفلاین)"

    def __init__(self):
        import pytesseract
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
            import pytesseract
        except Exception:
            return False, "کتابخانه pytesseract نصب نشده است. فایل Install.bat را اجرا کنید."
        exe = cls._find_exe()
        if not exe:
            return False, (
                "برنامه Tesseract روی ویندوز پیدا نشد.\n\n"
                "۱) فایل Install-Tesseract.bat را اجرا کنید\n"
                "۲) یا دستی نصب کنید: https://github.com/UB-Mannheim/tesseract/wiki\n"
            )
        if not os.path.exists(os.path.join(TESSDATA_DIR, "fas.traineddata")):
            return False, "فایل زبان فارسی (fas.traineddata) کنار برنامه پیدا نشد."
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
        # جدول: 5 کانفیگ برتر، متن: 5 کانفیگ برتر - تعادل سرعت و دقت
        if table_mode:
            # برای جدول، PSM 6 بهترین است، ولی fallback های قوی هم لازم است
            configs = [
                (lang, 6, 3, ""),  # اصلی
                ("fas", 6, 3, ""),  # فقط فارسی
                (lang, 6, 1, "-c preserve_interword_spaces=1"),
                (lang, 4, 1, ""),
                (lang, 3, 3, ""),
                ("fas+eng", 11, 3, ""),  # برای جدول‌های شلوغ
            ]
            # اگر lang قبلاً fas+eng است، fas را هم امتحان کن
            if lang == "fas+eng":
                # قبلاً در لیست هست
                pass
            elif lang == "fas":
                configs.insert(1, ("fas+eng", 6, 3, ""))
            
            best_words = []
            best_conf = 0
            for try_lang, psm, oem, extra in configs:
                try:
                    data = self._recognize_psm(gray_img, try_lang, psm, oem, extra)
                    words = words_from_tesseract_data(data)
                    if not words:
                        continue
                    conf = float(np.mean([w.conf for w in words])) if words else 0
                    # امتیاز: تعداد کلمات + اطمینان
                    score = len(words) * 2 + conf
                    if score > best_conf:
                        best_conf = score
                        best_words = words
                        # اگر نتیجه خیلی خوب است، ادامه نده
                        if len(words) > 20 and conf > 50:
                            break
                except Exception:
                    continue
            
            if best_words:
                conf = float(np.mean([w.conf for w in best_words])) if best_words else 0.0
                return best_words, conf
            
            # آخرین تلاش: image_to_string و ساخت کلمات از آن
            try:
                text = self._recognize_string(gray_img, lang, 6, 3, "")
                if text and len(text.strip()) > 10:
                    words = []
                    y = 0
                    for line in text.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        x = 1000
                        for wt in line.split():
                            if len(wt) < 1:
                                continue
                            words.append(Word(x=x, y=y, w=len(wt)*15, h=18, text=wt, conf=40,
                                              block_num=0, par_num=0, line_num=y//30, word_num=x))
                            x -= 100
                        y += 30
                    if words:
                        return words, 40.0
            except Exception:
                pass
            
            return [], 0.0
        else:
            # دست‌نویس/متن: از image_to_string برای حفظ معنی
            best_words = []
            best_text = ""
            best_score = -1
            
            # کانفیگ‌های بهینه برای دست‌نویس فارسی - 5 تا برتر
            configs = [
                (6, 1, "-c preserve_interword_spaces=1"),  # بهترین برای پاراگراف فارسی
                (6, 3, "-c preserve_interword_spaces=1"),
                (4, 1, "-c preserve_interword_spaces=1"),
                (3, 1, ""),
                (11, 1, ""),
            ]
            
            langs = [lang]
            if lang == "fas+eng":
                langs = ["fas", "fas+eng"]  # اول فقط فارسی برای دست‌نویس
            elif lang == "fas":
                langs = ["fas", "fas+eng"]
            
            for try_lang in langs:
                for psm, oem, extra in configs:
                    try:
                        text = self._recognize_string(gray_img, try_lang, psm, oem, extra)
                        if not text or len(text.strip()) < 3:
                            continue
                        
                        data = self._recognize_psm(gray_img, try_lang, psm, oem, extra)
                        words = words_from_tesseract_data(data)
                        
                        total_chars = len(text.strip())
                        persian_chars = len(re.findall(r'[ء-ی]', text))
                        avg_conf = float(np.mean([w.conf for w in words])) if words else 20
                        
                        # امتیاز
                        score = total_chars + persian_chars * 1.5 + avg_conf + len(words)
                        if persian_chars > total_chars * 0.2:
                            score += 30
                        if total_chars > 30:
                            score += 20
                        
                        if score > best_score:
                            best_score = score
                            best_words = words
                            best_text = text
                            
                            # اگر نتیجه خیلی خوب، ادامه نده
                            if total_chars > 80 and persian_chars > 15 and avg_conf > 35:
                                break
                    except Exception:
                        continue
                if best_score > 100:
                    break
            
            # اگر متنی داریم ولی کلمه نداریم، از متن کلمات بساز
            if best_text and not best_words:
                words = []
                y = 0
                for line in best_text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    x = 1000
                    for wt in line.split():
                        if not wt:
                            continue
                        words.append(Word(x=x, y=y, w=len(wt)*15, h=18, text=wt, conf=40,
                                          block_num=0, par_num=0, line_num=y//30, word_num=x))
                        x -= 100
                    y += 30
                conf = 40.0
                return words, conf
            
            conf = float(np.mean([w.conf for w in best_words])) if best_words else 0.0
            # اگر هنوز خالی است ولی best_text داریم، از آن استفاده کن
            if not best_words and best_text:
                words = []
                y = 0
                for line in best_text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    x = 1000
                    for wt in line.split():
                        words.append(Word(x=x, y=y, w=len(wt)*12, h=16, text=wt, conf=35,
                                          block_num=0, par_num=0, line_num=y//25, word_num=x))
                        x -= 80
                    y += 25
                return words, 35.0
            
            return best_words, conf

    def recognize_with_lines(self, gray_img, lang="fas+eng"):
        """مستقیم خطوط را بگیر - 4 کانفیگ برتر"""
        best_lines = []
        best_score = -1
        
        configs = [
            (6, 1, "-c preserve_interword_spaces=1"),
            (6, 3, "-c preserve_interword_spaces=1"),
            (4, 1, ""),
            (3, 1, ""),
            (11, 1, ""),
        ]
        
        langs = [lang]
        if lang == "fas+eng":
            langs = ["fas", "fas+eng"]
        
        for try_lang in langs:
            for psm, oem, extra in configs:
                try:
                    text = self._recognize_string(gray_img, try_lang, psm, oem, extra)
                    if not text or len(text.strip()) < 3:
                        continue
                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                    if not lines:
                        continue
                    
                    # فیلتر نویز
                    filtered = []
                    for l in lines:
                        if re.match(r'^[|_\-—–¦\s]+$', l):
                            continue
                        if len(l) < 2:
                            continue
                        filtered.append(l)
                    if not filtered:
                        continue
                    
                    total_chars = sum(len(l) for l in filtered)
                    persian_chars = len(re.findall(r'[ء-ی]', "".join(filtered)))
                    score = total_chars + persian_chars + len(filtered)*5
                    
                    if score > best_score:
                        best_score = score
                        best_lines = filtered
                        if total_chars > 100 and persian_chars > 20:
                            break
                except Exception:
                    continue
            if best_score > 80:
                break
        
        return best_lines

    def quick_conf(self, gray_img, lang="fas+eng"):
        import cv2
        h, w = gray_img.shape[:2]
        s = min(1.0, 800.0 / max(h, w))
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
        s = min(1.0, 1200.0 / max(h, w))
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


def _paddle_model_root():
    home = os.path.expanduser("~")
    return [
        os.path.join(home, ".paddleocr"),
        os.path.join(home, ".paddlex"),
        os.path.join(home, ".paddle", "ocr"),
    ]

def _local_paddle_model_candidates():
    from .util import app_base_dir
    base = app_base_dir()
    here = os.path.dirname(os.path.abspath(__file__))
    return [
        os.path.join(base, "paddle_models"),
        os.path.join(base, "TABDIL", "paddle_models"),
        os.path.join(here, "paddle_models"),
        os.path.join(here, "..", "paddle_models"),
        os.path.join(os.path.dirname(base), "paddle_models"),
    ]

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
                "نسخه PaddleOCR 3 پشتیبانی نمی‌شود. Install-PaddleOCR.bat را اجرا کنید.")

        local_models = _find_local_paddle_models()
        has_cache = _paddle_models_exist()
        
        if not local_models and not has_cache:
            raise RuntimeError(
                "مدل‌های PaddleOCR هنوز دانلود نشده‌اند.\n\n"
                "راه‌حل فوری: از موتور سبک (Tesseract) استفاده کنید - آفلاین و سریع\n"
                "یا Download-PaddleModels-GitHub.bat را اجرا کنید (از گیت‌هاب)\n"
            )

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
        except Exception:
            pass

        try:
            return PaddleOCR(**kwargs)
        except Exception as e:
            err = str(e).lower()
            if any(k in err for k in ["download", "urlopen", "timeout", "connection", "ssl", "bcebos"]):
                raise RuntimeError(
                    "دانلود مدل PaddleOCR هنگ کرده (نیاز به VPN).\n"
                    "از موتور سبک استفاده کنید یا Download-PaddleModels-GitHub.bat\n"
                    f"خطا: {e}"
                ) from e
            raise

    @classmethod
    def is_available(cls):
        try:
            import paddleocr
            import paddle
        except Exception as ex:
            return False, f"PaddleOCR نصب نیست. Install-PaddleOCR.bat را اجرا کنید.\n{ex}"
        try:
            import paddleocr as _p
            ver = getattr(_p, "__version__", "0") or "0"
            major = int(ver.split(".")[0])
            if major >= 3:
                return False, "نسخه 3 پشتیبانی نمی‌شود. Install-PaddleOCR.bat"
        except Exception:
            pass
        local = _find_local_paddle_models()
        if local and "rec_model_dir" in local and "det_model_dir" in local:
            return True, f"paddleocr (local {len(local)} models)"
        if not _paddle_models_exist():
            return True, "paddleocr (مدل‌ها دانلود می‌شوند - نیاز به VPN یا GitHub)"
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
            if score < 0.25 and len(text.strip()) < 2:
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
                    f"خطا در دانلود مدل PaddleOCR. Download-PaddleModels-GitHub.bat را امتحان کنید.\n{e}"
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
