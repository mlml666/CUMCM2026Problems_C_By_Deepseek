# -*- coding: utf-8 -*-
"""审稿修复（第一批）：恒等式口径、表内表外口径、缺失 \\cref、附录行数、放电口径说明"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def edit(path, pairs):
    p = os.path.join(ROOT, path)
    s = open(p, encoding='utf-8').read()
    for a, b in pairs:
        if a in s:
            s = s.replace(a, b, 1)
            print('  [OK] %s :: %s' % (os.path.basename(path), a[:40].replace('\n', ' ')))
        else:
            print('  [--] %s :: 未命中 %s' % (os.path.basename(path), a[:40].replace('\n', ' ')))
    open(p, 'w', encoding='utf-8').write(s)


# 1) sec02：恒等式用精确系数，并显式说明 A 的口径
edit('论文/sections/sec02_assumptions.tex', [
    (r'''  \sum_{t=1}^{T} g_t=\underbrace{\sum_{t=1}^{T}(L_t-P_t)\Delta t}_{\text{净缺口能量}}
  +\sum_{t=1}^{T} s_t+\left(\frac{1}{\eta_c}-\eta_d\right)A
  =\text{净缺口}+\text{弃光}+0.2111A .''',
     r'''  \sum_{t=1}^{T} g_t=\underbrace{\sum_{t=1}^{T}(L_t-P_t)\Delta t}_{\text{净缺口能量}}
  +\sum_{t=1}^{T} s_t+\left(\frac{1}{\eta_c}-\eta_d\right)A
  =\text{净缺口}+\text{弃光}+\frac{19}{90}A ,'''),
    (r'该式表明：每在电池中搬运 $1$ \si{kWh}（电池侧），全天需多购 $0.2111$ \si{kWh}；换算为向负载多供 $1$ \si{kWh} 的代价是 $1/(\eta_c\eta_d)-1=23.46\%$。',
     r'式中 $A=\sum_t a_t$ 为\textbf{电池侧}全天吞吐量，与母线侧充电量相差效率因子：'
     r'$A=\eta_c\sum_t(a_t/\eta_c)$，系数 $\frac{1}{\eta_c}-\eta_d=\frac{19}{90}=0.2111\overline{1}$ 为精确值；'
     r'等价地，损耗项也可写为 $(1-\eta_c\eta_d)\times$ 母线侧充电量 $=0.19\sum_t(a_t/\eta_c)$。'
     r'该式表明：每在电池中搬运 $1$ \si{kWh}（电池侧），全天需多购 $19/90=0.2111$ \si{kWh}；'
     r'换算为向负载多供 $1$ \si{kWh} 的代价是 $1/(\eta_c\eta_d)-1=23.46\%$。'),
])

# 2) sec03：算术展示改精确系数；放电口径补充母线侧换算
edit('论文/sections/sec03_p1.tex', [
    (r'理论购电量为 $55541.97+0.2111\times18666.60=59482.70$ \si{kWh}，与求解结果完全一致（残差 $1.5\times10^{-11}$）。',
     r'理论购电量为 $55541.97+\frac{19}{90}\times18666.60=59482.70$ \si{kWh}，与求解结果一致（残差 $2.2\times10^{-11}$）；'
     r'其中 $A=18666.60$ \si{kWh} 为电池侧吞吐量，等于 $0.9\times$ 母线侧充电量（$0.9\times20740.67=18666.60$ \si{kWh}）。'),
    (r'最大放电量为 $795.17$ \si{kWh}。',
     r'最大放电量为 $795.17$ \si{kWh}（电池侧；对应母线侧 $0.9\times795.17=715.65$ \si{kWh}）。'),
])

# 3) 核心公式汇总：同步精确系数与 A 的说明
edit('论文/sections/sec06b_formulas.tex', [
    (r'+\sum_{t=1}^{T}s_t+0.2111A .',
     r'+\sum_{t=1}^{T}s_t+\frac{19}{90}A,\qquad A=\sum_t a_t\ (\text{电池侧吞吐量}).'),
])

# 4) 摘要：去掉易被误读的四位小数系数
edit('论文/front/abstract.tex', [
    (r'$\sum_tg_t=\text{净缺口}+\text{弃光}+0.2111A$',
     r'$\sum_tg_t=\text{净缺口}+\text{弃光}+(1/\eta_c-\eta_d)A$'),
])

# 5) §7.1：信息上界口径与策略表统一
edit('论文/sections/sec07_validation.tex', [
    (r"实测：P5 $=14324819\le$ P3 $=21369475$；P5$'$ $=19249721\le$ P0 $=21252227$；A\_load $=16048332\le$ P0；P5 的紧急购电费为 $4.7\times10^{-10}$ 元（数值零）。",
     r"实测（单阶段边界口径、不计违约费，与 \cref{tab:p3-pol} 一致）：P5 $=12229643\le$ P3 $=21369475$；"
     r"P5$\prime$ $=19249721\le$ P0 $=21252227$；A\_load $=16048332\le$ P0；完美信息下紧急购电费为 "
     r"$4.7\times10^{-10}$ 元（数值零）。若改用含违约费的全账基，P5 为 $14324819$ 元，同样不高于任何实际策略。"),
])

# 6) 补齐 7 个图表标签的 \cref
edit('论文/sections/sec01_intro.tex', [
    ('\\begin{table}[H]\n  \\centering\n  \\caption{四个问题的信息结构与决策要求对比}',
     '\\cref{tab:problems} 对比了四问的信息结构与决策要求。\n\n\\begin{table}[H]\n  \\centering\n  \\caption{四个问题的信息结构与决策要求对比}'),
    ('\\begin{table}[H]\n  \\centering\n  \\caption{附件数据内容与规模}',
     '\\cref{tab:attachments} 汇总了四个附件的内容与规模。\n\n\\begin{table}[H]\n  \\centering\n  \\caption{附件数据内容与规模}'),
    ('由 \\cref{fig:data-overview,tab:stats} 可得三点对建模直接有用的认识：',
     '\\cref{fig:monthly} 进一步给出月度特征。由 \\cref{fig:data-overview,fig:monthly,tab:stats} 可得三点对建模直接有用的认识：'),
])
edit('论文/sections/sec03_p1.tex', [
    ('由 \\cref{tab:p1-t2} 可见，储能全天完成约 1.9 个充放循环：',
     '\\cref{tab:p1-t1} 给出表1 指定时段的购电量，\\cref{tab:p1-t2} 给出储能充放电量。'
     '由 \\cref{tab:p1-t2,fig:p1-plan} 可见，储能全天完成约 1.9 个充放循环：'),
])
edit('论文/sections/sec04_p2.tex', [
    ('标定的最优裕度为 $\\alpha=0.15,\\ \\beta=0$，1 月总费用由 $1945353.62$ 元降至 $1524501.83$ 元，',
     '\\cref{tab:p2-margin} 列出前 5 名标定结果。标定的最优裕度为 $\\alpha=0.15,\\ \\beta=0$，'
     '1 月总费用由 $1945353.62$ 元降至 $1524501.83$ 元，'),
])
edit('论文/sections/sec06_p4.tex', [
    ('由 \\cref{tab:p4-pred}，\\textbf{7 日滑动平均}',
     '\\cref{fig:p4-forecast} 给出各预测器精度与典型日对比。由 \\cref{tab:p4-pred}，\\textbf{7 日滑动平均}'),
])

# 7) 附录 A 行数按实测更新
src = os.path.join(ROOT, '论文', 'src')
cnt = {os.path.basename(f): sum(1 for _ in open(f, encoding='utf-8'))
       for f in sorted(glob.glob(os.path.join(src, '*.py')))}
p = os.path.join(ROOT, '论文', 'sections', 'sec10_appendix.tex')
s = open(p, encoding='utf-8').read()
n_fix = 0
for fn, n in cnt.items():
    pat = r'(\\verb\|src/' + re.escape(fn) + r'\|[^\n]*&\s*)(\d+)(\s*\\\\)'
    m = re.search(pat, s)
    if m:
        if int(m.group(2)) != n:
            s = s[:m.start(2)] + str(n) + s[m.end(2):]
            n_fix += 1
    else:
        print('  [--] 附录行数未匹配: %s' % fn)
open(p, 'w', encoding='utf-8').write(s)
print('  附录 A 行数修正 %d 处；实测：%s' % (n_fix, cnt))
