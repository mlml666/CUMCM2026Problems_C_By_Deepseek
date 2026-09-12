# -*- coding: utf-8 -*-
"""问题2 求解：预测不确定 + 5 倍紧急购电（2025-02-01 ~ 12-31，334 天）
方法：
  1) 用历史实际数据做同时段 W=7 日滑动平均预测（严禁使用附件3）
  2) 安全裕度参数 (α,β) 在 1 月数据上按"计划费+紧急费"最小标定
  3) 每天 0:00 解 LP（日周期边界 E144=E0）→ 实际结算紧急购电
输出：result2.xlsx（项目根）、求解/结果/*.csv、图片
运行：python 求解/问题2/问题2_求解.py
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
ALPHAS = [0.00, 0.03, 0.06, 0.09, 0.12, 0.15, 0.18, 0.21, 0.24]
BETAS = [0.00, 0.06, 0.12, 0.18]
PREDICTORS = ['昨日持续', '3日均', '7日均', '14日均', '30日均', 'EWMA(0.7,14)', 'EWMA(0.5,7)', '同月均']


def pred(hist, hist_dates, name, target_date):
    """历史预测器：hist=(n,144) 历史实际，hist_dates 对应日期"""
    if name == '昨日持续':
        return hist[-1]
    if name == '3日均':
        return hist[-3:].mean(0)
    if name == '7日均':
        return hist[-7:].mean(0)
    if name == '14日均':
        return hist[-14:].mean(0)
    if name == '30日均':
        return hist[-30:].mean(0)
    if name == 'EWMA(0.7,14)':
        h = hist[-14:]; w = 0.7 ** np.arange(len(h) - 1, -1, -1)
        return (h * (w / w.sum())[:, None]).sum(0)
    if name == 'EWMA(0.5,7)':
        h = hist[-7:]; w = 0.5 ** np.arange(len(h) - 1, -1, -1)
        return (h * (w / w.sum())[:, None]).sum(0)
    if name == '同月均':
        m = [j for j, dd in enumerate(hist_dates) if dd.month == target_date.month]
        if not m:
            return hist[-7:].mean(0)
        return hist[m].mean(0)
    raise KeyError(name)


def eval_predictors(dates, load, pv):
    """滚动起点评价：对 Feb–Dec 每天只用其之前的数据做预测（严禁前视偏差）"""
    rows = []
    rep = C.report_dates()
    idx = [C.day_index(dates, d) for d in rep]
    for name in PREDICTORS:
        el, ep = [], []
        for d, i in zip(rep, idx):
            hL, hP = load[:i], pv[:i]
            hd = dates[:i]
            Lf = pred(hL, hd, name, d); Pf = pred(hP, hd, name, d)
            el.append(load[i] - Lf); ep.append(pv[i] - Pf)
        el = np.array(el); ep = np.array(ep)
        rows.append({'预测器': name,
                     '负载MAE(kW)': float(np.abs(el).mean()), '负载RMSE(kW)': float(np.sqrt((el ** 2).mean())),
                     '光伏MAE(kW)': float(np.abs(ep).mean()), '光伏RMSE(kW)': float(np.sqrt((ep ** 2).mean()))})
    return pd.DataFrame(rows)


def simulate(L_fc, P_fc, price, L_act, P_act, alpha, beta):
    r = C.solve_plan((1 + alpha) * L_fc, (1 - beta) * P_fc, price, E_init=C.E0, E_term=C.E0)
    e = C.emergency_amount(L_act, P_act, r['g'], r['b'])
    return r, e


def main():
    t_start = time.time()
    df1 = C.load_att1()
    price = df1['电价'].values.astype(float)
    dates, load, pv = C.load_att2()
    n_all = len(dates)
    rep_dates = C.report_dates()
    rep_idx = [C.day_index(dates, d) for d in rep_dates]
    assert all(i is not None for i in rep_idx) and len(rep_dates) == 334, (len(rep_dates), sum(i is not None for i in rep_idx))

    # ---------- 0) 预测器精度对比（滚动评价，严禁前视偏差） ----------
    pdf = eval_predictors(dates, load, pv)
    pdf.to_csv(os.path.join(C.RES, '问题2_预测器精度.csv'), index=False, encoding='utf-8-sig')
    print('=' * 72)
    print('问题2 预测器精度对比（2025-02-01 ~ 12-31 滚动评价）')
    print('=' * 72)
    print(pdf.to_string(index=False, float_format=lambda x: '%.1f' % x))
    L_name = pdf.loc[pdf['负载MAE(kW)'].idxmin(), '预测器']
    P_name = pdf.loc[pdf['光伏MAE(kW)'].idxmin(), '预测器']
    print('按 MAE 选定预测器：负载 = %s，光伏 = %s' % (L_name, P_name))

    # ---------- 1) 决策导向的"预测器 + 裕度"联合标定（1 月 8–31 日） ----------
    jan_idx = [i for i in range(n_all) if dates[i].month == 1]
    tune_idx = [i for i in jan_idx if i >= W]   # 1/8 ~ 1/31
    L_cands = list(dict.fromkeys([str(pdf.loc[pdf['负载MAE(kW)'].idxmin(), '预测器']),
                                  str(pdf.loc[pdf['负载RMSE(kW)'].idxmin(), '预测器'])]))
    P_cands = list(dict.fromkeys([str(pdf.loc[pdf['光伏MAE(kW)'].idxmin(), '预测器']),
                                  str(pdf.loc[pdf['光伏RMSE(kW)'].idxmin(), '预测器'])]))
    print('候选预测器：负载 %s | 光伏 %s（MAE/RMSE 最优各一）' % (L_cands, P_cands))
    fc_cache = {}
    for ln in L_cands:
        for pn in P_cands:
            fc_cache[(ln, pn)] = {i: (pred(load[:i], dates[:i], ln, dates[i]),
                                      pred(pv[:i], dates[:i], pn, dates[i])) for i in tune_idx}
    grid = []
    for ln in L_cands:
        for pn in P_cands:
            for alpha in ALPHAS:
                for beta in BETAS:
                    tot = 0.0
                    for i in tune_idx:
                        Lf, Pf = fc_cache[(ln, pn)][i]
                        r, e = simulate(Lf, Pf, price, load[i], pv[i], alpha, beta)
                        tot += C.planned_cost(r['g'], price) + C.emergency_cost(e, price)
                    grid.append({'负载预测器': ln, '光伏预测器': pn, 'alpha': alpha, 'beta': beta,
                                 'total_cost_jan': tot, 'avg_daily': tot / len(tune_idx)})
    gdf = pd.DataFrame(grid).sort_values('total_cost_jan').reset_index(drop=True)
    best = gdf.iloc[0]
    alpha, beta = float(best['alpha']), float(best['beta'])
    L_name, P_name = str(best['负载预测器']), str(best['光伏预测器'])
    print('=' * 72)
    print('问题2 预测器+裕度联合标定（训练集：2025 年 1 月 8–31 日，共 %d 天）' % len(tune_idx))
    print('=' * 72)
    print(gdf.head(8).to_string(index=False, float_format=lambda x: '%.1f' % x))
    print('最优组合: 负载预测器=%s, 光伏预测器=%s, alpha=%.2f (负载上浮), beta=%.2f (光伏下调)'
          % (L_name, P_name, alpha, beta))
    zero = gdf[(gdf.alpha == 0) & (gdf.beta == 0) & (gdf['负载预测器'] == L_name)
               & (gdf['光伏预测器'] == P_name)].iloc[0]
    print('无裕度基线(α=β=0) 1 月总费用 = %.2f 元 → 最优裕度节省 %.2f 元 (%.2f%%)'
          % (zero['total_cost_jan'], zero['total_cost_jan'] - best['total_cost_jan'],
             100 * (zero['total_cost_jan'] - best['total_cost_jan']) / zero['total_cost_jan']))
    gdf.to_csv(os.path.join(C.RES, '问题2_裕度标定.csv'), index=False, encoding='utf-8-sig')

    # ---------- 2) 报告期逐日求解 ----------
    nd = len(rep_dates)
    G = np.zeros((nd, C.T)); A = np.zeros((nd, C.T)); B = np.zeros((nd, C.T))
    S = np.zeros((nd, C.T)); E = np.zeros((nd, C.T + 1)); EM = np.zeros((nd, C.T))
    plan_cost = np.zeros(nd); emg_cost = np.zeros(nd)
    G0 = np.zeros((nd, C.T)); EM0 = np.zeros((nd, C.T)); cost0 = np.zeros(nd)     # 无裕度对照
    GP = np.zeros((nd, C.T)); EMP = np.zeros((nd, C.T)); costP = np.zeros(nd)     # 完美信息下界
    for k, (d, i) in enumerate(zip(rep_dates, rep_idx)):
        Lf = pred(load[:i], dates[:i], L_name, d); Pf = pred(pv[:i], dates[:i], P_name, d)
        r, e = simulate(Lf, Pf, price, load[i], pv[i], alpha, beta)
        G[k], A[k], B[k], S[k] = r['g'], r['a'], r['b'], r['s']
        E[k, 0] = C.E0; E[k, 1:] = r['E']; EM[k] = e
        plan_cost[k] = C.planned_cost(r['g'], price); emg_cost[k] = C.emergency_cost(e, price)
        r0, e0 = simulate(Lf, Pf, price, load[i], pv[i], 0.0, 0.0)
        G0[k] = r0['g']; EM0[k] = e0
        cost0[k] = C.planned_cost(r0['g'], price) + C.emergency_cost(e0, price)
        rp, ep = simulate(load[i], pv[i], price, load[i], pv[i], 0.0, 0.0)
        GP[k] = rp['g']; EMP[k] = ep
        costP[k] = C.planned_cost(rp['g'], price) + C.emergency_cost(ep, price)
        if (k + 1) % 60 == 0:
            print('  已完成 %d/%d 天  (%.1f s)' % (k + 1, nd, time.time() - t_start))

    total = plan_cost.sum() + emg_cost.sum()
    print('-' * 72)
    print('问题2 报告期（2025-02-01 ~ 12-31，%d 天）' % nd)
    print('计划购电费 = %.2f 元 | 紧急购电费 = %.2f 元 | 总费用 = %.2f 元'
          % (plan_cost.sum(), emg_cost.sum(), total))
    print('紧急购电电量 = %.2f kWh（占负载 %.3f%%）；出现紧急购电的天数 = %d'
          % (EM.sum(), 100 * EM.sum() / (load[rep_idx].sum() * C.DT), int((EM.sum(1) > 1e-3).sum())))
    print('对照① 无裕度(α=β=0): 总费用 = %.2f 元 → 裕度节省 %.2f 元 (%.2f%%)'
          % (cost0.sum(), cost0.sum() - total, 100 * (cost0.sum() - total) / cost0.sum()))
    print('对照② 完美信息下界: 总费用 = %.2f 元（不可达，缺口 %d%% 量级）'
          % (costP.sum(), round(100 * (total - costP.sum()) / total)))
    print('储能吞吐量合计 = %.0f kWh' % A.sum())

    # ---------- 3) 写 result2.xlsx ----------
    wb = C._wb('result2.xlsx')
    C.write_wide_sheet(wb['计划购电量'], rep_dates, G, G.sum(1), plan_cost)
    chg = np.array([C.blocks_of(A[k] / C.ETA_C) for k in range(nd)])
    dis = np.array([C.blocks_of(C.ETA_D * B[k]) for k in range(nd)])
    C.write_charge_discharge(wb['充放电量'], rep_dates, chg, dis, E)
    em_rows = []
    for k, d in enumerate(rep_dates):
        for span in C.merge_intervals(EM[k]):
            em_rows.append((d, '%s-%s' % (span[0], span[1]), span[2]))
    C.write_emergency(wb['紧急购电量'], em_rows)
    out = os.path.join(C.ROOT, 'result2.xlsx')
    wb.save(out)
    print('已写出: %s（紧急购电记录 %d 条）' % (out, len(em_rows)))

    # ---------- 4) CSV ----------
    months = sorted(set(d.month for d in rep_dates))
    mrows = []
    for m in months:
        mk = [k for k, d in enumerate(rep_dates) if d.month == m]
        mrows.append({'月份': m, '天数': len(mk),
                      '计划购电量kWh': G[mk].sum(), '计划购电费元': plan_cost[mk].sum(),
                      '紧急购电量kWh': EM[mk].sum(), '紧急购电费元': emg_cost[mk].sum(),
                      '总费用元': plan_cost[mk].sum() + emg_cost[mk].sum(),
                      '紧急天数': int((EM[mk].sum(1) > 1e-3).sum())})
    mdf = pd.DataFrame(mrows)
    mdf.loc[len(mdf)] = ['合计', nd, G.sum(), plan_cost.sum(), EM.sum(), emg_cost.sum(), total,
                         int((EM.sum(1) > 1e-3).sum())]
    mdf.to_csv(os.path.join(C.RES, '问题2_月度费用汇总.csv'), index=False, encoding='utf-8-sig')
    print('\n月度汇总：')
    print(mdf.to_string(index=False))

    # 指定四天明细（表1/表2/表3 格式）
    key_dates = [pd.Timestamp('2025-03-20').date(), pd.Timestamp('2025-06-21').date(),
                 pd.Timestamp('2025-09-23').date(), pd.Timestamp('2025-12-21').date()]
    slots = {'10:00-10:10': 61, '12:00-12:10': 73, '14:00-14:10': 85,
             '16:00-16:10': 97, '18:00-18:10': 109, '20:00-20:10': 121}
    rows = []
    for d in key_dates:
        k = rep_dates.index(d)
        for label, v in slots.items():
            rows.append({'日期': str(d), '时段': label, '购电量kWh': round(float(G[k, v - 1]), 2)})
        rows.append({'日期': str(d), '时段': '全天购电量', '购电量kWh': round(float(G[k].sum()), 2)})
        rows.append({'日期': str(d), '时段': '全天购电费(计划)', '购电量kWh': round(float(plan_cost[k]), 2)})
        rows.append({'日期': str(d), '时段': '全天紧急购电量', '购电量kWh': round(float(EM[k].sum()), 2)})
        rows.append({'日期': str(d), '时段': '全天紧急购电费', '购电量kWh': round(float(emg_cost[k]), 2)})
    t1 = pd.DataFrame(rows)
    t1.to_csv(os.path.join(C.RES, '表1_问题2_四天.csv'), index=False, encoding='utf-8-sig')
    rows = []
    for d in key_dates:
        k = rep_dates.index(d)
        for j, blk in enumerate(C.BLOCKS):
            rows.append({'日期': str(d), '时间段': blk, '充电量kWh': round(float(chg[k, j]), 2),
                         '放电量kWh': round(float(dis[k, j]), 2)})
        rows.append({'日期': str(d), '时间段': '0:00储电量', '充电量kWh': round(C.E0, 2), '放电量kWh': np.nan})
        rows.append({'日期': str(d), '时间段': '24:00储电量', '充电量kWh': round(float(E[k, -1]), 2),
                     '放电量kWh': np.nan})
    pd.DataFrame(rows).to_csv(os.path.join(C.RES, '表2_问题2_四天.csv'), index=False, encoding='utf-8-sig')
    rows = []
    for d in key_dates:
        k = rep_dates.index(d)
        ms = C.merge_intervals(EM[k])
        if not ms:
            rows.append({'日期': str(d), '紧急购电时间段': '无', '紧急购电量kWh': 0.0})
        for sp in ms:
            rows.append({'日期': str(d), '紧急购电时间段': '%s-%s' % (sp[0], sp[1]),
                         '紧急购电量kWh': round(sp[2], 2)})
    pd.DataFrame(rows).to_csv(os.path.join(C.RES, '表3_问题2_紧急购电_四天.csv'), index=False,
                              encoding='utf-8-sig')

    np.savez(os.path.join(C.RES, '问题2_结果.npz'), G=G, A=A, B=B, S=S, E=E, EM=EM,
             plan_cost=plan_cost, emg_cost=emg_cost, G0=G0, EM0=EM0, cost0=cost0,
             GP=GP, EMP=EMP, costP=costP, rep_idx=np.array(rep_idx), price=price,
             alpha=alpha, beta=beta)

    # ---------- 5) 图 ----------
    h = C.hours_axis()
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    ax[0].bar(mdf['月份'][:-1], mdf['计划购电费元'][:-1], label='计划购电费', color='tab:blue')
    ax[0].bar(mdf['月份'][:-1], mdf['紧急购电费元'][:-1], bottom=mdf['计划购电费元'][:-1],
              label='紧急购电费', color='tab:red')
    ax[0].set_xlabel('月份'); ax[0].set_ylabel('费用 (元)'); ax[0].legend()
    ax[0].set_title('问题2：月度费用构成')
    ax[1].plot(range(1, nd + 1), EM.sum(1), color='tab:red', lw=0.8)
    ax[1].set_xlabel('报告期第几天 (2025-02-01 起)'); ax[1].set_ylabel('当日紧急购电量 (kWh)')
    ax[1].set_title('问题2：每日紧急购电量')
    fig.savefig(os.path.join(C.FIG, '图3_问题2_月度费用与紧急购电.png'))
    plt.close(fig)

    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    sub = gdf[(gdf['负载预测器'] == L_name) & (gdf['光伏预测器'] == P_name)]
    piv = sub.pivot(index='alpha', columns='beta', values='avg_daily')
    im = ax[0].imshow(piv.values, aspect='auto', cmap='viridis', origin='lower')
    ax[0].set_xticks(range(len(piv.columns))); ax[0].set_xticklabels(['%.2f' % b for b in piv.columns])
    ax[0].set_yticks(range(len(piv.index))); ax[0].set_yticklabels(['%.2f' % a for a in piv.index])
    ax[0].set_xlabel('光伏下调系数 β'); ax[0].set_ylabel('负载上浮系数 α')
    ax[0].set_title('1 月标定：日均总费用 (元)')
    fig.colorbar(im, ax=ax[0])
    ax[1].bar(['无裕度', '最优裕度', '完美信息'],
              [cost0.sum() / 1e4, total / 1e4, costP.sum() / 1e4],
              color=['tab:gray', 'tab:blue', 'tab:green'])
    for i, v in enumerate([cost0.sum() / 1e4, total / 1e4, costP.sum() / 1e4]):
        ax[1].text(i, v, '%.1f' % v, ha='center', va='bottom')
    ax[1].set_ylabel('全年总费用 (万元)'); ax[1].set_title('问题2：裕度价值与信息价值')
    fig.savefig(os.path.join(C.FIG, '图4_问题2_裕度标定与价值对比.png'))
    plt.close(fig)

    k = rep_dates.index(key_dates[3])
    fig, ax = plt.subplots(2, 1, figsize=(11, 6.4), sharex=True)
    ax[0].plot(h, G[k] / C.DT, label='计划购电功率 (kW)', color='tab:blue')
    ax[0].plot(h, EM[k] / C.DT, label='紧急购电功率 (kW)', color='tab:red')
    ax[0].plot(h, load[rep_idx[k]], label='实际负载 (kW)', color='tab:green', lw=0.8)
    ax[0].set_ylabel('功率 (kW)'); ax[0].legend(); ax[0].set_title('问题2：2025-12-21（最难日）购电与紧急购电')
    ax[1].plot(np.concatenate([[0], h]), E[k], color='tab:blue')
    ax[1].axhline(C.E_MAX, color='gray', ls='--', lw=1); ax[1].axhline(C.E_MIN, color='gray', ls=':', lw=1)
    ax[1].set_ylabel('储电量 (kWh)'); ax[1].set_xlabel('时刻 (h)'); ax[1].set_xlim(0, 24)
    fig.savefig(os.path.join(C.FIG, '图5_问题2_最难日策略.png'))
    plt.close(fig)
    print('已输出 3 张图；总用时 %.1f s' % (time.time() - t_start))
    return total


if __name__ == '__main__':
    main()
