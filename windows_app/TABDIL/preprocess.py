# -*- coding: utf-8 -*-
"""پیش‌پردازش عکس - نسخه متعادل: قوی برای تشخیص ولی سریع بدون هنگ"""
import cv2
import numpy as np


def imread_unicode(path: str) -> np.ndarray:
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"خواندن عکس ممکن نشد: {path}")
    return img


def rotate_image(image: np.ndarray, angle: float, border=(255, 255, 255)) -> np.ndarray:
    h, w = image.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), angle, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    nw = int(h * sin + w * cos)
    nh = int(h * cos + w * sin)
    m[0, 2] += (nw - w) / 2.0
    m[1, 2] += (nh - h) / 2.0
    return cv2.warpAffine(
        image, m, (nw, nh),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border,
    )


def estimate_skew(gray: np.ndarray) -> float:
    # برای سرعت روی تصویر کوچک 1000px
    h, w = gray.shape
    if max(h, w) > 1200:
        scale = 1000.0 / max(h, w)
        small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    else:
        small = gray
    
    h_s, w_s = small.shape
    inv = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    klen = max(30, int(w_s * 0.45))
    hor = cv2.morphologyEx(
        inv, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (klen, 1)),
    )
    pts = cv2.findNonZero(hor)
    if pts is not None and len(pts) > 80:
        line = cv2.fitLine(pts, cv2.DIST_L1, 0.0, 0.01, 0.01)
        vx, vy = float(line[0]), float(line[1])
        angle = np.degrees(np.arctan2(vy, vx))
        if abs(angle) <= 10 and abs(angle) > 0.2:
            return angle
    
    # fallback Hough سریع روی تصویر کوچک
    try:
        edges = cv2.Canny(small, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180.0, threshold=120,
                                minLineLength=int(w_s * 0.25), maxLineGap=20)
        angles = []
        if lines is not None:
            for ln in lines:
                x1, y1, x2, y2 = ln[0]
                a = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                if abs(a) < 12 and abs(a) > 0.3:
                    angles.append(a)
        if angles:
            return float(np.median(angles))
    except Exception:
        pass
    return 0.0


def deskew(gray: np.ndarray) -> np.ndarray:
    try:
        a = estimate_skew(gray)
        if abs(a) > 0.3:
            gray = rotate_image(gray, a)
    except Exception:
        pass
    return gray


def load_gray(path_or_img):
    if isinstance(path_or_img, str):
        img = imread_unicode(path_or_img)
    elif hasattr(path_or_img, 'ndim') and path_or_img.ndim == 3:
        img = path_or_img
    else:
        return path_or_img.copy()
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _limit_size(gray, max_w=2400, max_h=3200):
    """محدودیت سایز برای جلوگیری از هنگ - ولی نه خیلی کوچک"""
    h, w = gray.shape[:2]
    if w > max_w or h > max_h:
        scale = min(max_w / float(w), max_h / float(h))
        if scale < 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
            return gray, scale
    return gray, 1.0


def enhance_handwritten(gray):
    """بهبود متعادل برای دست‌نویس - قوی ولی سریع"""
    gray, _ = _limit_size(gray, max_w=2200, max_h=3000)
    
    try:
        gray = deskew(gray)
    except Exception:
        pass
    
    h, w = gray.shape
    # بزرگ‌نمایی برای دست‌نویس فارسی مهم است - Tesseract متن ریز را نمی‌خواند
    target_w = 2000
    scale = 1.0
    if w < target_w:
        scale = min(2.0, target_w / float(w))
        if scale > 1.05:
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    # CLAHE قوی‌تر برای کنتراست بهتر
    try:
        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
    except Exception:
        pass
    
    # نویزگیری متوسط
    try:
        gray = cv2.fastNlMeansDenoising(gray, None, 7, 7, 21)
    except Exception:
        try:
            gray = cv2.fastNlMeansDenoising(gray, h=7)
        except Exception:
            pass
    
    # شارپ کردن برای خوانایی بهتر
    try:
        blur = cv2.GaussianBlur(gray, (0, 0), 1.5)
        gray = cv2.addWeighted(gray, 1.3, blur, -0.3, 0)
    except Exception:
        pass
    
    # نرمال‌سازی برای کنتراست نهایی
    try:
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    except Exception:
        pass
    
    return gray, scale


def enhance_gray(gray, enhance: bool = True, polish: bool = True, handwritten: bool = False):
    if handwritten:
        gray_enhanced, scale = enhance_handwritten(gray)
        color = cv2.cvtColor(gray_enhanced, cv2.COLOR_GRAY2BGR)
        return gray_enhanced, color, scale
    
    gray, _ = _limit_size(gray, max_w=2400, max_h=3200)
    
    scale = 1.0
    if enhance:
        try:
            gray = deskew(gray)
        except Exception:
            pass
        h, w = gray.shape
        target_w = 2000
        if w < target_w:
            scale = min(1.8, target_w / float(w))
            if scale > 1.05:
                gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        try:
            clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
        except Exception:
            pass
        if polish:
            try:
                gray = cv2.fastNlMeansDenoising(gray, None, 8, 7, 21)
            except Exception:
                try:
                    gray = cv2.fastNlMeansDenoising(gray, h=8)
                except Exception:
                    pass
            try:
                blur = cv2.GaussianBlur(gray, (0, 0), 2)
                gray = cv2.addWeighted(gray, 1.3, blur, -0.3, 0)
            except Exception:
                pass

    color = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    return gray, color, scale


def polish_gray(gray):
    """پولیش نهایی قوی برای OCR"""
    try:
        gray = cv2.fastNlMeansDenoising(gray, None, 8, 7, 21)
    except Exception:
        try:
            gray = cv2.fastNlMeansDenoising(gray, h=8)
        except Exception:
            pass
    try:
        blur = cv2.GaussianBlur(gray, (0, 0), 2)
        return cv2.addWeighted(gray, 1.3, blur, -0.3, 0)
    except Exception:
        return gray


def enhance_image(path_or_img, enhance: bool = True):
    gray = load_gray(path_or_img)
    return enhance_gray(gray, enhance)
