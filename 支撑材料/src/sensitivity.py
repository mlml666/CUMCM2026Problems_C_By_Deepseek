# -*- coding: utf-8 -*-
"""Phase 3 补充灵敏度实验
(1) 问题2：紧急购电费率倍数 K 的敏感性（计划不变，按实际负载/光伏重新结算）
(2) 问题3：违约费率取对称 (1.0,1.0)（dev_pen=1.0）时 P0--P3 的全年费用
输出：论文/图/灵敏度_问题2_费率.csv、灵敏度_问题3_费率.csv
"""
import os
import sys
import importlib.util
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '求解'))
import common as C

OUT = os.path.join(ROOT, '论文', '图')
RES = C.RES

d1 = C.load_att1()
price = d1['电价'].values.astype(float)
dates, load, pv = C.load_att2()
rep = C.report_dates()
ridx = [C.day_index(dates, d) for d in rep]
n2 = np.load(os.path.join(RES, '问题2_结果.npz'))
G, A, B = n2['G'], n2['A'], n2['B']
L, P = load[ridx], pv[ridx]

# ---------- (1) 紧急费率倍数 K ----------
e_all = np.maximum(0.0, L * C.DT - G - C.ETA_D * B - P * C.DT)
plan_fee = float((G * price).sum())
rows = []
for K in [3, 4, 5, 6, 8]:
    emg = K * float((e_all * price).sum())
    rows.append({'紧急费率倍数K': K, '计划购电费元': plan_fee, '紧急购电费元': emg,
                 '总费用元': plan_fee + emg, '紧急费占比%': 100 * emg / (plan_fee + emg)})
df1 = pd.DataFrame(rows)
df1.to_csv(os.path.join(OUT, '灵敏度_问题2_费率.csv'), index=False, encoding='utf-8-sig')
print('（1）问题2 紧急费率倍数敏感性（总费用为 334 天合计）')
print(df1.to_string(index=False, float_format=lambda x: '%.0f' % x))

# ---------- (2) 问题3 违约费率对称 (1.0,1.0) ----------
spec = importlib.util.spec_from_file_location('p3', os.path.join(ROOT, '求解', '问题3', '问题3_求解.py'))
p3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p3)
fc = C.load_att3()
L_PRED = C.best_load_predictor()
ALPHA = 0.05

for dev_pen, tag in [(0.5, '基准(0.5,1.5)'), (1.0, '对称(1.0,1.0)')]:
    p3.DEV = dev_pen
    tot = {p: 0.0 for p in ['P0', 'P1', 'P2', 'P3']}
    for d, i in zip(rep, ridx):
        Lhat = C.pred(load[:i], dates[:i], L_PRED, d)
        out = p3.run_day(fc, d, i, load, pv, price, Lhat, ALPHA, hourly=False)
        for p in tot:
            tot[p] += out[p]['total']
    rows = [{'违约费率口径': tag, '策略': p, '总费用元': tot[p]} for p in ['P0', 'P1', 'P2', 'P3']]
    df2 = pd.DataFrame(rows)
    if dev_pen == 0.5:
        df_all = df2
    else:
        df_all = pd.concat([df_all, df2], ignore_index=True)
    print('（2）%s：P0=%.0f P1=%.0f P2=%.0f P3=%.0f' % (tag, tot['P0'], tot['P1'], tot['P2'], tot['P3']))
df_all.to_csv(os.path.join(OUT, '灵敏度_问题3_费率.csv'), index=False, encoding='utf-8-sig')
print('完成')
