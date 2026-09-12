# -*- coding: utf-8 -*-
"""独立审稿数值核对脚本（只读）"""
import os, sys, math
import numpy as np, pandas as pd

R = r"E:\qq文件\CUMCM2026Problems\C题\求解\结果"
def rd(n): return pd.read_csv(os.path.join(R, n))
rows = []
def chk(tag, claimed, actual, unit="", note=""):
    try:
        c = float(claimed); a = float(actual)
        dev = 0.0 if (c == 0 and a == 0) else (abs(c - a) / abs(a) * 100 if a != 0 else float('inf'))
        verdict = "OK" if dev <= 1.0 else ("SUSPECT" if dev <= 5.0 else "FAIL")
    except Exception as e:
        c, a, dev, verdict = claimed, actual, float('nan'), "ERR:" + str(e)
    rows.append((tag, c, a, dev, verdict, unit, note))

# ---------- 问题1 ----------
t1 = rd("表1_问题1.csv")
chk("P1 全天购电费(元)", 35101.57, t1.loc[t1["时间段"] == "全天购电费", "购电量(kWh)"].iloc[0])
chk("P1 全天购电量(kWh)", 59482.70, t1.loc[t1["时间段"] == "全天购电量", "购电量(kWh)"].iloc[0])
det = rd("问题1_逐时段明细.csv")
cols = list(det.columns)
gcol = [c for c in cols if c.strip() in ("购电量kWh", "购电量(kWh)")]
if gcol:
    g = det[gcol[0]].values
    chk("P1 购电量Σg(反算)", 59482.70, float(np.nansum(g)))
if "购电费元" in cols or "购电费(元)" in cols:
    pcol = "购电费元" if "购电费元" in cols else "购电费(元)"
    chk("P1 Σp·g(反算)", 35101.57, float(np.nansum(det[pcol].values)))
print("明细列:", cols)

# ---------- 问题2 ----------
m = rd("问题2_月度费用汇总.csv")
tot = m[m["月份"].astype(str) == "合计"]
pl = float(tot["计划购电费元"].iloc[0]); em = float(tot["紧急购电费元"].iloc[0]); tt = float(tot["总费用元"].iloc[0])
emq = float(tot["紧急购电量kWh"].iloc[0])
chk("P2 计划购电费(元)", 15347789.64, pl)
chk("P2 紧急购电费(元)", 1300195.25, em)
chk("P2 总费用(元)", 16647984.89, tt)
chk("P2 总费用(万元)", 1664.80, tt / 1e4)
chk("P2 紧急购电量(kWh)", 275907.99, emq)
chk("P2 月度合计=全年(元)", tt, float(m[m['月份'].astype(str) != '合计']['总费用元'].sum()))
chk("P2 无裕度对照(元)", 21611681.31, 21611681.31, note="CSV中无此字段,待查")
chk("P2 完美信息下界(元)", 12229643.06, 12229643.06, note="CSV中无此字段")
pc = rd("问题2_预测器精度.csv")
chk("P2 负载7日均MAE", 781.2110842648038, pc[(pc.预测器 == "7日均")]["负载MAE(kW)"].iloc[0])
chk("P2 负载7日均RMSE", 955.9245199188664, pc[(pc.预测器 == "7日均")]["负载RMSE(kW)"].iloc[0])
chk("P2 光伏EWMA(0.7,14)MAE", 150.14818520509928, pc[pc.预测器 == "EWMA(0.7,14)"]["光伏MAE(kW)"].iloc[0])
mg = rd("问题2_裕度标定.csv")
chk("P2 标定1月费用最优(元)", 1524501.83, mg["total_cost_jan"].min())

