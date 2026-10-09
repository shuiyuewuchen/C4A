#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate.py — 用 samples/expected.json 验证评审器的误判率。

跑法：
  python3 scripts/validate.py

输出：
  - 15 个判定点逐点对照（期望 vs 实际）
  - 误判数与误判率（相邻档不算误判）
  - 排名顺序与分数带校验
"""
import json
import sys
from pathlib import Path

# 直接导入评审器内部
sys.path.insert(0, str(Path(__file__).parent))
from c4_evaluator import scan_folder, check_completeness, evaluate_quality, REQUIRED_DELIVERABLES  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent.parent / "samples"
EXPECTED = SAMPLES / "expected.json"

ORDER = {"❌": 0, "⚠️": 1, "✅": 2}


def close(a: str, b: str) -> bool:
    """相邻档视为一致（容差）。"""
    return abs(ORDER[a] - ORDER[b]) <= 1


def main() -> int:
    exp = json.loads(EXPECTED.read_text(encoding="utf-8"))
    groups = scan_folder(SAMPLES)
    subs = {}
    for author, sub in groups.items():
        # 与 run() 保持一致：过滤无 C4 标记的 Unknown 组
        has_c4 = any("_C4_" in f.path.name or "C4" in f.path.name for f in sub.files)
        if author == "Unknown" and not has_c4:
            continue
        check_completeness(sub)
        evaluate_quality(sub)
        subs[author] = sub

    total = len(exp["cases"])
    errors = []
    rows = []
    for case in exp["cases"]:
        author, key, want = case["author"], case["deliverable"], case["expected"]
        sub = subs.get(author)
        if sub is None:
            errors.append(f"{author}/{key}: 作者未识别")
            actual = "?"
        else:
            actual = sub.completeness.get(key, {}).get("status", "?")
        ok = close(want, actual)
        rows.append((author, key, want, actual, "✅" if ok else "❌ 误判"))
        if not ok:
            errors.append(f"{author}/{key}: 期望 {want}，实际 {actual}")

    print("=" * 72)
    print(f"{'作者':<10}{'交付件':<22}{'期望':<6}{'实际':<6}{'判定'}")
    print("-" * 72)
    for author, key, want, actual, mark in rows:
        label = REQUIRED_DELIVERABLES.get(key, {}).get("label_cn", key)
        print(f"{author:<10}{label:<22}{want:<6}{actual:<6}{mark}")
    print("=" * 72)

    n_err = len(errors)
    print(f"\n判定点总数：{total}")
    print(f"误判数（跨档）：{n_err}")
    print(f"误判率：{n_err/total*100:.1f}%")
    if errors:
        print("\n误判明细：")
        for e in errors:
            print(f"  - {e}")

    # 排名校验
    ranked = sorted(subs.values(), key=lambda s: -s.composite_score)
    actual_order = [s.author for s in ranked]
    expected_order = exp["expected_rank_order"]
    rank_ok = actual_order == expected_order
    print(f"\n排名顺序：期望 {expected_order} / 实际 {actual_order} → {'✅' if rank_ok else '❌'}")

    # 分数带校验
    band_issues = []
    for s in subs.values():
        band = exp["expected_score_bands"].get(s.author)
        if not band:
            continue
        if not (band["composite_min"] <= s.composite_score <= band["composite_max"]):
            band_issues.append(
                f"{s.author}: 综合分 {s.composite_score} 不在期望带 [{band['composite_min']}, {band['composite_max']}]"
            )
    if band_issues:
        print("\n分数带偏离：")
        for b in band_issues:
            print(f"  - {b}")
    else:
        print("分数带：全部落在期望区间内 ✅")

    print("\n" + ("✅ 验证通过" if n_err == 0 and rank_ok and not band_issues else "⚠️ 见上方问题"))
    return 0 if (n_err == 0 and rank_ok and not band_issues) else 1


if __name__ == "__main__":
    sys.exit(main())
