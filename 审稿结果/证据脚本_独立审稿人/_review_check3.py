# -*- coding: utf-8 -*-
import os, io, glob, numpy as np, pandas as pd
B = r"E:\qq文件\CUMCM2026Problems\C题"
print("=== 日志文件读取 (UTF-16LE) ===")
for f in glob.glob(os.path.join(B, "求解", "结果", "日志_*.txt")) + glob.glob(os.path.join(B, "求解", "验算", "日志_*.txt")):
    t = io.open(f, encoding="utf-16").read()
    print("----------", os.path.basename(f), "----------")
    print(t[:2500])

print("\n=== 产物计数 ===")
print("CSV in 求解/结果:", len(glob.glob(os.path.join(B, "求解", "结果", "*.csv"))))
print("PNG in 论文/图:", len(glob.glob(os.path.join(B, "论文", "图", "*.png"))))
print("PNG in 求解/图片:", len(glob.glob(os.path.join(B, "求解", "图片", "*.png"))))
print("src py in 论文/src:", [os.path.basename(p) for p in glob.glob(os.path.join(B, "论文", "src", "*.py"))])

print("\n=== 问题1 795.17 溯源 ===")
d = pd.read_csv(os.path.join(B, "求解", "结果", "问题1_逐时段明细.csv"))
a = d["充电量kWh"].values; b = d["放电量kWh"].values
print("sum a =", a.sum(), "sum b =", b.sum(), "sum a/0.9 =", (a/0.9).sum(), "0.9*sum b =", (0.9*b).sum())
print("0.9*max(a) =", 0.9*a.max(), " max(0.9*a) =", (0.9*a).max())
print("search 795.17 among derived:", [v for v in [0.9*a.sum(), a.sum()*0.9, (a/0.9).max(), 0.9*b.max()] ])
print("max of a/0.9 =", (a/0.9).max(), " -> 论文称最大充电 833.33")
print("max of b*0.9 =", (b*0.9).max())

print("\n=== 问题1 功率约束是否真的起作用 ===")
print("a 达到上限 925.9259 的时段数 =", int((a > 925.92).sum()))
print("b 达到上限 925.9259 的时段数 =", int((b > 925.92).sum()))
print("b 最大值 =", b.max(), " 上限 925.9259")
print("论文称: 最大充电达上限 833.33, 最大放电 795.17（电池侧口径）")
print("电池侧口径 a=充电/0.9 max =", (a/0.9).max(), " b=放电/0.9 max =", (b/0.9).max())
