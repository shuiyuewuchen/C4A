# PDF Summarizer 使用教学

## 上手指南（5 分钟跑通）

1. 克隆仓库并安装依赖（见 skill 说明）
2. 设置 `export OPENAI_API_KEY=sk-xxx`
3. 把要处理的 PDF 放进 `./papers/`
4. 运行：`python run.py --input ./papers --output ./out`
5. 打开 `./out/summary.md` 查看结果

## 常见坑

| 坑 | 原因 | 解决 |
|----|------|------|
| 输出全是空 | 扫描版 PDF | 先跑 OCR（如 ocrmypdf） |
| token 超限 | PDF 太长 | 加 `--max-pages 50` |
| 中文摘要夹英文 | 模型默认英文 | 在 prompt 里强制"用中文" |

## 测试用例

- 测试 1：单篇 10 页论文 → 输出应有 TL;DR + 章节要点
- 测试 2：空文件夹 → 应友好报错，不要 traceback
- 测试 3：加密 PDF → 应提示需要密码

## 注意事项

- 不要把 API key 写死在代码里，用环境变量
- 第一次运行会下载 spacy 模型，约 500MB
