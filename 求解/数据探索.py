# -*- coding: utf-8 -*-
"""CUMCM2026 C题 数据探索脚本（分析阶段）
输出关键统计量，供《框架设计.md》引用。
运行方式：在工作区根目录执行  python 求解/数据探索.py
"""
import os
import datetime as dt
import numpy as np
import pandas as pd

ROOT = os.getcwd()
def P(*a):
    return os.path.join(ROOT, *a)

def hour_label(k):
    """小时 k (1..24) 对应的附件2时间列标签（区间末时刻）。"""
    return '0:00+1' if k == 24 else dt.time(k, 0)

print("=" * 78)
print("附件1（某天：电价 / 小区负载 / 光伏预测功率，10分钟粒度）")
print("=" * 78)
df1 = pd.read_excel(P("附件", "附件1.xlsx"))
df1.columns = ["时间", "电价", "小区负载", "光伏发电预测功率"]
for c in df1.columns[1:]:
    df1[c] = pd.to_numeric(df1[c], errors="coerce")
print("行数 =", len(df1), "| 首/末时间标签:", df1["时间"].iloc[0], "->", df1["时间"].iloc[-1])
print("电价: min %.4f / max %.4f / mean %.4f 元/kWh" % (df1["电价"].min(), df1["电价"].max(), df1["电价"].mean()))
print("负载: min %.0f / max %.0f / mean %.0f kW | 日电量 %.0f kWh" %
      (df1["小区负载"].min(), df1["小区负载"].max(), df1["小区负载"].mean(),
       df1["小区负载"].sum() * 10 / 60))
print("光伏预测: max %.0f kW | 非零时段 %d 个(%.1f h) | 日电量 %.0f kWh" %
      (df1["光伏发电预测功率"].max(), (df1["光伏发电预测功率"] > 0).sum(),
       (df1["光伏发电预测功率"] > 0).sum() * 10 / 60,
       df1["光伏发电预测功率"].sum() * 10 / 60))
print("净缺口(负载-光伏)日电量 %.0f kWh | 光伏日电量占负载 %.1f%%" %
      ((df1["小区负载"] - df1["光伏发电预测功率"]).sum() * 10 / 60,
       100 * df1["光伏发电预测功率"].sum() / df1["小区负载"].sum()))
print("电价日内小时均值曲线(元/kWh):")
hp = df1["电价"].values.reshape(24, 6).mean(1)
print("  " + "  ".join("%2d时%.3f" % (h, hp[h]) for h in range(24)))

print()
print("=" * 78)
print("附件2（2025.1.1-12.31 每天 小区负载 / 光伏实际功率，10分钟粒度）")
print("=" * 78)
load_df = pd.read_excel(P("附件", "附件2.xlsx"), sheet_name="小区负载")
pv_df = pd.read_excel(P("附件", "附件2.xlsx"), sheet_name="光伏发电实际功率")
load_v = load_df.iloc[:, 1:].astype(float).values   # (365, 144)
pv_v = pv_df.iloc[:, 1:].astype(float).values
times = list(load_df.columns[1:])
dates = pd.to_datetime(load_df.iloc[:, 0].astype(str).str[:10])
print("形状:", load_v.shape, "| 列标签类型:", type(times[0]).__name__, "| 末列:", times[-1])
print("负载: 全年 min %.0f / max %.0f / mean %.0f kW | 日电量 mean %.0f / max %.0f kWh" %
      (load_v.min(), load_v.max(), load_v.mean(),
       (load_v.sum(1) * 10 / 60).mean(), (load_v.sum(1) * 10 / 60).max()))
print("光伏实际: max %.0f kW | 日电量 min %.0f / mean %.0f / max %.0f kWh" %
      (pv_v.max(), (pv_v.sum(1) * 10 / 60).min(),
       (pv_v.sum(1) * 10 / 60).mean(), (pv_v.sum(1) * 10 / 60).max()))
print("月度统计（日均负载 kW | 日均光伏电量 kWh | 日均缺口电量 kWh）:")
month = dates.dt.month.values
for m in range(1, 13):
    mask = month == m
    print("  %2d月: %6.0f | %6.0f | %6.0f" %
          (m, load_v[mask].mean(), (pv_v[mask].sum(1) * 10 / 60).mean(),
           ((load_v - pv_v)[mask].sum(1) * 10 / 60).mean()))
