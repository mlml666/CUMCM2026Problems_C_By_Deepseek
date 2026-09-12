# -*- coding: utf-8 -*-
"""问题4 求解：波动电价下重算问题2（result4-2）与问题3（result4-3）

要点：
  - 电价 0:00 未知 → 用历史电价滚动预测（预测器由滚动评价选定）；结算一律用附件4 实际电价
  - result4-2：0:00 计划 + 5 倍实际电价紧急购电（裕度在 1 月按实际价结算标定）
  - result4-3：0:00 计划 + 6/12/18 时调整（违约费 0.5*p_act*|Δ|），紧急 5*p_act；
               负载/光伏预报源与问题3 相同；裕度按 P3 策略在 1 月标定
运行：python 求解/问题4/问题4_求解.py
"""
import os
import sys
import time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as C

plt = C.setup_matplotlib()
W = 7
DEV = 0.5
STAGES = [6, 12, 18]
ALPHAS = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25]
BETAS = [0.00, 0.06, 0.12, 0.18]


def forecast_slots(fc, d, u):
    h = fc.get((d, '%d:00' % u))
    return None if h is None else C.fc_hourly_to_slots(h, u)


def eval_price_predictors(dp, price):
    rows = []
    rep = C.report_dates()
    idx = [C.day_index(dp, d) for d in rep]
    for name in C.PREDICTORS:
        e = np.array([price[i] - C.pred(price[:i], dp[:i], name, d) for d, i in zip(rep, idx)])
        rows.append({'预测器': name, 'MAE(元/kWh)': float(np.abs(e).mean()),
                     'RMSE(元/kWh)': float(np.sqrt((e ** 2).mean())), 'bias(元/kWh)': float(e.mean())})
    return pd.DataFrame(rows)


def run_day43(fc, d, i, load, pv, pa, Lhat, alpha, pf, hourly=False):
    """4-3 单日：计划用预测电价 pf，结算用实际电价 pa"""
    Lplan = (1 + alpha) * Lhat
    P0f = forecast_slots(fc, d, 0)
    plan0 = C.solve_plan(Lplan, P0f, pf, E_init=C.E0, E_term=C.E0)
    g_hat = plan0['g'].copy()
    a_run, b_run = plan0['a'].copy(), plan0['b'].copy()
    sols = {}
    for u in STAGES:
        t1 = 6 * u + 1
        if t1 > C.T:
            continue
        Pf = forecast_slots(fc, d, u)
        if Pf is None:
            continue
        E_init = C.E0 + a_run[:t1 - 1].sum() - b_run[:t1 - 1].sum()
        r = C.solve_plan(Lplan[t1 - 1:], Pf[t1 - 1:], pf[t1 - 1:], E_init=E_init,
                         E_term=C.E0, ghat=g_hat[t1 - 1:], dev_pen=DEV)
        sols[u] = r
        a_run[t1 - 1:], b_run[t1 - 1:] = r['a'], r['b']

    def compose(us):
        g, a, b = g_hat.copy(), plan0['a'].copy(), plan0['b'].copy()
        for u in us:
            if u in sols:
                t1 = 6 * u
                g[t1:], a[t1:], b[t1:] = sols[u]['g'], sols[u]['a'], sols[u]['b']
        return g, a, b

    L_act, P_act = load[i], pv[i]

    def ev(g, a, b):
        e = np.maximum(0.0, L_act * C.DT - g - C.ETA_D * b - P_act * C.DT)
        plan = float(np.dot(pa, g))
        dev = DEV * float(np.dot(pa, np.abs(g - g_hat)))
        emg = 5.0 * float(np.dot(pa, e))
        return dict(plan=plan, dev=dev, emg=emg, total=plan + dev + emg, e=e, g=g, a=a, b=b)

    out = {'g_hat': g_hat}
    for name, us in [('P0', []), ('P1', [6]), ('P2', [6, 12]), ('P3', [6, 12, 18])]:
        g, a, b = compose(us)
        out[name] = ev(g, a, b)
    rp = C.solve_plan(L_act, P_act, pf, E_init=C.E0, E_term=C.E0)
    out['P5'] = ev(rp['g'], rp['a'], rp['b'])
    rq = C.solve_plan(Lplan, P_act, pf, E_init=C.E0, E_term=C.E0)
    out["P5'"] = ev(rq['g'], rq['a'], rq['b'])
    return out


