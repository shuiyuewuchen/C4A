# C4A 开发 AI 日志

> 本日志记录开发 c4-skill-evaluator 全过程中 AI 工具的使用。

## 使用的 AI 工具

- **豆包（Doubao）**：主开发环境。从读题、设计架构、写代码、写文档、跑测试到修 bug 全程在豆包里完成。
- 模型：Doubao 桌面端 Agent 模式（带工具调用能力）。

## 任务拆解过程（多轮对话，非一句话生成）

### Round 1：理解挑战
- Prompt："读一下挑战的原始指引，告诉我这个挑战要交什么、评分标准是什么。"
- 产出：列出 6 个必须交付物、5 个评分维度、4 个 Level。
- 反思：第一次只看了挑战原文，没看 rubric.json 和 starter zip。豆包主动提示我"还要看评分细则和 starter"，于是继续读 rubric.json 和解压 starter。

### Round 2：拆解 starter
- Prompt："读一下 starter 里的 SKILL.md 和 c4_rubric.yaml，总结它已经给了什么、还缺什么。"
- 产出：starter 给了工作流骨架、信号字典、报告模板；缺真正能跑的 Python 代码、缺测试样例、缺 LLM 深审策略。
- 决策：选择"纯规则 Python 脚本 + SKILL.md 指导 Agent 做 LLM 深审"的混合方案。理由是挑战要求"可安装运行"，纯靠 SKILL.md 里的 prompt 不够，必须有确定性代码。

### Round 3：写第一版脚本
- Prompt："按 starter 的工作流，写一个 c4_evaluator.py，实现扫描→分组→完整性→质量→报告。"
- 产出：第一版 ~400 行 Python。
- 问题：跑了一遍发现三个 bug：
  1. `demo说明.md` 被判定为 ❌（因为扩展名不在 preferred_ext）
  2. `github.com/example` 里的 "example" 被误命中为"示例"信号
  3. 可执行内容匹配到了 skill说明.md 而不是真正的 .skill 文件

### Round 4：修 bug（迭代）
- Prompt："跑出来的报告有这几个误判，帮我修：①demo.md 应该算弱匹配 ②URL 里的 example 不该算信号 ③匹配要优先 .skill 扩展名。"
- 产出：
  - 给 demo 加了 `weak_ext` 字段，.md 类 demo 说明算 ⚠️
  - `_collect_all_text` 里加正则把 `https?://...` 和 `www....` 删掉
  - 重写 `check_completeness`，区分 strong/weak 两档匹配

### Round 5：构造测试样例
- Prompt："帮我造 3 份 C4 提交样例：一份优秀（5 文件齐、质量高）、一份部分缺失、一份严重缺失。再放一个非 C4 文件测试过滤。"
- 产出：samples/ 下 9 个文件，覆盖 wangfang（优）、liming（中）、zhangwei（差）+ 课程表（非 C4 干扰项）。

### Round 6：跑真实评审
- Prompt："用脚本跑 samples，看输出对不对。"
- 产出：output/评审报告.md + xlsx + json。
- 验证：排名 wangfang(0.97) > liming(0.47) > zhangwei(0.15)，符合预期。

### Round 7：写文档
- Prompt："写方案设计、教学说明、AI日志、拿来说明。"
- 产出：4 份 Markdown。

## Prompt 优化记录

| 版本 | Prompt | 问题 | 改进 |
|------|--------|------|------|
| v1 | "写个评审器" | 太宽泛，AI 会从零瞎写 | 改为"按 starter 的 SKILL.md 工作流实现" |
| v2 | "修 bug" | 没说具体哪个 bug | 改为贴出误判的具体 case（demo.md 被误判 ❌） |
| v3 | "写文档" | 会写成骨架 | 改为"参考 rubric.json 的 5 个维度，每个维度都要覆盖" |

## 迭代次数

- 代码：2 个版本（v1 初版 → v2 修误判）
- 测试：3 个样例作者 × 5 文件 = 9 个测试文件
- 文档：6 份（方案/教学/AI日志/拿来/SKILL.md/脚本）

## 失败经验

1. **第一版没考虑扩展名优先级**——以为文件名命中就够了，结果把 skill说明.md 误判成可执行内容。教训：完整性检查必须"文件名 + 扩展名 + 内容"三重信号联合判定。
2. **直接拿全文做关键词匹配**——没过滤 URL，导致 zhangwei 的 GitHub 链接里 "example" 命中了"示例"信号，假阳性。教训：评审语料要先做噪声清理。
3. **一开始想写纯 LLM 评审**——写到一半意识到挑战要求"可安装运行"，纯 prompt 方案无法在命令行独立跑，果断切回规则引擎。教训：先看"交付物形态"再选技术栈。

## AI 使用统计

- 总对话轮次：约 12 轮（读题 → 设计 → 写码 → 跑测 → 修 bug → 写文档）
- AI 直接生成的代码行数：~450 行 Python
- 人工改动：约 30 行（主要是修误判逻辑、加注释）
