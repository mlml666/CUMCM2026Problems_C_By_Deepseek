# -*- coding: utf-8 -*-
import pandas as pd, numpy as np
A = r"E:\qq文件\CUMCM2026Problems\C题\附件"
p4 = pd.read_excel(A + r"\附件4.xlsx", header=None)
lab = p4.iloc[0, 1:].astype(str).values
v4 = p4.iloc[1:, 1:].astype(float).values
print("附件4 shape", v4.shape)
print("price min/max/mean %.4f %.4f %.4f" % (v4.min(), v4.max(), v4.mean()))
rng = v4.max(1) - v4.min(1)
print("日内极差 mean %.4f max %.4f" % (rng.mean(), rng.max()))
print("同一时刻跨日 std 均值 %.4f" % v4.std(0).mean())

a1 = pd.read_excel(A + r"\附件1.xlsx")
a1.columns = ['时间', '电价', '小区负载', '光伏发电预测功率']
print("附件1 电价 min/max/mean %.4f %.4f %.4f" % (a1['电价'].min(), a1['电价'].max(), a1['电价'].mean()))
print("附件1 负载 min/max/mean %.1f %.1f %.1f 日电量 %.1f" % (
    a1['小区负载'].min(), a1['小区负载'].max(), a1['小区负载'].mean(), a1['小区负载'].sum() / 6))
print("附件1 光伏 peak %.1f 日电量 %.1f 占负载 %.3f%%" % (
    a1['光伏发电预测功率'].max(), a1['光伏发电预测功率'].sum() / 6,
    100 * (a1['光伏发电预测功率'].sum() / 6) / (a1['小区负载'].sum() / 6)))
print("附件1 净缺口 %.2f" % ((a1['小区负载'] - a1['光伏发电预测功率']).sum() / 6))

d2 = pd.read_excel(A + r"\附件2.xlsx", sheet_name='小区负载')
lv = d2.iloc[:, 1:].astype(float).values
print("附件2 负载 min/max/mean %.1f %.1f %.1f" % (lv.min(), lv.max(), lv.mean()))
d2b = pd.read_excel(A + r"\附件2.xlsx", sheet_name='光伏发电实际功率')
pv = d2b.iloc[:, 1:].astype(float).values
pvday = pv.sum(1) / 6
print("附件2 光伏日电量 min/mean/max %.1f %.1f %.1f" % (pvday.min(), pvday.mean(), pvday.max()))
gap = (lv - pv).sum(1) / 6
print("月度净缺口:", {m: round(float(gap[[i for i in range(len(gap)) if i % 1 == 0]].__len__())) for m in []} or "")
import datetime as dt
dates = pd.to_datetime(d2.iloc[:, 0].astype(str).str[:10]).dt.date.values
mon = np.array([d.month for d in dates])
for m in range(1, 13):
    print("  月%2d 净缺口日均 %10.1f  负载日均 %8.1f  光伏日电量 %9.1f  电价月均 %.4f" % (
        m, gap[mon == m].mean(), v4[mon == m].mean() * 0 + lv[mon == m].mean(), pvday[mon == m].mean(),
        v4[mon == m].mean()))
print("电价-负载 corr %.4f" % np.corrcoef(v4.ravel(), lv.ravel())[0, 1])
print("电价-光伏 corr %.4f" % np.corrcoef(v4.ravel(), pv.ravel())[0, 1])
# 典型日曲线与全年均值曲线相关性
print("附件1 负载 vs 附件2 全年均值曲线 corr %.6f" % np.corrcoef(a1['小区负载'].values, lv.mean(0))[0, 1])
print("附件1 光伏 vs 附件2 全年均值曲线 corr %.6f" % np.corrcoef(a1['光伏发电预测功率'].values, pv.mean(0))[0, 1])
# 四天
for s in ['2025-03-20', '2025-06-21', '2025-09-23', '2025-12-21']:
    d = dt.date.fromisoformat(s); i = list(dates).index(d)
    print("%s: 负载日均 %.1f 光伏日电量 %.1f 净缺口 %.1f 电价均值 %.4f" % (
        s, lv[i].mean(), pvday[i], gap[i], v4[i].mean()))
