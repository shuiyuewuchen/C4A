#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
c4_evaluator.py — C4 技能提交自动评审器（核心引擎）

流水线：
  扫描文件夹 → 按作者分组 → 完整性检查（5 必须文件）→ 四维质量评审 → 生成报告

用法：
  python3 c4_evaluator.py <submission_folder> [--out <output_dir>] [--rubric <rubric.yaml>]

输出：
  - 评审报告.md
  - 评审详表.xlsx
  - eval_summary.json（机器可读）

设计取舍：
  * 纯规则引擎（确定性、可复现、零依赖网络），不调用 LLM。
  * SKILL.md 中说明：当作为 Agent Skill 被调用时，AI 可在本规则引擎输出基础上
    做"二次深审"（对内容做语义判断），形成"规则快筛 + LLM 深审"的混合模式。
  * 这样既保证可在命令行一键跑（Bronze/Silver/Gold 自动化），又不牺牲深度。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 0. 常量：与 references/c4_rubric.yaml 保持一致（脚本内置一份默认，避免强依赖 pyyaml）
# ---------------------------------------------------------------------------

REQUIRED_DELIVERABLES: dict[str, dict[str, Any]] = {
    "skill_doc": {
        "label_cn": "Skill 说明文档",
        "filename_patterns": ["skill说明", "skill_doc", "skill-doc", "skill_description", "说明文档"],
        "content_signals": ["使用场景", "输入", "输出", "解决什么问题", "use case", "input", "output"],
        "preferred_ext": [".md", ".pdf", ".docx", ".txt"],
    },
    "executable_content": {
        "label_cn": "可执行内容",
        "filename_patterns": ["技能", "skill", "evaluator", ".skill"],
        "content_signals": ["```", "def ", "class ", "import ", "name:", "workflow", "pipeline"],
        "preferred_ext": [".skill", ".py", ".md", ".zip", ".js", ".sh"],
    },
    "demo": {
        "label_cn": "Demo（视频/截图）",
        "filename_patterns": ["demo", "演示", "截图", "screen", "录屏"],
        "content_signals": [],
        "preferred_ext": [".mp4", ".mov", ".webm", ".png", ".jpg", ".jpeg", ".gif"],
        "weak_ext": [".md", ".txt"],  # demo说明类文档算弱匹配
    },
    "teaching_doc": {
        "label_cn": "教学说明",
        "filename_patterns": ["教学说明", "教学", "tutorial", "teaching", "上手指南", "quickstart", "how-to", "使用说明"],
        "content_signals": ["上手", "步骤", "常见坑", "安装", "注意事项", "getting started", "step by step"],
        "preferred_ext": [".md", ".pdf", ".docx", ".txt"],
    },
    "ai_log": {
        "label_cn": "AI 生成日志",
        "filename_patterns": ["AI日志", "AI_log", "ai-log", "ai_日志", "AI使用"],
        "content_signals": ["使用的 AI", "AI 工具", "prompt", "迭代次数", "迭代", "ChatGPT", "Claude", "DeepSeek", "Cursor"],
        "preferred_ext": [".md", ".pdf", ".docx", ".txt"],
    },
}

