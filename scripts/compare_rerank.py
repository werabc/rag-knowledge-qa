"""
重排通道对照实验：RRF 原序 vs 本地 cross-encoder vs LLM listwise
用法：python -X utf8 scripts/compare_rerank.py [--skip-llm]
进程内直调检索链路，不需要启动服务。输出每题位次 + 三通道 hit@1/hit@4/MRR，
落盘 eval/rerank_compare.json。LLM 通道需要 .env 配置 OPENAI_API_KEY。
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.services import reranker  # noqa: E402
from app.services.qa_service import qa_service  # noqa: E402

GOLDEN = Path(__file__).resolve().parent.parent / "eval" / "golden_set.json"


def rank_of(order, expect):
    for i, fn in enumerate(order, 1):
        if fn == expect:
            return i
    return None


def metrics(rows, key):
    ks = settings.SEARCH_K
    vals = [r[key] for r in rows if r[key] is not None]
    if not vals:
        return {}
    return {
        "n": len(vals),
        "hit@1": round(sum(1 for v in vals if v == 1) / len(vals), 3),
        f"hit@{ks}": round(sum(1 for v in vals if v <= ks) / len(vals), 3),
        "MRR": round(sum(1.0 / v for v in vals) / len(vals), 3),
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-llm", action="store_true")
    args = ap.parse_args()

    cases = [c for c in json.load(open(GOLDEN, encoding="utf-8"))["cases"]
             if c["expect"] is not None]
    rows = []
    t0 = time.perf_counter()
    for c in cases:
        q, expect = c["question"], c["expect"]
        cands, _ = await qa_service.hybrid_search(q)
        rrf_order = [r["metadata"].get("filename", "") for r in cands]
        ce_ranked = await reranker.ce_rerank(q, cands, len(cands))
        ce_order = [r["metadata"].get("filename", "") for r in ce_ranked]
        row = {"question": q, "category": c.get("category", ""), "expect": expect,
               "rrf_rank": rank_of(rrf_order, expect),
               "ce_rank": rank_of(ce_order, expect)}
        if args.skip_llm or not settings.OPENAI_API_KEY:
            row["llm_rank"] = None
        else:
            llm_ranked, _ = await qa_service._llm_rerank(q, cands)
            row["llm_rank"] = rank_of(
                [r["metadata"].get("filename", "") for r in llm_ranked], expect)
        print(f"[{len(rows) + 1}/{len(cases)}] {q[:30]}… "
              f"rrf={row['rrf_rank']} ce={row['ce_rank']} llm={row['llm_rank']}")
        rows.append(row)

    out = {"seconds": round(time.perf_counter() - t0, 1),
           "channels": {"rrf_only": metrics(rows, "rrf_rank"),
                        "cross_encoder": metrics(rows, "ce_rank"),
                        "llm_listwise": metrics(rows, "llm_rank")},
           "ce_model": settings.RERANKER_MODEL,
           "rows": rows}
    dst = Path(__file__).resolve().parent.parent / "eval" / "rerank_compare.json"
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["channels"], ensure_ascii=False, indent=1))
    print("saved ->", dst)


if __name__ == "__main__":
    asyncio.run(main())
