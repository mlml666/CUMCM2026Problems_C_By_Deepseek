# -*- coding: utf-8 -*-
"""Phase 3 编译门禁检查：两遍 XeLaTeX 编译 + 日志检查
门禁要求：致命错误（^!）数 = 0；无缺字；无未定义引用；不含目录命令。
用法：python 论文/编译检查.py
"""
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))


def check(tex_name='论文.tex', runs=2):
    os.chdir(BASE)
    for _ in range(runs):
        subprocess.run(['xelatex', '-interaction=nonstopmode', '-file-line-error', tex_name],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log_path = os.path.join(BASE, tex_name.replace('.tex', '.log'))
    log = open(log_path, encoding='utf-8', errors='ignore').read()
    src = open(os.path.join(BASE, tex_name), encoding='utf-8').read()
    err = re.findall(r'^!.*$', log, re.M)
    missing = re.findall(r'Missing character.*$', log, re.M)
    undef = re.findall(r"Reference .*undefined.*$", log, re.M)
    overfull = re.findall(r'Overfull \\hbox.*$', log, re.M)
    pages = re.findall(r'Output written on .*\((\d+) pages?', log)
    has_toc = 'tableofcontents' in src
    print('=' * 62)
    print('Phase 3 门禁检查：%s' % tex_name)
    print('=' * 62)
    print('  致命错误 (^!)      : %d' % len(err))
    for e in err[:5]:
        print('      %s' % e)
    print('  缺字 (missing char): %d' % len(missing))
    print('  未定义引用         : %d' % len(undef))
    print('  目录命令           : %s' % ('存在（不合规）' if has_toc else '无（合规）'))
    print('  Overfull hbox      : %d（仅提示，不阻断）' % len(overfull))
    print('  总页数             : %s' % (pages[-1] if pages else '未知'))
    ok = (len(err) == 0) and (len(missing) == 0) and (len(undef) == 0) and not has_toc
    print('  判定               : %s' % ('PASS' if ok else 'FAIL'))
    return ok, pages[-1] if pages else None


if __name__ == '__main__':
    ok, _ = check()
    sys.exit(0 if ok else 1)
