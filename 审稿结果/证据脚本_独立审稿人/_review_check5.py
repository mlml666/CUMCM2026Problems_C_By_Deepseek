# -*- coding: utf-8 -*-
import os, struct, glob
B = r"E:\qq文件\CUMCM2026Problems\C题"
def png_dpi(p):
    b = open(p, "rb").read(4096)
    i = 8; dpi = None; w = h = None
    while i < len(b) - 8:
        ln = struct.unpack(">I", b[i:i+4])[0]
        typ = b[i+4:i+8]
        if typ == b"IHDR":
            w, h = struct.unpack(">II", b[i+8:i+16]); dpi = "no-pHYs"
        if typ == b"pHYs":
            px, py, u = struct.unpack(">IIB", b[i+8:i+17])
            dpi = (round(px*0.0254), round(py*0.0254), "m")
        i += 12 + ln
        if typ == b"IDAT": break
    return w, h, dpi

print("=== 论文/图 中 16 张被引用图片的实际分辨率与 DPI ===")
used = ['fig01.png','fig02.png','fig03.png','fig04.png','fig05.png','fig06.png','fig07.png','fig08.png',
        'fig09.png','fig10.png','fig11.png','fig12.png','fig14.png','fig15.png','fig16.png','fig17.png']
for f in used:
    p = os.path.join(B, "论文", "图", f)
    w, h, d = png_dpi(p)
    print(f"  {f}: {w}x{h} px, pHYs={d}, size={os.path.getsize(p)//1024} KB")
print("\n=== 论文/图 目录全部 PNG 数 ===", len(glob.glob(os.path.join(B,"论文","图","*.png"))))
print("其中 fig*.png:", len(glob.glob(os.path.join(B,"论文","图","fig*.png"))),
      " 图*.png:", len(glob.glob(os.path.join(B,"论文","图","图*.png"))))
print("\n=== 打印版 PDF 完整性 ===")
p = os.path.join(B, "论文", "论文_打印版.pdf")
raw = open(p, "rb").read()
print("size:", len(raw), " tail:", raw[-40:])
print(" 含 %%EOF:", b"%%EOF" in raw[-1024:])
pe = os.path.join(B, "论文", "论文.pdf"); rawe = open(pe,"rb").read()
print("电子版 size:", len(rawe), " 含 %%EOF:", b"%%EOF" in rawe[-1024:])
