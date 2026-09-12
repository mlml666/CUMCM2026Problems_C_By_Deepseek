# -*- coding: utf-8 -*-
"""审稿补充实验：对照模型数值（问题2）
两阶段随机规划 SAA（S=10，情景=前 10 日实际曲线）与鲁棒模型（Γ=1，箱式不确定集）
输出：审稿结果/补充实验_对照模型.csv
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linprog

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '求解'))
import common as C

OUT = os.path.join(ROOT, '审稿结果')
df1 = C.load_att1()
price = df1['电价'].values.astype(float)
dates, load, pv = C.load_att2()
rep = C.report_dates()
ridx = [C.day_index(dates, d) for d in rep]
L_PRED = C.best_load_predictor()
P_PRED = C.best_pv_predictor()


def saa_plan(price_t, scen_L, scen_P, e0=C.E0):
    """两阶段随机规划：第一段 (g,a,b,E) 与情景无关，第二段 e^s、s^s 追偿
    情景平衡：g_i + η_d b_i + P^s_i Δt + e^s_i = L^s_i Δt + a_i/η_c + s^s_i
    """
    n, S = len(price_t), len(scen_L)
    nv = 5 * n + 2 * S * n
    c = np.zeros(nv)
    c[:n] = price_t
    c[5 * n:5 * n + S * n] = 5.0 * np.tile(price_t, S)
    rows, cols, vals, beq = [], [], [], []
    r = 0
    for s in range(S):
        for i in range(n):
            rows += [r, r, r, r, r]
            cols += [i, 2 * n + i, n + i, 5 * n + s * n + i, 5 * n + S * n + s * n + i]
            vals += [1.0, C.ETA_D, -1.0 / C.ETA_C, 1.0, -1.0]
            beq.append(scen_L[s][i] * C.DT - scen_P[s][i] * C.DT)
            r += 1
    for i in range(n):                                   # 储能动态（全情景共享）
        rows.append(r); cols.append(4 * n + i); vals.append(1.0)
        if i == 0:
            rows.append(r); cols.append(n + i); vals.append(-1.0)
            rows.append(r); cols.append(2 * n + i); vals.append(1.0)
            beq.append(e0)
        else:
            rows.append(r); cols.append(4 * n + i - 1); vals.append(-1.0)
            rows.append(r); cols.append(n + i); vals.append(-1.0)
            rows.append(r); cols.append(2 * n + i); vals.append(1.0)
            beq.append(0.0)
        r += 1
    rows.append(r); cols.append(4 * n + n - 1); vals.append(1.0); beq.append(e0); r += 1
    A = sparse.csr_matrix((vals, (rows, cols)), shape=(r, nv))
    bounds = ([(0, None)] * n + [(0, C.ABAR)] * n + [(0, C.ABAR)] * n + [(0, None)] * n
              + [(C.E_MIN, C.E_MAX)] * n + [(0, None)] * (S * n) + [(0, None)] * (S * n))
    res = linprog(c, A_eq=A, b_eq=np.array(beq), bounds=bounds, method='highs')
    if not res.success:
        raise RuntimeError(res.message)
    x = res.x
    return x[:n], x[n:2 * n], x[2 * n:3 * n]


S = 10
tot_saa = tot_rob = 0.0
n_saa_emg = n_rob_emg = 0.0
for d, i in zip(rep, ridx):
    hist = list(range(max(0, i - S), i))
    if len(hist) < 2:
        hist = list(range(0, i)) or [0]
    scen_L = [load[j] for j in hist]
    scen_P = [pv[j] for j in hist]
    g, a, b = saa_plan(price, scen_L, scen_P)
    e = np.maximum(0.0, load[i] * C.DT - g - C.ETA_D * b - pv[i] * C.DT)
    tot_saa += float(np.dot(price, g)) + 5.0 * float(np.dot(price, e))
    n_saa_emg += float(e.sum())
    Lhat = C.pred(load[:i], dates[:i], L_PRED, d)
    Phat = C.pred(pv[:i], dates[:i], P_PRED, d)
    sig_L = load[hist].std(0)
    sig_P = pv[hist].std(0)
    r = C.solve_plan(Lhat + sig_L, np.maximum(0.0, Phat - sig_P), price, E_init=C.E0, E_term=C.E0)
    e2 = np.maximum(0.0, load[i] * C.DT - r['g'] - C.ETA_D * r['b'] - pv[i] * C.DT)
    tot_rob += float(np.dot(price, r['g'])) + 5.0 * float(np.dot(price, e2))
    n_rob_emg += float(e2.sum())

n2 = np.load(os.path.join(RES := os.path.join(ROOT, '求解', '结果'), '问题2_结果.npz'))
base = float(n2['plan_cost'].sum() + n2['emg_cost'].sum())
neg = float(n2['cost0'].sum())
perfect = float(n2['costP'].sum())
dfb = pd.DataFrame([
    {'模型': '本文：预测 + 安全裕度（α=0.15）', '全年总费用元': base,
     '紧急购电量kWh': float(n2['EM'].sum()), '说明': '主模型'},
    {'模型': '对照①：无裕度计划（α=β=0）', '全年总费用元': neg,
     '紧急购电量kWh': float(n2['EM0'].sum()), '说明': '不作安全准备'},
    {'模型': '对照②：两阶段随机规划（SAA, S=10）', '全年总费用元': tot_saa,
     '紧急购电量kWh': n_saa_emg, '说明': '情景取前 10 日实际曲线，样本外结算'},
    {'模型': '对照③：鲁棒优化（Γ=1，箱式不确定集）', '全年总费用元': tot_rob,
     '紧急购电量kWh': n_rob_emg, '说明': 'L̂+σ_L、P̂−σ_P（σ 由前 10 日同时段标准差估）'},
    {'模型': '对照④：完美信息下界', '全年总费用元': perfect,
     '紧急购电量kWh': 0.0, '说明': '不可达，信息价值基准'},
])
dfb['相对主模型%'] = 100 * (dfb['全年总费用元'] - base) / base
dfb.to_csv(os.path.join(OUT, '补充实验_对照模型.csv'), index=False, encoding='utf-8-sig')
print(dfb.to_string(index=False, float_format=lambda x: '%.2f' % x))