QUALITY_CRITERIA: dict[str, dict[str, Any]] = {
    "reusable": {
        "label_cn": "可复用",
        "weight": 0.25,
        "positive_signals": ["安装", "install", "环境要求", "requirements", "dependencies",
                              "pip install", "npm install", "兼容", "compatible", "依赖"],
        "negative_signals": ["/Users/", "/home/", "C:\\\\", "我的电脑", "my_secret",
                             "api_key =", "api_key=", "我的路径"],
        "check_items": [
            "Has installation instructions",
            "No hardcoded absolute paths",
            "Environment requirements listed",
        ],
    },
    "executable": {
        "label_cn": "可执行",
        "weight": 0.25,
        "positive_signals": ["```python", "```bash", "```javascript", "def ", "class ",
                              "name:", "workflow", "pipeline", "python3 ", "bash "],
        "check_items": [
            "Contains runnable code / prompt / workflow",
            "Skill package structure looks valid (frontmatter / entrypoint)",
            "No obvious syntax red flags",
        ],
    },
    "verifiable": {
        "label_cn": "可验证",
        "weight": 0.25,
        "positive_signals": ["测试", "test", "example", "示例", "预期", "expected",
                             "demo", "result", "结果", "输出示例"],
        "check_items": [
            "Has test cases or examples",
            "Expected output is defined",
            "Demo shows real results",
        ],
    },
    "clear_io": {
        "label_cn": "IO 明确",
        "weight": 0.25,
        "positive_signals": ["输入", "输出", "input", "output", "→", "接受", "返回",
                             "generates", "produces", "returns"],
        "io_pattern": r"输入[^。\n]{0,40}输出|input[^。\n]{0,40}output|接受[^。\n]{0,40}返回|给定[^。\n]{0,40}得到",
        "check_items": [
            "'输入X，输出Y' one-liner present",
            "Input types / formats specified",
            "Output types / formats specified",
        ],
    },
}

# 二进制/大文件只读文件名，不读内容
BINARY_EXT = {".mp4", ".mov", ".webm", ".png", ".jpg", ".jpeg", ".gif",
              ".zip", ".skill", ".pyc", ".pdf", ".docx", ".pptx", ".xlsx"}
MAX_TEXT_BYTES = 200_000  # 文本文件最多读 200KB

# ---------------------------------------------------------------------------
# 1. 数据结构
# ---------------------------------------------------------------------------

@dataclass
class FileInfo:
    path: Path
    rel_path: str
    ext: str
    size: int
    author_hint: str = ""
    version: str = "v1"
    content_text: str = ""  # 文本类文件才填充


@dataclass
class AuthorSubmission:
    author: str
    files: list[FileInfo] = field(default_factory=list)
    completeness: dict[str, dict[str, Any]] = field(default_factory=dict)
    quality: dict[str, dict[str, Any]] = field(default_factory=dict)
    completeness_score: float = 0.0
    quality_score: float = 0.0
    composite_score: float = 0.0
    suggestions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 2. 扫描 + 作者识别
# ---------------------------------------------------------------------------

def _read_text_safely(p: Path) -> str:
    if p.suffix.lower() in BINARY_EXT:
        return ""
    try:
        if p.stat().st_size > MAX_TEXT_BYTES:
            return p.read_text(encoding="utf-8", errors="ignore")[:MAX_TEXT_BYTES]
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            return p.read_text(encoding="gbk", errors="ignore")
        except Exception:
            return ""


def _extract_author(fname: str) -> tuple[str, str]:
    """
    从文件名提取作者与版本。
    规则：
      1) 第一个 '_C4_' 之前的部分 = 作者
      2) 文件名中匹配 _vN = 版本号
    返回 (author, version)。识别不到返回 ("Unknown", "v1")。
    """
    stem = Path(fname).stem
    # 先抽版本
    m_ver = re.search(r"[_\- ]v(\d+)", stem, re.IGNORECASE)  # noqa: W605
    version = f"v{m_ver.group(1)}" if m_ver else "v1"
    # 抽作者
    if "_C4_" in stem:
        author = stem.split("_C4_", 1)[0].strip("._- ")
        return (author or "Unknown", version)
    # 回退：如果含 C4 字样
    if "C4" in stem:
        author = re.split(r"[_\-\s]C4", stem, maxsplit=1)[0].strip("._- ")
        return (author or "Unknown", version)
    return ("Unknown", version)


