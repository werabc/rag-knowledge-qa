"""
L5 检索评估：对 eval/golden_set.json 逐条走 /api/chat/query，从 trace 取
RRF 融合序（rerank 前）与最终 sources 序（rerank 后），分别算 hit@1 / hit@k / MRR。

用法：先起服务，再 python -X utf8 scripts/evaluate_retrieval.py
报告打印到控制台并写入 eval/report.json
"""

import json
import os
import sys
import time

import requests

BASE = os.environ.get("RAG_BASE", "http://127.0.0.1:8000")
HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, "..", "eval", "golden_set.json")
REPORT = os.path.join(HERE, "..", "eval", "report.json")


def rank_of(names, expect):
    for i, n in enumerate(names):
        if n == expect:
            return i + 1
    return None


def evaluate():
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
        rows.append({
            "question": c["question"], "expect": c["expect"],
            "rrf_rank": rank_of(rrf_order, c["expect"]),
            "final_rank": rank_of(final_order, c["expect"]),
            "rerank_mode": trace.get("rerank", {}).get("detail", {}).get("mode"),
            "seconds": round(time.perf_counter() - t0, 1),
        })
        print(f"  [{rows[-1]['final_rank'] or '✗'}] {c['question'][:30]} → {c['expect']}")

    n = len(rows)

    def summarize(key):
        ranks = [x[key] for x in rows]
        hit1 = sum(1 for r in ranks if r == 1) / n
        hitk = sum(1 for r in ranks if r is not None and r <= 4) / n
        mrr = sum(1.0 / r for r in ranks if r) / n
        return {"hit@1": round(hit1, 3), "hit@4": round(hitk, 3), "MRR": round(mrr, 3)}

    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cases": n,
        "retrieval_rrf_only": summarize("rrf_rank"),
        "retrieval_with_rerank": summarize("final_rank"),
        "per_case": rows,
    }
    print("\n== 仅RRF融合 ==", report["retrieval_rrf_only"])
    print("== RRF+LLM重排 ==", report["retrieval_with_rerank"])
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(f"报告已写入 {os.path.relpath(REPORT)}")
    return 0


if __name__ == "__main__":
    sys.exit(evaluate())
