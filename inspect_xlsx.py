# -*- coding: utf-8 -*-
"""Inspect attachments, output UTF-8 report file."""
import pandas as pd
import os, glob, io, sys

base = os.path.dirname(os.path.abspath(__file__))
out = io.open(os.path.join(base, "附件检查报告.txt"), "w", encoding="utf-8")

def p(*a):
    s = " ".join(str(x) for x in a)
    out.write(s + "\n")

files = sorted(glob.glob(os.path.join(base, "附件", "附件*.xlsx"))) + \
        sorted(glob.glob(os.path.join(base, "附件", "附件5", "*.xlsx")))

for f in files:
    rel = os.path.relpath(f, base)
    p("=" * 100)
    p("FILE:", rel)
    try:
        xls = pd.ExcelFile(f)
        p("  sheets:", xls.sheet_names)
        for sh in xls.sheet_names:
            df = pd.read_excel(f, sheet_name=sh, nrows=5, header=None)
            p(f"  --- sheet [{sh}] shape(first5)={df.shape}, dtype row0={df.iloc[0].dtype}")
            for i in range(min(3, len(df))):
                vals = [str(v)[:18] for v in df.iloc[i].tolist()[:8]]
                p(f"    row{i}:", vals)
            if df.shape[1] > 8:
                p("    (last cols):", [str(v)[:18] for v in df.iloc[0].tolist()[-6:]])
    except Exception as e:
        p("  ERROR:", repr(e))

# full shape + row counts per sheet
p("=" * 100)
p("FULL SHAPES:")
for f in files:
    rel = os.path.relpath(f, base)
    try:
        xls = pd.ExcelFile(f)
        info = []
        for sh in xls.sheet_names:
            df = pd.read_excel(f, sheet_name=sh)
            info.append(f"{sh}: {df.shape}")
        p(" ", rel, "|", " ; ".join(info))
    except Exception as e:
        p(" ", rel, "ERROR", repr(e))
out.close()
print("done")
