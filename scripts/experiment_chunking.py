"""
P2 分块策略离线实验：不起服务、不走 LLM 生成，直接进程内重建语料并跑检索链路。

对每个 (CHUNK_MODE, CHUNK_SIZE) 配置：清空实验向量库 → 重新上传 test_data 语料
（含 make_scan_pdf 生成的扫描件）→ 金标 26 道可答题逐题 hybrid_search(RRF) + ce 重排，
按 evaluate_retrieval 同口径算 hit@1 / hit@4 / MRR 与分类别指标，写 eval/chunk_experiment.json。

用法：python -X utf8 scripts/experiment_chunking.py [--sizes 200,300,500,1000]
"""

import argparse
import asyncio
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
# 与生产环境完全隔离：独立向量库目录 + 独立文档台账（必须在 import app.* 之前设置）
os.environ["CHROMA_PERSIST_DIRECTORY"] = os.path.join(ROOT, "vector_db_exp")
os.environ["DOCUMENT_STORAGE_PATH"] = os.path.join(ROOT, "data_exp")

sys.path.insert(0, ROOT)

from app.config import settings  # noqa: E402
from app.services.document_service import document_service  # noqa: E402
from app.services.qa_service import qa_service  # noqa: E402
from app.services.vector_store import vector_store  # noqa: E402
from app.services.bm25_index import bm25_index  # noqa: E402
from scripts.evaluate_retrieval import best_rank, summarize  # noqa: E402

GOLDEN = os.path.join(ROOT, "eval", "golden_set.json")
OUT = os.path.join(ROOT, "eval", "chunk_experiment.json")


def corpus_files():
    scan = os.path.join(ROOT, "data_exp", "scan_xuanhe.pdf")
    if not os.path.exists(scan):
        from scripts.make_scan_pdf import main as make_scan
        os.makedirs(os.path.dirname(scan), exist_ok=True)
        make_scan(scan)
    files = [os.path.join(ROOT, "test_data", n) for n in
             ("kb_sample.txt", "decoy_zh.txt", "roadmap_zh.txt", "star_editor.txt")]
    return files + [scan]


async def run_config(mode: str, size: int, cases):
    settings.CHUNK_MODE = mode
    settings.CHUNK_SIZE = size
    document_service.text_splitter = document_service._make_splitter()
    # 清空实验集合，重灌语料（PersistentClient 句柄常驻，不删目录只重建集合）
    document_service.documents_db = {}
    await vector_store.recreate_collection()
    bm25_index.build([])
    n_chunks = {}
    for path in corpus_files():
        doc = await document_service.upload_document(
            path, os.path.basename(path), os.path.getsize(path))
        n_chunks[doc.filename] = doc.chunk_count
    rows = []
    for c in cases:
        results, detail = await qa_service.hybrid_search(c["question"])
        rrf_rank = best_rank([m["metadata"].get("filename", "") for m in results],
                             c["expect"])
        ranked, _ = await qa_service._rerank(c["question"], results)
        final_rank = best_rank([r["metadata"].get("filename", "") for r in ranked],
                               c["expect"])
        rows.append({"question": c["question"], "expect": c["expect"],
                     "category": c.get("category"), "rrf_rank": rrf_rank,
                     "final_rank": final_rank})
    return n_chunks, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="200,300,500,1000",
                    help="structure 模式实验的块大小列表")
    args = ap.parse_args()
    sizes = [int(s) for s in args.sizes.split(",")]

    with open(GOLDEN, encoding="utf-8") as f:
        cases = [c for c in json.load(f)["cases"] if c["expect"] is not None]

    configs = [("fixed", settings.CHUNK_SIZE)] + [
        ("structure", s) for s in sizes]
    out = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "rerank_mode": "ce", "configs": []}
    for mode, size in configs:
        t0 = time.perf_counter()
        n_chunks, rows = asyncio.run(run_config(mode, size, cases))
        summary = {
            "mode": mode, "chunk_size": size,
            "chunks_per_doc": n_chunks,
            "rrf": summarize("rrf_rank", rows),
            "ce": summarize("final_rank", rows),
            "by_category_ce": {cat: summarize("final_rank", [r for r in rows
                                        if r["category"] == cat])
                               for cat in sorted({r["category"] for r in rows})},
            "rows": rows,
        }
        out["configs"].append(summary)
        print(f"\n### {mode}@{size} ({time.perf_counter() - t0:.0f}s) "
              f"chunks={n_chunks}")
        print(f"  rrf: {summary['rrf']}")
        print(f"  ce : {summary['ce']}")
        for cat, m in summary["by_category_ce"].items():
            print(f"    [{cat}] hit@1={m['hit@1']} MRR={m['MRR']}")
        moved = [f"  Δ {r['question'][:24]}: {r['rrf_rank']}→{r['final_rank']}"
                 for r in rows if r["final_rank"] != 1]
        print("\n".join(moved) if moved else "  全部 hit@1")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n实验结果已写入 {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
