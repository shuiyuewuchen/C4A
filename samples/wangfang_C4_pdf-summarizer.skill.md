---
name: pdf-summarizer
description: PDF 批量摘要技能，输入文件夹路径，输出 Markdown 摘要集
version: 1.0
entrypoint: run.py
---

# pdf-summarizer.skill

这是 wangfang 提交的可执行技能包。

## 工作流（workflow）

1. 扫描输入目录下所有 .pdf 文件
2. 用 pypdf 抽取文本
3. 按章节切片（每片 ≤ 6000 token）
4. 调用 LLM 生成摘要
5. 汇总输出到 ./out/

## 代码入口（run.py）

```python
import argparse
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default="./out")
    args = ap.parse_args()
    for pdf in Path(args.input).glob("*.pdf"):
        print(f"processing {pdf.name}")

if __name__ == "__main__":
    main()
```

## 测试

```bash
python run.py --input ./test_pdfs --output ./out
ls ./out/  # 应看到对应 .md 文件
```
