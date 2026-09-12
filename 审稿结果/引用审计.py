# -*- coding: utf-8 -*-
"""引用完整性审计：bibitem ↔ \\cite 双向核对，输出每处引用位置"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files = [os.path.join(ROOT, '论文', 'front', 'abstract.tex')] + \
        sorted(glob.glob(os.path.join(ROOT, '论文', 'sections', 'sec*.tex')))

cites = []           # (file, line, keys)
bibs = {}            # key -> file
for p in files:
    fn = os.path.basename(p)
    for i, line in enumerate(open(p, encoding='utf-8'), 1):
        for m in re.finditer(r'\\cite\{([^}]+)\}', line):
            for k in m.group(1).split(','):
                cites.append((fn, i, k.strip()))
            if 'bibitem' not in line:
                pass
    for m in re.finditer(r'\\bibitem\{([^}]+)\}', open(p, encoding='utf-8').read()):
        bibs[m.group(1)] = fn

print('① 正文引用（\\cite）共 %d 处，涉及 %d 种文献：' % (len(cites), len(set(c[2] for c in cites))))
for fn, ln, k in cites:
    print('   %-24s 第 %3d 行  → %s' % (fn, ln, k))
print('\n② 参考文献条目共 %d 条：' % len(bibs))
for k, fn in bibs.items():
    n = sum(1 for c in cites if c[2] == k)
    print('   %-22s 被引用 %d 次%s' % (k, n, '' if n else '   ★未被引用'))
print('\n③ 双向核对：')
miss1 = [k for k in bibs if k not in set(c[2] for c in cites)]
miss2 = [k for c in cites for k in [c[2]] if k not in bibs]
print('   已列未引用的文献：%s' % (miss1 if miss1 else '无'))
print('   已引用但未列出的文献：%s' % (miss2 if miss2 else '无'))
print('   结论：%s' % ('全部匹配（无遗漏、无悬空引用）' if not miss1 and not miss2 else '存在不一致'))
