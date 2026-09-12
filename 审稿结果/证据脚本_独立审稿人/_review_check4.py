# -*- coding: utf-8 -*-
"""格式与引用合规检查（只读）"""
import os, re, io, glob, sys
B = r"E:\qq文件\CUMCM2026Problems\C题"
P = os.path.join(B, "论文")
files = [os.path.join(P, "论文.tex"), os.path.join(P, "论文_打印版.tex"), os.path.join(P, "preamble.tex")]
files += glob.glob(os.path.join(P, "front", "*.tex")) + glob.glob(os.path.join(P, "sections", "*.tex"))
text = {}
for f in files:
    text[os.path.basename(f)] = io.open(f, encoding="utf-8").read()
allsrc = "\n".join(text.values())
body = "\n".join(v for k, v in text.items() if k.startswith("sec"))

def show(name, pat, src=body, flags=0):
    hits = [(m.start(), m.group(0)) for m in re.finditer(pat, src, flags)]
    print(f"[{name}] {len(hits)} 处")
    for pos, h in hits[:20]:
        line = src[:pos].count("\n") + 1
        print("   line", line, ":", h.replace("\n", "\\n")[:120])
    return hits

print("=" * 70); print("1. 格式硬指标")
show("tableofcontents", r"\\tableofcontents")
show("newpage/clearpage(正文分节文件)", r"\\(?:newpage|clearpage|cleardoublepage)")
show("目录/contentsline", r"\\contentsline")
print()
print("2. 正文分点符号（应无 •/·/▪ 及无 enumerate 之外的圆点）")
show("bullet 字符", r"[•·▪◦‣]")
show("'\\item' 前无列表环境的裸 item", r"(?<!\n)\\item")
print()
print("3. 公式后的句读（display 公式 $$...$$ 后是否以逗号/句号结尾）")
eqs = re.findall(r"\\begin\{equation\}(.*?)\\end\{equation\}", body, re.S)
print("equation 环境数:", len(eqs))
bad = [e for e in eqs if not re.search(r"[,，。；;\.]\s*$", e.strip())]
print("公式末尾无标点的个数:", len(bad))
for e in bad[:10]:
    print("   >>", e.strip().replace("\n", " ")[:110])
print()
print("4. 图表引用覆盖")
labels = re.findall(r"\\label\{(fig:[^}]+|tab:[^}]+)\}", body)
refs = set(re.findall(r"\\cref\{([^}]+)\}", body)) | set(re.findall(r"\\ref\{([^}]+)\}", body))
refkeys = set()
for r in refs:
    for k in r.split(","):
        refkeys.add(k.strip())
labels_set = set(labels)
print("label 总数:", len(labels_set), " 被引用 key 数:", len(refkeys))
unref = sorted(labels_set - refkeys)
print("定义但从未被 \\cref/\\ref 引用的 fig/table label:", unref)
missing = sorted(k for k in refkeys if k.startswith(("fig:", "tab:")) and k not in labels_set)
print("被引用但无定义:", missing)
print()
print("5. 文献引用")
bibkeys = re.findall(r"\\bibitem\{([^}]+)\}", body)
citekeys = set()
for m in re.findall(r"\\cite\{([^}]+)\}", body):
    for k in m.split(","):
        citekeys.add(k.strip())
print("bibitem:", len(bibkeys), bibkeys)
print("正文 cite 使用:", len(citekeys), sorted(citekeys))
print("定义未引用:", sorted(set(bibkeys) - citekeys))
print("引用未定义:", sorted(citekeys - set(bibkeys)))
print()
print("6. 匿名性检查（姓名/学校/指导教师/学号/队号）")
pats = [r"[\u4e00-\u9fa5]{2,4}(同学|老师)", r"指导教师[:：]\s*\S", r"大学|学院|中学",
        r"学号|班级|队号|参赛队号[:：]\s*\S", r"[A-Za-z]{2,}\s*(University|College)",
        r"(?<![数])[0-9]{8,12}(?![0-9])"]
for pat in pats:
    hits = [(m.group(0), allsrc[:m.start()].count("\n") + 1) for m in re.finditer(pat, allsrc)]
    if hits:
        print(" ", pat, "->", hits[:8])
print("  (承诺书/编号页含姓名栏属规范要求)")
print()
print("7. 摘要字数（中文字符+西文词）")
abs_txt = text["abstract.tex"]
abs_txt = re.sub(r"%.*", "", abs_txt)
abs_txt = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", abs_txt)   # 去命令
abs_txt = re.sub(r"[\{\}\\$]", " ", abs_txt)
cjk = re.findall(r"[\u4e00-\u9fa5]", abs_txt)
words = re.findall(r"[A-Za-z]+", abs_txt)
digits = re.findall(r"[0-9]+(?:\.[0-9]+)?", abs_txt)
print("  中文字符:", len(cjk), " 英文词:", len(words), " 数字串:", len(digits))
print("  估算总字数(中文+英文词+数字):", len(cjk) + len(words) + len(digits))
print()
print("8. 三线表（booktabs）与竖线")
print("  \\toprule 次数:", body.count("\\toprule"), " \\midrule:", body.count("\\midrule"), " \\bottomrule:", body.count("\\bottomrule"))
print("  含竖线的 tabular 列格式:", len(re.findall(r"\\begin\{tabular\}\{[^}]*\|", body)))
print()
print("9. 图片文件名引用 vs 实际存在")
inc = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", body)
print("  includegraphics:", inc)
missing_img = [i for i in inc if not os.path.exists(os.path.join(P, "图", i))]
print("  缺失图片:", missing_img)
print()
print("10. PDF 页数与摘要页")
aux = os.path.join(P, "论文.log")
log = io.open(os.path.join(P, "论文.log"), encoding="utf-8", errors="replace").read()
print("  log 中 'Error' 出现次数:", len(re.findall(r"(?i)^!|^! ", log, re.M)), "  'Error' 关键字:", log.count("Error"))
print("  Overfull \\hbox 次数:", len(re.findall(r"Overfull \\hbox", log)))
print("  Underfull \\hbox 次数:", len(re.findall(r"Underfull \\hbox", log)))
m = re.findall(r"Output written on .*?\((\d+) pages", log)
print("  Output written pages:", m)
