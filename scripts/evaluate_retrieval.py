"""
L5/G3 检索+回答质量评估：对 eval/golden_set.json 逐条走 /api/v1/chat/query。

通道：RRF 融合序（rerank 前）与最终 sources 序（rerank 后），各算 hit@1 / hit@4 / MRR；
类别拆分（direct/paraphrase/adversarial/multihop）；不可回答题算拒答正确率。

用法：先起服务，再
  python -X utf8 scripts/evaluate_retrieval.py               # 跑评估、写 report.json
  python -X utf8 scripts/evaluate_retrieval.py --update-baseline  # 把当前结果固化为 baseline.json
  python -X utf8 scripts/evaluate_retrieval.py --strict      # 回归门禁：任一核心指标低于 baseline → exit 1
"""

import argparse
import json
import os
import re
import sys
import time

import requests

BASE = os.environ.get("RAG_BASE", "http://127.0.0.1:8000")
HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, "..", "eval", "golden_set.json")
REPORT = os.path.join(HERE, "..", "eval", "report.json")
BASELINE = os.path.join(HERE, "..", "eval", "baseline.json")

REFUSAL_RE = re.compile(
    r"(不知道|无法回答|无法得知|没有找到|未提及|无相关|不清楚|抱歉|未找到|资料中没有|未包含)")


def best_rank(names, expect):
    """expect 为 str 或 list（多跳任一命中）；返回期望文档最好名次，未命中 None"""
    wanted = [expect] if isinstance(expect, str) else (expect or [])
    ranks = [i + 1 for i, n in enumerate(names) if n in wanted]
    return min(ranks) if ranks else None


def evaluate():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="与 baseline.json 对照，回退则退出码 1")
    ap.add_argument("--update-baseline", action="store_true", help="用本次结果覆盖 baseline.json")
    args = ap.parse_args()

    with open(GOLDEN, encoding="utf-8") as f:
        cases = json.load(f)["cases"]

    rows = []
    for c in cases:
        t0 = time.perf_counter()
        r = requests.post(f"{BASE}/api/v1/chat/query", json={
            "question": c["question"], "use_history": False}, timeout=180)
        r.raise_for_status()
        data = r.json()
        trace = {s["step"]: s for s in data["trace"]}
        rrf_order = [m["filename"] for m in trace["retrieval"]["detail"]["merged"]]
        final_order = [s["filename"] for s in data["sources"]]
        expect = c["expect"]
        row = {
            "question": c["question"], "expect": expect,
            "category": c.get("category", "direct"),
            "answer": data["answer"][:200],
            "seconds": round(time.perf_counter() - t0, 1),
        }
        if expect is None:
            row["refused"] = bool(REFUSAL_RE.search(data["answer"]))
            mark = "拒✓" if row["refused"] else "答✗"
        else:
            row["rrf_rank"] = best_rank(rrf_order, expect)
            row["final_rank"] = best_rank(final_order, expect)
            row["rerank_mode"] = trace.get("rerank", {}).get("detail", {}).get("mode")
            mark = row["final_rank"] or "✗"
        rows.append(row)
        print(f"  [{mark}] ({row['category']}) {c['question'][:30]}")

    answerable = [x for x in rows if x["expect"] is not None]
    unanswerable = [x for x in rows if x["expect"] is None]
    n = len(answerable)

    def summarize(key, subset):
        m = len(subset) or 1
        hit1 = sum(1 for x in subset if x.get(key) == 1) / m
        hitk = sum(1 for x in subset if x.get(key) and x[key] <= 4) / m
        mrr = sum(1.0 / x[key] for x in subset if x.get(key)) / m
        return {"hit@1": round(hit1, 3), "hit@4": round(hitk, 3),
                "MRR": round(mrr, 3), "n": m}

    refusal_acc = (sum(1 for x in unanswerable if x["refused"]) / len(unanswerable)
                   if unanswerable else 1.0)

    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cases": len(rows),
        "answerable": n,
        "unanswerable": len(unanswerable),
        "retrieval_rrf_only": summarize("rrf_rank", answerable),
        "retrieval_with_rerank": summarize("final_rank", answerable),
        "refusal_accuracy": round(refusal_acc, 3),
        "by_category": {cat: summarize("final_rank", [x for x in answerable
                                 if x["category"] == cat])
                        for cat in sorted({x["category"] for x in answerable})},
        "per_case": rows,
    }
    print(f"\n== 仅RRF融合 ({n}题) ==", report["retrieval_rrf_only"])
    print(f"== RRF+LLM重排 ({n}题) ==", report["retrieval_with_rerank"])
    print(f"== 拒答正确率 ({len(unanswerable)}题) ==", report["refusal_accuracy"])
    for cat, m in report["by_category"].items():
        print(f"   [{cat}] {m}")
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(f"报告已写入 {os.path.relpath(REPORT)}")

    if args.update_baseline:
        core = _core_metrics(report)
        with open(BASELINE, "w", encoding="utf-8") as f:
            json.dump(core, f, ensure_ascii=False, indent=1)
        print(f"baseline 已更新: {json.dumps(core, ensure_ascii=False)}")
        return 0

    if args.strict:
        if not os.path.exists(BASELINE):
            print("--strict 需要 baseline.json（先 --update-baseline）")
            return 1
        with open(BASELINE, encoding="utf-8") as f:
            base = _flatten(json.load(f))
        cur = _flatten(_core_metrics(report))
        regressions = [f"{p}: {v} → {cur.get(p)}"
                       for p, v in base.items() if cur.get(p, -1) < v - 1e-9]
        if regressions:
            print("\n⛔ 门禁拦截：指标低于基线")
            for r_ in regressions:
                print("   ", r_)
            return 1
        print("\n✅ 门禁通过：无指标低于基线")
    return 0


def _flatten(obj, prefix=""):
    out = {}
    for k, v in obj.items():
        path = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, path + "."))
        else:
            out[path] = v
    return out


def _core_metrics(report):
    return {
        "retrieval_rrf_only": {
            "hit@1": report["retrieval_rrf_only"]["hit@1"],
            "MRR": report["retrieval_rrf_only"]["MRR"]},
        "retrieval_with_rerank": {
            "hit@1": report["retrieval_with_rerank"]["hit@1"],
            "hit@4": report["retrieval_with_rerank"]["hit@4"],
            "MRR": report["retrieval_with_rerank"]["MRR"]},
        "refusal_accuracy": report["refusal_accuracy"],
        "by_category": {c: m["hit@1"] for c, m in report["by_category"].items()},
    }


if __name__ == "__main__":
    sys.exit(evaluate())
