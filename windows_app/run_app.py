# -*- coding: utf-8 -*-
"""نقطه ورود برنامه TABDIL روی ویندوز."""
import os
import sys

# اطمینان از Import شدن پکیج وقتی به صورت اسکریپت اجرا می‌شود
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# در اجرای بدون کنسول (pythonw.exe) جریان‌های خروجی مقدار None دارند؛
# برای جلوگیری از کرش کتابخانه‌هایی مثل tqdm، آن‌ها را به دستگاه نامعتبر هدایت می‌کنیم.
# این باید قبل از هر import دیگری انجام شود.
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

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from TABDIL.app import main

if __name__ == "__main__":
    main()