print("日内典型曲线（全年小时均值, kW）:")
for k in range(24):
    a, b = k * 6, min(k * 6 + 6, 144)
    print("  %2d:00 %6.0f %6.0f" % (k, load_v[:, a:b].mean(), pv_v[:, a:b].mean()))
print("附件1 vs 附件2全年均值: 负载相关 %.4f | 光伏相关 %.4f" %
      (np.corrcoef(df1["小区负载"].values, load_v.mean(0))[0, 1],
       np.corrcoef(df1["光伏发电预测功率"].values, pv_v.mean(0))[0, 1]))

print()
print("=" * 78)
print("预测难度评估（为问题2的0:00决策提供依据）")
print("=" * 78)
# 昨日持续法：用昨天同时刻值预测今天
persist_load = load_v[:-1]          # 预测 = 昨日实际
persist_pv = pv_v[:-1]
err_l = load_v[1:] - persist_load
err_p = pv_v[1:] - persist_pv
print("昨日持续法误差(同时刻, kW): 负载 MAE %.0f RMSE %.0f | 光伏 MAE %.0f RMSE %.0f" %
      (np.abs(err_l).mean(), np.sqrt((err_l ** 2).mean()),
       np.abs(err_p).mean(), np.sqrt((err_p ** 2).mean())))
# 7天滑动平均法
w = np.ones(7) / 7
smooth_l = np.apply_along_axis(lambda c: np.convolve(c, w, 'valid'), 0, load_v)
smooth_p = np.apply_along_axis(lambda c: np.convolve(c, w, 'valid'), 0, pv_v)
err_l7 = load_v[6:] - smooth_l
err_p7 = pv_v[6:] - smooth_p
print("7天滑动平均法误差(同时刻, kW): 负载 MAE %.0f RMSE %.0f | 光伏 MAE %.0f RMSE %.0f" %
      (np.abs(err_l7).mean(), np.sqrt((err_l7 ** 2).mean()),
       np.abs(err_p7).mean(), np.sqrt((err_p7 ** 2).mean())))
# 缺口电量误差（预测-实际，全天）：昨日持续法的缺口能量误差分布
gap_act = (load_v - pv_v).sum(1) * 10 / 60
gap_fc = (load_v[:-1] - pv_v[:-1]).sum(1) * 10 / 60
e_gap = gap_act[1:] - gap_fc
print("全天缺口电量 昨日持续法误差: mean %+.0f kWh | MAE %.0f | std %.0f | P5/P95 %+.0f/%+.0f" %
      (e_gap.mean(), np.abs(e_gap).mean(), e_gap.std(),
       np.percentile(e_gap, 5), np.percentile(e_gap, 95)))

print()
print("=" * 78)
print("附件3（4个预报时刻 x 未来24小时整点光伏预报）")
print("=" * 78)
fc = pd.read_excel(P("附件", "附件3.xlsx"))
fc.columns = ["日期", "预报时刻"] + ["预报%d小时" % i for i in range(1, 25)]
fc["日期"] = fc["日期"].ffill()
fc["日期"] = pd.to_datetime(fc["日期"])
print("行数:", len(fc), "| 每天预报次数:", set(fc.groupby("日期").size().values),
      "| 预报时刻:", sorted(fc["预报时刻"].unique()))
# 实际小时光伏（区间末时刻列）
actual_h = {k: pv_v[:, times.index(hour_label(k))] for k in range(1, 25)}
print("0:00预报按提前期的误差（365天, kW | MAE / RMSE / bias）:")
zero_fc = fc[fc["预报时刻"] == "0:00"]
for lead in [1, 3, 6, 9, 12, 15, 18, 21, 24]:
    fv = zero_fc["预报%d小时" % lead].astype(float).values
    av = actual_h[lead]
    err = fv - av
    print("  提前%2dh: MAE %6.1f | RMSE %6.1f | bias %+6.1f" %
          (lead, np.abs(err).mean(), np.sqrt((err ** 2).mean()), err.mean()))
print("0:00预报全天电量误差: |误差|日电量 mean %.0f kWh (实际日均 %.0f, 相对 %.1f%%)" %
      (np.abs(zero_fc.iloc[:, 2:].astype(float).values -
              np.column_stack([actual_h[k] for k in range(1, 25)])).sum(1).mean(),
       np.column_stack([actual_h[k] for k in range(1, 25)]).sum(1).mean(),
       100 * np.abs(zero_fc.iloc[:, 2:].astype(float).values.sum(1) -
                    np.column_stack([actual_h[k] for k in range(1, 25)]).sum(1)).mean() /
       np.column_stack([actual_h[k] for k in range(1, 25)]).sum(1).mean()))
