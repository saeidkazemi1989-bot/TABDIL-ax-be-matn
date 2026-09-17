# -*- coding: utf-8 -*-
"""خروجی‌سازها:
  جدول تایپی  -> Excel (.xlsx) یا Word جدول‌دار (.docx)
  متن/دست‌نویس -> Word پاراگرافی (.docx) یا Excel سطری (.xlsx)
همه فایل‌ها با فونت Calibri (طبق خواسته کاربر) و راست‌به‌چپ ساخته می‌شوند.
بهبود برای دست‌نویس: پاراگراف‌بندی هوشمند، حفظ معنی و مفهوم
"""
import os
import re

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from .util import OUTPUT_FONT, safe_sheet_name

HEADER_FILL = PatternFill("solid", fgColor="DCE6F1")
THIN = Side(style="thin", color="B7C3D0")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEADER_FONT = Font(name=OUTPUT_FONT, size=11, bold=True, color="1F3864")
BODY_FONT = Font(name=OUTPUT_FONT, size=11)
TITLE_FONT = Font(name=OUTPUT_FONT, size=14, bold=True, color="1F3864")
HANDWRITING_FONT = Font(name=OUTPUT_FONT, size=12)  # کمی بزرگتر برای دست‌نویس


# ================================================================ Excel

def _sheet_rtl(ws):
    ws.sheet_view.rightToLeft = True


def _write_matrix(ws, rows, header=True, title=None, is_handwritten=False):
    r0 = 1
    if title:
        ws.cell(row=1, column=1, value=title).font = TITLE_FONT
        ws.row_dimensions[1].height = 24
        r0 = 2
    for i, row in enumerate(rows):
        r = r0 + i
        for j, val in enumerate(row):
            # هندل None
            if val is None:
                val = ""
            c = ws.cell(row=r, column=j + 1, value=str(val) if not isinstance(val, (int, float)) else val)
            # برای دست‌نویس فونت کمی بزرگتر
            if is_handwritten:
                c.font = Font(name=OUTPUT_FONT, size=12, bold=(header and i==0))
            else:
                c.font = HEADER_FONT if (header and i == 0) else BODY_FONT
            c.alignment = Alignment(horizontal="right", vertical="center",
                                    wrap_text=True)
            c.border = BORDER
            if header and i == 0:
                c.fill = HEADER_FILL
        ws.row_dimensions[r].height = 22 if (header and i == 0) else 18

    if rows:
        ncols = max(len(r) for r in rows)
        for j in range(ncols):
            letter = get_column_letter(j + 1)
            width = 12
            for r in rows:
                if j < len(r) and r[j]:
                    # تقریب عرض برای فارسی/لاتین
                    L = sum(2 if ord(ch) > 0x0600 else 1 for ch in str(r[j]))
                    width = max(width, min(60 if is_handwritten else 45, L + 3))
            ws.column_dimensions[letter].width = width
    ws.freeze_panes = "A2" if not title else "A3"


def export_excel_tables(sheets, path, multi_sheet=True):
    """sheets: [{'name','rows'}] برای جداول."""
    wb = Workbook()
    wb.remove(wb.active)
    if multi_sheet:
        used = set()
        for idx, sh in enumerate(sheets):
            nm = safe_sheet_name(sh["name"], f"Sheet{idx+1}")
            base, k = nm, 1
            while nm in used:
                k += 1
                nm = f"{base[:25]}_{k}"
            used.add(nm)
            ws = wb.create_sheet(nm)
            _sheet_rtl(ws)
            _write_matrix(ws, sh["rows"])
    else:
        ws = wb.create_sheet("TABDIL")
        _sheet_rtl(ws)
        combined = []
        for sh in sheets:
            combined.append([sh["name"]])
            combined.extend(sh["rows"])
            combined.append([])
        _write_matrix(ws, combined, header=False)
    wb.save(path)
    return path


