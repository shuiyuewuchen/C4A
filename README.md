# C4A 技能提交自动评审 — 交付包

## 这是什么

一个能自动评审 C4 技能提交的技能（递归套娃：用技能评审技能）。

## 文件清单

| 文件 | 说明 |
|------|------|
| `c4-skill-evaluator.skill` | 可安装的技能包（zip） |
| `c4a-skill-evaluator/` | 技能源码目录（SKILL.md + scripts + references） |
| `方案设计.md` | 架构、评审维度、技术选型理由 |
| `教学说明.md` | 怎么安装、怎么用、输入输出 |
| `真实评审报告.md` | 用技能对 3 份仿真 C4 提交跑出来的报告 |
| `AI日志.md` | 开发全过程的 AI 使用记录 |
| `拿来说明.md` | 从 starter 拿了什么、改了什么、为什么 |
| `samples/` | 3 份仿真 C4 提交（wangfang/liming/zhangwei） |
| `output/` | 最近一次跑出来的报告（.md/.xlsx/.json） |

## 快速体验

```bash
cd c4a-skill-evaluator
python3 scripts/c4_evaluator.py ../samples --out ../output
# 打开 ../output/评审报告.md 看效果
```

## 完成级别（诚实版）

| Level | 状态 | 说明 |
|-------|------|------|
| L1 文件采集 | ✅ 已实现 | `_C4_` 前缀分组、非 C4 文件过滤、版本号识别 |
| L2 完整性检查 | ✅ 已实现 | 5 个必须文件三级判定（✅/⚠️/❌），且按内容充实度加权（空文件/两行文件不能拿满分） |
| L3 质量评审 | ✅ 已实现 | 四维 × 3 check_items，规则引擎，附 LLM 深审钩子 |
| L4 完整报告系统 | 🟡 部分实现 | Markdown 报告 + 排名 + 改进建议 ✅；Excel 详表（需 `pip install openpyxl`）✅；班级仪表板 ✅；**版本进步轨迹对比 ❌（v2）** |

## v2 路线图（未实现，不假装已做）

- WeChat 群文件自动同步（当前需手动下载到文件夹）
- PDF/DOCX 内容解析（当前只读 .md/.py/.txt）
- v1 vs v2 提交进步轨迹 diff
- LLM 深审的自动化调用（当前靠 Agent 加载 SKILL.md 时自然完成）

## 依赖

- Python 3.9+（必需）
- `openpyxl`（可选，仅用于 Excel 输出；不装也能跑 Markdown 报告）
