**这是今年数学建模国赛C题的全部解答过程，使用了DeepSeek来完成，agent框架使用了dsh（算是尝鲜使用，第一次用AI来完成国赛题目），主要想作为一个测试使用，之后可能会评估一下正确性（如果能记起来的话...）,上传仓库以免搞忘了。**

This is the solution process for this year's National College Mathematical Modeling Contest Problem C, completed using DeepSeek, with the agent framework dsh (a bit of a trial run, as it was my first time using AI to complete a National Contest problem），mainly intended as a test, and I may evaluate its correctness later (if I remember to...). Uploading it to the repository so I don't forget..

---

# CUMCM 2026 C题：微网与外部电网电力调控策略

> 一句话：给"光伏 + 储能 + 外网购电"的微网定一套购电和充放电策略，花最少的钱把小区负载喂饱。四问从"啥都已知"一路加到"电价也波动"，信息越来越不确定。

## 目录长这样

- `求解/` —— 代码 + 推导 + 结果
  - `模型推导/` —— 四个问题的推导文档（每篇末尾都有"口语化解题思路·速读版"）
  - `问题1/` ~ `问题4/` —— 每问的求解脚本 `问题X_求解.py`
  - `结果/` —— result*.xlsx、CSV、图、日志，以及 `求解结果汇总.md`
  - `数据探索.py`、`进度.md`
- `论文/` —— 论文源码（`论文.tex`）和编译好的 `论文.pdf`
- `支撑材料/` —— 支撑材料（论文源码副本、源码、AI 工具说明）
- `审稿结果/` —— 审稿 checklist
- `附件/` —— 附件 1~5（只读数据）
- 根目录的 `result1.xlsx` ~ `result4-3.xlsx` —— 按题目模板填好的结果文件

## 四问的解题思路（速览）

- **问题 1**：电价、负载、光伏全给定，直接上线性规划（LP），一次性算好 144 个时段的购电/充放电，储能"低买高卖"。
- **问题 2**：负载光伏要自己猜，猜少了按 5 倍价紧急买电 → "预测 + 安全裕度（15%）"。
- **问题 3**：每 6 小时来新预报，滚动重优化；调低罚 0.5 倍、调高 1.5 倍 → 结论是**不用再加别的预报时刻**。
- **问题 4**：电价也波动，用历史电价预测 + 按实际电价结算，重算问题 2/3。

详细推导看 `求解/模型推导/框架设计.md` 和各 `问题X_数学推导.md`（每篇末尾有口语化速读版）。

## 怎么复现

```bash
python 求解/问题1/问题1_求解.py   # 问题 1
python 求解/问题2/问题2_求解.py   # 问题 2
python 求解/问题3/问题3_求解.py   # 问题 3
python 求解/问题4/问题4_求解.py   # 问题 4
```

随机种子统一 `np.random.seed(42)`，求解器用 scipy 自带的 HiGHS。

## 关键结果

| 问题 | 购电费 |
|------|--------|
| 问题 1（典型日） | 35101.57 元 |
| 问题 2 | 1664.80 万元 |
| 问题 3 | 2136.95 万元 |
| 问题 4-2 / 4-3 | 2034.59 万 / 2224.44 万元 |

完整结果见 `求解/结果/求解结果汇总.md`。
