# -*- coding: utf-8 -*-
"""Phase 4 审稿证据：论文数值 ↔ 求解结果文件 一致性核对
输出：审稿结果/数值核对.csv（每项：论文值、来源值、偏差%、判定）
"""
import os
import re
import glob
import numpy as np
import pandas as pd
import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, '求解', '结果')
ATT = os.path.join(ROOT, '附件')

TEX = ''.join(open(p, encoding='utf-8').read()
              for p in [os.path.join(ROOT, '论文', 'front', 'abstract.tex')]
              + sorted(glob.glob(os.path.join(ROOT, '论文', 'sections', 'sec*.tex'))))

rows = []


def chk(name, paper_text, src_value, src_desc):
    """paper_text 为论文中出现的数值字符串；核对其是否出现并与来源值一致"""
    present = paper_text in TEX
    pv = float(paper_text.replace(',', ''))
    dev = abs(pv - src_value) / max(abs(src_value), 1e-12)
    if not present:
        verdict = 'FAIL(论文中未找到该数值)'
    elif dev <= 0.005:
        verdict = 'PASS'
    elif dev <= 0.05:
        verdict = 'SUSPECT'
    else:
        verdict = 'FAIL'
    rows.append({'核对项': name, '论文值': paper_text, '来源值': '%.6g' % src_value,
                 '偏差%': round(100 * dev, 4), '判定': verdict, '来源': src_desc})


# ---------- 附件1 独立读取（不用求解代码） ----------
df1 = pd.read_excel(os.path.join(ATT, '附件1.xlsx'))
df1.columns = ['t', 'p', 'L', 'P']
for c in 'pLP':
    df1[c] = pd.to_numeric(df1[c])
L1, P1, p1 = df1['L'].values, df1['P'].values, df1['p'].values
base_nostorage = float(np.dot(p1, np.maximum(0.0, (L1 - P1)) * (1 / 6)))

# ---------- 问题1 ----------
t1 = pd.read_csv(os.path.join(RES, '表1_问题1.csv'))
fee1 = float(t1.loc[t1['时间段'] == '全天购电费', '购电量(kWh)'].values[0])
qty1 = float(t1.loc[t1['时间段'] == '全天购电量', '购电量(kWh)'].values[0])
chk('问题1 全天购电费', '35101.57', fee1, '表1_问题1.csv')
chk('问题1 全天购电量', '59482.70', qty1, '表1_问题1.csv')
chk('问题1 无储能基线', '48052.05', base_nostorage, '附件1 独立复算')
chk('问题1 储能节省', '12950.48', base_nostorage - fee1, '附件1 独立复算')

# ---------- 问题2 ----------
m2 = pd.read_csv(os.path.join(RES, '问题2_月度费用汇总.csv'))
tot2 = m2[m2['月份'] == '合计'].iloc[0]
chk('问题2 计划购电费', '15347789.64', float(tot2['计划购电费元']), '问题2_月度费用汇总.csv')
chk('问题2 紧急购电费', '1300195.25', float(tot2['紧急购电费元']), '问题2_月度费用汇总.csv')
chk('问题2 总费用', '16647984.89', float(tot2['总费用元']), '问题2_月度费用汇总.csv')
chk('问题2 紧急购电量', '275907.99', float(tot2['紧急购电量kWh']), '问题2_月度费用汇总.csv')
n2 = np.load(os.path.join(RES, '问题2_结果.npz'))
chk('问题2 无裕度对照', '21611681.31', float(n2['cost0'].sum()), '问题2_结果.npz cost0')
chk('问题2 裕度节省', '4963696.42', float(n2['cost0'].sum() - tot2['总费用元']), 'npz cost0 − 合计')
chk('问题2 完美信息下界', '12229643.06', float(n2['costP'].sum()), '问题2_结果.npz costP')
cal2 = pd.read_csv(os.path.join(RES, '问题2_裕度标定.csv'))
chk('问题2 最优裕度 α', '0.15', float(cal2.iloc[0]['alpha']), '问题2_裕度标定.csv 首行')
prec = pd.read_csv(os.path.join(RES, '问题2_预测器精度.csv'))
chk('负载预测 RMSE(7日均)', '955.9', float(prec.loc[prec.预测器 == '7日均', '负载RMSE(kW)'].values[0]),
    '问题2_预测器精度.csv')
chk('光伏预测 MAE(EWMA)', '150.1', float(prec.loc[prec.预测器 == 'EWMA(0.7,14)', '光伏MAE(kW)'].values[0]),
    '问题2_预测器精度.csv')

