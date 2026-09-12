# -*- coding: utf-8 -*-
"""修复 common.py 的路径依赖：向上查找含"附件/"的根目录，并使结果/图片目录兼容两种布局"""
p = '求解/common.py'
s = open(p, encoding='utf-8').read()
old = """HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ATT = os.path.join(ROOT, '附件')
TPL = os.path.join(ATT, '附件5')
RES = os.path.join(HERE, '结果')
FIG = os.path.join(HERE, '图片')"""
new = '''HERE = os.path.dirname(os.path.abspath(__file__))


def _find_root(start):
    """向上查找包含 附件/ 的目录，使附录中的源码副本在任意布局下均可运行"""
    cur = start
    for _ in range(6):
        if os.path.isdir(os.path.join(cur, '附件')):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.dirname(start)


def _pick_dir(*cands):
    for c in cands:
        if os.path.isdir(c):
            return c
    return cands[0]


ROOT = _find_root(HERE)
ATT = os.path.join(ROOT, '附件')
TPL = os.path.join(ATT, '附件5')
RES = _pick_dir(os.path.join(HERE, '结果'), os.path.join(ROOT, '求解', '结果'))
FIG = _pick_dir(os.path.join(HERE, '图片'), os.path.join(ROOT, '求解', '图片'))'''
assert old in s, '未找到待替换的路径块'
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)
print('common.py 路径探测已修复')

# 同步到附录源码副本
import shutil
shutil.copy(os.path.join('求解', 'common.py'), os.path.join('论文', 'src', 'common.py'))
print('已同步 论文/src/common.py')
