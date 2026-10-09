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
| `output/` | 最近一次跑出来的报告（.md + .xlsx + .json） |

## 快速体验

```bash
cd c4a-skill-evaluator
python3 scripts/c4_evaluator.py ../samples --out ../output
# 打开 ../output/评审报告.md 看效果
```

## 完成级别

- Level 1 文件采集 ✅
- Level 2 完整性检查 ✅
- Level 3 质量评审 ✅
- Level 4 完整报告系统（Markdown + Excel + 排名 + 改进建议）✅
