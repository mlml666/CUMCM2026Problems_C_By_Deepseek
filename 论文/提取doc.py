# -*- coding: utf-8 -*-
"""从 Word 97-2003 (.doc, OLE2) 中按 piece table 规范提取正文文本。
用法: python 论文/提取doc.py <输入.doc> <输出.txt>
"""
import re
import struct
import sys
import olefile


def extract(path):
    ole = olefile.OleFileIO(path)
    streams = ['/'.join(s) for s in ole.listdir()]
    wd = ole.openstream('WordDocument').read()
    flags = struct.unpack_from('<H', wd, 0x0A)[0]
    tbl_name = '1Table' if (flags & 0x0200) else '0Table'
    if tbl_name not in streams:
        tbl_name = '0Table' if '0Table' in streams else '1Table'
    tbl = ole.openstream(tbl_name).read()
    fc_clx, lcb_clx = struct.unpack_from('<II', wd, 0x01A2)
    clx = tbl[fc_clx:fc_clx + lcb_clx]
    # 定位 Pcdt (clxt == 2)
    i, pcdt = 0, None
    while i < len(clx):
        t = clx[i]
        if t == 1:
            cb = struct.unpack_from('<h', clx, i + 1)[0]
            i += 3 + cb
        elif t == 2:
            lcb = struct.unpack_from('<I', clx, i + 1)[0]
            pcdt = clx[i + 5:i + 5 + lcb]
            break
        else:
            break
    if pcdt is None:
        raise RuntimeError('未找到 piece table (Pcdt)')
    n = (len(pcdt) - 4) // 12
    cps = list(struct.unpack_from('<%dI' % (n + 1), pcdt, 0))
    parts = []
    for k in range(n):
        off = 4 * (n + 1) + 8 * k
        fc = struct.unpack_from('<I', pcdt, off + 2)[0]
        compressed = bool(fc & 0x40000000)
        fcv = fc & 0x3FFFFFFF
        cch = cps[k + 1] - cps[k]
        if compressed:
            raw = wd[fcv // 2: fcv // 2 + cch]
            parts.append(raw.decode('cp1252', errors='replace'))
        else:
            raw = wd[fcv: fcv + cch * 2]
            parts.append(raw.decode('utf-16-le', errors='replace'))
    text = ''.join(parts)
    text = (text.replace('\r', '\n').replace('\x0b', '\n')
                .replace('\x0c', '\n').replace('\x07', ' | '))
    text = re.sub(r'[\x00-\x06\x08\x0e-\x1f]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    meta = {'streams': streams, 'table_stream': tbl_name, 'pieces': n,
            'text_len': len(text)}
    return text, meta


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else '论文/格式要求2026.doc'
    dst = sys.argv[2] if len(sys.argv) > 2 else '论文/格式要求2026.txt'
    text, meta = extract(src)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(text)
    print('流: %s' % meta['streams'])
    print('piece 数: %d | 表格流: %s | 文本长度: %d 字符' % (meta['pieces'], meta['table_stream'], meta['text_len']))
    print('已写出: %s' % dst)
