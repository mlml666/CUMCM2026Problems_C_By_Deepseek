# -*- coding: utf-8 -*-
"""第二轮：账基不一致、代码行数、附件1 基线、月度合计"""
import os, numpy as np, pandas as pd
B = r"E:\qq文件\CUMCM2026Problems\C题"
R = os.path.join(B, "求解", "结果")

print("=== A. 问题3 策略对比：三种账基对照 ===")
s3 = pd.read_csv(os.path.join(R, "问题3_策略对比.csv"))
s3["计划+紧急"] = s3["计划购电费"] + s3["紧急购电费"]
s3["计划+紧急+违约"] = s3["计划加紧急"] + s3["违约费"]
print(s3[["策略", "计划购电费", "违约费", "紧急购电费", "计划+紧急", "计划+紧急+违约"]].to_string(index=False))

print("\n=== B. 论文表中 P5'/A_load/P5 数值 vs CSV ===")
for k, paper in [("P5'", 19249721), ("A_load", 16048332), ("P5", 12229643)]:
    r = s3[s3.策略 == k].iloc[0]
    print(f"{k}: 论文={paper} | 计划+紧急={r['计划+紧急']:.2f} | 计划+紧急+违约={r['计划+紧急+违约']:.2f}"
          f" | 偏差(对计划+紧急)={abs(paper-r['计划+紧急'])/r['计划+紧急']*100:.4f}%"
          f" | 偏差(对全账)={abs(paper-r['计划+紧急+违约'])/r['计划+紧急+违约']*100:.4f}%")

print("\n=== C. 论文 A_load 数值 16048332 vs CSV 17806627 ===")
print("差 =", 17806627.05 - 16048332, "元")

print("\n=== D. 附录声明的代码行数 vs 实际 ===")
import io
for f, claim in [("common.py", 368), ("solve_p1.py", 116), ("solve_p2.py", 292), ("solve_p3.py", 294),
                 ("solve_p4.py", 345), ("verify_p25.py", 386), ("plots.py", 383),
                 ("sensitivity.py", 63), ("explore_data.py", 185)]:
    p = os.path.join(B, "论文", "src", f)
    n = sum(1 for _ in io.open(p, encoding="utf-8"))
    print(f"{f}: 声明 {claim} 行 / 实际 {n} 行 -> {'OK' if n == claim else 'MISMATCH'}")

print("\n=== E. 问题2/3 月度费用合计核对 ===")
m = pd.read_csv(os.path.join(R, "问题2_月度费用汇总.csv"))
body = m[m["月份"].astype(str) != "合计"]
print("月度 12 行(论文表只列 11 行, 缺 1 月): 月份 =", list(body["月份"]))
print("月度计划费和 =", body["计划购电费元"].sum(), " 论文合计 1534.78万 =", 1534.78e4)
print("月度紧急费和 =", body["紧急购电费元"].sum(), " 论文合计 130.02万 =", 130.02e4)
print("月度总费和 =", body["总费用元"].sum())
p2 = pd.read_csv(os.path.join(R, "表2_问题1.csv"))
print("\n表2_问题1.csv:"); print(p2.to_string())
p1d = pd.read_csv(os.path.join(R, "问题1_逐时段明细.csv"))
print("\n=== F. 问题1 关键量独立复算 ===")
g = p1d["购电量kWh"].values; p = p1d["电价"].values
L = p1d["负载kW"].values; P = p1d["光伏kW"].values
a = p1d["充电量kWh"].values; b = p1d["放电量kWh"].values; s = p1d["弃光kWh"].values
E = p1d["储电量kWh"].values
print("Σg =", g.sum(), " Σp·g =", (p*g).sum())
gap = ((L - P)*(1/6)).sum()
print("净缺口 =", gap, " 弃光 =", s.sum(), " A=Σa =", a.sum(), " Σb =", b.sum())
print("恒等式 Σg - (缺口+弃光+0.2111A) =", g.sum()-(gap+s.sum()+0.2111*a.sum()))
print("无储能基线 Σp·(L-P)/6 (仅正缺口) =", (p*np.maximum(L-P,0)/6).sum())
print("无储能基线 Σp·(L-P)/6 (含负)     =", (p*(L-P)/6).sum())
print("储能节省 = 48052.05 -", (p*g).sum(), "=", 48052.05-(p*g).sum())
print("E[0] =", E[0], "E[-1] =", E[-1], "min =", E.min(), "max =", E.max())
print("最大单段充电 =", a.max(), " 最大单段放电 =", b.max())
print("论文称 电池侧吞吐量=18666.60, 母线侧充 20740.67 / 放 16799.94")
print("Σ a/ηc =", (a/0.9).sum(), " Σ ηd*b =", (0.9*b).sum())
print("\n时段1-6 充放电:", list(zip(a[:6], b[:6])))
print("前 24 段电价最大/最小:", p[:24].max(), p[:24].min())