# ---------- 问题3 ----------
s3 = pd.read_csv(os.path.join(RES, '问题3_策略对比.csv'))
v3 = dict(zip(s3['策略'], s3['总费用']))
chk('问题3 P0 总费用', '21252227', float(v3['P0']), '问题3_策略对比.csv')
chk('问题3 P3 总费用', '21369474.67', float(v3['P3']), '问题3_策略对比.csv')
chk('问题3 P4 总费用', '21385247', float(v3['P4']), '问题3_策略对比.csv')
chk('问题3 完美光伏信息费用', '19249721', float(s3.loc[s3.策略 == "P5'", ['计划购电费', '紧急购电费']].sum(axis=1).values[0]), '问题3_策略对比.csv（计划+紧急，不计违约费）')
chk('问题3 完美负载信息费用', '16048332', float(s3.loc[s3.策略 == 'A_load', ['计划购电费', '紧急购电费']].sum(axis=1).values[0]), '问题3_策略对比.csv（计划+紧急）')
chk('问题3 完美信息费用', '14324819', float(v3['P5']), '问题3_策略对比.csv')
mv = pd.read_csv(os.path.join(RES, '问题3_更新边际价值.csv'))
d = dict(zip(mv['项目'], mv['费用下降(元)']))
chk('完美光伏信息价值(万元)', '200.25', float(d['完美光伏信息价值(单阶段, 无违约费)']) / 1e4, '问题3_更新边际价值.csv')
chk('完美负载信息价值(万元)', '520.39', float(d['完美负载信息价值(单阶段, 无违约费)']) / 1e4, '问题3_更新边际价值.csv')
chk('完美信息价值(万元)', '902.26', float(d['完美信息价值(单阶段, 无违约费)']) / 1e4, '问题3_更新边际价值.csv')
rev = pd.read_csv(os.path.join(RES, '问题3_预报修订幅度.csv'))
chk('预报修订 MAE(0:00→6:00)', '279.5', float(rev.loc[rev.修订 == '0:00->6:00', 'MAE(kW)'].values[0]),
    '问题3_预报修订幅度.csv')
chk('预报修订 MAE(6:00→12:00)', '120.0', float(rev.loc[rev.修订 == '6:00->12:00', 'MAE(kW)'].values[0]),
    '问题3_预报修订幅度.csv')
n3 = np.load(os.path.join(RES, '问题3_结果.npz'))
chk('问题3 紧急购电量(万kWh)', '169.97', float(n3['EM3'].sum()) / 1e4, '问题3_结果.npz EM3')

# ---------- 问题4 ----------
n4 = np.load(os.path.join(RES, '问题4_结果.npz'))
chk('问题4-2 总费用', '20345866.93', float(n4['plan42'].sum() + n4['emg42'].sum()), '问题4_结果.npz')
chk('问题4-2 紧急购电量', '1391491.14', float(n4['EM42'].sum()), '问题4_结果.npz EM42')
chk('问题4-2 计划购电费', '13752204.93', float(n4['plan42'].sum()), '问题4_结果.npz plan42')
chk('问题4-2 紧急购电费', '6593662.00', float(n4['emg42'].sum()), '问题4_结果.npz emg42')
chk('问题4-2 无裕度对照', '20952588.33', float(n4['c42_0'].sum()), '问题4_结果.npz c42_0')
s43 = pd.read_csv(os.path.join(RES, '问题4_4-3策略对比.csv'))
chk('问题4-3 P3 总费用', '22244432.98', float(s43.loc[s43.策略 == 'P3', '总费用'].values[0]), '问题4_4-3策略对比.csv')
chk('问题4-3 P0 总费用', '22071537.66', float(s43.loc[s43.策略 == 'P0', '总费用'].values[0]), '问题4_4-3策略对比.csv')
pdfp4 = pd.read_csv(os.path.join(RES, '问题4_电价预测精度.csv'))
chk('电价预测 MAE(7日均)', '0.0827', float(pdfp4.loc[pdfp4.预测器 == '7日均', 'MAE(元/kWh)'].values[0]),
    '问题4_电价预测精度.csv')

# ---------- 灵敏度与验算 ----------
s1 = pd.read_csv(os.path.join(ROOT, '论文', '图', '灵敏度_问题1.csv'))
sc = dict(zip(s1['scenario'], s1['费用变化%']))
chk('灵敏度 η=0.85 变化%', '4.12', abs(float(sc['$\\eta=0.85$'])), '论文/图/灵敏度_问题1.csv')
chk('灵敏度 η=0.95 变化%', '3.83', abs(float(sc['$\\eta=0.95$'])), '论文/图/灵敏度_问题1.csv')
chk('灵敏度 电量下限 变化%', '2.60', abs(float(sc['$E_{\\min}=2400$'])), '论文/图/灵敏度_问题1.csv')
sk = pd.read_csv(os.path.join(ROOT, '论文', '图', '灵敏度_问题2_费率.csv'))
chk('紧急费率 K=5 总费用', '16647985', float(sk.loc[sk['紧急费率倍数K'] == 5, '总费用元'].values[0]),
    '论文/图/灵敏度_问题2_费率.csv')
sd = pd.read_csv(os.path.join(ROOT, '论文', '图', '灵敏度_问题3_费率.csv'))
chk('对称违约费率 P3', '21531999', float(sd.loc[(sd.违约费率口径 == '对称(1.0,1.0)') & (sd.策略 == 'P3'), '总费用元'].values[0]),
    '论文/图/灵敏度_问题3_费率.csv')
vd = pd.read_csv(os.path.join(ROOT, '求解', '验算', 'phase25_验算明细.csv'))
chk('独立验算 PASS 项数', '40', float((vd['判定'] == 'PASS').sum()), 'phase25_验算明细.csv')

df = pd.DataFrame(rows)
out = os.path.join(ROOT, '审稿结果')
os.makedirs(out, exist_ok=True)
df.to_csv(os.path.join(out, '数值核对.csv'), index=False, encoding='utf-8-sig')
n_fail = int((df['判定'].str.startswith('FAIL')).sum())
n_susp = int((df['判定'] == 'SUSPECT').sum())
print(df.to_string(index=False))
print('\n合计 %d 项：PASS %d，SUSPECT %d，FAIL %d' %
      (len(df), int((df['判定'] == 'PASS').sum()), n_susp, n_fail))
