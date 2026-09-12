# -*- coding: utf-8 -*-
"""让独立验算脚本与补充实验脚本也具备健壮路径（附录副本可就地运行）"""
import os
import shutil

ROBUST = '''def _find_dir(name, maxup=8):
    """自脚本目录向上查找子目录 name，使附录中的源码副本在任意布局下均可运行"""
    cur = os.path.dirname(os.path.abspath(__file__))
    for _ in range(maxup):
        cand = os.path.join(cur, name)
        if os.path.isdir(cand):
            return cand
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


'''

# ---------- 1) 独立验算脚本 ----------
p = '求解/验算/phase25_独立验算.py'
s = open(p, encoding='utf-8').read()
old = """HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ATT = os.path.join(ROOT, '附件')
RES = os.path.join(os.path.dirname(HERE), '结果')"""
new = """HERE = os.path.dirname(os.path.abspath(__file__))

""" + ROBUST + """ATT = _find_dir('附件')
ROOT = os.path.dirname(ATT)
RES = _find_dir(os.path.join('求解', '结果'))"""
assert old in s, 'phase25 路径块未命中'
open(p, 'w', encoding='utf-8').write(s.replace(old, new, 1))
print('已修复 phase25_独立验算.py 路径')

# ---------- 2) 补充灵敏度脚本 ----------
p = '论文/补充灵敏度.py'
s = open(p, encoding='utf-8').read()
old2 = """ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '求解'))
import common as C"""
new2 = ROBUST + """_att = _find_dir('附件')
ROOT = os.path.dirname(_att)
sys.path.insert(0, os.path.join(ROOT, '求解'))
import common as C"""
assert old2 in s, 'sensitivity 路径块未命中'
open(p, 'w', encoding='utf-8').write(s.replace(old2, new2, 1))
print('已修复 补充灵敏度.py 路径')

# ---------- 3) 同步附录源码副本 ----------
pairs = [('求解/common.py', 'common.py'), ('求解/数据探索.py', 'explore_data.py'),
         ('求解/问题1/问题1_求解.py', 'solve_p1.py'), ('求解/问题2/问题2_求解.py', 'solve_p2.py'),
         ('求解/问题3/问题3_求解.py', 'solve_p3.py'), ('求解/问题4/问题4_求解.py', 'solve_p4.py'),
         ('求解/验算/phase25_独立验算.py', 'verify_p25.py'), ('论文/绘图.py', 'plots.py'),
         ('论文/补充灵敏度.py', 'sensitivity.py'), ('论文/编译检查.py', 'compile_check.py')]
for a, b in pairs:
    if os.path.exists(a):
        shutil.copy(a, os.path.join('论文', 'src', b))
print('附录源码副本已同步 %d 个文件' % len(pairs))