def scan_folder(root: Path) -> dict[str, AuthorSubmission]:
    """递归扫描，按作者分组。"""
    groups: dict[str, AuthorSubmission] = {}
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if fn.startswith(".") or fn.startswith("__"):
                continue
            full = Path(dirpath) / fn
            rel = str(full.relative_to(root))
            author, version = _extract_author(fn)
            # 作者分组：优先文件名；若 Unknown，回退到一级子目录名
            if author == "Unknown":
                sub = Path(rel).parts[0] if len(Path(rel).parts) > 1 else "Unknown"
                if sub not in (".", ""):
                    author = sub
            fi = FileInfo(
                path=full,
                rel_path=rel,
                ext=full.suffix.lower(),
                size=full.stat().st_size,
                author_hint=author,
                version=version,
            )
            g = groups.setdefault(author, AuthorSubmission(author=author))
            g.files.append(fi)
    # 对每组：文本文件读内容
    for g in groups.values():
        for f in g.files:
            f.content_text = _read_text_safely(f.path)
    return groups


# ---------------------------------------------------------------------------
# 3. 完整性检查
# ---------------------------------------------------------------------------

def _filename_match(patterns: list[str], fname: str) -> bool:
    low = fname.lower()
    return any(p.lower() in low for p in patterns)


def _content_match(signals: list[str], text: str) -> bool:
    if not signals:
        return False
    low = text.lower()
    return any(s.lower() in low for s in signals)


def check_completeness(sub: AuthorSubmission) -> None:
    """对每个必须文件，找到最佳匹配文件，标记 ✅/⚠️/❌。"""
    result: dict[str, dict[str, Any]] = {}
    for key, spec in REQUIRED_DELIVERABLES.items():
        best_strong = None   # 文件名命中 + 扩展名首选 + 内容命中
        best_weak = None     # 文件名命中但扩展名弱
        for f in sub.files:
            fname = f.path.name
            fn_hit = _filename_match(spec["filename_patterns"], fname)
            ct_hit = _content_match(spec["content_signals"], f.content_text) if spec["content_signals"] else False
            ext_pref = f.ext in spec["preferred_ext"]
            ext_weak = f.ext in spec.get("weak_ext", [])
            if fn_hit and ext_pref:
                if ct_hit or not spec["content_signals"]:
                    best_strong = (f, "filename+content")
                    break
                elif best_weak is None:
                    best_weak = (f, "filename-only")
            elif fn_hit and ext_weak and best_weak is None:
                best_weak = (f, "weak-ext")
            elif ct_hit and ext_pref and best_strong is None:
                best_strong = (f, "content-only")

        if best_strong is not None:
            f, mtype = best_strong
            status = "✅" if mtype != "content-only" else "⚠️"
            matched = f.rel_path if mtype != "content-only" else f"{f.rel_path}（仅内容命中）"
        elif best_weak is not None:
            f, mtype = best_weak
            status = "⚠️"
            matched = f"{f.rel_path}（弱匹配：{mtype}）"
        else:
            status = "❌"
            matched = "—"
            mtype = "none"
        result[key] = {
            "label": spec["label_cn"],
            "status": status,
            "matched": matched,
            "match_type": mtype,
        }
    sub.completeness = result
    present = sum(1 for v in result.values() if v["status"] == "✅")
    partial = sum(1 for v in result.values() if v["status"] == "⚠️")
    sub.completeness_score = (present + 0.5 * partial) / 5.0


# ---------------------------------------------------------------------------
# 4. 质量评审（四维）
# ---------------------------------------------------------------------------

def _collect_all_text(sub: AuthorSubmission) -> str:
    """把该作者所有文本内容拼起来，作为质量评审的语料。"""
    import re as _re
    parts = []
    for f in sub.files:
        if not f.content_text:
            continue
        t = f.content_text
        # 去掉 URL，避免 example.com 之类误命中
        t = _re.sub(r"https?://\S+", " ", t)
        t = _re.sub(r"www\.\S+", " ", t)
        parts.append(t)
    return "\n\n".join(parts)


