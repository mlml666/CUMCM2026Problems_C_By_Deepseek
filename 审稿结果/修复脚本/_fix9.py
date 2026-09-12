# -*- coding: utf-8 -*-
"""修正圈码缺字 + 压缩篇幅（正文+声明+参考文献 ≤30 页）"""
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1) 圈码 → 汉字序号
m = {'①': '一', '②': '二', '③': '三', '④': '四'}
tot = 0
for p in sorted(glob.glob(os.path.join(ROOT, '论文', 'sections', 'sec*.tex'))):
    s = open(p, encoding='utf-8').read()
    o = s
    for a, b in m.items():
        s = s.replace('对照' + a, '对照' + b).replace(a, b)
    if s != o:
        open(p, 'w', encoding='utf-8').write(s)
        tot += 1
print('圈码替换涉及 %d 个文件' % tot)

# 2) 行距 1.14 → 1.10
p = os.path.join(ROOT, '论文', 'preamble.tex')
s = open(p, encoding='utf-8').read()
s = s.replace('\\linespread{1.14}', '\\linespread{1.10}')
open(p, 'w', encoding='utf-8').write(s)
print('行距已调为 1.10')

# 3) 插图再缩 6%
REPS = [('width=0.74\\linewidth', 'width=0.70\\linewidth'),
        ('width=0.70\\linewidth', 'width=0.66\\linewidth')]
n = 0
for f in sorted(glob.glob(os.path.join(ROOT, '论文', 'sections', 'sec*.tex'))):
    s = open(f, encoding='utf-8').read()
    o = s
    for a, b in REPS:
        s = s.replace(a, b)
    if s != o:
        open(f, 'w', encoding='utf-8').write(s)
        n += 1
print('缩放插图文件 %d 个' % n)
