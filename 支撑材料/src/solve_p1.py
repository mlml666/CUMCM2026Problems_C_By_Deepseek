# -*- coding: utf-8 -*-
"""问题1 求解：完美信息下的日计划购电 LP
输出：result1.xlsx（项目根）、求解/结果/表1_问题1.csv、表2_问题1.csv、图片
运行：python 求解/问题1/问题1_求解.py
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as C

plt = C.setup_matplotlib()


def main():
    df1 = C.load_att1()
    L = df1['小区负载'].values.astype(float)
    P = df1['光伏发电预测功率'].values.astype(float)
    price = df1['电价'].values.astype(float)

    res = C.solve_plan(L, P, price, E_init=C.E0, E_term=C.E0)
    g, a, b, s, E = res['g'], res['a'], res['b'], res['s'], res['E']

    # ---- 指标 ----
    gap = float((L - P).sum() * C.DT)
    A = float(a.sum())
    total_g = float(g.sum())
    fee = C.planned_cost(g, price)
    baseline = float(np.dot(price, np.maximum(0.0, (L - P)) * C.DT))   # 无储能基线
    identity_rhs = gap + float(s.sum()) + (1.0 / C.ETA_C - C.ETA_D) * A

    print('=' * 72)
    print('问题1 结果（附件1 典型日）')
    print('=' * 72)
    print('LP 状态: %s  目标(全天购电费) = %.2f 元' % (res['status'], fee))
    print('全天购电量 = %.2f kWh | 全天净缺口 = %.2f kWh | 弃光 = %.2f kWh' % (total_g, gap, s.sum()))
    print('储能电池侧吞吐量 A = %.2f kWh（母线侧充电 %.2f / 放电 %.2f）'
          % (A, a.sum() / C.ETA_C, C.ETA_D * b.sum()))
    print('恒等式核对: Σg = %.4f vs 缺口+弃光+0.2111A = %.4f  残差 = %.2e'
          % (total_g, identity_rhs, abs(total_g - identity_rhs)))
    print('无储能基线购电费 = %.2f 元 → 储能节省 %.2f 元（%.1f%%）'
          % (baseline, baseline - fee, 100 * (baseline - fee) / baseline))
    print('储电量: 0:00 = %.1f, 24:00 = %.1f, min = %.1f (t=%d), max = %.1f (t=%d)'
          % (C.E0, E[-1], E.min(), E.argmin() + 1, E.max(), E.argmax() + 1))
    print('功率上限核对: max a = %.2f, max b = %.2f (上限 %.2f)' % (a.max(), b.max(), C.ABAR))

    # ---- 表1 ----
    slots = {'10:00-10:10': 61, '12:00-12:10': 73, '14:00-14:10': 85,
             '16:00-16:10': 97, '18:00-18:10': 109, '20:00-20:10': 121}
    rows1 = [{'时间段': k, '购电量(kWh)': round(float(g[v - 1]), 2)} for k, v in slots.items()]
    rows1.append({'时间段': '全天购电量', '购电量(kWh)': round(total_g, 2)})
    rows1.append({'时间段': '全天购电费', '购电量(kWh)': round(fee, 2)})
    t1 = pd.DataFrame(rows1)
    t1.to_csv(os.path.join(C.RES, '表1_问题1.csv'), index=False, encoding='utf-8-sig')
    print('\n表1 指定时段购电量：')
    print(t1.to_string(index=False))

    # ---- 表2 ----
    rows2 = []
    for i, blk in enumerate(C.BLOCKS):
        t0, t1_ = i * 24, (i + 1) * 24
        rows2.append({'时间段': blk, '充电量(kWh)': round(float(a[t0:t1_].sum() / C.ETA_C), 2),
                      '放电量(kWh)': round(float(C.ETA_D * b[t0:t1_].sum()), 2)})
    rows2.append({'时间段': '0:00储电量', '充电量(kWh)': round(C.E0, 2), '放电量(kWh)': np.nan})
    rows2.append({'时间段': '24:00储电量', '充电量(kWh)': round(float(E[-1]), 2), '放电量(kWh)': np.nan})
    t2 = pd.DataFrame(rows2)
    t2.to_csv(os.path.join(C.RES, '表2_问题1.csv'), index=False, encoding='utf-8-sig')
    print('\n表2 储能充放电量与储电量：')
    print(t2.to_string(index=False))

    # ---- 明细 ----
    det = pd.DataFrame({'时段': np.arange(1, C.T + 1), '起(h)': (np.arange(C.T)) / 6.0,
                        '电价': price, '负载kW': L, '光伏kW': P, '购电量kWh': g,
                        '充电量kWh': a / C.ETA_C, '放电量kWh': C.ETA_D * b,
                        '弃光kWh': s, '储电量kWh': E})
    det.to_csv(os.path.join(C.RES, '问题1_逐时段明细.csv'), index=False, encoding='utf-8-sig')

    # ---- 写 result1.xlsx ----
    out = os.path.join(C.ROOT, 'result1.xlsx')
    C.write_result1(out, g, a, b, E)
    print('\n已写出: %s' % out)

    # ---- 图 ----
    h = C.hours_axis()
    fig, ax = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    ax[0].plot(h, price, color='tab:red', label='电价(元/kWh)')
    ax[0].set_ylabel('电价 (元/kWh)'); ax[0].legend(loc='upper left')
    ax[0].set_title('问题1：附件1 典型日 —— 电价 / 负载 / 光伏 / 最优购电 / 储电量')
    ax[1].plot(h, L, color='tab:blue', label='小区负载 (kW)')
    ax[1].plot(h, P, color='tab:orange', label='光伏预测 (kW)')
    ax[1].fill_between(h, 0, np.minimum(L, P), color='tab:green', alpha=0.15, label='光伏直接消纳')
    ax[1].set_ylabel('功率 (kW)'); ax[1].legend(loc='upper left')
    ax[2].bar(h, g, width=1 / 6.0, color='tab:cyan', label='计划购电量 (kWh/10min)')
    ax[2].bar(h, a / C.ETA_C, width=1 / 6.0, color='tab:purple', alpha=0.7, label='充电量(母线侧)')
    ax[2].bar(h, -C.ETA_D * b, width=1 / 6.0, color='tab:brown', alpha=0.7, label='放电量(母线侧)')
    ax[2].set_ylabel('电量 (kWh)'); ax[2].set_xlabel('时刻 (h)'); ax[2].legend(loc='upper left')
    ax[2].set_xlim(0, 24)
    fig.savefig(os.path.join(C.FIG, '图1_问题1_最优购电与充放电策略.png'))
    plt.close(fig)

    fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    ax[0].plot(h, price, color='tab:red'); ax[0].set_ylabel('电价 (元/kWh)')
    ax[0].set_title('问题1：电价与储电量轨迹（影子价格阈值策略）')
    ax[1].plot(np.concatenate([[0], h]), np.concatenate([[C.E0], E]), color='tab:blue')
    ax[1].axhline(C.E_MAX, color='gray', ls='--', lw=1, label='上限 10800')
    ax[1].axhline(C.E_MIN, color='gray', ls=':', lw=1, label='下限 1200')
    ax[1].set_ylabel('储电量 (kWh)'); ax[1].set_xlabel('时刻 (h)'); ax[1].legend(loc='lower left')
    ax[1].set_xlim(0, 24)
    fig.savefig(os.path.join(C.FIG, '图2_问题1_储电量轨迹.png'))
    plt.close(fig)
    print('已输出 2 张图到 %s' % C.FIG)
    return fee


if __name__ == '__main__':
    main()
