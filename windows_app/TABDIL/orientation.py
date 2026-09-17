# -*- coding: utf-8 -*-
"""تشخیص خودکار جهت عکس (۰/۹۰/۱۸۰/۲۷۰ درجه).

راهبرد:
  ۱) اگر جدول خط‌کشی‌شده باشد، با تعداد پیکسل خطوط افقی، محور درست پیدا می‌شود
     (سپس برای تفکیک ۰ از ۱۸۰، یک OCR سریع روی وضوح پایین انجام می‌شود).
  ۲) اگر صفحه متنی/دست‌نویس باشد، از بخش OSD تسراکت استفاده می‌شود و در صورت
     اطمینان کم، OCR سریع روی هر چهار جهت.
"""
import cv2
import numpy as np

from .table import detect_grid, table_crop


def content_crop(gray, margin=45):
    """برش ناحیه اصلی محتوا (حذف حاشیه میز/کاغذ و لکه‌های پراکنده).

    جعبه محتوا روی نسخه کوچک‌شده (ضد نویز) پیدا و به وضوح اصلی نگاشت می‌شود.
    """
    h, w = gray.shape
    scale = min(1.0, 1100.0 / max(h, w))
    if scale < 1.0:
        small = cv2.resize(gray, None, fx=scale, fy=scale,
                           interpolation=cv2.INTER_AREA)
    else:
        small = gray
    sh, sw = small.shape
    dark = cv2.threshold(small, 0, 255,
                         cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    # به هم چسباندن اجزای نزدیک برای پیدا کردن بزرگ‌ترین بلوک محتوا
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (31, 31))
    merged = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, k)
    cnts, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL,
                               cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return gray
    c = max(cnts, key=cv2.contourArea)
    x, y, bw, bh = cv2.boundingRect(c)
    if bw * bh < 0.10 * sw * sh:  # بلوک معنادار پیدا نشد
        return gray
    inv = 1.0 / scale
    x, y = int(x * inv), int(y * inv)
    bw, bh = int(bw * inv), int(bh * inv)
    m = int(margin / scale)
    return gray[max(0, y - m):min(h, y + bh + m),
                max(0, x - m):min(w, x + bw + m)]


def _table_score(crop):
    """امتیاز «جدول راست‌بودن» جهت؛ در جهت درست، خطوط افقی (ردیف‌ها)
    باید بیش از خطوط عمودی (ستون‌ها) باشند و حداقل شبکه‌ای وجود داشته باشد."""
    xs, ys = detect_grid(crop)
    nx, ny = len(xs), len(ys)
    if ny >= 4 and nx >= 2 and ny >= nx:
        return (ny - 1) * (nx - 1)
    return 0


def _downscale(gray, max_dim=1100):
    h, w = gray.shape
    s = min(1.0, max_dim / float(max(h, w)))
    if s < 1.0:
        return cv2.resize(gray, None, fx=s, fy=s,
                          interpolation=cv2.INTER_AREA)
    return gray


def detect_rotation_k(gray, quick_ocr_conf=None, osd_result=None):
    """(عدد k برای np.rot90، «جدول بودن سند») را برمی‌گرداند.

    quick_ocr_conf(gray) -> float         : تابع اختیاری OCR سریع
    osd_result -> (degrees, confidence)   : نتیجه OSD تسراکت (درجه ساعتگرد)
    """
    crops, tscore = [], []
    for k in range(4):
        c = content_crop(np.rot90(gray, k))
        crops.append(c)
        tscore.append(_table_score(c))

    pair_portrait = max(tscore[0], tscore[2])  # جهت‌های ۰ و ۱۸۰
    pair_landscape = max(tscore[1], tscore[3])  # جهت‌های ۹۰ و ۲۷۰
    if max(pair_portrait, pair_landscape) > 0:
        candidates = [0, 2] if pair_portrait >= pair_landscape else [1, 3]
        if quick_ocr_conf is None:
            return candidates[0], True
        scores = {k: quick_ocr_conf(crops[k]) for k in candidates}
        return max(candidates, key=lambda k: scores[k]), True

    # صفحه متنی/دست‌نویس بدون خطوط جدول
    if osd_result is not None:
        deg, conf = osd_result
        if deg is not None and (conf is None or conf >= 1.5):
            deg_to_k = {0: 0, 90: 3, 180: 2, 270: 1}
            k = deg_to_k.get((int(deg) // 90 * 90) % 360)
            if k is not None:
                return k, False
    if quick_ocr_conf is not None:
        scores = [quick_ocr_conf(_downscale(c)) for c in crops]
        return int(np.argmax(scores)), False
    return 0, False


def upright(gray, quick_ocr_conf=None, osd_result=None):
    """تصویر خاکستری را در جهت درست برمی‌گرداند.

    خروجی: (تصویر راست‌شده، k، جدول_بودن). برای جداول، تصویر به ناحیه جدول
    کراپ می‌شود تا حاشیه و یادداشت‌های کناری حذف شوند؛ برای متون کل صفحه می‌ماند.
    """
    k, is_table = detect_rotation_k(gray, quick_ocr_conf, osd_result)
    if k:
        gray = np.ascontiguousarray(np.rot90(gray, k))
    if is_table:
        # برش درشت ناحیه محتوا (پیش از بزرگ‌نمایی) تا جدول کوچک در صفحه بزرگ گم نشود
        gray = content_crop(gray, margin=60)
    # برش دقیق خطوط جدول بعد از بهبود تصویر انجام می‌شود (در خط لوله app)
    return gray, k, is_table