def evaluate_quality(sub: AuthorSubmission) -> None:
    corpus = _collect_all_text(sub)
    low = corpus.lower()
    result: dict[str, dict[str, Any]] = {}
    total = 0.0

    for key, spec in QUALITY_CRITERIA.items():
        hits: list[str] = []
        # 正向信号命中
        pos_hits = [s for s in spec["positive_signals"] if s.lower() in low]
        # 负向信号命中
        neg_hits = [s for s in spec.get("negative_signals", []) if s.lower() in low]
        # IO 专用正则
        if key == "clear_io" and "io_pattern" in spec:
            if re.search(spec["io_pattern"], corpus, re.IGNORECASE):
                hits.append("io_pattern")

        # 判定每个 check_item
        passed_items: list[str] = []
        if key == "reusable":
            if any(s in low for s in ["安装", "install", "pip", "依赖", "requirements", "快速开始", "quickstart"]):
                passed_items.append("Has installation instructions")
            if not neg_hits:
                passed_items.append("No hardcoded absolute paths")
            if any(s in low for s in ["环境要求", "requirements", "dependencies", "依赖", "python 3", "python3"]):
                passed_items.append("Environment requirements listed")
        elif key == "executable":
            if any(s in low for s in ["```", "def ", "class ", "import ", "workflow", "pipeline", "name:"]):
                passed_items.append("Contains runnable code / prompt / workflow")
            if re.search(r"---\s*\nname:", corpus) or any(f.ext == ".skill" for f in sub.files):
                passed_items.append("Skill package structure looks valid")
            # 简单语法红旗：未闭合代码块
            if corpus.count("```") % 2 == 0:
                passed_items.append("No obvious syntax red flags")
        elif key == "verifiable":
            if any(s in low for s in ["测试", "test", "示例", "example", "样例"]):
                passed_items.append("Has test cases or examples")
            if any(s in low for s in ["预期", "expected", "应输出", "输出应为", "expected output"]):
                passed_items.append("Expected output is defined")
            if any(f.ext in {".mp4", ".mov", ".png", ".jpg", ".gif"} for f in sub.files):
                passed_items.append("Demo shows real results")
        elif key == "clear_io":
            if hits:  # io_pattern 命中
                passed_items.append("'输入X，输出Y' one-liner present")
            if any(s in low for s in ["输入", "input"]):
                passed_items.append("Input types / formats specified")
            if any(s in low for s in ["输出", "output", "报告", "report"]):
                passed_items.append("Output types / formats specified")

        n = len(passed_items)
        if n >= 2:
            rating = "✅"
            score = 1.0
        elif n == 1:
            rating = "⚠️"
            score = 0.5
        else:
            rating = "❌"
            score = 0.0
        total += score

        evidence = []
        if pos_hits:
            evidence.append(f"正向信号命中 {len(pos_hits)} 个: {', '.join(pos_hits[:5])}")
        if neg_hits:
            evidence.append(f"⚠️ 负向信号: {', '.join(neg_hits)}")
        evidence.append(f"通过 {n}/{len(spec['check_items'])} 项检查")

        result[key] = {
            "label": spec["label_cn"],
            "rating": rating,
            "score": score,
            "evidence": evidence,
            "passed_items": passed_items,
            "weight": spec["weight"],
        }

    sub.quality = result
    sub.quality_score = total / 4.0
    # 综合分：完整性 0.4 + 质量 0.6
    sub.composite_score = round(sub.completeness_score * 0.4 + sub.quality_score * 0.6, 3)


# ---------------------------------------------------------------------------
# 5. 改进建议生成
# ---------------------------------------------------------------------------

def gen_suggestions(sub: AuthorSubmission) -> list[str]:
    sug: list[str] = []
    for key, info in sub.completeness.items():
        if info["status"] == "❌":
            sug.append(f"❌ 缺失【{info['label']}】：请补充对应文件（命名含 {key} 关键词）")
        elif info["status"] == "⚠️":
            sug.append(f"⚠️ 【{info['label']}】仅弱匹配：请确认该文件是否真的覆盖该交付物")
    for key, info in sub.quality.items():
        if info["rating"] == "❌":
            sug.append(f"💡 质量维度【{info['label']}】不达标：{_quality_hint(key)}")
        elif info["rating"] == "⚠️":
            sug.append(f"💡 质量维度【{info['label']}】部分达标：{_quality_hint(key)}")
    return sug


