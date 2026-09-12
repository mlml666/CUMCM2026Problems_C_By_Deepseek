# -*- coding: utf-8 -*-
"""问题3 求解：0:00 计划 + 6/12/18 时预报更新与付费调整（2025-02-01 ~ 12-31）

机制：违约费 = 0.5*p*|调整量-计划量|（等价三档阶梯 1.5p/0.5p），紧急购电 5p
预报：附件3（预报k小时 = 时钟 u+k 时，分段常数下采样到 10 分钟）
负载：无预报数据 → 历史滚动预测（与问题2 同一预测器）+ 安全裕度 α（在 1 月按 P3 策略标定，各策略共用）
策略：P0 不调整 / P1 +6:00 / P2 +12:00 / P3 +18:00（题目方案）/ P4 逐小时(插值预报) /
      P5 完美信息(负载+光伏，上界) / P5' 仅完美光伏信息(隔离光伏预报价值)
运行：python 求解/问题3/问题3_求解.py
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
ALPHAS = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]


def forecast_slots(fc, d, u):
    """发布时刻 u 的预报 → 当日 144 时段（预报k小时 = 时钟 u+k 时）"""
    h = fc.get((d, '%d:00' % u))
    return None if h is None else C.fc_hourly_to_slots(h, u)


def soc_of(a, b, E_init=C.E0):
    E = np.empty(C.T + 1); E[0] = E_init
    E[1:] = E_init + np.cumsum(a - b)
    return E


def evaluate(g, a, b, L_act, P_act, price, g_hat):
    e = np.maximum(0.0, L_act * C.DT - g - C.ETA_D * b - P_act * C.DT)
    plan = float(np.dot(price, g))
    dev = DEV * float(np.dot(price, np.abs(g - g_hat)))
    emg = 5.0 * float(np.dot(price, e))
    return dict(plan=plan, dev=dev, emg=emg, total=plan + dev + emg, e=e, g=g, a=a, b=b)


def run_day(fc, d, i, load, pv, price, Lhat, alpha, hourly=False):
    """返回该日各策略的费用与 P3 明细"""
    Lplan = (1 + alpha) * Lhat
    P0f = forecast_slots(fc, d, 0)
    plan0 = C.solve_plan(Lplan, P0f, price, E_init=C.E0, E_term=C.E0)
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
        r = C.solve_plan(Lplan[t1 - 1:], Pf[t1 - 1:], price[t1 - 1:], E_init=E_init,
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
    out = {'g_hat': g_hat, 'plan0': plan0, 'alpha': alpha}
    for name, us in [('P0', []), ('P1', [6]), ('P2', [6, 12]), ('P3', [6, 12, 18])]:
        g, a, b = compose(us)
        out[name] = evaluate(g, a, b, L_act, P_act, price, g_hat)
    # P5 完美信息（负载+光伏）
    rp = C.solve_plan(L_act, P_act, price, E_init=C.E0, E_term=C.E0)
    out['P5'] = evaluate(rp['g'], rp['a'], rp['b'], L_act, P_act, price, g_hat)
    # P5' 仅完美光伏信息（负载仍为预测+裕度，无调整）
    rq = C.solve_plan(Lplan, P_act, price, E_init=C.E0, E_term=C.E0)
    out["P5'"] = evaluate(rq['g'], rq['a'], rq['b'], L_act, P_act, price, g_hat)
    # A_load 仅完美负载信息（光伏仍为 0:00 预报，无调整）→ 隔离负载信息价值
    rs = C.solve_plan(L_act, P0f, price, E_init=C.E0, E_term=C.E0)
    out['A_load'] = evaluate(rs['g'], rs['a'], rs['b'], L_act, P_act, price, g_hat)
    if hourly:
        g4, a4, b4 = g_hat.copy(), plan0['a'].copy(), plan0['b'].copy()
        for u in range(1, 24):
            t1 = 6 * u + 1
            if t1 > C.T:
                break
            Pf = C.clock_path_to_slots(C.forecast_path_clock(fc, d, u))
            E_init = C.E0 + a4[:t1 - 1].sum() - b4[:t1 - 1].sum()
            r = C.solve_plan(Lplan[t1 - 1:], Pf[t1 - 1:], price[t1 - 1:], E_init=E_init,
                             E_term=C.E0, ghat=g_hat[t1 - 1:], dev_pen=DEV)
            g4[t1 - 1:], a4[t1 - 1:], b4[t1 - 1:] = r['g'], r['a'], r['b']
        out['P4'] = evaluate(g4, a4, b4, L_act, P_act, price, g_hat)
    return out


def main():
    t0 = time.time()
    df1 = C.load_att1()
    price = df1['电价'].values.astype(float)
    dates, load, pv = C.load_att2()
    fc = C.load_att3()
    rep_dates = C.report_dates()
    rep_idx = [C.day_index(dates, d) for d in rep_dates]
    nd = len(rep_dates)
    L_PRED = C.best_load_predictor()
    print('负载预测器（与问题2 一致）: %s' % L_PRED)

    # ---------- 预报修订幅度（同一时钟小时对齐） ----------
    rev = []
    for d in rep_dates:
        p0 = C.forecast_path_clock(fc, d, 0); p6 = C.forecast_path_clock(fc, d, 6)
        p12 = C.forecast_path_clock(fc, d, 12); p18 = C.forecast_path_clock(fc, d, 18)
        for cell, a_, b_, lo in [('0:00->6:00', p0, p6, 7), ('6:00->12:00', p6, p12, 13),
                                 ('12:00->18:00', p12, p18, 19)]:
            sl = slice(lo - 1, 24)
            diff = b_[sl] - a_[sl]
            rev.append({'修订': cell, 'MAE(kW)': float(np.abs(diff).mean()),
                        'RMSE(kW)': float(np.sqrt((diff ** 2).mean()))})
    rdf = pd.DataFrame(rev).groupby('修订', as_index=False).mean()
    print('预报修订幅度（同一时钟小时的预报之差）：')
    print(rdf.to_string(index=False, float_format=lambda x: '%.1f' % x))
    rdf.to_csv(os.path.join(C.RES, '问题3_预报修订幅度.csv'), index=False, encoding='utf-8-sig')

    # ---------- 安全裕度 α 标定（1 月，按 P3 策略、各策略共用） ----------
    jan_idx = [i for i in range(len(dates)) if dates[i].month == 1 and i >= W]
    tune = []
    for alpha in ALPHAS:
        tot = 0.0
        for i in jan_idx:
            d = dates[i]
            Lhat = C.pred(load[:i], dates[:i], L_PRED, d)
            out = run_day(fc, d, i, load, pv, price, Lhat, alpha)
            tot += out['P3']['total']
        tune.append({'alpha': alpha, 'total_cost_jan': tot, 'avg_daily': tot / len(jan_idx)})
    tdf = pd.DataFrame(tune).sort_values('total_cost_jan').reset_index(drop=True)
    alpha = float(tdf.iloc[0]['alpha'])
    print('\n安全裕度标定（1 月 8–31 日，P3 策略）：')
    print(tdf.to_string(index=False, float_format=lambda x: '%.1f' % x))
    print('选定 alpha = %.2f' % alpha)
    tdf.to_csv(os.path.join(C.RES, '问题3_裕度标定.csv'), index=False, encoding='utf-8-sig')

    # ---------- 报告期 ----------
    G_HAT = np.zeros((nd, C.T)); G3 = np.zeros((nd, C.T))
    A3 = np.zeros((nd, C.T)); B3 = np.zeros((nd, C.T)); E3 = np.zeros((nd, C.T + 1))
    EM3 = np.zeros((nd, C.T))
    pol_names = ['P0', 'P1', 'P2', 'P3', 'P4', "P5'", 'A_load', 'P5']
    pol = {p: np.zeros(nd) for p in pol_names}
    det = {p: {kk: np.zeros(nd) for kk in ('plan', 'dev', 'emg')} for p in pol_names}
    for k, (d, i) in enumerate(zip(rep_dates, rep_idx)):
        Lhat = C.pred(load[:i], dates[:i], L_PRED, d)
        out = run_day(fc, d, i, load, pv, price, Lhat, alpha, hourly=True)
        for p in pol_names:
            pol[p][k] = out[p]['total']
            for kk in ('plan', 'dev', 'emg'):
                det[p][kk][k] = out[p][kk]
        G_HAT[k] = out['g_hat']
        r3 = out['P3']
        G3[k], A3[k], B3[k], EM3[k] = r3['g'], r3['a'], r3['b'], r3['e']
        E3[k] = soc_of(r3['a'], r3['b'])
        if (k + 1) % 60 == 0:
            print('  已完成 %d/%d 天 (%.1f s)' % (k + 1, nd, time.time() - t0))

    # ---------- 策略对比 ----------
    print('=' * 72)
    print('问题3 策略对比（2025-02-01 ~ 12-31，%d 天，裕度 α=%.2f）' % (nd, alpha))
    print('=' * 72)
    desc = {'P0': '仅 0:00 计划', 'P1': '0:00 + 6:00 调整', 'P2': '0:00 + 6:00 + 12:00',
            'P3': '0:00 + 6/12/18（题目方案）', 'P4': '逐小时更新（插值预报）',
            "P5'": '仅完美光伏信息（无调整，上界）', 'A_load': '仅完美负载信息（无调整，上界）',
            'P5': '完美信息（负载+光伏，上界）'}
    sdf = pd.DataFrame([{'策略': p, '说明': desc[p], '计划购电费': det[p]['plan'].sum(),
                         '违约费': det[p]['dev'].sum(), '紧急购电费': det[p]['emg'].sum(),
                         '计划加紧急': det[p]['plan'].sum() + det[p]['emg'].sum(),
                         '总费用': float(pol[p].sum())} for p in pol_names])
    base = float(pol['P0'].sum())
    sdf['相对P0节省'] = base - sdf['总费用']
    sdf['节省比例%'] = 100 * (base - sdf['总费用']) / base
    print(sdf.to_string(index=False, float_format=lambda x: '%.2f' % x))
    sdf.to_csv(os.path.join(C.RES, '问题3_策略对比.csv'), index=False, encoding='utf-8-sig')

    def nofee(p):
        """单阶段（完美信息）边界：不应计违约费，只计购电费+紧急费"""
        return float(det[p]['plan'].sum() + det[p]['emg'].sum())
    marg = {'6:00 更新边际价值(P0-P1)': float(pol['P0'].sum() - pol['P1'].sum()),
            '12:00 更新边际价值(P1-P2)': float(pol['P1'].sum() - pol['P2'].sum()),
            '18:00 更新边际价值(P2-P3)': float(pol['P2'].sum() - pol['P3'].sum()),
            '逐小时更新增益(P3-P4)': float(pol['P3'].sum() - pol['P4'].sum()),
            '完美光伏信息价值(单阶段, 无违约费)': float(pol['P0'].sum() - nofee("P5'")),
            '完美负载信息价值(单阶段, 无违约费)': float(pol['P0'].sum() - nofee('A_load')),
            '完美信息价值(单阶段, 无违约费)': float(pol['P0'].sum() - nofee('P5'))}
    print('\n边际价值（正 = 有价值，元）：')
    for kk, vv in marg.items():
        print('  %s: %.2f' % (kk, vv))
    pd.DataFrame([{'项目': kk, '费用下降(元)': vv} for kk, vv in marg.items()]).to_csv(
        os.path.join(C.RES, '问题3_更新边际价值.csv'), index=False, encoding='utf-8-sig')
    print('\nP3 全年费用构成：计划 %.2f + 违约 %.2f + 紧急 %.2f = %.2f 元'
          % (det['P3']['plan'].sum(), det['P3']['dev'].sum(), det['P3']['emg'].sum(), pol['P3'].sum()))
    print('P3 紧急购电量 = %.2f kWh，紧急天数 = %d，违约调整量 = %.0f kWh'
          % (EM3.sum(), int((EM3.sum(1) > 1e-3).sum()), float(np.abs(G3 - G_HAT).sum())))

    # ---------- 写 result3.xlsx ----------
    wb = C._wb('result3.xlsx')
    C.write_wide_sheet(wb['计划购电量'], rep_dates, G_HAT, G_HAT.sum(1),
                       np.array([float(np.dot(price, G_HAT[k])) for k in range(nd)]))
    C.write_wide_sheet(wb['调整购电量'], rep_dates, G3, G3.sum(1),
                       np.array([float(np.dot(price, G3[k])) for k in range(nd)]))
    chg = np.array([C.blocks_of(A3[k] / C.ETA_C) for k in range(nd)])
    dis = np.array([C.blocks_of(C.ETA_D * B3[k]) for k in range(nd)])
    C.write_charge_discharge(wb['充放电量'], rep_dates, chg, dis, E3)
    em_rows = []
    for k, d in enumerate(rep_dates):
        for sp in C.merge_intervals(EM3[k]):
            em_rows.append((d, '%s-%s' % (sp[0], sp[1]), sp[2]))
    C.write_emergency(wb['紧急购电量'], em_rows)
    out_path = os.path.join(C.ROOT, 'result3.xlsx')
    wb.save(out_path)
    print('已写出: %s（紧急记录 %d 条）' % (out_path, len(em_rows)))

    # ---------- 四天明细 ----------
    key_dates = [pd.Timestamp('2025-03-20').date(), pd.Timestamp('2025-06-21').date(),
                 pd.Timestamp('2025-09-23').date(), pd.Timestamp('2025-12-21').date()]
    slots = {'10:00-10:10': 61, '12:00-12:10': 73, '14:00-14:10': 85,
             '16:00-16:10': 97, '18:00-18:10': 109, '20:00-20:10': 121}
    rows1, rows2, rows3 = [], [], []
    for d in key_dates:
        k = rep_dates.index(d)
        for lab, v in slots.items():
            rows1.append({'日期': str(d), '时段': lab, '计划购电量kWh': round(float(G_HAT[k, v - 1]), 2),
                          '调整购电量kWh': round(float(G3[k, v - 1]), 2)})
        rows1.append({'日期': str(d), '时段': '全天购电量(计划)', '计划购电量kWh': round(float(G_HAT[k].sum()), 2),
                      '调整购电量kWh': round(float(G3[k].sum()), 2)})
        rows1.append({'日期': str(d), '时段': '全天购电费(元, 计划/调整)',
                      '计划购电量kWh': round(float(np.dot(price, G_HAT[k])), 2),
                      '调整购电量kWh': round(float(np.dot(price, G3[k])), 2)})
        for j, blk in enumerate(C.BLOCKS):
            rows2.append({'日期': str(d), '时间段': blk, '充电量kWh': round(float(chg[k, j]), 2),
                          '放电量kWh': round(float(dis[k, j]), 2)})
        rows2.append({'日期': str(d), '时间段': '0:00储电量', '充电量kWh': round(C.E0, 2), '放电量kWh': np.nan})
        rows2.append({'日期': str(d), '时间段': '24:00储电量', '充电量kWh': round(float(E3[k, -1]), 2),
                      '放电量kWh': np.nan})
        ms = C.merge_intervals(EM3[k])
        if not ms:
            rows3.append({'日期': str(d), '紧急购电时间段': '无', '紧急购电量kWh': 0.0})
        for sp in ms:
            rows3.append({'日期': str(d), '紧急购电时间段': '%s-%s' % (sp[0], sp[1]),
                          '紧急购电量kWh': round(sp[2], 2)})
    pd.DataFrame(rows1).to_csv(os.path.join(C.RES, '表1_问题3_四天.csv'), index=False, encoding='utf-8-sig')
    pd.DataFrame(rows2).to_csv(os.path.join(C.RES, '表2_问题3_四天.csv'), index=False, encoding='utf-8-sig')
    pd.DataFrame(rows3).to_csv(os.path.join(C.RES, '表3_问题3_紧急购电_四天.csv'), index=False, encoding='utf-8-sig')

    np.savez(os.path.join(C.RES, '问题3_结果.npz'), G_HAT=G_HAT, G3=G3, A3=A3, B3=B3, E3=E3, EM3=EM3,
             price=price, rep_idx=np.array(rep_idx), alpha=alpha,
             **{('pol_%s' % p.replace("'", 'p')): pol[p] for p in pol_names})

    # ---------- 图 ----------
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    cols = ['tab:gray', 'tab:blue', 'tab:cyan', 'tab:green', 'tab:olive', 'tab:orange', 'tab:purple']
    ax[0].bar(sdf['策略'], sdf['总费用'] / 1e4, color=cols)
    for i, v in enumerate(sdf['总费用'] / 1e4):
        ax[0].text(i, v, '%.2f' % v, ha='center', va='bottom', fontsize=8)
    ax[0].set_ylabel('全年总费用 (万元)'); ax[0].set_title('问题3：预报更新策略费用对比')
    x = np.arange(3)
    vals = [float(pol['P0'].sum() - pol['P1'].sum()), float(pol['P1'].sum() - pol['P2'].sum()),
            float(pol['P2'].sum() - pol['P3'].sum())]
    ax[1].bar(x, vals, color='tab:red')
    ax[1].set_xticks(x); ax[1].set_xticklabels(['6:00 更新', '12:00 更新', '18:00 更新'])
    ax[1].axhline(0, color='k', lw=0.8)
    for i, v in enumerate(vals):
        ax[1].text(i, v, '%.0f' % v, ha='center', va='bottom' if v >= 0 else 'top', fontsize=9)
    ax[1].set_ylabel('边际价值 (元)'); ax[1].set_title('问题3：各更新时点的边际价值')
    fig.savefig(os.path.join(C.FIG, '图6_问题3_策略对比与边际价值.png'))
    plt.close(fig)

    k = rep_dates.index(key_dates[3])
    h = C.hours_axis()
    fig, ax = plt.subplots(2, 1, figsize=(11, 6.4), sharex=True)
    ax[0].plot(h, G_HAT[k] / C.DT, label='0:00 计划购电功率', color='tab:blue', lw=1.0)
    ax[0].plot(h, G3[k] / C.DT, label='最终调整购电功率', color='tab:green', lw=1.0)
    ax[0].plot(h, EM3[k] / C.DT, label='紧急购电功率', color='tab:red', lw=0.9)
    ax[0].set_ylabel('功率 (kW)'); ax[0].legend()
    ax[0].set_title('问题3：2025-12-21 计划/调整/紧急购电与储电量（裕度 α=%.2f）' % alpha)
    ax[1].plot(np.concatenate([[0], h]), E3[k], color='tab:blue')
    ax[1].axhline(C.E_MAX, color='gray', ls='--', lw=1); ax[1].axhline(C.E_MIN, color='gray', ls=':', lw=1)
    ax[1].set_ylabel('储电量 (kWh)'); ax[1].set_xlabel('时刻 (h)'); ax[1].set_xlim(0, 24)
    fig.savefig(os.path.join(C.FIG, '图7_问题3_最难日计划与调整.png'))
    plt.close(fig)
    print('已输出 2 张图；总用时 %.1f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
