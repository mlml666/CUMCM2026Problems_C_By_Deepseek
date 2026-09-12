# -*- coding: utf-8 -*-
"""审稿补充实验（对应审稿意见 H-6 与 M-5）
(1) 预报误差放大 1.5 倍情景下，问题3 各策略费用与边际价值
(2) 问题2 的对照模型数值：两阶段随机规划（SAA, S=10）与鲁棒模型（Γ=1）
输出：审稿结果/补充实验_预报放大.csv、审稿结果/补充实验_对照模型.csv
"""
import importlib.util
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
RES = C.RES

df1 = C.load_att1()
price = df1['电价'].values.astype(float)
dates, load, pv = C.load_att2()
fc = C.load_att3()
rep = C.report_dates()
ridx = [C.day_index(dates, d) for d in rep]
L_PRED = C.best_load_predictor()

# 载入问题3 模块以复用滚动策略实现
spec = importlib.util.spec_from_file_location('p3', os.path.join(ROOT, '求解', '问题3', '问题3_求解.py'))
p3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p3)
p3.DEV = 0.5


def hourly_actual(i):
    """当日实测逐小时光伏（与附件3 整点对齐）"""
    return np.array([pv[i, k * 6:(k + 1) * 6].mean() for k in range(24)])


def amplified_fc(scale):
    """把附件3 预报误差放大 scale 倍：F' = A + scale*(F - A)"""
    out = {}
    for (d, ts), h in fc.items():
        i = C.day_index(dates, d)
        if i is None:
            continue
        out[(d, ts)] = hourly_actual(i) + scale * (np.asarray(h, float) - hourly_actual(i))
    return out


# ---------- (1) 预报误差放大 ----------
rows = []
for scale in [1.0, 1.5]:
    fcx = fc if scale == 1.0 else amplified_fc(scale)
    tot = {p: 0.0 for p in ['P0', 'P1', 'P2', 'P3']}
    for d, i in zip(rep, ridx):
        Lhat = C.pred(load[:i], dates[:i], L_PRED, d)
        out = p3.run_day(fcx, d, i, load, pv, price, Lhat, 0.05, hourly=False)
        for p in tot:
            tot[p] += out[p]['total']
    rows.append({'预报误差倍数': scale, 'P0': tot['P0'], 'P1': tot['P1'],
                 'P2': tot['P2'], 'P3': tot['P3']})
    print('误差×%.1f: P0=%.0f P1=%.0f P2=%.0f P3=%.0f 元' %
          (scale, tot['P0'], tot['P1'], tot['P2'], tot['P3']))
dfa = pd.DataFrame(rows)
dfa['P3相对P0%'] = 100 * (dfa['P3'] - dfa['P0']) / dfa['P0']
dfa['12:00边际价值'] = dfa['P1'] - dfa['P2']
dfa.to_csv(os.path.join(OUT, '补充实验_预报放大.csv'), index=False, encoding='utf-8-sig')
print(dfa.to_string(index=False, float_format=lambda x: '%.2f' % x))


# ---------- (2) 对照模型：SAA 与鲁棒 ----------
def saa_plan(Lhat, Phat, price_t, scen_L, scen_P, e0=C.E0):
    """两阶段随机规划（第一段 g,a,b 与情景无关；第二段各情景紧急购电与弃光）"""
    n, S = len(Lhat), len(scen_L)
    nv = 5 * n + S * n + S * n          # e^s 与 s^s
    c = np.zeros(nv)
    c[:n] = price_t
    c[5 * n:5 * n + S * n] = 5.0 * np.tile(price_t, S)
    rows, cols, vals, beq = [], [], [], []
    r = 0
    for s in range(S):
        for i in range(n):
            rows += [r, r, r, r]
            cols += [i, 2 * n + i, 5 * n + s * n + i, 5 * n + S * n + s * n + i]
            vals += [1.0, C.ETA_D, 1.0, -1.0]
            beq.append(scen_L[s][i] * C.DT - scen_P[s][i] * C.DT)
            r += 1
    for i in range(n):                      # 储能动态（共享）
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
    for i in range(n):                      # 充电量进入平衡（共享，母线侧）
        rows.append(r); cols.append(n + i); vals.append(-1.0 / C.ETA_C)
        rows.append(r); cols.append(5 * n + S * n + 0 * n + i); vals.append(0.0)
        # 充电项统一在情景行中扣除：此处仅占位，见下方情景行修改
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
for d, i in zip(rep, ridx):
    Lhat = C.pred(load[:i], dates[:i], L_PRED, d)
    Phat = C.pred(pv[:i], dates[:i], C.best_pv_predictor(), d)
    hist = list(range(max(0, i - S), i))
    scen_L = [load[j] for j in hist]
    scen_P = [pv[j] for j in hist]
    g, a, b = saa_plan(Lhat, Phat, price, scen_L, scen_P)
    e = np.maximum(0.0, load[i] * C.DT - g - C.ETA_D * b - pv[i] * C.DT)
    tot_saa += float(np.dot(price, g)) + 5.0 * float(np.dot(price, e))
    # 鲁棒（Γ=1）：用历史同时段标准差构造不确定集
    sig_L = load[hist].std(0) if len(hist) > 1 else Lhat * 0.05
    sig_P = pv[hist].std(0) if len(hist) > 1 else Phat * 0.05
    r = C.solve_plan(Lhat + sig_L, np.maximum(0.0, Phat - sig_P), price, E_init=C.E0, E_term=C.E0)
    e2 = np.maximum(0.0, load[i] * C.DT - r['g'] - C.ETA_D * r['b'] - pv[i] * C.DT)
    tot_rob += float(np.dot(price, r['g'])) + 5.0 * float(np.dot(price, e2))

n2 = np.load(os.path.join(RES, '问题2_结果.npz'))
base = float(n2['plan_cost'].sum() + n2['emg_cost'].sum())
neg = float(n2['cost0'].sum())
perfect = float(n2['costP'].sum())
dfb = pd.DataFrame([
    {'模型': '本文：预测 + 安全裕度（α=0.15）', '全年总费用元': base, '说明': '主模型'},
    {'模型': '对照①：无裕度计划', '全年总费用元': neg, '说明': 'α=β=0'},
    {'模型': '对照②：两阶段随机规划（SAA, S=10）', '全年总费用元': tot_saa, '说明': '情景=前 10 日实际曲线，样本外结算'},
    {'模型': '对照③：鲁棒优化（Γ=1，箱式不确定集）', '全年总费用元': tot_rob, '说明': 'σ 由前 10 日同时段标准差估计'},
    {'模型': '对照④：完美信息下界', '全年总费用元': perfect, '说明': '不可达，信息价值基准'},
])
dfb['相对主模型%'] = 100 * (dfb['全年总费用元'] - base) / base
dfb.to_csv(os.path.join(OUT, '补充实验_对照模型.csv'), index=False, encoding='utf-8-sig')
print()
print(dfb.to_string(index=False, float_format=lambda x: '%.2f' % x))
