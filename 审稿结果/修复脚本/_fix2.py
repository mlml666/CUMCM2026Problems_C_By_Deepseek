# -*- coding: utf-8 -*-
"""压缩篇幅，使"正文+AI声明+参考文献"回到 30 页以内"""
import glob
import re

# 1) 行距 1.18 → 1.14
p = '论文/preamble.tex'
s = open(p, encoding='utf-8').read()
s = s.replace(r'\linespread{1.18}', r'\linespread{1.14}')
open(p, 'w', encoding='utf-8').write(s)
print('行距已调整为 1.14')

# 2) 图宽再缩一档
REPS = [(r'width=0.80\linewidth', r'width=0.74\linewidth'),
        (r'width=0.76\linewidth', r'width=0.70\linewidth')]
n = 0
for f in sorted(glob.glob('论文/sections/*.tex')):
    t = open(f, encoding='utf-8').read()
    o = t
    for a, b in REPS:
        t = t.replace(a, b)
    if t != o:
        open(f, 'w', encoding='utf-8').write(t)
        n += 1
print('缩放插图文件数:', n)

# 3) 核心公式汇总节整体用小一号字
p = '论文/sections/sec06b_formulas.tex'
s = open(p, encoding='utf-8').read()
s = s.replace(r'\section{核心公式汇总}',
              '\\section{核心公式汇总}\n\\begingroup\\small', 1)
s = s.rstrip() + '\n\\endgroup\n'
open(p, 'w', encoding='utf-8').write(s)
print('核心公式汇总节已改为 \\small')
