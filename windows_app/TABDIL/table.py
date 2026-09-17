# -*- coding: utf-8 -*-
"""تبدیل کلمه‌های تشخیص داده‌شده به جدول سطری/ستونی و یا متن پاراگرافی.

راهبرد برای جداول تایپی:
  ۱) خطوط افقی/عمودی جدول با OpenCV پیدا می‌شوند و کلمه‌ها داخل خانه‌ها جای می‌گیرند.
  ۲) اگر خط‌کشی پیدا نشد، با خوشه‌بندی مختصات y و فاصله‌های افقی ستون‌ها تخمین زده می‌شوند.
برای متون دست‌نویس/پاراگرافی کلمه‌ها فقط در سطرها چیده می‌شوند - با بهبود برای دست‌نویس فارسی.
نسخه جدید: استفاده از line_num تسرکت برای گروه‌بندی دقیق‌تر
"""
from dataclasses import dataclass, field
from bisect import bisect_left, bisect_right
import re

import cv2
import numpy as np

from .util import clean_ocr_word, maybe_latinize_numeric_cell

LATIN_RE = re.compile(r"[A-Za-z0-9]")
PERSIAN_RE = re.compile(r"[ء-ی]")


@dataclass
class Word:
    x: int
    y: int
    w: int
    h: int
    text: str
    conf: float = -1.0
    block_num: int = 0
    par_num: int = 0
    line_num: int = 0
    word_num: int = 0

    @property
    def cx(self):
        return self.x + self.w / 2.0

    @property
    def cy(self):
        return self.y + self.h / 2.0

    @property
    def x2(self):
        return self.x + self.w

    @property
    def y2(self):
        return self.y + self.h


def _group_positions(values, tolerance):
    """ادغام موقعیت‌های نزدیک به هم (مثلاً پیکسل‌های یک خط)."""
    if len(values) == 0:
        return []
    values = sorted(values)
    groups = [[values[0]]]
    for v in values[1:]:
        if v - groups[-1][-1] <= tolerance:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [int(round(sum(g) / len(g))) for g in groups]


def detect_grid(gray):
    """موقعیت خطوط افقی (ys) و عمودی (xs) جدول را برمی‌گرداند."""
    h, w = gray.shape
    inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    hlen = max(40, int(w * 0.40))
    horizontal = cv2.morphologyEx(
        inv, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (hlen, 1)),
    )
    vlen = max(40, int(h * 0.20))
    vertical = cv2.morphologyEx(
        inv, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, vlen)),
    )
    proj_h = (horizontal > 0).sum(axis=1)
    proj_v = (vertical > 0).sum(axis=0)
    y_rows = np.where(proj_h >= w * 0.30)[0]
    x_cols = np.where(proj_v >= h * 0.15)[0]
    ys = _group_positions(y_rows.tolist(), tolerance=12)
    xs = _group_positions(x_cols.tolist(), tolerance=12)
    def dedupe(vals, min_gap):
        out = []
        for v in vals:
            if not out or abs(v - out[-1]) > min_gap:
                out.append(v)
        return out
    ys = dedupe(ys, 18)
    xs = dedupe(xs, 25)
    xs = _filter_by_coverage(xs, proj_v, span=h, fraction=0.60,
                             floor=0.30, min_keep=2)
    ys = _filter_by_coverage(ys, proj_h, span=w, fraction=0.60,
                             floor=0.35, min_keep=4)
    return xs, ys


def _filter_by_coverage(positions, proj, span, fraction=0.6,
                        floor=0.3, min_keep=2, window=7):
    if len(positions) <= min_keep:
        return positions
    cover = []
    n = len(proj)
    for p in positions:
        a, b = max(0, p - window), min(n, p + window + 1)
        cover.append(float(proj[a:b].max()) / span if span else 0.0)
    med = float(np.median(cover))
    thresh = max(floor, min(0.45, med * fraction))
    kept = [p for p, c in zip(positions, cover) if c >= thresh]
    if len(kept) < min_keep:
        order = sorted(range(len(positions)), key=lambda i: -cover[i])
        kept = sorted(positions[i] for i in order[:min_keep])
    return kept


