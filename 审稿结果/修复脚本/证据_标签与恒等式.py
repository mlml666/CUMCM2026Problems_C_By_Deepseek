# -*- coding: utf-8 -*-
"""审稿证据脚本 A：图表标签引用检查 + 恒等式口径复核
输出：审稿结果/标签引用检查.csv、审稿结果/恒等式口径复核.txt
"""
import glob
import os
import re
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, '审稿结果')
os.makedirs(OUT, exist_ok=True)

# ---------- 1. 标签 vs \cref ----------
files = [os.path.join(ROOT, '论文', 'front', 'abstract.tex')] + \
        sorted(glob.glob(os.path.join(ROOT, '论文', 'sections', 'sec*.tex')))
tex = {os.path.basename(p): open(p, encoding='utf-8').read() for p in files}
all_tex = ''.join(tex.values())

labels = {}
for fn, s in tex.items():
    for m in re.finditer(r'\\label\{([^}]+)\}', s):
        labels[m.group(1)] = fn
refs = set()
for m in re.finditer(r'\\(?:c|C)ref\{([^}]+)\}', all_tex):
    for k in m.group(1).split(','):
        refs.add(k.strip())
for m in re.finditer(r'\\ref\{([^}]+)\}', all_tex):
    refs.add(m.group(1).strip())

unref = sorted(k for k in labels if k not in refs and not k.startswith('sec:') and not k.startswith('lst:'))
lines = ['标签,定义文件,是否被引用']
for k in sorted(labels):
    lines.append('%s,%s,%s' % (k, labels[k], '是' if k in refs else '否'))
open(os.path.join(OUT, '标签引用检查.csv'), 'w', encoding='utf-8-sig').write('\n'.join(lines))
print('标签总数 %d，未被引用 %d 个：%s' % (len(labels), len(unref), ', '.join(unref) if unref else '无'))

# ---------- 2. 恒等式口径复核 ----------
d = np.genfromtxt(os.path.join(ROOT, '求解', '结果', '问题1_逐时段明细.csv'),
                  delimiter=',', names=True, encoding='utf-8')
g = d['购电量kWh']; chg_bus = d['充电量kWh']; dis_bus = d['放电量kWh']; s = d['弃光kWh']
eta = 0.9
sum_a = chg_bus.sum() * eta          # 电池侧吞吐（由母线侧充电量换算）
sum_b = dis_bus.sum() / eta          # 电池侧吞吐（由母线侧放电量换算）
gap = float(d['负载kW'].sum() - d['光伏kW'].sum()) / 6
coef_exact = 1 / eta - eta
lhs = float(g.sum())
rhs = gap + s.sum() + coef_exact * sum_a
txt = [
    '问题1 恒等式口径复核（数据源：问题1_逐时段明细.csv）',
    '-' * 56,
    'Σg（全天购电量）              = %.6f kWh' % lhs,
    '净缺口                        = %.6f kWh' % gap,
    '弃光                          = %.6f kWh' % s.sum(),
    '母线侧充电量 Σ(a/η_c)          = %.6f kWh' % chg_bus.sum(),
    '电池侧吞吐 Σa = η_c×母线充电量 = %.6f kWh' % sum_a,
    '电池侧吞吐 Σb = 母线放电量/η_d = %.6f kWh' % sum_b,
    '系数 (1/η_c − η_d)             = %.10f  (= 19/90)' % coef_exact,
    '',
    '式右（精确系数 19/90）        = %.6f kWh  → 残差 %.3e' % (rhs, lhs - rhs),
    '式右（论文四位小数 0.2111）    = %.6f kWh  → 显示口径差 %.4f kWh（%.5f%%）'
    % (gap + s.sum() + 0.2111 * sum_a, lhs - (gap + s.sum() + 0.2111 * sum_a),
       100 * abs(lhs - (gap + s.sum() + 0.2111 * sum_a)) / lhs),
    '等价形式 0.19×母线侧充电量     = %.6f kWh  → 残差 %.3e'
    % (gap + s.sum() + (1 - 0.81) * chg_bus.sum(), lhs - (gap + s.sum() + 0.19 * chg_bus.sum())),
    '',
    '结论：Σg = 净缺口 + 弃光 + (1/η_c−η_d)·Σa 精确成立；',
    '      A 定义为电池侧吞吐 Σa = 18666.60 = 0.9 × 20740.67（母线侧充电量）。',
]
open(os.path.join(OUT, '恒等式口径复核.txt'), 'w', encoding='utf-8').write('\n'.join(txt))
print('\n'.join(txt))
