# -*- coding: utf-8 -*-
"""核对 display 公式末尾标点覆盖情况"""
import glob
import os
import re

tot = punct = 0
miss = []
for p in sorted(glob.glob('论文/sections/sec*.tex')):
    s = open(p, encoding='utf-8').read()
    for m in re.finditer(r'\\begin\{equation\}(.*?)\\end\{equation\}', s, re.S):
        tot += 1
        lines = m.group(1).split('\n')
        cur = ''
        for i in range(len(lines) - 1, -1, -1):
            t = lines[i].strip()
            if t and not t.startswith('\\label'):
                cur = t
                break
        if cur and cur[-1] in '，。；,.;':
            punct += 1
        else:
            miss.append('%s :: %s' % (os.path.basename(p), cur[-50:]))
print('公式总数 %d，已带标点 %d，仍缺 %d' % (tot, punct, len(miss)))
for x in miss:
    print('   缺:', x)
