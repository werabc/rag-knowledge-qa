"""
真实语料深度测试：上传 deep_test/corpus/*.md → 逐题跑 /query 验证（期望文档位次、
答案事实子串、耗时）→ 可选并发压测。结果写 deep_test/results.json 并打印汇总。

用法：
  python -X utf8 deep_test/run_deep_test.py            # 上传+串行逐题
  python -X utf8 deep_test/run_deep_test.py --parallel 4   # 附加并发压测
"""
import json
import os
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from evaluate_retrieval import REFUSAL_RE  # noqa: E402
BASE = os.environ.get("RAG_BASE", "http://127.0.0.1:8000")
CORPUS = os.path.join(HERE, "corpus")
QUESTIONS = os.path.join(HERE, "questions.json")
RESULTS = os.path.join(HERE, "results.json")


def upload_corpus():
    docs = {}
    for name in sorted(os.listdir(CORPUS)):
        if not name.endswith((".md", ".txt")):
            continue
        path = os.path.join(CORPUS, name)
        with open(path, "rb") as f:
            r = requests.post(f"{BASE}/api/v1/documents/upload",
                              files={"file": (name, f)}, timeout=1800)
        r.raise_for_status()
        d = r.json()
        docs[name] = d
        print(f"上传 {name}: {d['chunk_count']} 块 status={d['status']}")
    return docs


def ask(q):
    t0 = time.perf_counter()
    r = requests.post(f"{BASE}/api/v1/chat/query",
                      json={"question": q, "use_history": False}, timeout=300)
    r.raise_for_status()
    return r.json(), round(time.perf_counter() - t0, 2)


def rank_of(doc_names, sources):
    for name in doc_names if isinstance(doc_names, list) else [doc_names]:
        ranks = [i + 1 for i, s in enumerate(sources) if s["filename"] == name]
        if ranks:
            return min(ranks)
    return None


def main():
    parallel = int(sys.argv[sys.argv.index("--parallel") + 1]) \
        if "--parallel" in sys.argv else 0
    with open(QUESTIONS, encoding="utf-8") as f:
        qs = json.load(f)["cases"]
    upload_corpus()

    rows = []
    for c in qs:
        d, sec = ask(c["question"])
        srcs = d["sources"]
        if c["expect"] is None:  # 不可回答题：看拒答
            refused = bool(REFUSAL_RE.search(d["answer"]))
            rows.append({"question": c["question"], "category": "unanswerable",
                         "expect": None, "rank": None, "seconds": sec,
                         "fact_ok": refused, "refused": refused,
                         "answer": d["answer"][:160]})
            print(f"  [{'拒✓' if refused else '答✗'}] {c['question'][:34]} {sec}s")
            continue
        rank = rank_of(c["expect"], srcs)
        ac = c.get("answer_contains", [])
        hit_all = all(any(alt in d["answer"] for alt in s.split("|")) for s in ac) if ac else True
        row = {"question": c["question"], "category": c.get("category", "?"),
               "expect": c["expect"], "rank": rank, "seconds": sec,
               "fact_ok": hit_all,
               "answer": d["answer"][:160]}
        rows.append(row)
        mark = f"r{rank}" if rank else "MISS"
        print(f"  [{mark}{'✓' if hit_all else '✗事实'}] ({row['category']}) "
              f"{c['question'][:34]} {sec}s")

    # 并发压测：随机抽 8 题并行打，量吞吐与延迟分布（与检索质量无关，只看服务承载）
    load = None
    if parallel:
        pick = [c["question"] for c in qs[:max(8, parallel * 2)]]
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=parallel) as ex:
            secs = list(ex.map(lambda q: ask(q)[1], pick))
        load = {"workers": parallel, "n": len(pick),
                "wall_s": round(time.perf_counter() - t0, 1),
                "p50": round(statistics.median(secs), 1),
                "p95": round(sorted(secs)[int(len(secs) * 0.95)] if len(secs) > 1 else max(secs), 1),
                "max": round(max(secs), 1), "per_q": secs}
        print(f"\n并发{parallel}×{len(pick)}题: wall={load['wall_s']}s "
              f"p50={load['p50']}s p95={load['p95']}s max={load['max']}s")

    ans_rows = [r for r in rows if r["expect"] is not None]
    un_rows = [r for r in rows if r["expect"] is None]
    n = len(ans_rows) or 1
    hit1 = sum(1 for r in ans_rows if r["rank"] == 1) / n
    hit4 = sum(1 for r in ans_rows if r["rank"] and r["rank"] <= 4) / n
    fact = sum(1 for r in ans_rows if r["fact_ok"]) / n
    refusal = (sum(1 for r in un_rows if r["refused"]) / len(un_rows)) if un_rows else 1.0
    summary = {"n": len(rows), "answerable": len(ans_rows),
               "hit@1": round(hit1, 3), "hit@4": round(hit4, 3),
               "fact_rate": round(fact, 3), "refusal": round(refusal, 3),
               "avg_seconds": round(statistics.mean(r["seconds"] for r in rows), 1),
               "by_category": {}}
    for cat in sorted({r["category"] for r in rows}):
        sub = [r for r in rows if r["category"] == cat]
        if cat == "unanswerable":
            summary["by_category"][cat] = {"n": len(sub),
                                           "refused": sum(1 for r in sub if r["refused"])}
            continue
        summary["by_category"][cat] = {
            "n": len(sub),
            "hit@1": round(sum(1 for r in sub if r["rank"] == 1) / len(sub), 2),
            "fact_ok": sum(1 for r in sub if r["fact_ok"]) }
    print("\n汇总:", json.dumps(summary, ensure_ascii=False))
    with open(RESULTS, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "load": load, "rows": rows},
                  f, ensure_ascii=False, indent=1)
    print(f"结果写入 {os.path.relpath(RESULTS, HERE)}")


if __name__ == "__main__":
    main()
