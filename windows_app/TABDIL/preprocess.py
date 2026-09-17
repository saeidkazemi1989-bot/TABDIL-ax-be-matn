# -*- coding: utf-8 -*-
"""پیش‌پردازش عکس: خواندن امن (مسیر فارسی)، حذف کجی، بهبود کنتراست و بزرگ‌نمایی.
بهبود برای دست‌نویس فارسی: حفظ اتصالات حروف، کنتراست ملایم
"""
import cv2
import numpy as np


def imread_unicode(path: str) -> np.ndarray:
    """cv2.imread با مسیرهای دارای کاراکتر فارسی/یونیکد کار می‌کند."""
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"خواندن عکس ممکن نشد: {path}")
    return img


def rotate_image(image: np.ndarray, angle: float, border=(255, 255, 255)) -> np.ndarray:
    """چرخش تصویر حول مرکز با زاویه درجه"""
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
    """تخمین زاویه کجی"""
    h, w = gray.shape
    inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    klen = max(30, int(w * 0.45))
    hor = cv2.morphologyEx(
        inv, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (klen, 1)),
    )
    pts = cv2.findNonZero(hor)
    if pts is not None and len(pts) > 200:
        line = cv2.fitLine(pts, cv2.DIST_L1, 0.0, 0.01, 0.01)
        vx, vy = float(line[0]), float(line[1])
        angle = np.degrees(np.arctan2(vy, vx))
        if abs(angle) <= 8:
            return angle
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180.0, threshold=160,
                            minLineLength=int(w * 0.25), maxLineGap=20)
    angles = []
    if lines is not None:
        for ln in lines:
            x1, y1, x2, y2 = ln[0]
            a = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(a) < 12:
                angles.append(a)
    if angles:
        return float(np.median(angles))
    return 0.0


def deskew(gray: np.ndarray, max_angle: float = 8.0) -> np.ndarray:
    a = estimate_skew(gray)
    if abs(a) > 0.15:
        gray = rotate_image(gray, a)
    return gray


def load_gray(path_or_img):
    """خواندن عکس و تبدیل به خاکستری."""
    if isinstance(path_or_img, str):
        img = imread_unicode(path_or_img)
    elif hasattr(path_or_img, 'ndim') and path_or_img.ndim == 3:
        img = path_or_img
    else:
        return path_or_img.copy()
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def remove_shadow_simple(gray):
    """حذف سایه ساده - بدون شکستن اتصالات حروف فارسی"""
    try:
        # برای دست‌نویس فارسی، از فیلتر بزرگ برای تخمین پس‌زمینه استفاده کن
        # اما ملایم‌تر از قبل
        dilated = cv2.dilate(gray, np.ones((7,7), np.uint8))
        bg = cv2.medianBlur(dilated, 21)
        diff = 255 - cv2.absdiff(gray, bg)
        # نرمال‌سازی ملایم
        norm = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
        # ترکیب: 80% اصلی + 20% بهبود یافته
        result = cv2.addWeighted(gray, 0.8, norm, 0.2, 0)
        return result
    except Exception:
        return gray


def enhance_handwritten(gray):
    """بهبود مخصوص دست‌نویس فارسی - حفظ اتصالات"""
    # 1. حذف کجی
    try:
        gray = deskew(gray)
    except Exception:
        pass
    
    # 2. افزایش اندازه - برای دست‌نویس فارسی مهم است
    # Tesseract برای متن ریز ضعیف است
    h, w = gray.shape
    target_w = 2200  # کمی کمتر از قبل تا نویز زیاد نشود
    scale = 1.0
    if w < target_w:
        scale = min(2.2, target_w / float(w))
    if scale > 1.05:
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)
    
    # 3. حذف سایه ملایم (مهم برای عکس‌های موبایل)
    try:
        # فقط اگر تصویر سایه‌دار باشد
        mean_val = np.mean(gray)
        std_val = np.std(gray)
        # اگر کنتراست کم و روشنایی متوسط باشد، سایه‌دار است
        if std_val < 50 and mean_val > 100 and mean_val < 200:
            gray = remove_shadow_simple(gray)
    except Exception:
        pass
    
    # 4. CLAHE ملایم - برای دست‌نویس فارسی، کنتراست زیاد حروف را می‌شکند
    try:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
    except Exception:
        pass
    
    # 5. برای دست‌نویس، باینری نکن - Tesseract با خاکستری بهتر کار می کند
    # به خصوص برای فارسی متصل
    # فقط نویز را کم کن
    try:
        # نویز کم برای حفظ جزئیات دست‌نویس
        gray = cv2.fastNlMeansDenoising(gray, h=5)
    except Exception:
        pass
    
    # 6. شارپ کردن ملایم برای دست‌نویس
    try:
        blur = cv2.GaussianBlur(gray, (0, 0), 1.5)
        gray = cv2.addWeighted(gray, 1.3, blur, -0.3, 0)
    except Exception:
        pass
    
    # 7. افزایش کنتراست نهایی ملایم
    try:
        # نرمال‌سازی محدوده
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    except Exception:
        pass
    
    return gray, scale


def enhance_gray(gray, enhance: bool = True, polish: bool = True, handwritten: bool = False):
    """بهبود تصویر خاکستری."""
    if handwritten:
        gray_enhanced, scale = enhance_handwritten(gray)
        color = cv2.cvtColor(gray_enhanced, cv2.COLOR_GRAY2BGR)
        return gray_enhanced, color, scale
    
    scale = 1.0
    if enhance:
        try:
            gray = deskew(gray)
        except Exception:
            pass
        h, w = gray.shape
        target_w = 2000
        if w < target_w:
            scale = min(2.0, target_w / float(w))
        if scale > 1.05:
            gray = cv2.resize(gray, None, fx=scale, fy=scale,
                              interpolation=cv2.INTER_CUBIC)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        if polish:
            try:
                gray = cv2.fastNlMeansDenoising(gray, h=9)
            except Exception:
                pass
            blur = cv2.GaussianBlur(gray, (0, 0), 3)
            gray = cv2.addWeighted(gray, 1.4, blur, -0.4, 0)

    color = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    return gray, color, scale


def polish_gray(gray):
    """مرحله نهایی مخصوص OCR"""
    try:
        gray = cv2.fastNlMeansDenoising(gray, h=9)
    except Exception:
        pass
    blur = cv2.GaussianBlur(gray, (0, 0), 3)
    return cv2.addWeighted(gray, 1.4, blur, -0.4, 0)


def enhance_image(path_or_img, enhance: bool = True):
    gray = load_gray(path_or_img)
    return enhance_gray(gray, enhance)