# 6:00预报对当天剩余时段(7:00-24:00) 是否优于0:00预报
z7_24 = zero_fc[["预报%d小时" % k for k in range(7, 25)]].astype(float).values
six_fc = fc[fc["预报时刻"] == "6:00"][["预报%d小时" % k for k in range(1, 19)]].astype(float).values
act7_24 = np.column_stack([actual_h[k] for k in range(7, 25)])
print("当天7:00-24:00光伏 MAE: 0:00预报 %.0f kW vs 6:00预报 %.0f kW (改善 %.0f%%)" %
      (np.abs(z7_24 - act7_24).mean(), np.abs(six_fc - act7_24).mean(),
       100 * (1 - np.abs(six_fc - act7_24).mean() / np.abs(z7_24 - act7_24).mean())))

print()
print("=" * 78)
print("附件4（2025全年 10分钟电价）")
print("=" * 78)
pr_df = pd.read_excel(P("附件", "附件4.xlsx"))
pr_v = pr_df.iloc[:, 1:].astype(float).values
print("电价: 全年 min %.4f / max %.4f / mean %.4f 元/kWh" %
      (pr_v.min(), pr_v.max(), pr_v.mean()))
print("日内价差(日max-min): mean %.4f / max %.4f 元/kWh" %
      ((pr_v.max(1) - pr_v.min(1)).mean(), (pr_v.max(1) - pr_v.min(1)).max()))
print("同一时刻跨日标准差: mean %.4f 元/kWh | 相邻日同刻差 std %.4f" %
      (pr_v.std(0).mean(), np.diff(pr_v, axis=0).std()))
print("电价与负载(同时刻)相关系数 %.3f | 电价与光伏相关系数 %.3f" %
      (np.corrcoef(pr_v.ravel(), load_v.ravel())[0, 1],
       np.corrcoef(pr_v.ravel(), pv_v.ravel())[0, 1]))
print("电价日内典型曲线（小时均值, 元/kWh）:")
hourly = pr_v.reshape(365, 24, 6).mean(2).mean(0)
print("  " + "  ".join("%2d时%.3f" % (h, hourly[h]) for h in range(24)))
print("附件1电价曲线 vs 附件4年均日内曲线 相关系数: %.3f" %
      np.corrcoef(df1["电价"].values, hourly.repeat(6))[0, 1])
print("月度均价:")
for m in range(1, 13):
    print("  %2d月: %.4f" % (m, pr_v[month == m].mean()))
print("电价昨日持续法误差(元/kWh): MAE %.4f RMSE %.4f" %
      (np.abs(np.diff(pr_v, axis=0)).mean(), np.sqrt((np.diff(pr_v, axis=0) ** 2).mean())))

print()
print("=" * 78)
print("表3 指定4天的概况（负载/光伏/电价）")
print("=" * 78)
for ds in ["2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"]:
    d = pd.Timestamp(ds)
    i = np.where(dates == d)[0]
    if len(i) == 0:
        print(ds, "未找到"); continue
    i = i[0]
    print("%s: 负载max %.0f kW | 日负载电量 %.0f | 光伏电量 %.0f kWh | 缺口 %.0f kWh | 电价mean %.4f/max %.4f" %
          (ds, load_v[i].max(), load_v[i].sum() * 10 / 60, pv_v[i].sum() * 10 / 60,
           (load_v[i] - pv_v[i]).sum() * 10 / 60, pr_v[i].mean(), pr_v[i].max()))

print()
print("=" * 78)
print("附件5 模板核对")
print("=" * 78)
r1 = pd.read_excel(P("附件", "附件5", "result1.xlsx"), sheet_name=None)
for name, sh in r1.items():
    print("result1[%s] %s | 首行: %s | 末行: %s" % (name, sh.shape, list(sh.iloc[0]), list(sh.iloc[-1])))
r2 = pd.read_excel(P("附件", "附件5", "result2.xlsx"), sheet_name=None)
for name, sh in r2.items():
    print("result2[%s] %s | 首末列: %s ... %s" %
          (name, sh.shape, list(sh.columns[:2]), list(sh.columns[-3:])))
