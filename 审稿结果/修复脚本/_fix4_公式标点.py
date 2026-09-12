# -*- coding: utf-8 -*-
"""为 display 公式补末尾标点（GB/T 7714：句中用逗号，句末用句号）"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMA_HEADS = ('其中', '即', '式中', '这里', '故', '从而', '因此', '由此')
PUNCT = '，。；,.;'

changed = 0
for path in sorted(glob.glob(os.path.join(ROOT, '论文', 'sections', 'sec*.tex'))):
    src = open(path, encoding='utf-8').read()
    out = []
    pos = 0
    for m in re.finditer(r'\\begin\{equation\}(.*?)\\end\{equation\}', src, re.S):
        block = m.group(1)
        # 该公式之后（跳过空行/注释）的首个正文片段，用于判定标点
        after = src[m.end():m.end() + 200]
        after = re.sub(r'^\s*(?:%.*\n\s*)*', '', after)
        punc = '，' if after.startswith(COMMA_HEADS) else '。'
        # 定位块内最后一行“内容行”（排除 \label 行）
        lines = block.split('\n')
        idx = None
        for i in range(len(lines) - 1, -1, -1):
            t = lines[i].strip()
            if t and not t.startswith('\\label'):
                idx = i
                break
        if idx is None:
            continue
        cur = lines[idx].rstrip()
        if cur and cur[-1] in PUNCT:
            continue
        lines[idx] = cur + punc
        new_block = '\n'.join(lines)
        out.append(src[pos:m.start(1)])
        out.append(new_block)
        pos = m.end(1)
        changed += 1
        print('  %-24s %s' % (os.path.basename(path), ('…' + cur.strip()[-34:] + punc)))
    out.append(src[pos:])
    open(path, 'w', encoding='utf-8').write(''.join(out))

print('共补标点 %d 处' % changed)