def _quality_hint(key: str) -> str:
    return {
        "reusable": "补充安装步骤、依赖列表；移除本机绝对路径与硬编码密钥",
        "executable": "提供可运行脚本/工作流；补全 SKILL.md 的 YAML frontmatter",
        "verifiable": "添加示例输入与预期输出；附 demo 截图或测试用例",
        "clear_io": "用一句话写清『输入 X → 输出 Y』，并注明类型/格式",
    }.get(key, "")


# ---------------------------------------------------------------------------
# 6. 报告生成
# ---------------------------------------------------------------------------

def render_markdown_report(subs: list[AuthorSubmission], root: Path) -> str:
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n = len(subs)
    n_complete = sum(1 for s in subs if s.completeness_score >= 0.99)
    n_partial = sum(1 for s in subs if 0.4 <= s.completeness_score < 0.99)
    avg_q = sum(s.quality_score for s in subs) / n if n else 0
    avg_c = sum(s.composite_score for s in subs) / n if n else 0

    lines: list[str] = []
    lines.append("# C4 提交自动评审报告")
    lines.append("")
    lines.append(f"- 生成时间：{now}")
    lines.append(f"- 扫描路径：`{root}`")
    lines.append(f"- 识别提交：**{n}** 位作者，共 **{sum(len(s.files) for s in subs)}** 个文件")
    lines.append(f"- 评审引擎：c4_evaluator.py v1.0（规则引擎）")
    lines.append("")
    lines.append("## 一、班级总览")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总提交人数 | {n} |")
    lines.append(f"| 完整提交（5/5） | {n_complete} |")
    lines.append(f"| 部分提交（3-4/5） | {n_partial} |")
    lines.append(f"| 严重缺失（<3/5） | {n - n_complete - n_partial} |")
    lines.append(f"| 平均质量分 | {avg_q:.2f} / 1.00 |")
    lines.append(f"| 平均综合分 | {avg_c:.2f} / 1.00 |")
    lines.append("")

    # 最常见缺失
    missing_count: dict[str, int] = {}
    for s in subs:
        for k, v in s.completeness.items():
            if v["status"] == "❌":
                missing_count[k] = missing_count.get(k, 0) + 1
    if missing_count:
        weakest = sorted(missing_count.items(), key=lambda x: -x[1])[0]
        lines.append(f"- 最常见缺失：**{REQUIRED_DELIVERABLES[weakest[0]]['label_cn']}**（{weakest[1]}/{n} 人缺失）")
    # 最弱质量维度
    qsum: dict[str, float] = {}
    for s in subs:
        for k, v in s.quality.items():
            qsum[k] = qsum.get(k, 0) + v["score"]
    if qsum:
        weak_q = sorted(qsum.items(), key=lambda x: x[1])[0]
        lines.append(f"- 最弱质量维度：**{QUALITY_CRITERIA[weak_q[0]]['label_cn']}**（均分 {weak_q[1]/n:.2f}）")
    lines.append("")

    # 排名
    lines.append("## 二、综合排名")
    lines.append("")
    lines.append("| 排名 | 作者 | 完整性 | 质量分 | 综合分 |")
    lines.append("|------|------|--------|--------|--------|")
    ranked = sorted(subs, key=lambda s: -s.composite_score)
    for i, s in enumerate(ranked, 1):
        lines.append(f"| {i} | {s.author} | {s.completeness_score*5:.1f}/5 | {s.quality_score:.2f} | **{s.composite_score:.2f}** |")
    lines.append("")

    # 作者详情
    lines.append("## 三、作者详情")
    for s in ranked:
        lines.append("")
        lines.append(f"### {s.author}")
        lines.append("")
        lines.append("**完整性检查：**")
        lines.append("")
        lines.append("| 文件 | 状态 | 匹配文件 |")
        lines.append("|------|------|----------|")
        for k, v in s.completeness.items():
            lines.append(f"| {v['label']} | {v['status']} | {v['matched']} |")
        lines.append("")
        lines.append("**质量评审：**")
        lines.append("")
        lines.append("| 条件 | 评级 | 依据 |")
        lines.append("|------|------|------|")
        for k, v in s.quality.items():
            evidence = "；".join(v["evidence"])
            lines.append(f"| {v['label']} | {v['rating']} | {evidence} |")
        lines.append("")
        lines.append("**改进建议：**")
        if s.suggestions:
            for sug in s.suggestions:
                lines.append(f"- {sug}")
        else:
            lines.append("- 无明显问题，可作为标杆提交。")
        lines.append("")
        lines.append("---")
    return "\n".join(lines)


