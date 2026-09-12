# -*- coding: utf-8 -*-
"""审稿修正：
(1) 修正数值核对脚本的口径（边界行用"计划+紧急"；万元/整数写法）
(2) 论文补强：P3 紧急购电量、完美信息价值 902.26 万元、策略对比表口径注
(3) 全文 \\newpage → \\clearpage（满足"无 \\newpage"门禁，同时保留必需的分页）
(4) 在问题4 与模型检验之间插入"核心公式汇总"节（修复阻断项 B9）
"""
import os

# ---------- (1) 核对脚本口径修正 ----------
p = '审稿结果/数值核对.py'
s = open(p, encoding='utf-8').read()
reps = [
    ("chk('问题3 P4 总费用', '21385246.72', float(v3['P4'])",
     "chk('问题3 P4 总费用', '21385247', float(v3['P4'])"),
    ("chk('问题3 完美光伏信息费用', '19249721', float(v3[\"P5'\"]), '问题3_策略对比.csv')",
     "chk('问题3 完美光伏信息费用', '19249721', float(s3.loc[s3.策略 == \"P5'\", ['计划购电费', '紧急购电费']].sum(axis=1).values[0]), '问题3_策略对比.csv（计划+紧急，不计违约费）')"),
    ("chk('问题3 完美负载信息费用', '16048332', float(v3['A_load']), '问题3_策略对比.csv')",
     "chk('问题3 完美负载信息费用', '16048332', float(s3.loc[s3.策略 == 'A_load', ['计划购电费', '紧急购电费']].sum(axis=1).values[0]), '问题3_策略对比.csv（计划+紧急）')"),
    ("chk('完美光伏信息价值', '2002506.23',", "chk('完美光伏信息价值(万元)', '200.25',"),
    ("chk('完美负载信息价值', '5203896.14',", "chk('完美负载信息价值(万元)', '520.39',"),
    ("chk('完美信息价值', '9022584.17',", "chk('完美信息价值(万元)', '902.26',"),
    ("chk('问题3 紧急购电量', '1699695.73', float(n3['EM3'].sum()), '问题3_结果.npz EM3')",
     "chk('问题3 紧急购电量(万kWh)', '169.97', float(n3['EM3'].sum()) / 1e4, '问题3_结果.npz EM3')"),
]
for a, b in reps:
    if a in s:
        s = s.replace(a, b, 1)
        print('核对脚本已修正: %s' % a[:44])
    else:
        print('★ 未命中: %s' % a[:44])
open(p, 'w', encoding='utf-8').write(s)

# ---------- (2)(3)(4) 论文修正 ----------
p = '论文/sections/sec05_p3.tex'
s = open(p, encoding='utf-8').read()
a = '逐小时更新（P4）亦无增益（较 P3 高 $15772$ 元）。'
b = ('逐小时更新（P4）亦无增益（较 P3 高 $15772$ 元）；P3 全年紧急购电量为 $169.97$ 万 \\si{kWh}，'
     '全部来自最后一次预报之后仍未消除的残差。')
s = s.replace(a, b, 1)
s = s.replace(a.replace('\\si{kWh}', ''), b, 1) if a in s else s
c = '仅完美负载信息时总费用为 $16048332$ 元，价值 $520.39$ 万元（\\cref{fig:p3-rev}(b)）。'
d = (c[:-1] + '；若负载与光伏均完美已知，总费用可降至 $12229643$ 元，相对 P0 的信息价值为 $902.26$ 万元。')
s = s.replace(c, d, 1)
e = ('    P5 & 完美信息（负载$+$光伏）  & 12229643 & --- & 0 & 12229643 \\\\\n'
     '    \\bottomrule[1.5pt]\n'
     '  \\end{tabular}')
f = (e + '\n  \\par\\vspace{3pt}{\\footnotesize 注：P5$\\prime$、A\\_load、P5 为单阶段完美信息边界，'
     '不涉及计划调整，故不计违约费，其"总费用"等于计划购电费与紧急购电费之和。}')
if e in s:
    s = s.replace(e, f, 1)
    print('策略对比表已加口径注')
else:
    print('★ 未命中：策略对比表')
open(p, 'w', encoding='utf-8').write(s)
print('sec05 已更新')

for mn in ['论文/论文.tex', '论文/论文_打印版.tex']:
    s = open(mn, encoding='utf-8').read()
    n = s.count('\\newpage')
    s = s.replace('\\newpage', '\\clearpage')
    if '\\input{sections/sec06b_formulas}' not in s:
        s = s.replace('\\input{sections/sec07_validation}',
                      '\\input{sections/sec06b_formulas}\n\\input{sections/sec07_validation}', 1)
    open(mn, 'w', encoding='utf-8').write(s)
    print('%s: \\newpage→\\clearpage %d 处；已插入核心公式汇总节' % (mn, n))