def soc_of(a, b):
    E = np.empty(C.T + 1); E[0] = C.E0
    E[1:] = C.E0 + np.cumsum(a - b)
    return E


def key_tables(rep_dates, G_HAT, G_FIN, EM, price_act, chg, dis, E, tag):
    key_dates = [pd.Timestamp('2025-03-20').date(), pd.Timestamp('2025-06-21').date(),
                 pd.Timestamp('2025-09-23').date(), pd.Timestamp('2025-12-21').date()]
    slots = {'10:00-10:10': 61, '12:00-12:10': 73, '14:00-14:10': 85,
             '16:00-16:10': 97, '18:00-18:10': 109, '20:00-20:10': 121}
    rows1, rows2, rows3 = [], [], []
    for d in key_dates:
        k = rep_dates.index(d)
        for lab, v in slots.items():
            rows1.append({'日期': str(d), '时段': lab, '计划购电量kWh': round(float(G_HAT[k, v - 1]), 2),
                          '调整购电量kWh': round(float(G_FIN[k, v - 1]), 2)})
        rows1.append({'日期': str(d), '时段': '全天计划购电量', '计划购电量kWh': round(float(G_HAT[k].sum()), 2),
                      '调整购电量kWh': round(float(G_FIN[k].sum()), 2)})
        rows1.append({'日期': str(d), '时段': '全天购电费(实际电价结算,元)',
                      '计划购电量kWh': round(float(np.dot(price_act[k], G_HAT[k])), 2),
                      '调整购电量kWh': round(float(np.dot(price_act[k], G_FIN[k])), 2)})
        for j, blk in enumerate(C.BLOCKS):
            rows2.append({'日期': str(d), '时间段': blk, '充电量kWh': round(float(chg[k, j]), 2),
                          '放电量kWh': round(float(dis[k, j]), 2)})
        rows2.append({'日期': str(d), '时间段': '0:00储电量', '充电量kWh': round(C.E0, 2), '放电量kWh': np.nan})
        rows2.append({'日期': str(d), '时间段': '24:00储电量', '充电量kWh': round(float(E[k, -1]), 2),
                      '放电量kWh': np.nan})
        ms = C.merge_intervals(EM[k])
        if not ms:
            rows3.append({'日期': str(d), '紧急购电时间段': '无', '紧急购电量kWh': 0.0})
        for sp in ms:
            rows3.append({'日期': str(d), '紧急购电时间段': '%s-%s' % (sp[0], sp[1]),
                          '紧急购电量kWh': round(sp[2], 2)})
    pd.DataFrame(rows1).to_csv(os.path.join(C.RES, '表1_问题%s_四天.csv' % tag), index=False, encoding='utf-8-sig')
    pd.DataFrame(rows2).to_csv(os.path.join(C.RES, '表2_问题%s_四天.csv' % tag), index=False, encoding='utf-8-sig')
    pd.DataFrame(rows3).to_csv(os.path.join(C.RES, '表3_问题%s_紧急购电_四天.csv' % tag), index=False,
                               encoding='utf-8-sig')


