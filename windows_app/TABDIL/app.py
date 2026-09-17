# -*- coding: utf-8 -*-
"""برنامه ویندوزی TABDIL - تبدیل عکس صفحات تایپی/دست‌نویس به اکسل و ورد.

اجرا:
    python run_app.py
"""
import os
import queue
import threading
import datetime
import traceback

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image

from . import __version__
from .util import ASSETS_DIR, safe_sheet_name, split_stem, OUTPUT_FONT
from .preprocess import load_gray, enhance_gray, polish_gray
from .orientation import upright
from .table import (detect_grid, is_table_like, build_table_from_grid,
                    build_table_fallback, build_paragraph_lines,
                    remove_grid_lines, table_crop)
from .ocr import TesseractEngine, PaddleEngine
from . import exporter
from . import license as license_module

# کشیدن و رها کردن فایل (اختیاری)
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True

    class _BaseTk(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
except Exception:
    DND_AVAILABLE = False
    _BaseTk = ctk.CTk

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

FONT = "Tahoma"
IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif")

MODE_LABELS = ["خودکار (پیشنهادی)", "جدولی تایپی", "متن / دست‌نویس"]
MODE_VALUES = ["auto", "table", "text"]
LANG_LABELS = ["فارسی + انگلیسی", "فقط فارسی", "فقط انگلیسی"]
LANG_VALUES = ["fas+eng", "fas", "eng"]


class App(_BaseTk):
    def __init__(self):
        super().__init__()

        # --- چک لایسنس ---
        self.license_valid, self.license_days, self.license_msg, self.license_payload = license_module.check_license()
        if not self.license_valid:
            # سعی کن تریال 30 روزه بسازی
            self.license_valid, self.license_days, self.license_msg, self.license_payload = license_module.ensure_trial_license(days=30)
        
        if not self.license_valid:
            messagebox.showerror(
                "لایسنس منقضی شده",
                f"لایسنس برنامه منقضی شده یا یافت نشد.\n\n{self.license_msg}\n\n"
                "لطفاً با پشتیبانی تماس بگیرید یا فایل license.key جدید را در کنار برنامه قرار دهید.\n\n"
                "برنامه بسته خواهد شد."
            )
            self.after(100, self.destroy)
            return

        self.title(f"TABDIL {__version__} - تبدیل عکس به اکسل و ورد")
        self.geometry("1280x860")
        self.minsize(1100, 750)
        try:
            self.iconbitmap(os.path.join(ASSETS_DIR, "logo.ico"))
        except Exception:
            pass

        self.files = []          # مسیر فایل‌ها
        self.thumb_imgs = {}
        self.sheets = []         # نتیجه OCR
        self.entry_grids = {}
        self.msg_queue = queue.Queue()
        self.worker_busy = False
        self.last_save_dir = None

        self._build_ui()
        self._check_engines()
        self._show_license_info()
        self.after(120, self._poll_queue)

    def _show_license_info(self):
        # نمایش وضعیت لایسنس در استاتوس بار بعد از کمی تاخیر
        def _show():
            if hasattr(self, 'license_status_lbl'):
                txt = license_module.get_license_status_text()
                self.license_status_lbl.configure(text=txt)
                if not self.license_valid or self.license_days <= 3:
                    self.license_status_lbl.configure(text_color="#dc2626")
                elif self.license_days <= 7:
                    self.license_status_lbl.configure(text_color="#d97706")
        self.after(500, _show)

    # ------------------------------------------------------------- UI
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=350)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_sidebar()
        self._build_main()

    def _build_header(self):
        bar = ctk.CTkFrame(self, corner_radius=0, height=90,
                           fg_color="#ffffff", border_width=0)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_columnconfigure(1, weight=0)
        bar.grid_columnconfigure(2, weight=0)
        
        # لوگو بزرگتر - از logo.png استفاده می کنیم با کیفیت بهتر
        try:
            # اول logo.png را امتحان کن (باکیفیت تر)، اگر نبود logo_small.png
            logo_path = os.path.join(ASSETS_DIR, "logo.png")
            if not os.path.exists(logo_path):
                logo_path = os.path.join(ASSETS_DIR, "logo_small.png")
            
            logo_img = Image.open(logo_path)
            # لوگو بزرگتر: 72x72 به جای 40x40
            logo = ctk.CTkImage(logo_img, size=(72, 72))
            lbl = ctk.CTkLabel(bar, image=logo, text="")
            lbl.image = logo
            lbl.grid(row=0, column=2, rowspan=2, padx=(8, 20), pady=8)
        except Exception as e:
            print(f"Logo load failed: {e}")
            pass
        
        ctk.CTkLabel(bar, text="TABDIL", font=ctk.CTkFont(FONT, 24, "bold"),
                     text_color="#1e3a8a").grid(row=0, column=1, padx=14, sticky="w", pady=(10,0))
        ctk.CTkLabel(bar, text="تبدیل هوشمند عکس جدول و یادداشت به اکسل و ورد  •  فونت خروجی: " + OUTPUT_FONT,
                     font=ctk.CTkFont(FONT, 12), text_color="#64748b"
                     ).grid(row=1, column=1, padx=14, sticky="w", pady=(0,8))
        
        # عنوان اصلی
        title_frame = ctk.CTkFrame(bar, fg_color="transparent")
        title_frame.grid(row=0, column=0, rowspan=2, padx=16, sticky="e")
        ctk.CTkLabel(title_frame, text="کیفیت سازه پویش", font=ctk.CTkFont(FONT, 16, "bold"),
                     text_color="#14532d").pack(anchor="e")
        ctk.CTkLabel(title_frame, text="سعید کاظمی پور - 09216895359", font=ctk.CTkFont(FONT, 12, "bold"),
                     text_color="#1e3a8a").pack(anchor="e")
        ctk.CTkLabel(title_frame, text="سیستم هوشمند تبدیل تصاویر به متن",
                     font=ctk.CTkFont(FONT, 11), text_color="#64748b").pack(anchor="e")
        
        # وضعیت لایسنس در هدر
        self.license_status_lbl = ctk.CTkLabel(title_frame, text="در حال بررسی لایسنس...",
                                               font=ctk.CTkFont(FONT, 10, "bold"),
                                               text_color="#059669")
        self.license_status_lbl.pack(anchor="e", pady=(2,0))

    def _section(self, parent, title):
        f = ctk.CTkFrame(parent, fg_color="#ffffff", border_width=1,
                         border_color="#e2e8f0", corner_radius=14)
        f.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(FONT, 13, "bold"),
                     text_color="#0f172a", anchor="e").pack(
            anchor="e", padx=14, pady=(12, 6))
        return f

    def _build_sidebar(self):
        side = ctk.CTkScrollableFrame(self, width=340, fg_color="#f1f5f9",
                                      corner_radius=0)
        side.grid(row=1, column=1, sticky="nsew")

        # --- انتخاب عکس
        up = self._section(side, "۱) عکس‌ها")
        drop = ctk.CTkFrame(up, fg_color="#f8fafc", border_width=2,
                            border_color="#cbd5e1", corner_radius=12)
        drop.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(drop, text="📂  عکس‌ها را اینجا رها کنید\nیا کلیک کنید",
                     font=ctk.CTkFont(FONT, 12), justify="center",
                     text_color="#475569").pack(pady=10)
        ctk.CTkButton(drop, text="انتخاب عکس (چندتایی هم می‌شود)",
                      font=ctk.CTkFont(FONT, 12, "bold"), height=38,
                      command=self.pick_files).pack(fill="x", padx=12, pady=(0, 10))
        drop.bind("<Button-1>", lambda e: self.pick_files())
        if DND_AVAILABLE:
            for w in (up, drop):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self._on_drop)
        self.drop_hint = drop

        self.file_frame = ctk.CTkFrame(up, fg_color="transparent")
        self.file_frame.pack(fill="x", padx=12)
        self.file_count_lbl = ctk.CTkLabel(up, text="هنوز عکسی انتخاب نشده",
                                           font=ctk.CTkFont(FONT, 11),
                                           text_color="#94a3b8")
        self.file_count_lbl.pack(pady=(0, 10))
        ctk.CTkButton(up, text="پاک کردن همه عکس‌ها", height=28,
                      fg_color="#fee2e2", hover_color="#fecaca",
                      text_color="#b91c1c", font=ctk.CTkFont(FONT, 11),
                      command=self.clear_files).pack(fill="x", padx=12, pady=(0, 12))

        # --- نوع صفحه
        s2 = self._section(side, "۲) نوع صفحه")
        self.mode_menu = ctk.CTkOptionMenu(s2, values=MODE_LABELS,
                                          font=ctk.CTkFont(FONT, 12), height=34,
                                          dropdown_font=ctk.CTkFont(FONT, 12))
        self.mode_menu.set(MODE_LABELS[0])
        self.mode_menu.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(s2, text="💡 برای دست‌نویس، 'متن / دست‌نویس' را انتخاب کنید",
                     font=ctk.CTkFont(FONT, 10), text_color="#059669",
                     wraplength=280, justify="right").pack(fill="x", padx=12, pady=(0,8))

        # --- موتور و زبان
        s3 = self._section(side, "۳) موتور تشخیص و زبان")
        ctk.CTkLabel(s3, text="موتور OCR:", font=ctk.CTkFont(FONT, 11),
                     anchor="e").pack(anchor="e", padx=14)
        self.engine_seg = ctk.CTkSegmentedButton(
            s3, values=["سبک (Tesseract)", "دقیق (PaddleOCR)"],
            font=ctk.CTkFont(FONT, 11), height=32,
            command=self._engine_changed)
        self.engine_seg.set("سبک (Tesseract)")
        self.engine_seg.pack(fill="x", padx=12, pady=(2, 6))
        self.engine_status = ctk.CTkLabel(s3, text="", font=ctk.CTkFont(FONT, 10),
                                          justify="right", anchor="e",
                                          text_color="#94a3b8", wraplength=280)
        self.engine_status.pack(fill="x", padx=12, pady=(0, 2))

        # دکمه راهنما برای Paddle
        self.paddle_help_btn = ctk.CTkButton(
            s3, text="❓ راهنمای موتور دقیق (VPN)",
            font=ctk.CTkFont(FONT, 10), height=26,
            fg_color="#fef3c7", hover_color="#fde68a",
            text_color="#92400e", border_width=1, border_color="#f59e0b",
            command=self._show_paddle_help)
        # فقط وقتی Paddle انتخاب است نشان داده می‌شود

        ctk.CTkLabel(s3, text="زبان:", font=ctk.CTkFont(FONT, 11),
                     anchor="e").pack(anchor="e", padx=14, pady=(8, 0))
        self.lang_menu = ctk.CTkOptionMenu(s3, values=LANG_LABELS,
                                           font=ctk.CTkFont(FONT, 12), height=34,
                                           dropdown_font=ctk.CTkFont(FONT, 12))
        self.lang_menu.set(LANG_LABELS[0])
        self.lang_menu.pack(fill="x", padx=12, pady=(2, 10))

        self.enhance_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(s3, text="بهبود کیفیت / صاف‌کردن کجی عکس",
                        font=ctk.CTkFont(FONT, 11), variable=self.enhance_var
                        ).pack(anchor="e", padx=12, pady=(0, 12))

        # --- خروجی
        s4 = self._section(side, "۴) نوع خروجی")
        ctk.CTkLabel(s4, text="صفحات جدولی (لیست قطعات و...):",
                     font=ctk.CTkFont(FONT, 11), anchor="e"
                     ).pack(anchor="e", padx=14)
        self.table_fmt = ctk.CTkSegmentedButton(
            s4, values=["Excel", "Word جدول"], font=ctk.CTkFont(FONT, 11), height=30)
        self.table_fmt.set("Excel")
        self.table_fmt.pack(fill="x", padx=12, pady=(2, 8))

        ctk.CTkLabel(s4, text="صفحات متنی / دست‌نویس:",
                     font=ctk.CTkFont(FONT, 11), anchor="e"
                     ).pack(anchor="e", padx=14)
        self.text_fmt = ctk.CTkSegmentedButton(
            s4, values=["Word پاراگرافی", "Excel سطری"], font=ctk.CTkFont(FONT, 11), height=30)
        self.text_fmt.set("Word پاراگرافی")
        self.text_fmt.pack(fill="x", padx=12, pady=(2, 8))

        self.multi_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(s4, text="هر عکس = یک شیت جدا در اکسل",
                        font=ctk.CTkFont(FONT, 11), variable=self.multi_var
                        ).pack(anchor="e", padx=12)
        ctk.CTkLabel(s4, text=f"همه فایل‌های خروجی با فونت {OUTPUT_FONT} ذخیره می‌شوند.",
                     font=ctk.CTkFont(FONT, 10), text_color="#64748b",
                     wraplength=270, justify="right").pack(padx=12, pady=(8, 12))

        # --- اطلاعات تماس
        s5_info = self._section(side, "۵) اطلاعات")
        ctk.CTkLabel(s5_info, text="نام: سعید کاظمی پور", font=ctk.CTkFont(FONT, 11, "bold"),
                     text_color="#0f172a", anchor="e").pack(anchor="e", padx=12, pady=(2,0))
        ctk.CTkLabel(s5_info, text="موبایل: 09216895359", font=ctk.CTkFont(FONT, 11, "bold"),
                     text_color="#1e3a8a", anchor="e").pack(anchor="e", padx=12, pady=(0,2))
        ctk.CTkLabel(s5_info, text="کیفیت سازه پویش", font=ctk.CTkFont(FONT, 10),
                     text_color="#14532d", anchor="e").pack(anchor="e", padx=12, pady=(0,8))

        # --- لایسنس
        s5 = self._section(side, "۶) لایسنس")
        self.license_detail_lbl = ctk.CTkLabel(s5, text="در حال بارگذاری...",
                                               font=ctk.CTkFont(FONT, 10),
                                               text_color="#475569",
                                               wraplength=280, justify="right")
        self.license_detail_lbl.pack(fill="x", padx=12, pady=(4,8))
        ctk.CTkButton(s5, text="🔑 نمایش جزئیات لایسنس",
                      font=ctk.CTkFont(FONT, 11), height=30,
                      fg_color="#e0e7ff", hover_color="#c7d2fe",
                      text_color="#3730a3",
                      command=self._show_license_details).pack(fill="x", padx=12, pady=(0,4))
        ctk.CTkButton(s5, text="📁 بارگذاری لایسنس جدید",
                      font=ctk.CTkFont(FONT, 11), height=30,
                      fg_color="#dcfce7", hover_color="#bbf7d0",
                      text_color="#14532d",
                      command=self._load_new_license).pack(fill="x", padx=12, pady=(0,12))

        # --- اجرا
        self.convert_btn = ctk.CTkButton(
            side, text="🔎  شروع تشخیص", height=46,
            font=ctk.CTkFont(FONT, 14, "bold"),
            fg_color="#1d4ed8", hover_color="#1e40af",
            command=self.start_convert, state="disabled")
        self.convert_btn.pack(fill="x", pady=(4, 8))

    def _build_main(self):
        main = ctk.CTkFrame(self, corner_radius=0, fg_color="#f8fafc")
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_rowconfigure(2, weight=1)
        main.grid_columnconfigure(0, weight=1)

        self.progress = ctk.CTkProgressBar(main, height=14, corner_radius=7)
        self.progress.set(0)
        self.progress.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 2))
        self.status_lbl = ctk.CTkLabel(main, text="آماده - عکس‌ها را انتخاب کنید",
                                       font=ctk.CTkFont(FONT, 12),
                                       text_color="#475569", anchor="e")
        self.status_lbl.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        
        # فوتر با نام و شماره
        footer = ctk.CTkFrame(main, fg_color="#ffffff", corner_radius=0, height=28,
                              border_width=1, border_color="#e2e8f0")
        footer.grid(row=4, column=0, sticky="ew", padx=0, pady=(8,0))
        ctk.CTkLabel(footer, text="سعید کاظمی پور | 09216895359 | کیفیت سازه پویش",
                     font=ctk.CTkFont(FONT, 10), text_color="#64748b").pack(side="right", padx=16, pady=4)
        ctk.CTkLabel(footer, text=f"TABDIL v{__version__} - لایسنس 1 ماهه",
                     font=ctk.CTkFont(FONT, 9), text_color="#94a3b8").pack(side="left", padx=16, pady=4)

        # نوار ابزار نتیجه
        tools = ctk.CTkFrame(main, fg_color="transparent")
        tools.grid(row=3, column=0, sticky="ew", padx=16, pady=6)
        for t, cmd in [("＋ ردیف", self.add_row), ("＋ ستون", self.add_column),
                       ("－ حذف ردیف آخر", self.del_row), ("🔄 تازه‌سازی جدول", self.rerender_active)]:
            ctk.CTkButton(tools, text=t, width=110, height=30,
                          font=ctk.CTkFont(FONT, 11),
                          fg_color="#ffffff", text_color="#1e293b",
                          border_width=1, border_color="#cbd5e1",
                          hover_color="#f1f5f9", command=cmd).pack(side="right", padx=3)
        self.save_btn = ctk.CTkButton(tools, text="💾 ذخیره فایل خروجی", width=180, height=34,
                                      font=ctk.CTkFont(FONT, 12, "bold"),
                                      fg_color="#059669", hover_color="#047857",
                                      command=self.save_outputs, state="disabled")
        self.save_btn.pack(side="left", padx=3)
        self.quick_save_btn = ctk.CTkButton(tools, text="⚡ ذخیره سریع روی دسکتاپ", width=190, height=34,
                                      font=ctk.CTkFont(FONT, 11, "bold"),
                                      fg_color="#0ea5e9", hover_color="#0284c7",
                                      command=self.quick_save_to_desktop, state="disabled")
        self.quick_save_btn.pack(side="left", padx=6)

        # حالت خالی
        self.empty = ctk.CTkFrame(main, fg_color="#ffffff", corner_radius=16,
                                  border_width=1, border_color="#e2e8f0")
        self.empty.grid(row=2, column=0, sticky="nsew", padx=16, pady=(4, 8))
        ctk.CTkLabel(self.empty, text="🖼️", font=ctk.CTkFont(FONT, 56),
                     text_color="#94a3b8").pack(pady=(60, 8))
        ctk.CTkLabel(self.empty, text="هنوز عکسی انتخاب نشده",
                     font=ctk.CTkFont(FONT, 16, "bold")).pack()
        ctk.CTkLabel(self.empty,
                     text="عکس جدول تایپی یا یادداشت دست‌نویس را اضافه کنید.\n"
                          "بعد از تشخیص می‌توانید همه سلول‌ها را ویرایش کنید و\n"
                          "بین خروجی Excel یا Word انتخاب کنید.\n\n"
                          "💡 برای دست‌نویس: نوع صفحه را 'متن / دست‌نویس' بگذارید",
                     font=ctk.CTkFont(FONT, 12), justify="center",
                     text_color="#64748b").pack(pady=8)

        # نتایج (تب‌ها بعد از تشخیص ساخته و grid می‌شوند)
        self.tabs = ctk.CTkTabview(main, fg_color="#ffffff")

    # --------------------------------------------------------- files
    def pick_files(self):
        paths = filedialog.askopenfilenames(
            title="انتخاب عکس‌ها",
            filetypes=[("تصاویر", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.gif"),
                       ("همه فایل‌ها", "*.*")])
        self._add_files(paths)

    def _on_drop(self, event):
        raw = self.tk.splitlist(event.data)
        paths = []
        for p in raw:
            p = p.strip("{}")
            if os.path.isdir(p):
                for fn in sorted(os.listdir(p)):
                    if fn.lower().endswith(IMG_EXTS):
                        paths.append(os.path.join(p, fn))
            elif p.lower().endswith(IMG_EXTS):
                paths.append(p)
        self._add_files(paths)

    def _add_files(self, paths):
        added = 0
        for p in paths:
            if p not in self.files and p.lower().endswith(IMG_EXTS):
                self.files.append(p)
                added += 1
        if added:
            self._render_file_list()

    def clear_files(self):
        if self.worker_busy:
            return
        self.files = []
        self.sheets = []
        self.entry_grids = {}
        self._render_file_list()
        self.tabs.grid_remove()
        self.empty.grid()
        self.save_btn.configure(state="disabled")
        if hasattr(self, "quick_save_btn"):
            self.quick_save_btn.configure(state="disabled")
        self.progress.set(0)
        self.status_lbl.configure(text="آماده - عکس‌ها را انتخاب کنید")

    def _render_file_list(self):
        for w in self.file_frame.winfo_children():
            w.destroy()
        if not self.files:
            self.file_count_lbl.configure(text="هنوز عکسی انتخاب نشده")
            self.convert_btn.configure(state="disabled")
            return
        self.file_count_lbl.configure(text=f"{len(self.files)} عکس انتخاب شده")
        self.convert_btn.configure(state="normal")
        for idx, path in enumerate(self.files):
            row = ctk.CTkFrame(self.file_frame, fg_color="#ffffff",
                               border_width=1, border_color="#e2e8f0",
                               corner_radius=10)
            row.pack(fill="x", pady=3)
            try:
                if path not in self.thumb_imgs:
                    im = Image.open(path)
                    im.thumbnail((46, 46))
                    self.thumb_imgs[path] = ctk.CTkImage(im, size=im.size)
                thumb = ctk.CTkLabel(row, image=self.thumb_imgs[path], text="")
                thumb.image = self.thumb_imgs[path]
                thumb.pack(side="right", padx=6, pady=6)
            except Exception:
                pass
            name = os.path.basename(path)
            ctk.CTkLabel(row, text=name, font=ctk.CTkFont(FONT, 11, "bold"),
                         anchor="e", wraplength=190, justify="right"
                         ).pack(side="right", padx=4)
            ctk.CTkButton(row, text="✕", width=28, height=28,
                          fg_color="#fee2e2", hover_color="#fecaca",
                          text_color="#b91c1c",
                          command=lambda i=idx: self._remove_file(i)
                          ).pack(side="left", padx=6)

    def _remove_file(self, idx):
        if self.worker_busy:
            return
        self.files.pop(idx)
        self._render_file_list()

    # ------------------------------------------------------- engines
    def _engine_choice(self):
        return "paddle" if self.engine_seg.get().startswith("دقیق") else "tesseract"

    def _engine_changed(self, _=None):
        self._check_engines()

    def _check_engines(self):
        is_paddle = self._engine_choice() == "paddle"
        if not is_paddle:
            ok, msg = TesseractEngine.is_available()
            if ok:
                self.engine_status.configure(
                    text="✓ موتور سبک آماده است (آفلاین)", text_color="#059669")
            else:
                self.engine_status.configure(text="✗ " + msg, text_color="#dc2626")
            self.paddle_help_btn.pack_forget()
        else:
            ok, msg = PaddleEngine.is_available()
            if ok:
                if "vpn" in msg.lower() or "دانلود" in msg:
                    self.engine_status.configure(
                        text="⚠ موتور دقیق نصب است - اولین اجرا نیاز به VPN دارد",
                        text_color="#d97706")
                else:
                    self.engine_status.configure(
                        text="✓ موتور دقیق آماده است", text_color="#059669")
            else:
                self.engine_status.configure(text="✗ " + msg, text_color="#dc2626")
            self.paddle_help_btn.pack(fill="x", padx=12, pady=(0, 8))

    def _show_paddle_help(self):
        messagebox.showinfo(
            "راهنمای موتور دقیق PaddleOCR",
            "موتور دقیق (PaddleOCR) در اولین اجرا نیاز به دانلود مدل‌ها از اینترنت دارد.\n\n"
            "مشکل رایج در ایران:\n"
            "سرور مدل‌ها (Baidu) در ایران فیلتر یا بسیار کند است و برنامه روی "
            "\"در حال آماده‌سازی موتور تشخیص...\" می‌ماند.\n\n"
            "راه‌حل‌ها:\n"
            "۱) VPN روشن کنید و دوباره \"شروع تشخیص\" را بزنید. اولین دانلود چند دقیقه طول می‌کشد.\n"
            "۲) یا فایل Download-PaddleModels.bat را با VPN اجرا کنید تا مدل‌ها از قبل دانلود شوند.\n"
            "۳) اگر VPN ندارید، از موتور سبک (Tesseract) استفاده کنید که کاملاً آفلاین است و برای جدول‌های تایپی دقت خوبی دارد.\n\n"
            "نکته: اگر قبلاً دانلود ناقص انجام شده، این پوشه‌ها را حذف کنید:\n"
            "C:\\Users\\<نام شما>\\.paddleocr\n"
            "C:\\Users\\<نام شما>\\.paddlex\n"
            "و دوباره با VPN تلاش کنید."
        )

    def _show_license_details(self):
        valid, days_left, msg, payload = license_module.check_license()
        if payload:
            details = (
                f"نام: سعید کاظمی پور\n"
                f"موبایل: 09216895359\n"
                f"شرکت: کیفیت سازه پویش\n"
                f"----------------------------\n"
                f"وضعیت: {'معتبر' if valid else 'منقضی'}\n"
                f"نوع: {payload.get('type','نامشخص')}\n"
                f"تاریخ ساخت: {payload.get('created','?')}\n"
                f"تاریخ انقضا: {payload.get('exp','?')}\n"
                f"روزهای باقی‌مانده: {days_left}\n"
                f"شناسه: {payload.get('hwid','?')}\n\n"
                f"{msg}\n\n"
                "برای تمدید، فایل license.key جدید را از پشتیبانی دریافت کنید\n"
                "و با دکمه 'بارگذاری لایسنس جدید' آن را انتخاب کنید."
            )
        else:
            details = f"نام: سعید کاظمی پور\nموبایل: 09216895359\n\nلایسنس یافت نشد\n\n{msg}\n\nبرای دریافت لایسنس با پشتیبانی تماس بگیرید."
        
        messagebox.showinfo("جزئیات لایسنس", details)
        # آپدیت نمایش
        if hasattr(self, 'license_detail_lbl'):
            self.license_detail_lbl.configure(text=license_module.get_license_status_text() + f"\n{msg}")

    def _load_new_license(self):
        path = filedialog.askopenfilename(
            title="فایل لایسنس را انتخاب کنید",
            filetypes=[("License files", "*.key *.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            # اگر فایل متنی با توضیحات باشد، فقط خط آخر که لایسنس است را بگیر
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            # لایسنس معمولاً طولانی است و شامل نقطه است
            license_content = None
            for line in reversed(lines):
                if '.' in line and len(line) > 50:
                    license_content = line
                    break
            if not license_content:
                license_content = content
            
            # اعتبارسنجی
            payload, err = license_module._parse_license(license_content)
            if err:
                messagebox.showerror("خطا", f"لایسنس نامعتبر است:\n{err}")
                return
            
            # ذخیره
            saved = license_module.save_license(license_content)
            if saved:
                valid, days_left, msg, payload = license_module.check_license()
                messagebox.showinfo("موفق", f"لایسنس جدید با موفقیت ذخیره شد!\n\n{msg}\n\nذخیره در:\n" + "\n".join(saved))
                self.license_valid, self.license_days, self.license_msg, self.license_payload = valid, days_left, msg, payload
                self._show_license_info()
                if hasattr(self, 'license_detail_lbl'):
                    self.license_detail_lbl.configure(text=license_module.get_license_status_text() + f"\n{msg}")
            else:
                messagebox.showerror("خطا", "نمی‌توان لایسنس را ذخیره کرد")
        except Exception as e:
            messagebox.showerror("خطا", f"خطا در بارگذاری لایسنس:\n{e}")

    # ------------------------------------------------------- convert
    def _prompt_tesseract_path(self):
        """اگر Tesseract پیدا نشد، از کاربر بخواه مسیر را دستی انتخاب کند."""
        from .util import save_tesseract_path
        ask = messagebox.askyesno(
            "مسیر Tesseract پیدا نشد",
            "برنامه Tesseract روی ویندوز پیدا نشد.\n\n"
            "اگر قبلاً نصب کرده‌اید، آیا می‌خواهید مسیر tesseract.exe را دستی انتخاب کنید؟\n\n"
            "بله = انتخاب فایل\n"
            "خیر = نمایش راهنمای نصب"
        )
        if not ask:
            messagebox.showinfo(
                "نصب Tesseract",
                "لطفاً فایل Install-Tesseract.bat را اجرا کنید.\n\n"
                "یا دستی از این آدرس نصب کنید:\n"
                "https://github.com/UB-Mannheim/tesseract/wiki\n\n"
                "مسیر پیش‌فرض بعد از نصب:\n"
                "C:\\Program Files\\Tesseract-OCR\\tesseract.exe\n\n"
                "بعد از نصب، دوباره تلاش کنید."
            )
            return False
        path = filedialog.askopenfilename(
            title="مسیر tesseract.exe را انتخاب کنید",
            filetypes=[("tesseract.exe", "tesseract.exe"), ("همه فایل‌ها", "*.*")],
            initialdir=r"C:\Program Files\Tesseract-OCR"
        )
        if not path:
            return False
        if not os.path.exists(path):
            messagebox.showerror("خطا", "فایل انتخاب‌شده وجود ندارد.")
            return False
        save_tesseract_path(path)
        ok, _ = TesseractEngine.is_available()
        if ok:
            messagebox.showinfo("موفق", f"مسیر ذخیره شد:\n{path}\n\nحالا می‌توانید تبدیل را شروع کنید.")
            self._check_engines()
            return True
        else:
            messagebox.showerror("خطا", f"فایل انتخاب‌شده کار نمی‌کند:\n{path}\n\nلطفاً فایل درست tesseract.exe را انتخاب کنید.")
            return False

    def start_convert(self):
        if self.worker_busy or not self.files:
            return
        
        # چک لایسنس قبل از شروع
        valid, days_left, msg, payload = license_module.check_license()
        if not valid:
            messagebox.showerror("لایسنس منقضی شده", f"{msg}\n\nلطفاً لایسنس جدید تهیه کنید.")
            return
        if days_left <= 3:
            messagebox.showwarning("هشدار لایسنس", f"لایسنس شما فقط {days_left} روز دیگر اعتبار دارد!\n{msg}\n\nلطفاً برای تمدید اقدام کنید.")
        
        engine_name = self._engine_choice()
        if engine_name == "tesseract":
            ok, msg = TesseractEngine.is_available()
            if not ok:
                if self._prompt_tesseract_path():
                    ok, msg = TesseractEngine.is_available()
                if not ok:
                    messagebox.showerror("آماده نیست موتور OCR", msg)
                    return
        else:
            ok, msg = PaddleEngine.is_available()
            if not ok:
                messagebox.showerror("موتور OCR آماده نیست", msg)
                return
            if "vpn" in msg.lower() or "دانلود" in msg:
                proceed = messagebox.askyesno(
                    "مدل‌های PaddleOCR هنوز دانلود نشده",
                    f"{msg}\n\n"
                    "اولین اجرای موتور دقیق نیاز به دانلود مدل‌ها دارد که در ایران نیاز به VPN دارد.\n"
                    "آیا می‌خواهید ادامه دهید؟ (اگر VPN روشن است، چند دقیقه طول می‌کشد)\n\n"
                    "بله = ادامه با VPN\n"
                    "خیر = لغو و استفاده از موتور سبک"
                )
                if not proceed:
                    self.engine_seg.set("سبک (Tesseract)")
                    self._check_engines()
                    return

        self.worker_busy = True
        self.convert_btn.configure(state="disabled", text="در حال پردازش...")
        self.save_btn.configure(state="disabled")
        if hasattr(self, "quick_save_btn"):
            self.quick_save_btn.configure(state="disabled")
        self.progress.set(0)
        self.sheets = []
        self.entry_grids = {}
        self.empty.grid_remove()
        self.tabs.grid(row=2, column=0, sticky="nsew", padx=16, pady=(4, 8))
        for w in self.tabs.winfo_children():
            w.destroy()

        settings = {
            "engine": engine_name,
            "mode": MODE_VALUES[MODE_LABELS.index(self.mode_menu.get())],
            "lang": LANG_VALUES[LANG_LABELS.index(self.lang_menu.get())],
            "enhance": bool(self.enhance_var.get()),
            "multi": bool(self.multi_var.get()),
        }
        t = threading.Thread(target=self._worker, args=(list(self.files), settings),
                             daemon=True)
        t.start()

    def _worker(self, files, st):
        q = self.msg_queue
        try:
            if st["engine"] == "paddle":
                q.put(("status", "در حال آماده‌سازی موتور دقیق... (اگر اولین بار است، ممکن است چند دقیقه طول بکشد و نیاز به VPN داشته باشد)"))
            else:
                q.put(("status", "در حال آماده‌سازی موتور سبک..."))
            engine = TesseractEngine() if st["engine"] == "tesseract" else PaddleEngine()
            q.put(("status", "✓ موتور آماده شد - شروع پردازش عکس‌ها"))
        except Exception as e:
            # پیام خطای کاربرپسند
            err_text = str(e)
            q.put(("error", f"خطا در اجرای موتور OCR:\n{err_text}\n\n{traceback.format_exc()}"))
            q.put(("done", {}))
            return

        results = []
        total = len(files)
        for i, path in enumerate(files):
            name = safe_sheet_name(split_stem(path), f"Sheet{i+1}")
            q.put(("status", f"پردازش {i+1} از {total}: {os.path.basename(path)}"))
            q.put(("progress", i / total))
            try:
                raw = load_gray(path)
                # اگر عکس خیلی بزرگ است، اول کوچک کن تا هنگ نکند
                try:
                    import cv2
                    h0, w0 = raw.shape[:2]
                    if max(h0, w0) > 2400:
                        scale0 = 2000.0 / max(h0, w0)
                        raw = cv2.resize(raw, None, fx=scale0, fy=scale0, interpolation=cv2.INTER_AREA)
                except Exception:
                    pass
                
                # تشخیص خودکار جهت - برای سرعت، برای متن از OSD فقط استفاده کن نه OCR سریع
                osd = None
                try:
                    # OSD هم ممکن است کند باشد، فقط برای جدول استفاده کن
                    if st["mode"] != "text":
                        osd = engine.osd_degrees(raw)
                except Exception:
                    osd = None
                
                try:
                    if st["mode"] == "text":
                        # برای دست‌نویس، فقط deskew ساده، بدون OCR اضافی که هنگ می کند
                        from .preprocess import deskew
                        gray0 = deskew(raw)
                        rot_k, _was_table = 0, False
                    else:
                        gray0, rot_k, _was_table = upright(
                            raw,
                            quick_ocr_conf=lambda g: engine.quick_conf(g, st["lang"]),
                            osd_result=osd)
                except Exception:
                    gray0, rot_k, _was_table = raw, 0, False
                q.put(("status", f"جهت عکس اصلاح شد" if rot_k else "آماده پردازش"))
                
                # تشخیص نوع صفحه
                xs, ys = [], []
                light = None
                if st["mode"] != "text":
                    # نسخه سبک برای تشخیص خطوط جدول
                    light, _c, _s = enhance_gray(gray0, st["enhance"], polish=False)
                    if _was_table:
                        cropped = table_crop(light)
                        if cropped is not light:
                            light = cropped
                    xs, ys = detect_grid(light)
                
                kind = st["mode"]
                if kind == "auto":
                    if light is not None and (is_table_like(light, xs, ys) or _was_table):
                        kind = "table"
                    else:
                        kind = "text"
                
                if kind == "table":
                    # جدول: حذف خطوط و OCR با fallback های قوی
                    try:
                        nolines = remove_grid_lines(light, xs, ys)
                        ocr_img = polish_gray(nolines) if st["enhance"] else nolines
                        words, conf = engine.recognize(ocr_img, lang=st["lang"], table_mode=True)
                        
                        # اگر کلمه‌ای پیدا نشد، روی تصویر بدون حذف خطوط هم امتحان کن
                        if not words:
                            q.put(("status", f"تلاش مجدد بدون حذف خطوط جدول..."))
                            try:
                                words2, conf2 = engine.recognize(light, lang=st["lang"], table_mode=True)
                                if words2 and len(words2) > len(words):
                                    words, conf = words2, conf2
                            except Exception:
                                pass
                        
                        # اگر باز هم خالی، روی تصویر اصلی gray0 امتحان کن
                        if not words:
                            try:
                                words3, conf3 = engine.recognize(gray0, lang=st["lang"], table_mode=True)
                                if words3 and len(words3) > len(words):
                                    words, conf = words3, conf3
                            except Exception:
                                pass
                        
                        # ساخت جدول
                        if is_table_like(light, xs, ys) and words:
                            rows = build_table_from_grid(words, xs, ys,
                                                         light.shape[1], light.shape[0])
                        else:
                            rows = build_table_fallback(words) if words else []
                        
                        if not rows and words:
                            rows = [[l] for l in build_paragraph_lines(words)]
                        
                        # آخرین fallback: اگر هنوز خالی، از recognize_with_lines استفاده کن
                        if not rows:
                            try:
                                if hasattr(engine, 'recognize_with_lines'):
                                    lines = engine.recognize_with_lines(ocr_img, lang=st["lang"])
                                    if not lines:
                                        lines = engine.recognize_with_lines(light, lang=st["lang"])
                                    if lines:
                                        rows = [[l] for l in lines]
                            except Exception:
                                pass
                        
                        # اگر باز هم خالی، پیام راهنما
                        if not rows:
                            rows = [["(متنی تشخیص داده نشد)"]]
                            # سعی کن حداقل یک متن از image_to_string بگیری
                            try:
                                if hasattr(engine, '_recognize_string'):
                                    txt = engine._recognize_string(ocr_img, st["lang"], 6, 3, "")
                                    if txt and len(txt.strip()) > 5:
                                        rows = [[line] for line in txt.split('\n') if line.strip()]
                            except Exception:
                                pass
                            if not rows or rows == [["(متنی تشخیص داده نشد)"]]:
                                rows = [
                                    ["راهنما: متنی تشخیص داده نشد"],
                                    ["۱. زبان را 'فقط فارسی' بگذارید"],
                                    ["۲. عکس واضح‌تر با نور بهتر بگیرید"],
                                    ["۳. موتور 'سبک (Tesseract)' را انتخاب کنید"],
                                    ["۴. تیک 'بهبود کیفیت' را فعال کنید"]
                                ]
                                conf = 0
                    except Exception as e:
                        import traceback
                        print(f"Table error: {e}\n{traceback.format_exc()}")
                        rows = [[f"خطا: {e}"]]
                        conf = 0
                    results.append({"name": name, "kind": "table", "rows": rows,
                                    "conf": conf, "file": path})
                else:
                    # دست‌نویس/متن: با fallback قوی
                    try:
                        ocr_img, _c2, _s2 = enhance_gray(gray0, st["enhance"],
                                                        polish=True, handwritten=True)
                        
                        use_engine = engine
                        use_lang = st["lang"]
                        if st["engine"] == "paddle":
                            try:
                                tess = TesseractEngine()
                                use_engine = tess
                                if st["lang"].startswith("fas"):
                                    use_lang = "fas"
                                q.put(("status", "دست‌نویس - موتور سبک (سریع‌تر) استفاده می‌شود"))
                            except Exception:
                                use_engine = engine
                        
                        lines = []
                        words, conf = [], 0
                        
                        # تلاش ۱: خطوط مستقیم
                        try:
                            if hasattr(use_engine, 'recognize_with_lines'):
                                lines = use_engine.recognize_with_lines(ocr_img, lang=use_lang)
                        except Exception:
                            lines = []
                        
                        # تلاش ۲: کلمات
                        try:
                            words, conf = use_engine.recognize(ocr_img, lang=use_lang, table_mode=False)
                            if not lines and words:
                                lines = build_paragraph_lines(words)
                            elif words and lines:
                                # کدام بهتر؟
                                direct_len = sum(len(l) for l in lines) if lines else 0
                                words_len = sum(len(w.text) for w in words)
                                if words_len > direct_len * 1.2:
                                    lines_from_words = build_paragraph_lines(words)
                                    if sum(len(l) for l in lines_from_words) > direct_len:
                                        lines = lines_from_words
                        except Exception as e:
                            if not lines:
                                lines = []
                        
                        # تلاش ۳: اگر خالی، روی gray0 بدون enhance امتحان کن
                        if not lines:
                            q.put(("status", "تلاش مجدد بدون بهبود کیفیت..."))
                            try:
                                if hasattr(use_engine, 'recognize_with_lines'):
                                    lines2 = use_engine.recognize_with_lines(gray0, lang=use_lang)
                                    if lines2 and sum(len(l) for l in lines2) > 5:
                                        lines = lines2
                                if not lines:
                                    words2, conf2 = use_engine.recognize(gray0, lang=use_lang, table_mode=False)
                                    if words2:
                                        lines = build_paragraph_lines(words2)
                                        words, conf = words2, conf2
                            except Exception:
                                pass
                        
                        # تلاش ۴: زبان دیگر
                        if not lines and use_lang != "fas":
                            try:
                                if hasattr(use_engine, 'recognize_with_lines'):
                                    lines_fas = use_engine.recognize_with_lines(ocr_img, lang="fas")
                                    if lines_fas:
                                        lines = lines_fas
                            except Exception:
                                pass
                        
                        # تلاش ۵: image_to_string مستقیم
                        if not lines:
                            try:
                                if hasattr(use_engine, '_recognize_string'):
                                    txt = use_engine._recognize_string(ocr_img, use_lang, 6, 1, "-c preserve_interword_spaces=1")
                                    if txt and len(txt.strip()) > 3:
                                        lines = [l.strip() for l in txt.split('\n') if l.strip()]
                            except Exception:
                                pass
                        
                    except Exception as e:
                        import traceback
                        print(f"Text error: {e}\n{traceback.format_exc()}")
                        words, conf = [], 0
                        lines = [f"خطا در پردازش دست‌نویس: {e}"]
                    
                    if not lines:
                        lines = [
                            "(متنی تشخیص داده نشد)",
                            "پیشنهادات:",
                            "۱. زبان را 'فقط فارسی' بگذارید",
                            "۲. عکس واضح‌تر با نور بهتر",
                            "۳. حالت 'متن / دست‌نویس' انتخاب شود",
                            "۴. موتور 'سبک (Tesseract)' بهتر است برای دست‌نویس",
                            "۵. تیک 'بهبود کیفیت' فعال باشد"
                        ]
                    results.append({"name": name, "kind": "text", "lines": lines,
                                    "conf": conf, "file": path})
            except Exception as e:
                results.append({"name": name, "kind": "table",
                                "rows": [["خطا در پردازش", str(e)]],
                                "conf": 0.0, "file": path})
                q.put(("status", f"خطا در {os.path.basename(path)}: {e}"))

        q.put(("progress", 1.0))
        q.put(("done", {"sheets": results, "multi": st["multi"]}))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "status":
                    self.status_lbl.configure(text=payload)
                elif kind == "progress":
                    self.progress.set(payload)
                elif kind == "error":
                    messagebox.showerror("خطا", payload)
                elif kind == "done":
                    self._on_worker_done(payload)
        except queue.Empty:
            pass
        self.after(120, self._poll_queue)

    def _on_worker_done(self, payload):
        self.worker_busy = False
        self.convert_btn.configure(state="normal", text="🔎  شروع تشخیص")
        self.sheets = payload.get("sheets", [])
        self.multi_result = payload.get("multi", True)
        if not self.sheets:
            self.status_lbl.configure(text="نتیجه‌ای به دست نیامد - خطاها را بررسی کنید.")
            return
        self._render_sheets()
        self.save_btn.configure(state="normal")
        if hasattr(self, "quick_save_btn"):
            self.quick_save_btn.configure(state="normal")
        n = len(self.sheets)
        self.status_lbl.configure(text=f"✓ تشخیص {n} عکس تمام شد - نتیجه را مرور و ویرایش کنید، سپس ذخیره بزنید.")
        self.after(500, lambda: self.status_lbl.configure(text=f"✓ تشخیص {n} عکس تمام شد - روی 'ذخیره فایل خروجی' یا 'ذخیره سریع روی دسکتاپ' بزنید."))

    def _ask_save_first_time(self):
        if not getattr(self, "_first_save_pending", False):
            return
        self._first_save_pending = False
        self.save_outputs(prompt_after=True)

    # ------------------------------------------------------ results
    def _render_sheets(self):
        for name in list(getattr(self, "_tabs", {}).values()):
            try:
                self.tabs.delete(name)
            except Exception:
                pass
        self.entry_grids = {}
        self._tabs = {}
        for idx, sh in enumerate(self.sheets):
            name = f"{sh['name']} ({'متن' if sh['kind']=='text' else len(sh['rows'])})"
            tab = self.tabs.add(name)
            self._tabs[idx] = name
            if sh["kind"] == "table":
                self._build_table_editor(tab, idx, sh)
            else:
                box = ctk.CTkTextbox(tab, font=ctk.CTkFont(FONT, 13), wrap="word",
                                     fg_color="#ffffff")
                box.pack(fill="both", expand=True, padx=8, pady=8)
                box.insert("1.0", "\n".join(sh["lines"]))
                self.entry_grids[idx] = ("text", box)
        if self._tabs:
            self.tabs.set(self._tabs[0])

    def _build_table_editor(self, tab, idx, sh):
        wrap = ctk.CTkScrollableFrame(tab, fg_color="#f8fafc")
        wrap.pack(fill="both", expand=True)
        grid = ctk.CTkFrame(wrap, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=6, pady=6)
        entries = []
        rows = sh["rows"]
        for r, row in enumerate(rows):
            er = []
            for c in range(max(len(row), 1)):
                val = row[c] if c < len(row) else ""
                e = ctk.CTkEntry(grid, font=ctk.CTkFont(FONT, 12, bold=(r == 0)),
                                 height=30 if r == 0 else 26,
                                 fg_color="#dbeafe" if r == 0 else ("#ffffff" if r % 2 else "#f1f5f9"),
                                 border_width=1, border_color="#cbd5e1",
                                 corner_radius=0, justify="right")
                e.insert(0, str(val))
                e.grid(row=r, column=c, sticky="ew", padx=1, pady=1)
                er.append(e)
            entries.append(er)
        self.entry_grids[idx] = ("table", grid, entries)
        info = ctk.CTkLabel(tab, text=f"اطمینان تقریبی تشخیص: {sh.get('conf', 0):.0f}٪  -  "
                                      "سلول‌ها قابل ویرایش هستند",
                            font=ctk.CTkFont(FONT, 10), text_color="#64748b")
        info.pack(side="bottom", pady=4)

    def _active_sheet_idx(self):
        current = self.tabs.get()
        for idx, name in self._tabs.items():
            if name == current:
                return idx
        return 0

    def _sync_active(self):
        """نوشتن مقادیر ویجت‌ها در داده‌ها."""
        for idx, sh in enumerate(self.sheets):
            ed = self.entry_grids.get(idx)
            if not ed:
                continue
            if ed[0] == "text":
                txt = ed[1].get("1.0", "end").strip("\n")
                sh["lines"] = [l for l in txt.split("\n")]
            else:
                entries = ed[2]
                rows = []
                for er in entries:
                    rows.append([e.get() for e in er])
                sh["rows"] = rows

    def _rebuild_active_grid(self):
        idx = self._active_sheet_idx()
        sh = self.sheets[idx]
        if sh["kind"] != "table":
            return
        name = self._tabs[idx]
        frame = self.tabs.tab(name)
        for w in frame.winfo_children():
            w.destroy()
        self.entry_grids.pop(idx, None)
        self._build_table_editor(frame, idx, sh)

    def add_row(self):
        idx = self._active_sheet_idx()
        sh = self.sheets[idx] if self.sheets else None
        if not sh or sh["kind"] != "table":
            return
        self._sync_active()
        ncol = max((len(r) for r in sh["rows"]), default=1)
        sh["rows"].append([""] * ncol)
        self._rebuild_active_grid()

    def del_row(self):
        idx = self._active_sheet_idx()
        sh = self.sheets[idx] if self.sheets else None
        if not sh or sh["kind"] != "table":
            return
        self._sync_active()
        if len(sh["rows"]) > 1:
            sh["rows"].pop()
            self._rebuild_active_grid()

    def add_column(self):
        idx = self._active_sheet_idx()
        sh = self.sheets[idx] if self.sheets else None
        if not sh or sh["kind"] != "table":
            return
        self._sync_active()
        for r in sh["rows"]:
            r.append("")
        self._rebuild_active_grid()

    def rerender_active(self):
        self._sync_active()
        self._rebuild_active_grid()

    # -------------------------------------------------------- saving
    def save_outputs(self, prompt_after=False):
        if not self.sheets:
            messagebox.showwarning("خالی", "هنوز نتیجه‌ای برای ذخیره وجود ندارد.")
            return
        self._sync_active()

        # تلاش برای انتخاب پوشه - با هندل کردن خطاهای احتمالی pythonw
        directory = None
        try:
            # اگر قبلاً پوشه‌ای انتخاب شده، همان را پیشنهاد بده
            init_dir = self.last_save_dir or os.path.expanduser("~/Desktop") or os.path.expanduser("~")
            directory = filedialog.askdirectory(
                title="پوشه ذخیره فایل خروجی را انتخاب کنید",
                initialdir=init_dir,
                parent=self
            )
        except Exception as e:
            print(f"askdirectory failed: {e}")
            # fallback: از کاربر فایل بخواه
            try:
                directory = filedialog.askdirectory(title="پوشه ذخیره را انتخاب کنید", parent=self)
            except Exception:
                directory = None

        if not directory:
            # اگر کاربر کنسل کرد یا دیالوگ باز نشد، روی دسکتاپ ذخیره کن
            fallback = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(fallback):
                fallback = os.path.expanduser("~")
            ask = messagebox.askyesno(
                "پوشه انتخاب نشد",
                f"پوشه‌ای انتخاب نشد.\n\nآیا فایل‌ها روی دسکتاپ ذخیره شوند؟\n{fallback}\n\nبله = ذخیره روی دسکتاپ\nخیر = انتخاب دوباره پوشه"
            )
            if ask:
                directory = fallback
            else:
                # دوباره تلاش کن
                try:
                    directory = filedialog.askdirectory(title="پوشه ذخیره را انتخاب کنید", parent=self)
                except Exception:
                    directory = None
                if not directory:
                    return

        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                messagebox.showerror("خطا", f"نمی‌توان پوشه را ساخت:\n{directory}\n\n{e}")
                return

        self.last_save_dir = directory
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        saved = []
        errors = []
        try:
            table_sheets = [s for s in self.sheets if s["kind"] == "table"]
            text_sheets = [s for s in self.sheets if s["kind"] == "text"]
            multi = bool(getattr(self, "multi_result", True))

            if table_sheets:
                if self.table_fmt.get() == "Excel":
                    p = os.path.join(directory, f"TABDIL_jadval_{stamp}.xlsx")
                    exporter.export_excel_tables(table_sheets, p, multi_sheet=multi)
                else:
                    p = os.path.join(directory, f"TABDIL_jadval_{stamp}.docx")
                    exporter.export_word_tables(table_sheets, p)
                saved.append(p)

            if text_sheets:
                if self.text_fmt.get().startswith("Word"):
                    p = os.path.join(directory, f"TABDIL_matn_{stamp}.docx")
                    exporter.export_word_text(text_sheets, p)
                else:
                    p = os.path.join(directory, f"TABDIL_matn_{stamp}.xlsx")
                    exporter.export_excel_lines(text_sheets, p, multi_sheet=multi)
                saved.append(p)

            # اگر هیچ‌کدام از دسته‌ها نبود (مثلاً همه خالی)، همه را به عنوان جدول ذخیره کن
            if not saved and self.sheets:
                p = os.path.join(directory, f"TABDIL_khoroji_{stamp}.xlsx")
                # تبدیل همه به جدول
                all_tables = []
                for s in self.sheets:
                    if s["kind"] == "table":
                        all_tables.append(s)
                    else:
                        all_tables.append({"name": s["name"], "rows": [[l] for l in s["lines"]]})
                exporter.export_excel_tables(all_tables, p, multi_sheet=multi)
                saved.append(p)

        except Exception as e:
            err = traceback.format_exc()
            # لاگ به فایل برای عیب‌یابی
            try:
                log_path = os.path.join(directory, f"TABDIL_error_{stamp}.txt")
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(err)
            except Exception:
                pass
            messagebox.showerror("خطا در ذخیره", f"ذخیره با خطا مواجه شد:\n{e}\n\nجزئیات:\n{err}\n\nلطفاً این متن را بفرستید.")
            return

        if saved:
            names = "\n".join(os.path.basename(p) for p in saved)
            self.status_lbl.configure(text="✓ ذخیره شد در: " + " | ".join(names))
            # پیام موفقیت با جزئیات
            full_paths = "\n".join(saved)
            if messagebox.askyesno("ذخیره شد",
                                   f"فایل‌ها ذخیره شدند:\n{names}\n\nمسیر:\n{full_paths}\n\nپوشه خروجی باز شود؟"):
                self._open_dir(directory)
        else:
            messagebox.showwarning("ذخیره نشد", "هیچ فایلی ذخیره نشد. ممکن است نتیجه خالی باشد.\n\nلطفاً Check-Installation.bat را اجرا و نتیجه را بفرستید.")

    def quick_save_to_desktop(self):
        """ذخیره سریع بدون پرسیدن پوشه - مستقیم روی دسکتاپ."""
        if not self.sheets:
            messagebox.showwarning("خالی", "هنوز نتیجه‌ای برای ذخیره وجود ندارد.")
            return
        self._sync_active()
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop):
            desktop = os.path.expanduser("~")
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        saved = []
        try:
            table_sheets = [s for s in self.sheets if s["kind"] == "table"]
            text_sheets = [s for s in self.sheets if s["kind"] == "text"]
            multi = bool(getattr(self, "multi_result", True))

            if table_sheets:
                if self.table_fmt.get() == "Excel":
                    p = os.path.join(desktop, f"TABDIL_jadval_{stamp}.xlsx")
                    exporter.export_excel_tables(table_sheets, p, multi_sheet=multi)
                else:
                    p = os.path.join(desktop, f"TABDIL_jadval_{stamp}.docx")
                    exporter.export_word_tables(table_sheets, p)
                saved.append(p)

            if text_sheets:
                if self.text_fmt.get().startswith("Word"):
                    p = os.path.join(desktop, f"TABDIL_matn_{stamp}.docx")
                    exporter.export_word_text(text_sheets, p)
                else:
                    p = os.path.join(desktop, f"TABDIL_matn_{stamp}.xlsx")
                    exporter.export_excel_lines(text_sheets, p, multi_sheet=multi)
                saved.append(p)

            if not saved and self.sheets:
                p = os.path.join(desktop, f"TABDIL_khoroji_{stamp}.xlsx")
                all_tables = []
                for s in self.sheets:
                    if s["kind"] == "table":
                        all_tables.append(s)
                    else:
                        all_tables.append({"name": s["name"], "rows": [[l] for l in s["lines"]]})
                exporter.export_excel_tables(all_tables, p, multi_sheet=multi)
                saved.append(p)

        except Exception as e:
            err = traceback.format_exc()
            try:
                log_path = os.path.join(desktop, f"TABDIL_error_{stamp}.txt")
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(err)
            except Exception:
                pass
            messagebox.showerror("خطا در ذخیره", f"ذخیره سریع با خطا مواجه شد:\n{e}\n\n{err}")
            return

        if saved:
            names = "\n".join(os.path.basename(p) for p in saved)
            full_paths = "\n".join(saved)
            self.status_lbl.configure(text="✓ ذخیره شد روی دسکتاپ: " + " | ".join(names))
            if messagebox.askyesno("ذخیره شد روی دسکتاپ",
                                   f"فایل‌ها روی دسکتاپ ذخیره شدند:\n{names}\n\nمسیر:\n{full_paths}\n\nپوشه دسکتاپ باز شود؟"):
                self._open_dir(desktop)

    @staticmethod
    def _open_dir(directory):
        try:
            os.startfile(directory)  # type: ignore[attr-defined]
        except Exception:
            try:
                import subprocess
                subprocess.Popen(["explorer", os.path.normpath(directory)])
            except Exception:
                pass


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
