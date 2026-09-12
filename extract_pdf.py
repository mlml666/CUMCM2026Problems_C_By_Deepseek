# -*- coding: utf-8 -*-
"""Extract text from C题.pdf with PyPDF2 as a fallback (Word COM path preferred)."""
from PyPDF2 import PdfReader

SRC = r"E:\qq文件\CUMCM2026Problems\C题\C题.pdf"
DST = r"E:\qq文件\CUMCM2026Problems\C题\C题_pypdf.txt"

r = PdfReader(SRC)
print("pages:", len(r.pages))
with open(DST, "w", encoding="utf-8") as f:
    for i, p in enumerate(r.pages):
        f.write(f"--- page {i+1} ---\n")
        try:
            txt = p.extract_text() or ""
        except Exception as e:  # noqa: BLE001
            txt = f"[extract error: {e}]"
        f.write(txt)
        f.write("\n")
print("saved:", DST)
