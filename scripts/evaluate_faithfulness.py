"""
P4 生成质量量化（faithfulness）：抽样金标题 → 答案拆成句级论断 → LLM 评审逐条
在引用资料里找支撑（supported / not_supported / contradicted）→ 与规则引用核验对照。

规则层（_verify_citations）只查编号存在性，本脚本量它看不见的部分：编号没错但
内容没依据的"漏检"。产出 eval/faithfulness.json（总忠实率 + 分类别 + 分歧样本清单）。

用法：先起服务，再
  python -X utf8 scripts/evaluate_faithfulness.py
"""

import json
import os
import re
import sys
import time
import uuid

import requests
from openai import OpenAI

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app.config import settings  # noqa: E402

BASE = os.environ.get("RAG_BASE", "http://127.0.0.1:8000")
HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, "..", "eval", "golden_set.json")
OUT = os.path.join(HERE, "..", "eval", "faithfulness.json")

# 抽样方案：每类取前 2 题（multi_turn 取 3，含会话内拒答题）
SAMPLE_PLAN = {"direct": 2, "paraphrase": 2, "adversarial": 2,
               "multihop": 2, "ocr": 2, "multi_turn": 3}

JUDGE_PROMPT = """你是严格的答案忠实度评审。下面给出一个问题、检索到的编号资料、以及从回答中拆出的论断列表。
对每条论断判定其内容能否仅凭资料得出：
- supported：资料可直接支撑（允许同义转述与简单换算）
- not_supported：资料中没有该信息的依据
- contradicted：与资料内容矛盾
只输出 JSON 数组，每项形如 {{"id": 0, "verdict": "supported", "where": "资料2", "reason": "≤20字"}}。
where 在 not_supported 时为 null。不要输出其他文字。

问题：{question}

{sources}

论断列表：
{claims}
"""

CITE_LINE_RE = re.compile(r"^[（(]?\s*(引用(资料)?(编号)?|参考资料|来源)[：:]")


def split_claims(answer):
    body = []
    for line in re.split(r"\n+", answer):
        line = line.strip()
        if not line or CITE_LINE_RE.match(line):
            continue
        line = re.sub(r"\[资料\d+\]", "", line)  # 行内引用标记不参与语义
        for seg in re.split(r"(?<=[。！？；])", line):
            seg = seg.strip(" \t-—*0.123456789.、")
            if len(seg) >= 6:
                body.append(seg)
    return body


def post_query(payload):
    for attempt in range(3):
        try:
            r = requests.post(f"{BASE}/api/v1/chat/query", json=payload, timeout=300)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, OSError):
            if attempt == 2:
                raise
            time.sleep(3)


def run_case(case):
    turns = case.get("turns") or [case["question"]]
    sid = str(uuid.uuid4()) if len(turns) > 1 else None
    for t in turns[:-1]:
        post_query({"question": t, "session_id": sid, "use_history": True})
    return post_query({"question": turns[-1], "session_id": sid,
                       "use_history": sid is not None})


def judge(client, question, answer, sources):
    claims = split_claims(answer)
    if not claims:
        return [], True  # 拒答/空答案：无可核验论断，视为通过
    src_text = "\n\n".join(
        f"资料{i + 1}（{s['filename']}）：{s['content'][:900]}"
        for i, s in enumerate(sources))
    claim_text = "\n".join(f"{i}: {c}" for i, c in enumerate(claims))
    prompt = JUDGE_PROMPT.format(question=question, sources=src_text, claims=claim_text)
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0)
            raw = (resp.choices[0].message.content or "").strip()
            raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.M).strip()
            verdicts = json.loads(raw)
            return [{"claim": claims[v["id"]], **{k: v.get(k) for k in
                     ("verdict", "where", "reason")}}
                    for v in verdicts if 0 <= v.get("id", -1) < len(claims)], False
        except Exception as e:
            if attempt == 2:
                print(f"    评审失败({e})，该题记为 skipped")
                return [{"claim": c, "verdict": "skipped"} for c in claims], False
            time.sleep(3)


def main():
    with open(GOLDEN, encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    picked = []
    for cat, k in SAMPLE_PLAN.items():
        picked += [c for c in cases if c.get("category") == cat][:k]

    client = OpenAI(base_url=settings.OPENAI_API_BASE,
                    api_key=settings.OPENAI_API_KEY, timeout=180)
    rows = []
    for c in picked:
        q = (c.get("turns") or [c["question"]])[-1]
        d = run_case(c)
        verdicts, refusal = judge(client, q, d["answer"], d["sources"])
        n_ok = sum(1 for v in verdicts if v["verdict"] == "supported")
        n_bad = sum(1 for v in verdicts if v["verdict"] in
                    ("not_supported", "contradicted"))
        cite = next(s["detail"] for s in d["trace"] if s["step"] == "citation")
        rows.append({
            "question": q, "category": c.get("category"), "expect": c.get("expect"),
            "answer": d["answer"][:300], "refusal_only": refusal,
            "claims_total": len(verdicts), "supported": n_ok, "unsupported": n_bad,
            "rule_clean": cite.get("mode") == "ok",
            "rule_citation": cite, "verdicts": verdicts,
        })
        tag = "拒答" if refusal else f"{n_ok}/{len(verdicts)} 有据"
        print(f"  [{tag}] ({c.get('category')}) {q[:26]}")
        if not refusal:
            for v in verdicts:
                if v["verdict"] in ("not_supported", "contradicted"):
                    print(f"      ⚠ {v['verdict']}: {v['claim'][:50]} | {v.get('reason', '')}")

    checked = [r for r in rows if not r["refusal_only"] and r["claims_total"]]
    tot = sum(r["claims_total"] for r in checked)
    bad = sum(r["unsupported"] for r in checked)
    summary = {
        "sampled": len(rows), "cases_with_claims": len(checked),
        "claims_total": tot, "claims_supported": tot - bad,
        "faithfulness": round((tot - bad) / tot, 3) if tot else None,
        "rule_gap_cases": [r["question"] for r in checked if r["unsupported"]],
        "by_category": {},
    }
    for cat in sorted({r["category"] for r in checked}):
        sub = [r for r in checked if r["category"] == cat]
        t = sum(x["claims_total"] for x in sub)
        b = sum(x["unsupported"] for x in sub)
        summary["by_category"][cat] = {"claims": t,
                                       "faithfulness": round((t - b) / t, 3)}
    print("\n汇总:", json.dumps(summary, ensure_ascii=False))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": rows}, f, ensure_ascii=False, indent=1)
    print(f"写入 {os.path.relpath(OUT, HERE)}")


if __name__ == "__main__":
    main()