def is_table_like(gray, xs, ys) -> bool:
    h, w = gray.shape
    _ = (h, w)
    return len(ys) >= 4 and len(xs) >= 2


def _grid_masks(gray, h_ratio=0.30, v_ratio=0.15):
    h, w = gray.shape
    inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    hlen = max(30, int(w * h_ratio))
    vlen = max(30, int(h * v_ratio))
    hm = cv2.morphologyEx(
        inv, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (hlen, 1)))
    vm = cv2.morphologyEx(
        inv, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, vlen)))
    return inv, hm, vm


def table_crop(gray, margin=35):
    xs, ys = detect_grid(gray)
    h, w = gray.shape
    if len(xs) < 2 or len(ys) < 4:
        return gray
    x0, x1, y0, y1 = xs[0], xs[-1], ys[0], ys[-1]
    if (x1 - x0) * (y1 - y0) < 0.05 * w * h:
        return gray
    return gray[max(0, y0 - margin):min(h, y1 + margin),
                max(0, x0 - margin):min(w, x1 + margin)]


def remove_grid_lines(gray, xs=None, ys=None, thickness=3):
    out = gray.copy()
    _, hm, vm = _grid_masks(gray)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.dilate(cv2.bitwise_or(hm, vm), kernel, iterations=1)
    out[mask > 0] = 255
    if xs or ys:
        for x in (xs or []):
            out[:, max(0, x - thickness):min(out.shape[1], x + thickness + 1)] = 255
        for y in (ys or []):
            out[max(0, y - thickness):min(out.shape[0], y + thickness + 1), :] = 255
    return out


def _cell_text(words):
    if not words:
        return ""
    all_text = " ".join(w.text for w in words)
    lat = len(LATIN_RE.findall(all_text))
    per = len(PERSIAN_RE.findall(all_text))
    if lat > per:
        words_sorted = sorted(words, key=lambda w: w.x)
    else:
        words_sorted = sorted(words, key=lambda w: -w.cx)
    text = " ".join(w.text for w in words_sorted if w.text)
    return maybe_latinize_numeric_cell(text)


def build_table_from_grid(words, xs, ys, img_w, img_h):
    xs2 = list(xs)
    ys2 = list(ys)
    if xs2[0] > 10:
        xs2 = [max(0, xs2[0] - 5)] + xs2
    if xs2[-1] < img_w - 10:
        xs2 = xs2 + [min(img_w, xs2[-1] + 5)]
    if ys2[0] > 10:
        ys2 = [0] + ys2
    if ys2[-1] < img_h - 10:
        ys2 = ys2 + [img_h]
    n_cols = len(xs2) - 1
    n_rows = len(ys2) - 1
    cells = [[[] for _ in range(n_cols)] for _ in range(n_rows)]
    for wd in words:
        ci = bisect_right(xs2, wd.cx) - 1
        ri = bisect_right(ys2, wd.cy) - 1
        if 0 <= ci < n_cols and 0 <= ri < n_rows:
            cells[ri][ci].append(wd)
    rows = []
    for r in range(n_rows):
        row = [_cell_text(cells[r][c]) for c in range(n_cols)]
        row = list(reversed(row))
        if any(x.strip() for x in row):
            rows.append(row)
    if rows:
        n = max(len(r) for r in rows)
        for r in rows:
            r += [""] * (n - len(r))
        keep = [j for j in range(n) if any(r[j].strip() for r in rows)]
        rows = [[r[j] for j in keep] for r in rows]
    return rows