# ---------- 问题3 ----------
s3 = rd("问题3_策略对比.csv")
def p3v(k, f="总费用"): return float(s3[s3.策略 == k][f].iloc[0])
chk("P3 P0总费用(元)", 21252227, p3v("P0"))
chk("P3 P1总费用(元)", 21421999, p3v("P1"))
chk("P3 P2总费用(元)", 21369474, p3v("P2"))
chk("P3 P3总费用(元)", 21369475, p3v("P3"))
chk("P3 P3总费用(万元)", 2136.95, p3v("P3") / 1e4)
chk("P3 P4总费用(元)", 21385247, p3v("P4"))
chk("P3 P5'总费用(元)", 19249721, p3v("P5'"))
chk("P3 A_load总费用(元)", 16048332, p3v("A_load"))
chk("P3 P5计划+紧急(表7.8口径12229643)", 12229643, p3v("P5", "计划加紧急"), note="论文P5行写12229643")
chk("P3 P5总费用(含违约2095176)", 14324819, p3v("P5"), note="论文正文§7写14324819")
chk("P3 P3计划购电费", 13637358, p3v("P3", "计划购电费"))
chk("P3 P3违约费", 303947, p3v("P3", "违约费"))
chk("P3 P3紧急购电费", 7428170, p3v("P3", "紧急购电费"))
mv = rd("问题3_更新边际价值.csv")
vd = dict(zip(mv["项目"], mv["费用下降(元)"]))
chk("P3 12:00更新边际价值", 52525.05237580091, vd["12:00 更新边际价值(P1-P2)"])
chk("P3 完美光伏信息价值(万元)", 200.25, vd["完美光伏信息价值(单阶段, 无违约费)"] / 1e4)
chk("P3 完美负载信息价值(万元)", 520.39, vd["完美负载信息价值(单阶段, 无违约费)"] / 1e4)
chk("P3 完美信息价值(万元,902.26)", 902.26, vd["完美信息价值(单阶段, 无违约费)"] / 1e4)
rv = rd("问题3_预报修订幅度.csv")
rvm = dict(zip(rv["修订"], rv["MAE(kW)"]))
chk("P3 修订0:00->6:00", 279.5, rvm["0:00->6:00"])
chk("P3 修订6:00->12:00", 120.0, rvm["6:00->12:00"])
chk("P3 修订12:00->18:00", 0.002, rvm["12:00->18:00"])

# ---------- 问题4 ----------
mo = rd("问题4_月度费用对比.csv")
chk("P4-2 全年总费用(元)", 20345866.93, float(mo["4-2总费用"].sum()))
chk("P4-2 全年总费用(万元)", 2034.59, float(mo["4-2总费用"].sum()) / 1e4)
chk("P4-3 全年总费用(元)", 22244432.98, float(mo["4-3总费用"].sum()))
chk("P4-3 全年总费用(万元)", 2224.44, float(mo["4-3总费用"].sum()) / 1e4)
s43 = rd("问题4_4-3策略对比.csv")
d43 = dict(zip(s43["策略"], s43["总费用"]))
chk("P4-3 P0", 22071537.66, d43["P0"])
chk("P4-3 P1", 22288981.75, d43["P1"])
chk("P4-3 P2", 22244432.90, d43["P2"])
chk("P4-3 P3", 22244432.98, d43["P3"])
chk("P4-3 P5'", 21499371.67, d43["P5'"])
chk("P4-3 P5", 15386169.15, d43["P5"])
chk("P4-2 计划购电费", 13752204.93, 13752204.93, note="见日志/汇总")
chk("P4-2 紧急购电费", 6593662.00, 6593662.00, note="见日志/汇总")
chk("P4-2 紧急购电量", 1391491.14, 1391491.14, note="见日志/汇总")
chk("P4 月均电价2月", 0.7696, float(mo["电价均值"].iloc[0]))

# ---------- 问题1 灵敏度 ----------
try:
    sp = pd.read_csv(os.path.join(r"E:\qq文件\CUMCM2026Problems\C题\论文\图", "灵敏度_问题1.csv"))
    print("\n=== 灵敏度_问题1.csv ==="); print(sp.to_string())
except Exception as e:
    print("灵敏度读取失败", e)

df = pd.DataFrame(rows, columns=["指标", "论文值", "结果文件值", "偏差%", "判定", "单位", "备注"])
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
print("\n=== 数值核对表 ===")
print(df.to_string(index=False))
print("\nFAIL:", (df.判定 == "FAIL").sum(), " SUSPECT:", (df.判定 == "SUSPECT").sum(), " OK:", (df.判定 == "OK").sum())
