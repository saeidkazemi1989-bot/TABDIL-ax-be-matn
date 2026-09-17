# PaddleOCR Models - محل قرار دادن دستی مدل‌ها

اگر VPN ندارید و دانلود از Baidu کار نمی‌کند، مدل‌ها را دستی دانلود و اینجا قرار دهید.

## ساختار

```
paddle_models/
├─ det/
│  └─ ml/
│     └─ Multilingual_PP-OCRv3_det_infer/
│        ├─ inference.pdmodel
│        ├─ inference.pdiparams
│        └─ ...
├─ rec/
│  └─ arabic/
│     └─ arabic_PP-OCRv4_rec_infer/
│        ├─ inference.pdmodel
│        └─ ...
└─ cls/
   └─ ch/
      └─ ch_ppocr_mobile_v2.0_cls_infer/
         ├─ inference.pdmodel
         └─ ...
```

## لینک‌های دانلود مستقیم

- det: https://paddleocr.bj.bcebos.com/PP-OCRv3/multilingual/Multilingual_PP-OCRv3_det_infer.tar
- rec: https://paddleocr.bj.bcebos.com/PP-OCRv4/multilingual/arabic_PP-OCRv4_rec_infer.tar
- cls: https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar

یا از گیت‌هاب (بدون Baidu):
- https://github.com/saeidkazemi1989-bot/TABDIL-ax-be-matn/releases/tag/paddle-models

## بعد از قرار دادن

```bat
Setup-PaddleModels-Local.bat
Check-Installation.bat
```

همچنین ببینید: `PADDLE_MODELS_MANUAL.md`