def _cluster_lines(words, is_handwritten=False):
    """گروه‌بندی با استفاده از line_num تسرکت اگر موجود باشد، وگرنه با cy"""
    if not words:
        return []
    
    # اگر line_num از تسرکت داریم، از آن استفاده کن - دقیق‌تر است
    has_line_info = any(w.line_num != 0 or w.block_num != 0 for w in words)
    if has_line_info:
        # گروه‌بندی بر اساس block, par, line
        groups = {}
        for w in words:
            key = (w.block_num, w.par_num, w.line_num)
            if key not in groups:
                groups[key] = []
            groups[key].append(w)
        # مرتب‌سازی گروه‌ها بر اساس y (از بالا به پایین)
        # برای هر گروه، میانگین y را بگیر
        sorted_groups = sorted(groups.items(), 
                               key=lambda kv: (kv[0][0], kv[0][1], kv[0][2], 
                                               min(w.y for w in kv[1])))
        return [g[1] for g in sorted_groups]
    
    # fallback: خوشه‌بندی بر اساس cy (روش قدیمی بهبود یافته)
    srt = sorted(words, key=lambda w: (w.cy, w.x))
    if not srt:
        return []
    heights = sorted(w.h for w in srt)
    med_h = heights[len(heights) // 2] or 15
    
    if is_handwritten:
        tolerance_factor = 0.9
    else:
        tolerance_factor = 0.6
    
    lines = []
    for wd in srt:
        placed = False
        # نزدیک‌ترین خطوط را چک کن
        candidates = sorted(lines, key=lambda l: abs(wd.cy - l["cy"]))
        for line in candidates[:4]:
            y_dist = abs(wd.cy - line["cy"])
            if y_dist <= med_h * tolerance_factor:
                line_top = min(w.y for w in line["words"])
                line_bottom = max(w.y2 for w in line["words"])
                overlap = max(0, min(wd.y2, line_bottom) - max(wd.y, line_top))
                # برای دست‌نویس، همپوشانی مهم‌تر است
                if is_handwritten:
                    if overlap > med_h * 0.2 or y_dist < med_h * 0.4:
                        line["words"].append(wd)
                        line["cys"].append(wd.cy)
                        line["cy"] = float(np.mean(line["cys"]))
                        placed = True
                        break
                else:
                    if overlap > 0 or y_dist < med_h * 0.5:
                        line["words"].append(wd)
                        line["cys"].append(wd.cy)
                        line["cy"] = float(np.mean(line["cys"]))
                        placed = True
                        break
        if not placed:
            lines.append({"cy": wd.cy, "cys": [wd.cy], "words": [wd]})
    
    lines.sort(key=lambda l: l["cy"])
    return [l["words"] for l in lines]


def build_table_fallback(words):
    is_handwritten = False
    if words:
        heights = [w.h for w in words]
        if heights:
            med_h = float(np.median(heights))
            std_h = float(np.std(heights)) if len(heights) > 1 else 0
            if std_h > med_h * 0.4:
                is_handwritten = True
    
    line_words = _cluster_lines(words, is_handwritten=is_handwritten)
    if not line_words:
        return []
    med_h = float(np.median([w.h for w in words]) or 15)
    segments = []
    for li, line in enumerate(line_words):
        line = sorted(line, key=lambda w: w.x)
        gaps = []
        for a, b in zip(line, line[1:]):
            gaps.append((b.x - (a.x + a.w), a, b))
        gap_vals = sorted(g[0] for g in gaps)
        gap_thresh = med_h * 1.0
        if gap_vals:
            big = [g for g in gap_vals if g > med_h * 0.9]
            if big:
                gap_thresh = min(big)
        groups = [[line[0]]]
        for gap, _, b in gaps:
            if gap >= gap_thresh:
                groups.append([b])
            else:
                groups[-1].append(b)
        for g in groups:
            cx = np.mean([w.cx for w in g])
            segments.append((cx, li, g))
    centers = sorted(s[0] for s in segments)
    anchors = []
    for c in centers:
        if anchors and c - anchors[-1][-1] <= med_h * 1.4:
            anchors[-1].append(c)
        else:
            anchors.append([c])
    anchor_x = [float(np.mean(a)) for a in anchors]
    n_lines = len(line_words)
    raw = [dict() for _ in range(n_lines)]
    for cx, li, g in segments:
        col = min(range(len(anchor_x)), key=lambda k: abs(anchor_x[k] - cx))
        prev = raw[li].get(col)
        raw[li][col] = (prev + g) if prev else g
    rows = []
    for line_map in raw:
        if not line_map:
            continue
        row = []
        for col in range(len(anchor_x)):
            row.append(_cell_text(line_map.get(col, [])))
        row = list(reversed(row))
        if any(x.strip() for x in row):
            rows.append(row)
    if rows:
        n = max(len(r) for r in rows)
        for r in rows:
            r += [""] * (n - len(r))
        keep = [j for j in range(n) if any(r[j].strip() for r in rows)]
        rows = [[r[j] for j in keep] for r in rows]
    return rows


def build_paragraph_lines(words):
    """کلمه‌ها -> سطرهای متن - با استفاده از line_num تسرکت برای حفظ معنی"""
    if not words:
        return []
    
    heights = [w.h for w in words]
    med_h = float(np.median(heights)) if heights else 15
    std_h = float(np.std(heights)) if len(heights) > 1 else 0
    is_handwritten = std_h > med_h * 0.4 or med_h > 22
    
    lines = _cluster_lines(words, is_handwritten=is_handwritten)
    out = []
    
    for line in lines:
        if not line:
            continue
        all_text = " ".join(w.text for w in line)
        lat = len(LATIN_RE.findall(all_text))
        per = len(PERSIAN_RE.findall(all_text))
        
        # مرتب‌سازی داخل خط
        if lat > per:
            ordered = sorted(line, key=lambda w: (w.word_num, w.x))
        else:
            # فارسی: راست به چپ
            # اگر word_num داریم، از آن استفاده کن (ترتیب منطقی تسرکت)
            # وگرنه بر اساس x
            if any(w.word_num != 0 for w in line):
                # تسرکت برای فارسی، word_num از راست به چپ است یا چپ به راست؟
                # معمولاً از چپ به راست ذخیره می شود ولی نمایش راست به چپ است
                # برای اطمینان، بر اساس x مرتب می کنیم
                ordered = sorted(line, key=lambda w: -w.cx)
            else:
                ordered = sorted(line, key=lambda w: -w.cx)
        
        text = " ".join(w.text for w in ordered if w.text).strip()
        text = re.sub(r'\s+', ' ', text)
        if text:
            out.append(text)
    
    # فیلتر نویز
    filtered = []
    for line in out:
        if len(line) < 2 and len(out) > 2:
            if re.match(r'^[|_\-—–¦lI1\s]+$', line):
                continue
        # حذف خطوطی که فقط یک کاراکتر بی‌معنی هستند
        if len(line) == 1 and line in ['|', '_', '-', '¦']:
            continue
        filtered.append(line)
    
    return filtered


def words_from_tesseract_data(data):
    """تبدیل خروجی image_to_data به Word - با line_num - نسخه با فیلتر کمتر"""
    words = []
    n = len(data.get("text", []))
    for i in range(n):
        text = clean_ocr_word(data["text"][i])
        if not text:
            continue
        # فقط کاراکترهای واقعاً بی‌معنی را فیلتر کن
        if len(text) == 1 and text in ['|', '_', '—', '–', '¦']:
            try:
                conf = float(data["conf"][i])
                if conf < 30:  # اگر اطمینان کم و کاراکتر بی‌معنی
                    continue
            except:
                pass
        
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf < 0:
            continue
        if conf < 3:  # فیلتر خیلی کم - قبلاً 8 بود
            continue
            
        try:
            x = int(data["left"][i])
            y = int(data["top"][i])
            w = int(data["width"][i])
            h = int(data["height"][i])
            if w < 1 or h < 1 or w > 8000 or h > 8000:
                continue
            block_num = int(data.get("block_num", [0]*n)[i])
            par_num = int(data.get("par_num", [0]*n)[i])
            line_num = int(data.get("line_num", [0]*n)[i])
            word_num = int(data.get("word_num", [0]*n)[i])
        except:
            continue
            
        words.append(Word(
            x=x, y=y, w=w, h=h, text=text, conf=conf,
            block_num=block_num, par_num=par_num, 
            line_num=line_num, word_num=word_num
        ))
    return words