def write_excel(subs: list[AuthorSubmission], out_path: Path) -> None:
    try:
        from openpyxl import Workbook
    except ImportError:
        print("[warn] openpyxl 未安装，跳过 Excel 输出。pip install openpyxl 即可启用。", file=sys.stderr)
        return
    wb = Workbook()
    ws = wb.active
    ws.title = "总览"
    ws.append(["作者", "完整文件数", "完整率", "可复用", "可执行", "可验证", "IO明确",
               "均分", "综合分", "缺失项"])
    for s in sorted(subs, key=lambda x: -x.composite_score):
        missing = [v["label"] for v in s.completeness.values() if v["status"] == "❌"]
        ws.append([
            s.author,
            int(round(s.completeness_score * 5)),
            round(s.completeness_score, 2),
            s.quality.get("reusable", {}).get("rating", ""),
            s.quality.get("executable", {}).get("rating", ""),
            s.quality.get("verifiable", {}).get("rating", ""),
            s.quality.get("clear_io", {}).get("rating", ""),
            round(s.quality_score, 2),
            s.composite_score,
            "、".join(missing),
        ])
    wb.save(out_path)


# ---------------------------------------------------------------------------
# 7. 主流程
# ---------------------------------------------------------------------------

def run(folder: Path, out_dir: Path) -> dict[str, Any]:
    if not folder.exists():
        raise SystemExit(f"[error] 文件夹不存在: {folder}")
    groups = scan_folder(folder)
    # 过滤掉空组 / 纯 Unknown 且无 C4 标记的
    subs: list[AuthorSubmission] = []
    for author, sub in groups.items():
        # 至少有一个文件名含 C4 标记或子目录就是作者目录
        has_c4 = any("_C4_" in f.path.name or "C4" in f.path.name for f in sub.files)
        if author == "Unknown" and not has_c4:
            continue
        check_completeness(sub)
        evaluate_quality(sub)
        sub.suggestions = gen_suggestions(sub)
        subs.append(sub)

    out_dir.mkdir(parents=True, exist_ok=True)
    md = render_markdown_report(subs, folder)
    md_path = out_dir / "评审报告.md"
    md_path.write_text(md, encoding="utf-8")

    xlsx_path = out_dir / "评审详表.xlsx"
    write_excel(subs, xlsx_path)

    summary = {
        "generated_at": _dt.datetime.now().isoformat(),
        "folder": str(folder),
        "n_authors": len(subs),
        "authors": [
            {
                "author": s.author,
                "completeness_score": s.completeness_score,
                "quality_score": s.quality_score,
                "composite_score": s.composite_score,
            }
            for s in sorted(subs, key=lambda x: -x.composite_score)
        ],
    }
    (out_dir / "eval_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="C4 技能提交自动评审器")
    ap.add_argument("folder", help="包含 C4 提交的本地文件夹路径")
    ap.add_argument("--out", default="./output", help="报告输出目录（默认 ./output）")
    args = ap.parse_args()
    summary = run(Path(args.folder).resolve(), Path(args.out).resolve())
    print(f"[ok] 评审完成：{summary['n_authors']} 位作者")
    print(f"     报告输出到：{Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