def main():
    t0 = time.time()
    dates, load, pv = C.load_att2()
    dp, price_act = C.load_att4()
    fc = C.load_att3()
    rep_dates = C.report_dates()
    rep_idx = [C.day_index(dates, d) for d in rep_dates]
    assert [C.day_index(dp, d) for d in rep_dates] == rep_idx
    pa_rep = price_act[rep_idx]          # 报告期逐日实际电价（按报告日索引）
    nd = len(rep_dates)
    L_PRED = C.best_load_predictor()
    P_PRED = C.best_pv_predictor()

    pdf = eval_price_predictors(dp, price_act)
    pdf.to_csv(os.path.join(C.RES, '问题4_电价预测精度.csv'), index=False, encoding='utf-8-sig')
    print('=' * 72)
    print('问题4 电价预测器精度（2025-02-01 ~ 12-31 滚动评价）')
    print('=' * 72)
    print(pdf.to_string(index=False, float_format=lambda x: '%.4f' % x))
    PR_PRICE = str(pdf.loc[pdf['MAE(元/kWh)'].idxmin(), '预测器'])
    print('选定电价预测器: %s（负载 %s / 光伏 %s 沿用问题2）' % (PR_PRICE, L_PRED, P_PRED))

    # ---------- 4-2 裕度标定（1 月，按实际电价结算） ----------
    jan_idx = [i for i in range(len(dates)) if dates[i].month == 1 and i >= W]
    cache = {i: (C.pred(load[:i], dates[:i], L_PRED, dates[i]),
                 C.pred(pv[:i], dates[:i], P_PRED, dates[i]),
                 C.pred(price_act[:i], dp[:i], PR_PRICE, dates[i])) for i in jan_idx}
    grid = []
    for a in ALPHAS:
        for b in BETAS:
            tot = 0.0
            for i in jan_idx:
                Lf, Pf, pf = cache[i]
                r = C.solve_plan((1 + a) * Lf, (1 - b) * Pf, pf, E_init=C.E0, E_term=C.E0)
                e = np.maximum(0.0, load[i] * C.DT - r['g'] - C.ETA_D * r['b'] - pv[i] * C.DT)
                tot += float(np.dot(price_act[i], r['g'])) + 5.0 * float(np.dot(price_act[i], e))
            grid.append({'alpha': a, 'beta': b, 'total_cost_jan': tot})
    gdf = pd.DataFrame(grid).sort_values('total_cost_jan').reset_index(drop=True)
    a42, b42 = float(gdf.iloc[0]['alpha']), float(gdf.iloc[0]['beta'])
    gdf.to_csv(os.path.join(C.RES, '问题4_4-2裕度标定.csv'), index=False, encoding='utf-8-sig')
    print('4-2 最优裕度: alpha = %.2f, beta = %.2f（1 月按实际电价结算标定）' % (a42, b42))

    # ---------- 4-2 报告期 ----------
    G42 = np.zeros((nd, C.T)); A42 = np.zeros((nd, C.T)); B42 = np.zeros((nd, C.T))
    E42 = np.zeros((nd, C.T + 1)); EM42 = np.zeros((nd, C.T))
    plan42 = np.zeros(nd); emg42 = np.zeros(nd)
    c42_0 = np.zeros(nd)
    for k, (d, i) in enumerate(zip(rep_dates, rep_idx)):
        Lf = C.pred(load[:i], dates[:i], L_PRED, d)
        Pf = C.pred(pv[:i], dates[:i], P_PRED, d)
        pf = C.pred(price_act[:i], dp[:i], PR_PRICE, d)
        r = C.solve_plan((1 + a42) * Lf, (1 - b42) * Pf, pf, E_init=C.E0, E_term=C.E0)
        e = np.maximum(0.0, load[i] * C.DT - r['g'] - C.ETA_D * r['b'] - pv[i] * C.DT)
        G42[k], A42[k], B42[k], EM42[k] = r['g'], r['a'], r['b'], e
        E42[k, 0] = C.E0; E42[k, 1:] = r['E']
        plan42[k] = float(np.dot(price_act[i], r['g'])); emg42[k] = 5.0 * float(np.dot(price_act[i], e))
        r0 = C.solve_plan(Lf, Pf, pf, E_init=C.E0, E_term=C.E0)
        e0 = np.maximum(0.0, load[i] * C.DT - r0['g'] - C.ETA_D * r0['b'] - pv[i] * C.DT)
        c42_0[k] = float(np.dot(price_act[i], r0['g'])) + 5.0 * float(np.dot(price_act[i], e0))
        if (k + 1) % 80 == 0:
            print('  4-2 已完成 %d/%d 天 (%.1f s)' % (k + 1, nd, time.time() - t0))

    tot42 = plan42.sum() + emg42.sum()
    print('-' * 72)
    print('问题4-2（波动电价重算问题2，%d 天）' % nd)
    print('计划购电费(实际价) = %.2f | 紧急购电费 = %.2f | 总费用 = %.2f 元'
          % (plan42.sum(), emg42.sum(), tot42))
    print('紧急购电量 = %.2f kWh（占负载 %.3f%%），紧急天数 = %d'
          % (EM42.sum(), 100 * EM42.sum() / (load[rep_idx].sum() * C.DT), int((EM42.sum(1) > 1e-3).sum())))
    print('对照 无裕度: 总费用 = %.2f 元 → 裕度节省 %.2f 元（%.2f%%）'
          % (c42_0.sum(), c42_0.sum() - tot42, 100 * (c42_0.sum() - tot42) / c42_0.sum()))

    wb = C._wb('result4-2.xlsx')
    C.write_wide_sheet(wb['计划购电量'], rep_dates, G42, G42.sum(1), plan42)
    chg = np.array([C.blocks_of(A42[k] / C.ETA_C) for k in range(nd)])
    dis = np.array([C.blocks_of(C.ETA_D * B42[k]) for k in range(nd)])
    C.write_charge_discharge(wb['充放电量'], rep_dates, chg, dis, E42)
    rows = []
    for k, d in enumerate(rep_dates):
        for sp in C.merge_intervals(EM42[k]):
            rows.append((d, '%s-%s' % (sp[0], sp[1]), sp[2]))
    C.write_emergency(wb['紧急购电量'], rows)
    out = os.path.join(C.ROOT, 'result4-2.xlsx')
    wb.save(out)
    print('已写出: %s（紧急记录 %d 条）' % (out, len(rows)))
    key_tables(rep_dates, G42, G42, EM42, pa_rep, chg, dis, E42, '4-2')

    # ---------- 4-3 裕度标定（1 月，P3 策略） ----------
    tune43 = []
    for a in ALPHAS:
        tot = 0.0
        for i in jan_idx:
            d = dates[i]
            Lf = C.pred(load[:i], dates[:i], L_PRED, d)
            pf = C.pred(price_act[:i], dp[:i], PR_PRICE, d)
            out43 = run_day43(fc, d, i, load, pv, price_act[i], Lf, a, pf)
            tot += out43['P3']['total']
        tune43.append({'alpha': a, 'total_cost_jan': tot})
    t43 = pd.DataFrame(tune43).sort_values('total_cost_jan').reset_index(drop=True)
    a43 = float(t43.iloc[0]['alpha'])
    t43.to_csv(os.path.join(C.RES, '问题4_4-3裕度标定.csv'), index=False, encoding='utf-8-sig')
    print('4-3 最优裕度: alpha = %.2f（1 月按 P3 策略标定）' % a43)

    # ---------- 4-3 报告期 ----------
    G_HAT = np.zeros((nd, C.T)); G43 = np.zeros((nd, C.T))
    A43 = np.zeros((nd, C.T)); B43 = np.zeros((nd, C.T)); E43 = np.zeros((nd, C.T + 1))
    EM43 = np.zeros((nd, C.T))
    pol_names = ['P0', 'P1', 'P2', 'P3', "P5'", 'P5']
    pol = {p: np.zeros(nd) for p in pol_names}
    for k, (d, i) in enumerate(zip(rep_dates, rep_idx)):
        Lf = C.pred(load[:i], dates[:i], L_PRED, d)
        pf = C.pred(price_act[:i], dp[:i], PR_PRICE, d)
        out43 = run_day43(fc, d, i, load, pv, price_act[i], Lf, a43, pf)
        for p in pol_names:
            pol[p][k] = out43[p]['total']
        G_HAT[k] = out43['g_hat']
        G43[k], A43[k], B43[k], EM43[k] = out43['P3']['g'], out43['P3']['a'], out43['P3']['b'], out43['P3']['e']
        E43[k] = soc_of(out43['P3']['a'], out43['P3']['b'])
        if (k + 1) % 80 == 0:
            print('  4-3 已完成 %d/%d 天 (%.1f s)' % (k + 1, nd, time.time() - t0))

    desc = {'P0': '仅 0:00 计划', 'P1': '0:00 + 6:00 调整', 'P2': '0:00 + 6:00 + 12:00',
            'P3': '0:00 + 6/12/18（题目方案）', "P5'": '仅完美光伏信息（上界）',
            'P5': '完美信息（负载+光伏，上界）'}
    sdf = pd.DataFrame([{'策略': p, '说明': desc[p], '总费用': float(pol[p].sum())} for p in pol_names])
    base = float(pol['P0'].sum())
    sdf['相对P0节省'] = base - sdf['总费用']
    sdf['节省比例%'] = 100 * (base - sdf['总费用']) / base
    print('-' * 72)
    print('问题4-3 策略对比（波动电价，计划用预测价、结算用实际价，裕度 α=%.2f）' % a43)
    print(sdf.to_string(index=False, float_format=lambda x: '%.2f' % x))
    sdf.to_csv(os.path.join(C.RES, '问题4_4-3策略对比.csv'), index=False, encoding='utf-8-sig')
    marg = {'6:00 更新边际价值(P0-P1)': float(pol['P0'].sum() - pol['P1'].sum()),
            '12:00 更新边际价值(P1-P2)': float(pol['P1'].sum() - pol['P2'].sum()),
            '18:00 更新边际价值(P2-P3)': float(pol['P2'].sum() - pol['P3'].sum()),
            '完美光伏信息上界(P3-P5\')': float(pol['P3'].sum() - pol["P5'"].sum()),
            '完美信息上界(P3-P5)': float(pol['P3'].sum() - pol['P5'].sum())}
    print('\n边际价值（正 = 有价值，元）：')
    for kk, vv in marg.items():
        print('  %s: %.2f' % (kk, vv))
    pd.DataFrame([{'项目': kk, '费用下降(元)': vv} for kk, vv in marg.items()]).to_csv(
        os.path.join(C.RES, '问题4_4-3更新边际价值.csv'), index=False, encoding='utf-8-sig')

    wb = C._wb('result4-3.xlsx')
    C.write_wide_sheet(wb['计划购电量'], rep_dates, G_HAT, G_HAT.sum(1),
                       np.array([float(np.dot(pa_rep[k], G_HAT[k])) for k in range(nd)]))
    C.write_wide_sheet(wb['调整购电量'], rep_dates, G43, G43.sum(1),
                       np.array([float(np.dot(pa_rep[k], G43[k])) for k in range(nd)]))
    chg = np.array([C.blocks_of(A43[k] / C.ETA_C) for k in range(nd)])
    dis = np.array([C.blocks_of(C.ETA_D * B43[k]) for k in range(nd)])
    C.write_charge_discharge(wb['充放电量'], rep_dates, chg, dis, E43)
    rows = []
    for k, d in enumerate(rep_dates):
        for sp in C.merge_intervals(EM43[k]):
            rows.append((d, '%s-%s' % (sp[0], sp[1]), sp[2]))
    C.write_emergency(wb['紧急购电量'], rows)
    out = os.path.join(C.ROOT, 'result4-3.xlsx')
    wb.save(out)
    print('已写出: %s（紧急记录 %d 条）' % (out, len(rows)))
    key_tables(rep_dates, G_HAT, G43, EM43, pa_rep, chg, dis, E43, '4-3')

    mrows = []
    for m in sorted(set(x.month for x in rep_dates)):
        mk = [k for k, x in enumerate(rep_dates) if x.month == m]
        mrows.append({'月份': m, '电价均值': float(np.mean([price_act[rep_idx[k]].mean() for k in mk])),
                      '4-2总费用': plan42[mk].sum() + emg42[mk].sum(), '4-2紧急量kWh': EM42[mk].sum(),
                      '4-3总费用': pol['P3'][mk].sum(), '4-3紧急量kWh': EM43[mk].sum()})
    mdf = pd.DataFrame(mrows)
    mdf.to_csv(os.path.join(C.RES, '问题4_月度费用对比.csv'), index=False, encoding='utf-8-sig')
    print(mdf.to_string(index=False, float_format=lambda x: '%.0f' % x))

    np.savez(os.path.join(C.RES, '问题4_结果.npz'), G42=G42, A42=A42, B42=B42, E42=E42, EM42=EM42,
             plan42=plan42, emg42=emg42, c42_0=c42_0, G_HAT=G_HAT, G43=G43, A43=A43, B43=B43, E43=E43,
             EM43=EM43, price_act=price_act, rep_idx=np.array(rep_idx), a42=a42, b42=b42, a43=a43,
             **{('pol_%s' % p.replace("'", 'p')): pol[p] for p in pol_names})

    # ---------- 图 ----------
    k0 = rep_dates.index(pd.Timestamp('2025-06-21').date())
    h = C.hours_axis()
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    ax[0].plot(h, price_act[rep_idx[k0]], color='tab:red', lw=1.0, label='实际电价')
    ax[0].plot(h, C.pred(price_act[:rep_idx[k0]], dp[:rep_idx[k0]], PR_PRICE, rep_dates[k0]),
               color='tab:blue', ls='--', lw=1.0, label='预测电价')
    ax[0].set_xlabel('时刻 (h)'); ax[0].set_ylabel('电价 (元/kWh)'); ax[0].legend()
    ax[0].set_title('问题4：2025-06-21 电价预测 vs 实际'); ax[0].set_xlim(0, 24)
    ax[1].plot([price_act[i].mean() for i in rep_idx], lw=0.8, color='tab:purple')
    ax[1].set_xlabel('报告期第几天'); ax[1].set_ylabel('日均电价 (元/kWh)')
    ax[1].set_title('问题4：日均电价波动')
    fig.savefig(os.path.join(C.FIG, '图8_问题4_电价预测与波动.png'))
    plt.close(fig)

    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    p2_total = 16647984.89
    labels = ['问题2\n(固定电价)', '问题4-2\n(波动电价)', '问题3\n(固定电价)', '问题4-3\n(波动电价)']
    vals = [p2_total / 1e4, tot42 / 1e4]
    try:
        s3 = pd.read_csv(os.path.join(C.RES, '问题3_策略对比.csv'))
        vals.append(float(s3.loc[s3.策略 == 'P3', '总费用'].values[0]) / 1e4)
    except Exception:
        vals.append(np.nan)
    vals.append(float(pol['P3'].sum()) / 1e4)
    ax[0].bar(labels, vals, color=['tab:blue', 'tab:red', 'tab:cyan', 'tab:orange'])
    for i, v in enumerate(vals):
        ax[0].text(i, v, '%.1f' % v, ha='center', va='bottom', fontsize=9)
    ax[0].set_ylabel('全年总费用 (万元)'); ax[0].set_title('固定电价 vs 波动电价（总费用）')
    ax[1].bar(sdf['策略'], sdf['总费用'] / 1e4,
              color=['tab:gray', 'tab:blue', 'tab:cyan', 'tab:green', 'tab:olive', 'tab:purple'])
    for i, v in enumerate(sdf['总费用'] / 1e4):
        ax[1].text(i, v, '%.1f' % v, ha='center', va='bottom', fontsize=8)
    ax[1].set_ylabel('全年总费用 (万元)'); ax[1].set_title('问题4-3：各更新策略费用（波动电价）')
    fig.savefig(os.path.join(C.FIG, '图9_问题4_固定vs波动电价对比.png'))
    plt.close(fig)
    print('已输出 2 张图；总用时 %.1f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
