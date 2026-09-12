# -*- coding: utf-8 -*-
"""审稿修复（第二批）：
(1) 写入"预报误差放大"实验表并修正被夸大的表述（H-6）
(2) 写入"对照模型量化对比"表（M-5）
(3) 长表改用 \\footnotesize 抑制 Overfull（L-3）
(4) 改进验算脚本中"充放电守恒"条目的措辞（L-1）
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def edit(path, pairs):
    p = os.path.join(ROOT, path)
    s = open(p, encoding='utf-8').read()
    for a, b in pairs:
        if a in s:
            s = s.replace(a, b, 1)
            print('  [OK] %s :: %s' % (os.path.basename(path), a[:42].replace('\n', ' ')))
        else:
            print('  [--] %s :: 未命中 %s' % (os.path.basename(path), a[:42].replace('\n', ' ')))
    open(p, 'w', encoding='utf-8').write(s)


# ---------- (1) 问题3：误差放大实验 ----------
TAB_FC = r'''
\begin{table}[H]
  \centering
  \caption{预报误差放大情景下的策略对比（334 天，单位：元）}
  \label{tab:sens-fc}
  \small
  \begin{tabular}{ccccccc}
    \toprule[1.5pt]
    预报误差倍数 & P0 & P1 & P2 & P3 & P3 相对 P0 & 12:00 更新边际价值 \\
    \midrule[1pt]
    1.0（原始） & 21252227 & 21421999 & 21369474 & 21369475 & $+0.55\%$ & 52525 \\
    1.5（放大） & 22294529 & 31526865 & 28488706 & 24518005 & $+9.97\%$ & 3038159 \\
    \bottomrule[1.5pt]
  \end{tabular}
  \par\vspace{3pt}{\footnotesize 注：放大方式为 $\tilde P=F^{\text{预报}}+1.5\,(F^{\text{预报}}-F^{\text{实际}})$，即把附件3 预报误差整体放大 1.5 倍后重做全部策略。}
\end{table}
'''
edit('论文/sections/sec05_p3.tex', [
    ('需要说明的是，上述结论依赖于题目给定的预报数据质量：本文在 \\S\\ref{sec:validation} 中通过人为放大预报误差的方式作了敏感性检验，当预报误差显著增大时，更新机制的相对价值会随之上升。',
     '需要说明的是，上述结论依赖于题目给定的预报数据质量。本文将附件3 预报误差人为放大 $1.5$ 倍后重做全部策略（见 \\cref{tab:sens-fc}）：'
     '误差放大使各策略费用普遍上升，其中 12:00 更新的边际价值由 $5.25$ 万元升至 $303.82$ 万元，'
     '说明\textbf{预报质量越差、及时更新越有价值}；但 6:00 更新需支付的违约费同步放大，'
     'P3 相对 P0 的差额由 $+0.55\\%$ 扩大到 $+9.97\\%$。'
     '因此"更新无正收益"的结论在预报质量恶化时依然成立，且在数据质量较好时更为明确。'),
])

# ---------- (2) 问题2：对照模型量化对比 ----------
TAB_MD = r'''
\begin{table}[H]
  \centering
  \caption{问题2 的模型对比（334 天，样本外结算）}
  \label{tab:p2-models}
  \small
  \begin{tabular}{p{4.6cm}rrr}
    \toprule[1.5pt]
    模型 & 全年总费用 (元) & 紧急购电量 (\si{kWh}) & 相对主模型 \\
    \midrule[1pt]
    本文：预测 $+$ 安全裕度（$\alpha=0.15$） & 16647985 & 275908 & --- \\
    对照①：无裕度计划（$\alpha=\beta=0$） & 21611681 & 2225337 & $+29.82\%$ \\
    对照②：两阶段随机规划（SAA，$S=10$） & 16980919 & 94049 & $+2.00\%$ \\
    对照③：鲁棒优化（$\Gamma=1$，箱式不确定集） & 20653801 & 691072 & $+24.06\%$ \\
    对照④：完美信息下界 & 12229643 & 0 & $-26.54\%$ \\
    \bottomrule[1.5pt]
  \end{tabular}
  \par\vspace{3pt}{\footnotesize 注：对照②情景取该日之前 10 天的实际负载与光伏曲线，第一段计划在样本外与实际数据结算；对照③按 $\hat L+\sigma_L$、$\hat P-\sigma_P$ 编制计划，$\sigma$ 由前 10 天同时段标准差估计。}
\end{table}
'''
edit('论文/sections/sec04_p2.tex', [
    ('这说明了裕度法与鲁棒优化之间的关系：\\textbf{裕度框架是"柔性的鲁棒—随机折中"，其参数由数据标定而非先验给定}。',
     '这说明了裕度法与鲁棒优化之间的关系：\\textbf{裕度框架是"柔性的鲁棒—随机折中"，其参数由数据标定而非先验给定}。'
     '为给出量化对照，\\cref{tab:p2-models} 在同一 334 天报告期上比较了五种模型：'
     '本文的预测$+$裕度模型总费用最低（除不可达的完美信息下界外），'
     '两阶段随机规划（10 情景）高出 $2.00\%$，鲁棒模型因过度保守高出 $24.06\%$，'
     '无裕度计划高出 $29.82\%$。'),
])

# 在 §7.2 的违约费率表之后插入误差放大表
p = os.path.join(ROOT, '论文', 'sections', 'sec07_validation.tex')
s = open(p, encoding='utf-8').read()
anchor = '两种口径下\\textbf{结论一致且方向相同}'
if anchor in s:
    s = s.replace(anchor, TAB_FC.strip() + '\n\n' + anchor, 1)
    print('  [OK] sec07 :: 已插入预报误差放大表')
else:
    print('  [--] sec07 :: 未找到插入锚点')
# 长表改小一号，抑制 Overfull
for old, new in [('\\begin{tabular}{cc|cc|cc}', '\\footnotesize\\begin{tabular}{cc|cc|cc}'),
                 ('\\begin{tabular}{ccrrr}', '\\footnotesize\\begin{tabular}{ccrrr}')]:
    s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)

# ---------- (3) 其他长表改小一号 ----------
for f, pats in [('论文/sections/sec04_p2.tex', ['\\begin{tabular}{lrrr}', '\\begin{tabular}{ccrrr}']),
                ('论文/sections/sec06_p4.tex', ['\\begin{tabular}{lrrr}', '\\begin{tabular}{ccrrr}']),
                ('论文/sections/sec03_p1.tex', ['\\begin{tabular}{cc|cc|cc}'])]:
    p = os.path.join(ROOT, f)
    s = open(p, encoding='utf-8').read()
    n = 0
    for pat in pats:
        if pat in s:
            s = s.replace(pat, '\\footnotesize' + pat)
            n += 1
    open(p, 'w', encoding='utf-8').write(s)
    print('  [OK] %s :: %d 个长表改 \\footnotesize' % (os.path.basename(f), n))

# ---------- (4) 验算脚本措辞 ----------
p = os.path.join(ROOT, '求解', '验算', 'phase25_独立验算.py')
s = open(p, encoding='utf-8').read()
old = """    add('问题1 充电量-放电量守恒（母线侧效率换算）',
        chg_tot * ETA, dis_tot / ETA, abs(chg_tot * ETA - dis_tot / ETA) / max(dis_tot / ETA, 1e-9),
        'E(0)=E(24) ⇒ Σa=Σb')"""
new = """    add('问题1 充放电守恒（两条独立路径）',
        chg_tot * ETA, dis_tot / ETA, abs(chg_tot * ETA - dis_tot / ETA) / max(dis_tot / ETA, 1e-9),
        '由充电列反推电池侧吞吐 Σa = Σ(充电量)×η_c，与由放电列反推 Σb = Σ(放电量)/η_d 比较，'
        '二者相等即验证 E(0)=E(24) 下的 Σa=Σb')"""
if old in s:
    open(p, 'w', encoding='utf-8').write(s.replace(old, new, 1))
    print('  [OK] phase25 :: 措辞已改进')
else:
    print('  [--] phase25 :: 未命中')
