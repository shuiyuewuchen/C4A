# C4A 技能提交自动评审 — 交付包

## 这是什么

一个能自动评审 C4 技能提交的技能（递归套娃：用技能评审技能）。

## 挑战要求 → 本包文件对照

| 挑战要求（据课程挑战原始指引） | 本包文件 | 说明 |
|---|---|---|
| 方案设计文档 | `方案设计.md` | 架构、评审维度、技术选型理由 |
| 可安装技能包 | `c4-skill-evaluator.skill` + `c4a-skill-evaluator/` | SKILL.md + 脚本 + rubric |
| 真实评审报告 | `真实评审报告.md`（展示版）+ `output/评审报告.md`（机器产物） | 对 3 份仿真 C4 提交的评审结果 |
| 教学说明 | `教学说明.md` | 怎么安装、怎么用、输入输出 |
| AI 日志 | `AI日志.md` | 12 轮对话 + prompt 迭代表 |
| 拿来说明 | `拿来说明.md` | 从 starter 拿了什么、改了什么、为什么 |
| （额外）AAR 复盘 | `AAR复盘.md` | 目标 vs 实际、犯错记录、改进 |
| （额外）误判率验证 | `samples/expected.json` + `c4a-skill-evaluator/scripts/validate.py` + `output/误判率验证.txt` | 15 个判定点 0 误判 |

> 注：提交到群里前，建议把这些文件重命名为 `姓名拼音_C4A_描述.扩展名` 格式。

## 文件清单

| 路径 | 说明 |
|------|------|
| `c4-skill-evaluator.skill` | 可安装技能包（zip） |
| `c4a-skill-evaluator/` | 技能源码（SKILL.md + scripts/ + references/） |
| `方案设计.md` `教学说明.md` `AI日志.md` `拿来说明.md` `AAR复盘.md` | 6 份交付文档 |
| `samples/` | 3 份仿真 C4 提交 + `expected.json` 黄金答案 |
| `output/` | 最近一次跑出来的报告（.md/.xlsx/.json/验证.txt），**Excel 已实际产出并校验** |

## 快速体验

```bash
# 1. 跑评审
cd c4a-skill-evaluator
python3 scripts/c4_evaluator.py ../samples --out ../output

# 2. 跑误判率验证（15 点对照）
python3 scripts/validate.py
```

## 误判率证据（evaluatorQuality 信号）

```
判定点总数：15（3 作者 × 5 必交件）
跨档误判：0
误判率：0.0%
排名顺序：wangfang > liming > zhangwei ✅
分数带：全部落在期望区间 ✅
```

详见 `output/误判率验证.txt`。

## 完成级别（诚实版）

| Level | 状态 | 说明 |
|-------|------|------|
| L1 文件采集 | ✅ | `_C4_` 前缀分组、非 C4 文件过滤、版本号识别 |
| L2 完整性检查 | ✅ | 5 必交件三级判定（✅/⚠️/❌）+ 内容充实度加权（空文件不拿满分） |
| L3 质量评审 | ✅ | 四维 × 3 check_items，规则引擎 + LLM 深审钩子 |
| L4 完整报告 | 🟡 | Markdown + Excel + 排名 + 改进建议 ✅；**版本进步轨迹 diff ❌（v2）** |

## v2 路线图（未实现，不假装已做）

- WeChat 群文件自动同步（当前需手动下载到文件夹）
- PDF/DOCX 内容解析（当前只读 .md/.py/.txt）
- v1 vs v2 提交进步轨迹对比
- LLM 深审的自动化调用（当前靠 Agent 加载 SKILL.md 时自然完成）

## 关于 samples/ 里的"干扰文件"

`samples/课程表_2026秋.md` 是**故意放的非 C4 文件**，用于验证评审器的过滤逻辑——它没有 `_C4_` 标记，应该被自动忽略而不是被当成一个 Unknown 作者。跑 `validate.py` 时它确实被正确过滤了。

## 依赖

- Python 3.9+（必需）
- `openpyxl`（**已随 v1.2 重跑安装并验证**，用于生成 `output/评审详表.xlsx`）
  - 安装：`pip3 install openpyxl`
  - 缺失时的行为：不报错退出，报告正文生成「⚠️ 本次未生成 Excel 详表」提示，`eval_summary.json` 的 `excel_written` 字段标记为 `false`
  - 本次重跑状态：`excel_written: true`，`output/评审详表.xlsx` 共 4 行 × 9 列（总览表）
