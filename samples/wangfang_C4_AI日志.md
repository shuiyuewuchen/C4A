# PDF Summarizer — AI 使用日志

## 使用的 AI 工具

- ChatGPT (GPT-4o)：用于写代码初稿和调试
- Cursor：IDE，内置 Claude 3.5 Sonnet 做代码补全和重构
- 豆包：用于润色说明文档

## Prompt 迭代记录

### v1（初稿）
> "写一个 PDF 摘要脚本"

问题：只给了一个单文件脚本，没有模块化、没有错误处理。

### v2（改进）
> "把上面的脚本重构为模块化，加 argparse、加日志、加 try/except，支持批量文件夹输入"

问题：输出格式硬编码，不能定制。

### v3（最终）
> "再加一个 --template 参数，让用户可以选择 markdown / json / html 三种输出；补全 README 的常见坑部分"

## 迭代次数

- 代码迭代：6 轮（从单文件 → 包结构 → 测试覆盖）
- 文档迭代：3 轮
- 总耗时：约 4 小时（含调试 API 报错）

## 失败经验

- 第一次直接把 PDF 全文塞进 prompt，128k token 直接爆掉 → 后来改成按章节切片
- 忘了处理 `reader.pages[i].extract_text()` 返回 None 的情况 → 加了空值过滤
