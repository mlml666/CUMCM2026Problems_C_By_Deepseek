# -*- coding: utf-8 -*-
"""
tex合并脚本：将拆分的tex子文件合并为一个完整的单文件。
用法：python merge_tex.py 论文.tex 论文_完整版.tex
"""
import re, sys, os


def merge_tex(filepath, base_dir=None, depth=0, seen=None):
    """递归展开 \\input{} 为实际文件内容"""
    if seen is None:
        seen = set()
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(filepath))

    filepath_abs = os.path.normpath(
        os.path.join(base_dir, filepath) if not os.path.isabs(filepath) else filepath
    )

    # 防止循环引用，限制递归深度
    if filepath_abs in seen or depth > 10:
        return f"% [跳过: {filepath}]\n"
    seen.add(filepath_abs)

    if not os.path.exists(filepath_abs):
        return f"% [未找到: {filepath}]\n"

    with open(filepath_abs, 'r', encoding='utf-8') as f:
        content = f.read()

    def replacer(m):
        indent = m.group(1)
        inc_file = m.group(2).strip()
        if not inc_file.endswith('.tex'):
            inc_file += '.tex'
        inner_base = os.path.dirname(filepath_abs)
        merged = merge_tex(inc_file, inner_base, depth + 1, seen)
        # 保持原始缩进
        return ''.join(indent + line for line in merged.splitlines(True))

    # 匹配 \input{xxx}，支持前面有空格/缩进
    pattern = re.compile(r'^([ \t]*)\\input\{([^}]+)\}', re.MULTILINE)
    result = pattern.sub(replacer, content)
    return result


if __name__ == '__main__':
    main = sys.argv[1] if len(sys.argv) > 1 else '论文.tex'
    out = sys.argv[2] if len(sys.argv) > 2 else '论文_完整版.tex'

    merged = merge_tex(main)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(merged)

    # 统计
    lines = merged.count('\n')
    inputs_remaining = len(re.findall(r'\\input\{', merged))
    print(f"已合并: {out} ({lines}行, 剩余未展开input: {inputs_remaining})")