def export_excel_lines(sheets, path, multi_sheet=True):
    """هر خط متن در یک ردیف (ستون ردیف + متن) - بهبود برای دست‌نویس"""
    wb = Workbook()
    wb.remove(wb.active)
    
    # تشخیص دست‌نویس بودن: اگر میانگین طول خطوط کوتاه و تعداد خطوط زیاد باشد
    is_handwritten = False
    if sheets:
        total_lines = sum(len(sh.get("lines", [])) for sh in sheets)
        if total_lines > 5:
            is_handwritten = True
    
    if multi_sheet and len(sheets) > 1:
        used = set()
        for idx, sh in enumerate(sheets):
            nm = safe_sheet_name(sh["name"], f"Sheet{idx+1}")
            k, base = 1, nm
            while nm in used:
                k += 1
                nm = f"{base[:25]}_{k}"
            used.add(nm)
            ws = wb.create_sheet(nm)
            _sheet_rtl(ws)
            rows = [["ردیف", "متن"]] + [[i + 1, line] for i, line in enumerate(sh["lines"])]
            _write_matrix(ws, rows, is_handwritten=is_handwritten)
    else:
        ws = wb.create_sheet("TABDIL")
        _sheet_rtl(ws)
        # برای دست‌نویس، پاراگراف‌بندی: خطوط خالی را حفظ کن
        rows = [["فایل", "ردیف", "متن"]]
        for sh in sheets:
            for i, line in enumerate(sh["lines"]):
                # اگر خط خالی باشد، پاراگراف جدید است
                if not line.strip():
                    rows.append(["", "", ""])
                else:
                    rows.append([sh["name"], i + 1, line])
        _write_matrix(ws, rows, is_handwritten=is_handwritten)
    wb.save(path)
    return path


# ================================================================ Word

def _set_run_font(run, size=11, bold=False, color=None):
    run.font.name = OUTPUT_FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), OUTPUT_FONT)
    rtl = OxmlElement("w:rtl")
    rtl.set(qn("w:val"), "1")
    rPr.append(rtl)


def _rtl_paragraph(p):
    pPr = p._p.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    pPr.append(bidi)
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def _set_table_rtl(table):
    tblPr = table._tbl.tblPr
    bidi = OxmlElement("w:bidiVisual")
    bidi.set(qn("w:val"), "1")
    tblPr.append(bidi)
    table.alignment = WD_TABLE_ALIGNMENT.RIGHT


def _new_doc():
    doc = Document()
    # فونت پیش‌فرض استایل Normal
    style = doc.styles["Normal"]
    style.font.name = OUTPUT_FONT
    style.font.size = Pt(11)
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), OUTPUT_FONT)
    # جهت کلی سند RTL و حاشیه‌ها
    sect = doc.sections[0]
    sect.left_margin = Cm(1.8)
    sect.right_margin = Cm(1.8)
    sectPr = sect._sectPr
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    sectPr.append(bidi)
    return doc


def _add_heading(doc, text, size=13):
    p = doc.add_paragraph()
    _rtl_paragraph(p)
    run = p.add_run(text)
    _set_run_font(run, size=size, bold=True, color=(31, 56, 100))
    return p


