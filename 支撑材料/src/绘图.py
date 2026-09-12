# -*- coding: utf-8 -*-
"""Phase 3 论文图表生成（300 dpi，全部数据驱动，数据源为求解结果 npz/CSV 与附件）
输出目录：论文/图/
运行：python 论文/绘图.py
"""
import os
import sys
import datetime as dt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '求解'))
import common as C

ROOT = C.ROOT
OUT = os.path.join(ROOT, '论文', '图')
os.makedirs(OUT, exist_ok=True)
plt = C.setup_matplotlib()
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10.5
plt.rcParams['axes.titlesize'] = 11
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['lines.linewidth'] = 1.2

RES = C.RES
CMAP = 'viridis'


def sv(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p)
    plt.close(fig)
    print('  ->', name)


def lp_sens(L, P, price, eta_c=0.9, eta_d=0.9, abar=5000.0 / 6, emin=1200.0, emax=10800.0, e0=6000.0):
    """参数化单日 LP（仅供灵敏度分析使用，变量布局与 common.solve_plan 一致）
    变量 [g(n), a(n), b(n), s(n), E(n)]，返回 (费用, 购电量, 电池侧吞吐量, E轨迹)
    """
    import numpy as np
    from scipy.optimize import linprog
    from scipy import sparse
    n = len(L)
    nv = 5 * n
    c = np.zeros(nv); c[:n] = price
    rows, cols, vals, beq = [], [], [], []
    r = 0
    for i in range(n):
        rows += [r, r, r, r]; cols += [i, 2 * n + i, n + i, 3 * n + i]
        vals += [1.0, eta_d, -1.0 / eta_c, -1.0]
        beq.append(L[i] / 6.0 - P[i] / 6.0); r += 1
    for i in range(n):
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
    bounds = ([(0, None)] * n + [(0, abar)] * n + [(0, abar)] * n + [(0, None)] * n
              + [(emin, emax)] * n)
    res = linprog(c, A_eq=A, b_eq=np.array(beq), bounds=bounds, method='highs')
    x = res.x
    return float(res.fun), x[:n], float(x[n:2 * n].sum()), x[4 * n:5 * n]


