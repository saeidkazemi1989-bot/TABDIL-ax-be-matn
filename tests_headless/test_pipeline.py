# -*- coding: utf-8 -*-
"""تست بدون رابط گرافیکی خط لوله OCR روی نمونه‌عکس‌ها (فقط برای توسعه در لینوک).
به جای tesseract.exe از موتور tesserocr (که همان libtesseract است) استفاده می‌کند.
"""
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'windows_app'))

import numpy as np
from PIL import Image
import tesserocr

from TABDIL import ocr, table, exporter
from TABDIL.preprocess import load_gray, enhance_gray, polish_gray
from TABDIL.orientation import upright

TESSDATA = os.path.abspath(os.path.join(os.path.dirname(__file__), '..',
                                        'windows_app', 'TABDIL', 'tessdata'))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

PSM_MAP = {'0': tesserocr.PSM.OSD_ONLY, '6': tesserocr.PSM.SINGLE_BLOCK,
           '3': tesserocr.PSM.AUTO, '4': tesserocr.PSM.SINGLE_COLUMN,
           '11': tesserocr.PSM.SPARSE_TEXT}


class _OSD:
    @staticmethod
    def detect(pil):
        import cv2
        arr = np.array(pil)
        h, w = arr.shape[:2]
        s = min(1.0, 1400.0 / max(h, w))
        if s < 1.0:
            arr = cv2.resize(arr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            pil = Image.fromarray(arr)
        with tesserocr.PyTessBaseAPI(path=TESSDATA, lang='osd', psm=tesserocr.PSM.OSD_ONLY) as api:
            api.SetImage(pil)
            try:
                r = api.DetectOrientationScript()
            except Exception:
                r = None
        if not r:
            return "Rotate: 0\nOrientation: 0\nOrientation confidence: 0\n"
        return (f"Rotate: {r['orient_deg']}\nOrientation: {r['orient_deg']}\n"
                f"Orientation confidence: {r['orient_conf']:.2f}\n")


class FakePytesseract:
    class Output:
        DICT = 'dict'

    def __init__(self):
        self.pytesseract = self

    def image_to_data(self, image, lang='fas+eng', config='', output_type=None):
        import csv, io
        m = re.search(r'--psm\s+(\d+)', config)
        psm = PSM_MAP.get(m.group(1), tesserocr.PSM.SINGLE_BLOCK) if m else tesserocr.PSM.SINGLE_BLOCK
        if isinstance(image, np.ndarray):
            pil = Image.fromarray(image)
        else:
            pil = image
        data = {'left': [], 'top': [], 'width': [], 'height': [],
                'text': [], 'conf': [], 'level': [], 'page_num': [],
                'block_num': [], 'par_num': [], 'line_num': [], 'word_num': []}
        with tesserocr.PyTessBaseAPI(path=TESSDATA, lang=lang, psm=psm) as api:
            api.SetImage(pil)
            api.Recognize()
            tsv = api.GetTSVText(0)
        header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        reader = csv.DictReader(io.StringIO(header + tsv), delimiter='\t')
        for row in reader:
            for k in data:
                if k == 'text':
                    data[k].append(row.get('text', ''))
                else:
                    try:
                        data[k].append(int(float(row.get(k, 0))))
                    except (TypeError, ValueError):
                        data[k].append(0)
        return data

    def image_to_osd(self, image, lang='osd', config=''):
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        return _OSD.detect(image)


def main():
    fake = FakePytesseract()
    ocr.pytesseract = fake
    engine = ocr.TesseractEngine.__new__(ocr.TesseractEngine)
    engine._pytesseract = fake
    import threading
    engine._lock = threading.Lock()

    images = sorted(f for f in os.listdir(REPO) if f.lower().endswith('.jpg'))
    outdir = os.path.join(os.path.dirname(__file__), 'out')
    os.makedirs(outdir, exist_ok=True)
    sheets_table, sheets_text = [], []
    for fn in images:
        path = os.path.join(REPO, fn)
        print('=' * 70)
        print(fn)
        raw = load_gray(path)
        osd = engine.osd_degrees(raw)
        gray0, k, is_tab = upright(raw, quick_ocr_conf=lambda g: engine.quick_conf(g, 'fas+eng'),
                                   osd_result=osd)
        print(f'orientation: rot_k={k} table_crop={is_tab} (osd={osd})')
        light, _, _ = enhance_gray(gray0, True, polish=False)
        if is_tab:
            c = table.table_crop(light)
            if c is not light:
                light = c
        xs, ys = table.detect_grid(light)
        kind = 'table' if (table.is_table_like(light, xs, ys) or is_tab) else 'text'
        if kind == 'table':
            ocr_img = polish_gray(table.remove_grid_lines(light, xs, ys))
        else:
            ocr_img, _, _ = enhance_gray(gray0, True, polish=True)
        gray = light
        print(f'grid: vlines={len(xs)} hlines={len(ys)} -> {kind}, size={gray.shape[1]}x{gray.shape[0]}')
        words, conf = engine.recognize(ocr_img, 'fas+eng', kind == 'table')
        print(f'words={len(words)} conf={conf:.1f}')
        if kind == 'table':
            if len(xs) >= 2 and len(ys) >= 4:
                rows = table.build_table_from_grid(words, xs, ys, gray.shape[1], gray.shape[0])
            else:
                rows = table.build_table_fallback(words)
            print(f'rows={len(rows)}, cols={max((len(r) for r in rows), default=0)}')
            for r in rows[:8]:
                print(' | '.join(r))
            sheets_table.append({'name': fn.split('.')[0][:20], 'rows': rows})
        else:
            lines = table.build_paragraph_lines(words)
            print(f'lines={len(lines)}')
            for l in lines[:10]:
                print('   ', l)
            sheets_text.append({'name': fn.split('.')[0][:20], 'lines': lines})

    if sheets_table:
        exporter.export_excel_tables(sheets_table, os.path.join(outdir, 'tables.xlsx'))
        exporter.export_word_tables(sheets_table, os.path.join(outdir, 'tables.docx'))
    if sheets_text:
        exporter.export_word_text(sheets_text, os.path.join(outdir, 'text.docx'))
        exporter.export_excel_lines(sheets_text, os.path.join(outdir, 'text.xlsx'))
    print('\nOUTPUTS in', outdir)


if __name__ == '__main__':
    main()
