# -*- coding: utf-8 -*-
"""修正：数学模式中的中文标点、插入问题2 对照模型表、收窄误差放大表"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (a) 公式末尾的中文标点包进 \text{}
pat = re.compile(r'([。，])(\s*(?:\\label\{[^}]*\}\s*)?\\end\{equation\})')
tot = 0
for p in sorted(glob.glob(os.path.join(ROOT, '论文', 'sections', 'sec*.tex'))):
    s = open(p, encoding='utf-8').read()
    s2, n = pat.subn(lambda m: '\\text{%s}%s' % (m.group(1), m.group(2)), s)
    if n:
        open(p, 'w', encoding='utf-8').write(s2)
        tot += n
        print('  %-24s 修正 %d 处中文标点' % (os.path.basename(p), n))
print('合计修正 %d 处' % tot)

# (b) 插入问题2 对照模型表（§4.5 末）
TAB_MD = r'''
\begin{table}[H]
  \centering
  \caption{问题2 的模型对比（334 天，样本外结算）}
  \label{tab:p2-models}
  \footnotesize
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
  \par\vspace{3pt}{\footnotesize 注：对照②的情景取该日之前 10 天的实际负载与光伏曲线，第一段计划在样本外与实际数据结算；对照③按 $\hat L+\sigma_L$、$\hat P-\sigma_P$ 编制计划，$\sigma$ 取前 10 天同时段标准差。}
\end{table}
'''
p = os.path.join(ROOT, '论文', 'sections', 'sec04_p2.tex')
s = open(p, encoding='utf-8').read()
anchor = '\\subsection{日周期边界与储能执行规则}'
if anchor in s and 'tab:p2-models' in s.split(anchor)[0]:
    s = s.replace(anchor, TAB_MD.strip() + '\n\n' + anchor, 1)
    open(p, 'w', encoding='utf-8').write(s)
    print('  已插入 tab:p2-models 表格')
else:
    print('  [--] 插入位置判定失败')

# (c) 误差放大表收窄
p = os.path.join(ROOT, '论文', 'sections', 'sec07_validation.tex')
s = open(p, encoding='utf-8').read()
s = s.replace('''  \\caption{预报误差放大情景下的策略对比（334 天，单位：元）}
  \\label{tab:sens-fc}
  \\small''', '''  \\caption{预报误差放大情景下的策略对比（334 天，单位：元）}
  \\label{tab:sens-fc}
  \\footnotesize''')
open(p, 'w', encoding='utf-8').write(s)
print('  误差放大表已改 \\footnotesize')