def main():
    d1 = C.load_att1()
    price1 = d1['电价'].values.astype(float)
    L1 = d1['小区负载'].values.astype(float)
    P1 = d1['光伏发电预测功率'].values.astype(float)
    dates, load, pv = C.load_att2()
    dp, price4 = C.load_att4()
    rep = C.report_dates()
    ridx = [C.day_index(dates, d) for d in rep]
    nd = len(rep)
    h = C.hours_axis()
    hour_of = np.repeat(np.arange(24), 6)

    # ================= 数据画像 =================
    fig, ax = plt.subplots(2, 2, figsize=(11, 7))
    im0 = ax[0, 0].imshow(load.T, aspect='auto', origin='lower', cmap=CMAP,
                          extent=[0, 365, 0, 24])
    ax[0, 0].set_title('(a) 全年小区负载 (kW)'); ax[0, 0].set_ylabel('时刻 (h)')
    ax[0, 0].set_xlabel('日期序号 (2025-01-01 起)'); fig.colorbar(im0, ax=ax[0, 0])
    im1 = ax[0, 1].imshow(pv.T, aspect='auto', origin='lower', cmap=CMAP, extent=[0, 365, 0, 24])
    ax[0, 1].set_title('(b) 全年光伏实际功率 (kW)'); ax[0, 1].set_xlabel('日期序号')
    fig.colorbar(im1, ax=ax[0, 1])
    im2 = ax[1, 0].imshow(price4.T, aspect='auto', origin='lower', cmap=CMAP, extent=[0, 365, 0, 24])
    ax[1, 0].set_title('(c) 全年实时电价 (元/kWh)'); ax[1, 0].set_ylabel('时刻 (h)')
    ax[1, 0].set_xlabel('日期序号'); fig.colorbar(im2, ax=ax[1, 0])
    ax[1, 1].plot(h, L1, label='负载（附件1）', color='tab:blue')
    ax[1, 1].plot(h, P1, label='光伏预测（附件1）', color='tab:orange')
    ax[1, 1].plot(h, L1 - P1, label='净缺口', color='tab:red', lw=1.0)
    ax2 = ax[1, 1].twinx()
    ax2.plot(h, price1, label='电价（附件1）', color='tab:green', ls='--', lw=1.0)
    ax2.set_ylabel('电价 (元/kWh)', color='tab:green')
    ax[1, 1].set_title('(d) 典型日（附件1）负载/光伏/净缺口 与电价')
    ax[1, 1].set_xlabel('时刻 (h)'); ax[1, 1].set_ylabel('功率 (kW)')
    ax[1, 1].legend(loc='upper left', fontsize=8)
    ax2.legend(loc='upper right', fontsize=8)
    fig.tight_layout(); sv(fig, '图01_数据总览.png')

    month = np.array([d.month for d in dates])
    mr = []
    for m in range(1, 13):
        mk = month == m
        mr.append([m, load[mk].mean(), pv[mk].sum(1).mean() * C.DT / 1000,
                   (load[mk] - pv[mk]).sum(1).mean() * C.DT / 1000, price4[mk].mean()])
    mr = np.array(mr)
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.9))
    ax[0].bar(mr[:, 0] - 0.2, mr[:, 2], width=0.4, label='光伏日电量 (MWh)', color='tab:orange')
    ax[0].bar(mr[:, 0] + 0.2, mr[:, 3], width=0.4, label='净缺口日电量 (MWh)', color='tab:red')
    ax[0].set_xlabel('月份'); ax[0].set_ylabel('电量 (MWh)'); ax[0].legend()
    ax[0].set_title('(a) 光伏电量与净缺口电量的月度分布')
    ax[1].plot(mr[:, 0], mr[:, 1], 'o-', color='tab:blue', label='日均负载 (kW)')
    axb = ax[1].twinx()
    axb.bar(mr[:, 0], mr[:, 4], width=0.5, alpha=0.35, color='tab:green', label='月均价 (元/kWh)')
    axb.set_ylabel('电价 (元/kWh)', color='tab:green')
    ax[1].set_xlabel('月份'); ax[1].set_ylabel('负载 (kW)'); ax[1].legend(loc='upper left')
    ax[1].set_title('(b) 负载与电价的月度特征')
    fig.tight_layout(); sv(fig, '图02_月度特征.png')

    # 表3 四天
    kd = [pd.Timestamp(s).date() for s in ['2025-03-20', '2025-06-21', '2025-09-23', '2025-12-21']]
    fig, ax = plt.subplots(4, 1, figsize=(10.5, 9), sharex=True)
    for i, d in enumerate(kd):
        k = C.day_index(dates, d)
        ax[i].plot(h, load[k], color='tab:blue', label='负载')
        ax[i].plot(h, pv[k], color='tab:orange', label='光伏')
        ax[i].fill_between(h, 0, np.minimum(load[k], pv[k]), color='tab:green', alpha=0.18)
        ax2 = ax[i].twinx(); ax2.plot(h, price4[k], color='tab:red', ls='--', lw=1.0)
        ax2.set_ylabel('电价', color='tab:red', fontsize=8)
        ax[i].set_ylabel('kW'); ax[i].set_title('%s：负载 %.0f MWh，光伏 %.0f MWh，缺口 %.0f MWh'
                                                 % (d, load[k].sum() * C.DT / 1e3, pv[k].sum() * C.DT / 1e3,
                                                    (load[k] - pv[k]).sum() * C.DT / 1e3), fontsize=9)
        if i == 0:
            ax[i].legend(loc='upper left', fontsize=8)
    ax[-1].set_xlabel('时刻 (h)'); ax[-1].set_xlim(0, 24)
    fig.tight_layout(); sv(fig, '图03_表3四天.png')

    # ================= 问题1 =================
    det = pd.read_csv(os.path.join(RES, '问题1_逐时段明细.csv'))
    g, chg, dis, soc = det['购电量kWh'].values, det['充电量kWh'].values, det['放电量kWh'].values, det['储电量kWh'].values
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    ax[0].plot(h, price1, color='tab:red')
    ax[0].axhline(0.9 * 0.75, color='gray', ls='--', lw=1)
    ax[0].axhline(1.111 * 0.75, color='gray', ls=':', lw=1)
    ax[0].set_xlabel('时刻 (h)'); ax[0].set_ylabel('电价 (元/kWh)')
    ax[0].set_title('(a) 电价曲线与阈值示意（虚线 $0.9\\lambda$、点线 $1.111\\lambda$）')
    st = np.where(dis > 1e-3, 1, np.where(chg > 1e-3, -1, 0))
    ax[1].scatter(h[st == -1], price1[st == -1], s=10, color='tab:blue', label='充电')
    ax[1].scatter(h[st == 1], price1[st == 1], s=10, color='tab:red', label='放电')
    ax[1].scatter(h[st == 0], price1[st == 0], s=6, color='lightgray', label='闲置')
    ax[1].set_xlabel('时刻 (h)'); ax[1].set_ylabel('电价 (元/kWh)'); ax[1].legend()
    ax[1].set_title('(b) 充放电状态在电价轴上的分布（阈值策略验证）')
    fig.tight_layout(); sv(fig, '图04_问题1_阈值策略.png')

    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    ax[0].bar(h, g / C.DT, width=1 / 6.0, color='tab:cyan')
    ax[0].plot(h, (L1 - P1), color='tab:red', lw=1.0, label='净缺口功率')
    ax[0].set_xlabel('时刻 (h)'); ax[0].set_ylabel('功率 (kW)'); ax[0].legend()
    ax[0].set_title('(a) 计划购电功率与净缺口'); ax[0].set_xlim(0, 24)
    ax[1].plot(np.arange(0, C.T + 1) / 6.0, np.concatenate([[C.E0], soc]), color='tab:blue')
    ax[1].axhline(C.E_MAX, color='gray', ls='--', lw=1, label='上限 10800')
    ax[1].axhline(C.E_MIN, color='gray', ls=':', lw=1, label='下限 1200')
    ax[1].set_xlabel('时刻 (h)'); ax[1].set_ylabel('储电量 (kWh)'); ax[1].legend()
    ax[1].set_title('(b) 储电量轨迹（日周期 $E_{144}=E_0$）'); ax[1].set_xlim(0, 24)
    fig.tight_layout(); sv(fig, '图05_问题1_策略与储电量.png')

    # 灵敏度（参数化 LP 重解，OAT）
    scen = []
    variants = [('基准', {}), ('$\\eta=0.85$', dict(eta=0.85)), ('$\\eta=0.95$', dict(eta=0.95)),
                ('功率 $4000$ kW', dict(pb=4000.0)), ('功率 $6000$ kW', dict(pb=6000.0)),
                ('$E_{\\min}=2400$', dict(emin=2400.0)), ('$E_{\\max}=9600$', dict(emax=9600.0)),
                ('$E_0=3000$', dict(e0=3000.0)), ('$E_0=9000$', dict(e0=9000.0)),
                ('电价 $+10\\%$', dict(pmul=1.10)), ('电价 $-10\\%$', dict(pmul=0.90))]
    base_fee = None
    for name, kw in variants:
        fee, gg, tp, EE = lp_sens(L1, P1, price1 * kw.get('pmul', 1.0),
                                  eta_c=kw.get('eta', 0.9), eta_d=kw.get('eta', 0.9),
                                  abar=kw.get('pb', 5000.0) / 6.0,
                                  emin=kw.get('emin', 1200.0), emax=kw.get('emax', 10800.0),
                                  e0=kw.get('e0', 6000.0))
        if base_fee is None:
            base_fee = fee
        scen.append({'scenario': name, 'fee': fee, 'throughput': tp})
    sdf = pd.DataFrame(scen)
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 3.9))
    x = np.arange(len(sdf))
    ax[0].bar(x, sdf['fee'], color=['tab:gray'] + ['tab:blue'] * (len(sdf) - 1))
    ax[0].axhline(base_fee, color='tab:red', ls='--', lw=1)
    ax[0].set_xticks(x); ax[0].set_xticklabels(sdf['scenario'], rotation=40, ha='right', fontsize=8)
    ax[0].set_ylabel('全天购电费 (元)'); ax[0].set_title('(a) 单因素扰动下的全天购电费（虚线为基准）')
    ch = 100 * (sdf['fee'] - base_fee) / base_fee
    order = np.argsort(np.abs(ch.values))
    ax[1].barh(range(len(sdf)), ch.values[order],
               color=np.where(ch.values[order] >= 0, 'tab:red', 'tab:blue'))
    ax[1].set_yticks(range(len(sdf)))
    ax[1].set_yticklabels([sdf['scenario'].values[i] for i in order], fontsize=8)
    ax[1].axvline(0, color='k', lw=0.8); ax[1].set_xlabel('费用变化 (%)')
    ax[1].set_title('(b) 龙卷风图（按影响排序）')
    fig.tight_layout(); sv(fig, '图06_问题1_灵敏度.png')
    sdf['费用变化%'] = ch
    sdf.to_csv(os.path.join(OUT, '灵敏度_问题1.csv'), index=False, encoding='utf-8-sig')

    # ================= 问题2 =================
    n2 = np.load(os.path.join(RES, '问题2_结果.npz'))
    prec = pd.read_csv(os.path.join(RES, '问题2_预测器精度.csv'))
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.9))
    x = np.arange(len(prec))
    ax[0].bar(x - 0.2, prec['负载MAE(kW)'], width=0.4, label='负载 MAE', color='tab:blue')
    ax[0].bar(x + 0.2, prec['负载RMSE(kW)'], width=0.4, label='负载 RMSE', color='tab:cyan')
    ax[0].set_xticks(x); ax[0].set_xticklabels(prec['预测器'], rotation=38, ha='right', fontsize=8)
    ax[0].set_ylabel('kW'); ax[0].legend(); ax[0].set_title('(a) 负载预测器精度（滚动评价）')
    ax[1].bar(x - 0.2, prec['光伏MAE(kW)'], width=0.4, label='光伏 MAE', color='tab:orange')
    ax[1].bar(x + 0.2, prec['光伏RMSE(kW)'], width=0.4, label='光伏 RMSE', color='tab:red')
    ax[1].set_xticks(x); ax[1].set_xticklabels(prec['预测器'], rotation=38, ha='right', fontsize=8)
    ax[1].set_ylabel('kW'); ax[1].legend(); ax[1].set_title('(b) 光伏预测器精度（滚动评价）')
    fig.tight_layout(); sv(fig, '图07_问题2_预测器精度.png')

    cal = pd.read_csv(os.path.join(RES, '问题2_裕度标定.csv'))
    sel = cal[(cal.alpha > 0) | (cal.beta >= 0)]
    piv = sel.pivot_table(index='alpha', columns='beta', values='total_cost_jan', aggfunc='min')
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.9))
    im = ax[0].imshow(piv.values / 1e4, aspect='auto', origin='lower', cmap=CMAP)
    ax[0].set_xticks(range(len(piv.columns))); ax[0].set_xticklabels(['%.2f' % b for b in piv.columns])
    ax[0].set_yticks(range(len(piv.index))); ax[0].set_yticklabels(['%.2f' % a for a in piv.index])
    ax[0].set_xlabel('光伏下调系数 $\\beta$'); ax[0].set_ylabel('负载上浮系数 $\\alpha$')
    ax[0].set_title('(a) 1 月标定：总费用 (万元)'); fig.colorbar(im, ax=ax[0])
    b_alpha = sel.groupby('alpha')['total_cost_jan'].min()
    ax[1].plot(b_alpha.index, b_alpha.values / 1e4, 'o-', color='tab:blue')
    ax[1].axhline(sel['total_cost_jan'].max() / 1e4, color='tab:red', ls='--', lw=1, label='无裕度')
    ax[1].set_xlabel('负载上浮系数 $\\alpha$'); ax[1].set_ylabel('1 月总费用 (万元)')
    ax[1].legend(); ax[1].set_title('(b) 最优裕度的内部极小点')
    fig.tight_layout(); sv(fig, '图08_问题2_裕度标定.png')

    m2 = pd.read_csv(os.path.join(RES, '问题2_月度费用汇总.csv'))
    m2 = m2[m2['月份'] != '合计']
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.9))
    ax[0].bar(m2['月份'], m2['计划购电费元'] / 1e4, label='计划购电费', color='tab:blue')
    ax[0].bar(m2['月份'], m2['紧急购电费元'] / 1e4, bottom=m2['计划购电费元'] / 1e4,
              label='紧急购电费', color='tab:red')
    ax[0].set_xlabel('月份'); ax[0].set_ylabel('费用 (万元)'); ax[0].legend()
    ax[0].set_title('(a) 月度费用构成（问题2）')
    EM = n2['EM']
    mtx = np.zeros((12, 24))
    for k, d in enumerate(rep):
        mtx[d.month - 1] += EM[k].reshape(24, 6).sum(1)
    im = ax[1].imshow(mtx, aspect='auto', origin='lower', cmap=CMAP)
    ax[1].set_xlabel('时刻 (h)'); ax[1].set_ylabel('月份')
    ax[1].set_xticks(range(0, 24, 3)); ax[1].set_xticklabels(range(0, 24, 3))
    ax[1].set_title('(b) 紧急购电量的时段-月度分布 (kWh)'); fig.colorbar(im, ax=ax[1])
    fig.tight_layout(); sv(fig, '图09_问题2_月度与紧急分布.png')

    fig, ax = plt.subplots(1, 2, figsize=(11, 3.9))
    labs = ['无裕度计划', '预测+裕度', '完美信息']
    vals = [float(n2['cost0'].sum()) / 1e4, float((n2['plan_cost'].sum() + n2['emg_cost'].sum())) / 1e4,
            float(n2['costP'].sum()) / 1e4]
    ax[0].bar(labs, vals, color=['tab:gray', 'tab:blue', 'tab:green'])
    for i, v in enumerate(vals):
        ax[0].text(i, v, '%.0f' % v, ha='center', va='bottom', fontsize=9)
    ax[0].set_ylabel('全年总费用 (万元)'); ax[0].set_title('(a) 裕度价值与信息价值（问题2）')
    ax[1].hist(n2['EM'].sum(1), bins=30, color='tab:red', alpha=0.8)
    ax[1].set_xlabel('当日紧急购电量 (kWh)'); ax[1].set_ylabel('天数')
    ax[1].set_title('(b) 每日紧急购电量分布')
    fig.tight_layout(); sv(fig, '图10_问题2_价值与分布.png')

    # ================= 问题3 =================
    n3 = np.load(os.path.join(RES, '问题3_结果.npz'))
    s3 = pd.read_csv(os.path.join(RES, '问题3_策略对比.csv'))
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.1))
    cols = ['tab:gray', 'tab:blue', 'tab:cyan', 'tab:green', 'tab:olive', 'tab:orange', 'tab:brown', 'tab:purple']
    ax[0].bar(s3['策略'], s3['总费用'] / 1e4, color=cols[:len(s3)])
    for i, v in enumerate(s3['总费用'] / 1e4):
        ax[0].text(i, v, '%.0f' % v, ha='center', va='bottom', fontsize=8)
    ax[0].set_ylabel('全年总费用 (万元)'); ax[0].set_title('(a) 各预报更新策略的费用')
    ax[1].bar(s3['策略'], s3['违约费'] / 1e4, color='tab:orange', label='违约费')
    ax[1].bar(s3['策略'], s3['紧急购电费'] / 1e4, bottom=s3['违约费'] / 1e4, color='tab:red', label='紧急购电费')
    ax[1].set_ylabel('费用 (万元)'); ax[1].legend(); ax[1].set_title('(b) 费用构成对比')
    fig.tight_layout(); sv(fig, '图11_问题3_策略对比.png')

    rev = pd.read_csv(os.path.join(RES, '问题3_预报修订幅度.csv'))
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    x = np.arange(len(rev))
    ax[0].bar(x - 0.2, rev['MAE(kW)'], width=0.4, label='MAE', color='tab:blue')
    ax[0].bar(x + 0.2, rev['RMSE(kW)'], width=0.4, label='RMSE', color='tab:cyan')
    ax[0].set_xticks(x); ax[0].set_xticklabels(rev['修订'], fontsize=9)
    ax[0].set_ylabel('kW'); ax[0].legend(); ax[0].set_title('(a) 预报修订幅度（同一时钟小时）')
    marg = pd.read_csv(os.path.join(RES, '问题3_更新边际价值.csv'))
    info = marg[marg['项目'].str.contains('价值')]
    names = [s.split('(')[0] for s in info['项目']]
    ax[1].barh(range(len(info)), info['费用下降(元)'] / 1e4, color=['tab:orange', 'tab:blue', 'tab:green'])
    ax[1].set_yticks(range(len(info))); ax[1].set_yticklabels(names, fontsize=9)
    ax[1].set_xlabel('价值 (万元)'); ax[1].set_title('(b) 信息价值分解（单阶段口径）')
    fig.tight_layout(); sv(fig, '图12_问题3_修订与信息价值.png')

    EM3, G_HAT, G3 = n3['EM3'], n3['G_HAT'], n3['G3']
    fig, ax = plt.subplots(2, 1, figsize=(10.5, 6), sharex=True)
    ks = [C.day_index(dates, d) for d in kd]
    kk = rep.index(kd[3])
    ax[0].plot(h, G_HAT[kk] / C.DT, label='0:00 计划购电', color='tab:blue')
    ax[0].plot(h, G3[kk] / C.DT, label='最终调整购电', color='tab:green')
    ax[0].plot(h, EM3[kk] / C.DT, label='紧急购电', color='tab:red', lw=1.0)
    ax[0].plot(h, load[ks[3]], 'k--', lw=0.8, label='实际负载')
    ax[0].set_ylabel('功率 (kW)'); ax[0].legend(fontsize=8)
    ax[0].set_title('2025-12-21：计划/调整/紧急购电与实际负载')
    ax[1].plot(np.arange(0, C.T + 1) / 6.0, n3['E3'][kk], color='tab:blue')
    ax[1].axhline(C.E_MAX, color='gray', ls='--', lw=1); ax[1].axhline(C.E_MIN, color='gray', ls=':', lw=1)
    ax[1].set_ylabel('储电量 (kWh)'); ax[1].set_xlabel('时刻 (h)'); ax[1].set_xlim(0, 24)
    fig.tight_layout(); sv(fig, '图13_问题3_最难日.png')

    # ================= 问题4 =================
    n4 = np.load(os.path.join(RES, '问题4_结果.npz'))
    pdf4 = pd.read_csv(os.path.join(RES, '问题4_电价预测精度.csv'))
    idx4 = n4['rep_idx']
    pa = price4[idx4]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.9))
    x = np.arange(len(pdf4))
    ax[0].bar(x, pdf4['MAE(元/kWh)'] * 1000, color='tab:purple')
    ax[0].set_xticks(x); ax[0].set_xticklabels(pdf4['预测器'], rotation=38, ha='right', fontsize=8)
    ax[0].set_ylabel('MAE (×10$^{-3}$ 元/kWh)'); ax[0].set_title('(a) 电价预测器精度')
    d0 = C.day_index(dp, kd[1])
    ax[1].plot(h, price4[d0], color='tab:red', label='实际电价')
    ax[1].plot(h, C.pred(price4[:d0], dp[:d0], '7日均', kd[1]), color='tab:blue', ls='--', label='7 日均预测')
    ax[1].plot(h, C.pred(price4[:d0], dp[:d0], '昨日持续', kd[1]), color='tab:green', ls=':', label='昨日持续')
    ax[1].set_xlabel('时刻 (h)'); ax[1].set_ylabel('电价 (元/kWh)'); ax[1].legend(fontsize=8)
    ax[1].set_title('(b) 2025-06-21 电价预测与实际'); ax[1].set_xlim(0, 24)
    fig.tight_layout(); sv(fig, '图14_问题4_电价预测.png')

    m4 = pd.read_csv(os.path.join(RES, '问题4_月度费用对比.csv'))
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.9))
    ax[0].plot(m4['月份'], m4['电价均值'], 'o-', color='tab:green')
    ax[0].set_xlabel('月份'); ax[0].set_ylabel('月均电价 (元/kWh)')
    ax[0].set_title('(a) 实时电价月度水平')
    ax0b = ax[0].twinx()
    ax0b.bar(m4['月份'], m4['4-2紧急量kWh'] / 1e3, alpha=0.3, color='tab:red')
    ax0b.set_ylabel('紧急购电量 (MWh)', color='tab:red')
    ax[1].bar(m4['月份'] - 0.2, m4['4-2总费用'] / 1e4, width=0.4, label='问题4-2（重算问题2）', color='tab:blue')
    ax[1].bar(m4['月份'] + 0.2, m4['4-3总费用'] / 1e4, width=0.4, label='问题4-3（重算问题3）', color='tab:orange')
    ax[1].set_xlabel('月份'); ax[1].set_ylabel('总费用 (万元)'); ax[1].legend(fontsize=8)
    ax[1].set_title('(b) 波动电价下月度费用')
    fig.tight_layout(); sv(fig, '图15_问题4_月度对比.png')

    fig, ax = plt.subplots(1, 3, figsize=(12.5, 3.6))
    ax[0].scatter(load[ridx].ravel(), pa.ravel(), s=1, alpha=0.15, color='tab:blue')
    r = np.corrcoef(load[ridx].ravel(), pa.ravel())[0, 1]
    ax[0].set_xlabel('负载 (kW)'); ax[0].set_ylabel('电价 (元/kWh)')
    ax[0].set_title('(a) 电价与负载：$r=%.3f$' % r)
    ax[1].scatter(pv[ridx].ravel(), pa.ravel(), s=1, alpha=0.15, color='tab:orange')
    r2 = np.corrcoef(pv[ridx].ravel(), pa.ravel())[0, 1]
    ax[1].set_xlabel('光伏 (kW)'); ax[1].set_title('(b) 电价与光伏：$r=%.3f$' % r2)
    ax[2].boxplot([pa[np.array([d.month for d in rep]) == m].ravel() for m in range(2, 13)],
                  tick_labels=range(2, 13), showfliers=False)
    ax[2].set_xlabel('月份'); ax[2].set_ylabel('电价 (元/kWh)'); ax[2].set_title('(c) 电价月度箱线图')
    fig.tight_layout(); sv(fig, '图16_问题4_电价相关性.png')

    s43 = pd.read_csv(os.path.join(RES, '问题4_4-3策略对比.csv'))
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.9))
    tot2 = float(n4['plan42'].sum() + n4['emg42'].sum())
    s3p3 = float(s3.loc[s3.策略 == 'P3', '总费用'].values[0])
    lab = ['问题2\n(固定电价)', '问题4-2\n(波动电价)', '问题3\n(固定电价)', '问题4-3\n(波动电价)']
    val = [16647984.89 / 1e4, tot2 / 1e4, s3p3 / 1e4, float(s43.loc[s43.策略 == 'P3', '总费用'].values[0]) / 1e4]
    ax[0].bar(lab, val, color=['tab:blue', 'tab:red', 'tab:cyan', 'tab:orange'])
    for i, v in enumerate(val):
        ax[0].text(i, v, '%.0f' % v, ha='center', va='bottom', fontsize=9)
    ax[0].set_ylabel('全年总费用 (万元)'); ax[0].set_title('(a) 固定电价 vs 波动电价')
    ax[1].bar(s43['策略'], s43['总费用'] / 1e4,
              color=['tab:gray', 'tab:blue', 'tab:cyan', 'tab:green', 'tab:olive', 'tab:purple'][:len(s43)])
    ax[1].set_ylabel('全年总费用 (万元)'); ax[1].set_title('(b) 波动电价下的更新策略')
    fig.tight_layout(); sv(fig, '图17_问题4_策略对比.png')

    print('全部图表已输出到 %s' % OUT)


if __name__ == '__main__':
    main()