def _shade_cell(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _fill_cell(cell, text, bold=False, header=False):
    # پاک کردن کامل سلول برای جلوگیری از double run
    cell.text = ""
    # حذف run های اضافی که cell.text ساخته
    p = cell.paragraphs[0]
    # پاک کردن همه run ها
    for _ in range(len(p.runs)):
        try:
            p.runs[0]._element.getparent().remove(p.runs[0]._element)
        except:
            break
    _rtl_paragraph(p)
    clean_text = "" if text is None else str(text)
    run = p.add_run(clean_text)
    _set_run_font(run, size=10.5, bold=bold or header,
                  color=(31, 56, 100) if header else None)
    if header:
        _shade_cell(cell, "DCE6F1")


def export_word_tables(sheets, path):
    doc = _new_doc()
    for si, sh in enumerate(sheets):
        if si > 0:
            doc.add_paragraph()
        _add_heading(doc, sh["name"], size=12)
        rows = sh["rows"]
        if not rows:
            continue
        ncols = max(len(r) for r in rows)
        table = doc.add_table(rows=len(rows), cols=ncols)
        table.style = "Table Grid"
        _set_table_rtl(table)
        for ri, row in enumerate(rows):
            for ci in range(ncols):
                val = row[ci] if ci < len(row) else ""
                _fill_cell(table.rows[ri].cells[ci], val, header=(ri == 0))
    doc.save(path)
    return path


def _group_handwritten_lines(lines):
    """گروه‌بندی خطوط دست‌نویس به پاراگراف‌های منطقی"""
    if not lines:
        return []
    
    paragraphs = []
    current_para = []
    
    for line in lines:
        line = line.strip()
        if not line:
            # خط خالی = پاراگراف جدید
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            continue
        
        # اگر خط خیلی کوتاه باشد و با نقطه تمام شده باشد، احتمالاً پایان پاراگراف
        # اما برای دست‌نویس فارسی، این قانون همیشه درست نیست
        # پس فقط خطوط خالی را به عنوان جداکننده در نظر می گیریم
        
        # اگر خط با کلمه ربط شروع شود، احتمالاً ادامه پاراگراف قبلی است
        # کلمات ربط فارسی
        connectors = ["و", "به", "از", "در", "که", "با", "برای", "تا", "را"]
        first_word = line.split()[0] if line.split() else ""
        
        # اگر خط قبلی ناتمام به نظر برسد (بدون نقطه) و این خط کوتاه باشد، بچسبان
        if current_para and len(current_para[-1]) < 20 and not current_para[-1].endswith(('.', '。', '؟', '!', ':', '؛')):
            # اگر فاصله معنایی نزدیک باشد، به پاراگراف قبلی بچسبان
            # برای سادگی، فعلاً هر خط را جدا نگه می داریم تا معنی حفظ شود
            pass
        
        current_para.append(line)
        
        # اگر خط با نقطه تمام شده و طولانی است، پاراگراف جدید شروع کن
        # اما برای دست‌نویس، معمولاً هر 2-3 خط یک پاراگراف است
        if len(" ".join(current_para)) > 200 and line.endswith(('.', '。', '؟', '!', ':', '؛')):
            paragraphs.append(" ".join(current_para))
            current_para = []
    
    if current_para:
        paragraphs.append(" ".join(current_para))
    
    # اگر پاراگراف‌بندی خیلی به هم ریخت، همان خطوط اصلی را برگردان
    # اما اگر پاراگراف‌ها منطقی هستند، آنها را نگه دار
    # برای حفظ معنی، اگر تعداد پاراگراف‌ها خیلی کمتر از خطوط باشد، خطوط را نگه دار
    if len(paragraphs) == 0:
        return lines
    # اگر پاراگراف‌بندی باعث ادغام بیش از حد شده، خطوط اصلی بهتر است
    # تصمیم: اگر میانگین طول پاراگراف > 300 کاراکتر، خطوط را ترجیح بده
    avg_len = sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0
    if avg_len > 400:
        return lines
    return paragraphs


def export_word_text(sheets, path):
    """خروجی Word برای متن/دست‌نویس - بهبود یافته برای حفظ معنی"""
    doc = _new_doc()
    
    # تشخیص دست‌نویس بودن
    is_handwritten = False
    total_lines = sum(len(sh.get("lines", [])) for sh in sheets)
    if total_lines > 4:
        is_handwritten = True
    
    for si, sh in enumerate(sheets):
        if si > 0:
            doc.add_paragraph()
        _add_heading(doc, sh["name"], size=12)
        
        lines = sh["lines"]
        if not lines:
            continue
        
        # برای دست‌نویس، سعی کن پاراگراف‌بندی هوشمند انجام دهی
        # اما معنی را حفظ کن - خطوط را به هم نریز
        if is_handwritten:
            # برای دست‌نویس، هر خط را جداگانه نگه دار تا معنی حفظ شود
            # اما خطوط خیلی کوتاه را که احتمالاً ادامه خط قبل هستند، بچسبان
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # حذف کاراکترهای نویز
                # اگر خط فقط شامل علائم باشد، نادیده بگیر
                if re.match(r'^[|_\-—–¦lI1\s]+$', line):
                    continue
                cleaned_lines.append(line)
            
            # حالا هر خط را به عنوان پاراگراف جدا بنویس تا معنی حفظ شود
            # اما با فاصله مناسب
            for line in cleaned_lines:
                p = doc.add_paragraph()
                _rtl_paragraph(p)
                # برای دست‌نویس، فونت کمی بزرگتر و فاصله بیشتر
                run = p.add_run(line)
                _set_run_font(run, size=12 if is_handwritten else 11)
                p.paragraph_format.space_after = Pt(6 if is_handwritten else 4)
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.line_spacing = 1.15 if is_handwritten else 1.0
        else:
            # برای متن تایپی، همان روش قبلی
            for line in lines:
                if not line.strip():
                    doc.add_paragraph()
                    continue
                p = doc.add_paragraph()
                _rtl_paragraph(p)
                run = p.add_run(line)
                _set_run_font(run, size=11)
                p.paragraph_format.space_after = Pt(4)
    
    doc.save(path)
    return path
