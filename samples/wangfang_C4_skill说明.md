---
name: pdf-summarizer
description: >
  自动读取 PDF 文件，按章节抽取要点并输出 Markdown 摘要。
  当用户需要批量处理 PDF、提取文档摘要、或把长报告浓缩为结构化笔记时使用。
---

# PDF Summarizer 技能说明

## 解决什么问题

研究生每天要读 10+ 篇论文，但手动做摘要耗时；这个技能把"读 PDF → 输出要点"自动化。

## 使用场景

- 组会前批量读论文，快速生成文献综述初稿
- 把课程讲义 PDF 浓缩成复习提纲
- 长报告 / 年报抽取关键章节

## 输入

- 输入：一个本地文件夹路径（含 .pdf 文件），或单个 PDF 文件路径
- 支持类型：.pdf（文本型，非扫描件）
- 可选参数：max_pages（限制处理页数，默认全部）

## 输出

- 输出：一个 Markdown 文件，包含
  1. 一页一句话总结（TL;DR）
  2. 按章节的要点列表
  3. 关键术语表
  4. 引用建议

## 环境要求

- Python 3.9+
- 依赖：`pip install pypdf openai`
- 需要设置环境变量 `OPENAI_API_KEY`

## 安装步骤

```bash
git clone https://example.com/student/pdf-summarizer.git
cd pdf-summarizer
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## 工作流

```python
import pypdf

def extract_text(pdf_path: str) -> str:
    reader = pypdf.PdfReader(pdf_path)
    return "\n".join(page.extract_text() for page in reader.pages)

def summarize(text: str, client) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"用中文总结：{text[:8000]}"}]
    )
    return resp.choices[0].message.content
```

## 示例

输入：`./papers/attention-is-all-you-need.pdf`
预期输出：`./papers/attention-is-all-you-need.summary.md`，包含 Transformer 的核心贡献、Q/K/V 机制、对比 RNN 的优势三段。

## 常见坑

- 扫描件 PDF 抽不出文字，需要先 OCR
- 超大 PDF 会超 token，要按章节切片
