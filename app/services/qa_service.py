"""
最小可用问答服务：检索 → 上下文构建 → 生成（LLM可选/抽取式回退）+ 会话记忆
"""

import json
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.bm25_index import bm25_index
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是企业知识库问答助手。只根据提供的参考资料回答；"
    "资料中没有的内容要明确说明不知道。回答末尾标注引用的资料编号。"
)

HISTORY_ROUNDS = 6  # 参与 prompt 的最近消息条数


class QAService:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._store_file = os.path.join(settings.DOCUMENT_STORAGE_PATH, "sessions.json")
        self._load_sessions()

    # ---------- 会话记忆 ----------

    def _load_sessions(self):
        try:
            if os.path.exists(self._store_file):
                with open(self._store_file, "r", encoding="utf-8") as f:
                    self.sessions = json.load(f)
        except Exception:
            logger.exception("加载会话历史失败，从空会话开始")
            self.sessions = {}

    def _save_sessions(self):
        try:
            os.makedirs(settings.DOCUMENT_STORAGE_PATH, exist_ok=True)
            tmp = self._store_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.sessions, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self._store_file)
        except Exception:
            logger.exception("保存会话历史失败")

    def _append_message(self, session_id: str, question: str, answer: str,
                        sources: List[Dict[str, Any]]):
        now = datetime.now().isoformat()
        session = self.sessions.get(session_id)
        if session is None:
            session = {
                "id": session_id,
                "title": question[:30],
                "created_at": now,
                "updated_at": now,
                "messages": [],
            }
            self.sessions[session_id] = session
        session["messages"].append({"role": "user", "content": question, "timestamp": now})
        session["messages"].append({
            "role": "assistant", "content": answer, "timestamp": now,
        })
        session["updated_at"] = now

    # ---------- 问答主流程 ----------

    async def query(self, question: str, session_id: Optional[str] = None,
                    use_history: bool = True) -> Dict[str, Any]:
        import time
        t_total = time.perf_counter()
        trace: List[Dict[str, Any]] = []

        def _step(name: str, t0: float, **detail):
            trace.append({
                "step": name,
                "ms": round((time.perf_counter() - t0) * 1000, 1),
                "detail": detail,
            })

        # 0. 查询改写（多轮指代消解）
        t0 = time.perf_counter()
        search_query, rw_detail = await self._rewrite_query(
            question, session_id, use_history)
        _step("query_rewrite", t0, **rw_detail)

        # 1. 混合检索（向量语义 + BM25关键词，RRF融合），扩召回供重排
        pool = settings.RERANK_CANDIDATES if settings.LLM_RERANK else settings.SEARCH_K
        t0 = time.perf_counter()
        vec_results = await vector_store.search_similar(search_query, k=pool)
        bm25_results = (bm25_index.search(search_query, k=pool)
                        if settings.HYBRID_BM25 else [])
        results = self._rrf_merge(vec_results, bm25_results, cap=pool)
        _step("retrieval", t0, query=search_query, k=pool,
              channels={
                  "vector": [{"filename": r["metadata"].get("filename", ""),
                              "score": round(r["score"], 4), "preview": r["content"][:60]}
                             for r in vec_results],
                  "bm25": [{"filename": r["filename"], "score": r["score"],
                            "preview": r["content"][:60]} for r in bm25_results],
              },
              merged=[{"rank": i + 1, "filename": m["metadata"].get("filename", ""),
                       "rrf": m["score"], "vec_score": round(m["vec_score"], 4),
                       "bm25_score": round(m["bm25_score"], 4), "preview": m["content"][:80]}
                      for i, m in enumerate(results)])

        # 1.5 LLM listwise 重排 → 截取 top SEARCH_K
        t0 = time.perf_counter()
        results, rr_detail = await self._llm_rerank(search_query, results)
        _step("rerank", t0, **rr_detail)

        # 2. 上下文构建
        t0 = time.perf_counter()
        context = "\n\n".join(
            f"[资料{i + 1}] (来源: {r['metadata'].get('filename', '未知文档')})\n{r['content']}"
            for i, r in enumerate(results)
        )
        _step("context", t0, chars=len(context), source_count=len(results),
              strategy="top_k_concatenation")

        # 3. 生成
        t0 = time.perf_counter()
        if settings.OPENAI_API_KEY:
            answer, gen_detail = await self._generate_with_llm(
                question, context, session_id, use_history, results)
        else:
            answer = self._extractive_answer(question, results)
            gen_detail = {"mode": "extractive", "reason": "OPENAI_API_KEY 未配置"}
        _step("generation", t0, answer_chars=len(answer), **gen_detail)

        # 4. 写入会话记忆
        t0 = time.perf_counter()
        sid = session_id or str(uuid.uuid4())
        self._append_message(sid, question, answer, results)
        self.sessions[sid]["messages"][-1]["trace"] = trace
        self._save_sessions()
        _step("memory", t0, session_id=sid,
              total_messages=len(self.sessions[sid]["messages"]),
              store=self._store_file)

        trace.append({"step": "total",
                      "ms": round((time.perf_counter() - t_total) * 1000, 1),
                      "detail": {}})

        confidence = max((r["vec_score"] for r in results), default=0.0)

        return {
            "answer": answer,
            "sources": [
                {
                    "content": r["content"],
                    "score": r["score"],
                    "vec_score": round(r["vec_score"], 4),
                    "bm25_score": round(r["bm25_score"], 4),
                    "filename": r["metadata"].get("filename", ""),
                    "doc_id": r["metadata"].get("doc_id", ""),
                }
                for r in results
            ],
            "confidence": round(confidence, 4),
            "session_id": sid,
            "trace": trace,
        }

    @staticmethod
    def _rrf_merge(vec_results: List[Dict], bm25_results: List[Dict],
                   cap: int, rrf_k: int = 60) -> List[Dict[str, Any]]:
        """按名次做倒数排名融合：score = Σ 1/(rrf_k + rank)"""
        items: Dict[str, Dict[str, Any]] = {}
        for rank, r in enumerate(vec_results, 1):
            meta = r["metadata"]
            key = f"{meta.get('doc_id')}_chunk_{meta.get('chunk_index')}"
            it = items.setdefault(key, {"content": r["content"], "metadata": meta,
                                        "vec_score": 0.0, "bm25_score": 0.0, "rrf": 0.0})
            it["vec_score"] = r["score"]
            it["rrf"] += 1.0 / (rrf_k + rank)
        for rank, r in enumerate(bm25_results, 1):
            it = items.setdefault(r["chunk_id"], {
                "content": r["content"],
                "metadata": {"doc_id": r["doc_id"], "filename": r["filename"]},
                "vec_score": 0.0, "bm25_score": 0.0, "rrf": 0.0})
            it["bm25_score"] = r["score"]
            it["rrf"] += 1.0 / (rrf_k + rank)
        merged = sorted(items.values(), key=lambda x: -x["rrf"])[:cap]
        for m in merged:
            m["score"] = round(m["rrf"], 5)
        return merged

    # ---------- LLM 辅助调用 ----------

    async def _llm_chat(self, messages: List[Dict[str, str]],
                        temperature: float = 0.1) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
        )
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()

    async def _rewrite_query(self, question: str, session_id: Optional[str],
                             use_history: bool):
        """有历史时把追问改写成自包含查询（指代消解）；失败或无需改写返回原问题"""
        if not (settings.QUERY_REWRITE and settings.OPENAI_API_KEY
                and use_history and session_id and session_id in self.sessions
                and self.sessions[session_id]["messages"]):
            return question, {"mode": "skipped",
                              "reason": "首轮/无历史/未配置LLM", "rewritten": question}
        history = self.sessions[session_id]["messages"][-HISTORY_ROUNDS:]
        dialog = "\n".join(
            f"{'用户' if m['role'] == 'user' else '助手'}: {m['content'][:200]}"
            for m in history)
        prompt = (
            "根据对话历史，把用户的最新问题改写成一个不依赖历史、可独立检索的查询。"
            "若已自包含则原样输出。只输出查询本身，不要解释。\n\n"
            f"对话历史：\n{dialog}\n\n最新问题：{question}"
        )
        try:
            rewritten = await self._llm_chat(
                [{"role": "user", "content": prompt}], temperature=0.0)
            rewritten = rewritten.strip('"「」').splitlines()[0].strip()
            if rewritten and rewritten != question and len(rewritten) < 200:
                return rewritten, {"mode": "llm", "original": question,
                                   "rewritten": rewritten}
            return question, {"mode": "no_change", "original": question,
                              "rewritten": question}
        except Exception as e:
            logger.exception("查询改写失败，使用原问题检索")
            return question, {"mode": "fallback", "original": question,
                              "rewritten": question, "error": str(e)[:200]}

    async def _llm_rerank(self, query: str, candidates: List[Dict[str, Any]]):
        """LLM listwise 重排：按与问题的相关度对候选排序，截取 top SEARCH_K"""
        before = [c["metadata"].get("filename", "") for c in candidates]
        if not settings.LLM_RERANK:
            return candidates[:settings.SEARCH_K], {"mode": "disabled", "before": before}
        if not settings.OPENAI_API_KEY or len(candidates) <= 1:
            return candidates[:settings.SEARCH_K], {
                "mode": "skipped", "reason": "未配置LLM或候选≤1", "before": before}
        listing = "\n".join(
            f"{i + 1}. {c['content'][:200]}" for i, c in enumerate(candidates))
        prompt = (
            "以下是候选资料片段。请按与问题的相关度从高到低对全部候选重新排序，"
            f"必须输出全部 {len(candidates)} 个编号的 JSON 数组（如 [3,1,5,2,4]），不要其他内容。\n\n"
            f"问题：{query}\n\n候选资料：\n{listing}"
        )
        try:
            raw = await self._llm_chat([{"role": "user", "content": prompt}],
                                       temperature=0.0)
            m = re.search(r"\[[\s\d,]+\]", raw)
            order = json.loads(m.group(0)) if m else None
            n = len(candidates)
            # 容错：模型可能只给出部分排名（如最相关的几条），已列出的置顶、其余按 RRF 原序补齐
            picked = [i for i in (order or []) if isinstance(i, int) and 1 <= i <= n]
            picked = list(dict.fromkeys(picked))
            if not picked:
                raise ValueError(f"重排输出不合法: {raw[:100]}")
            full = picked + [i for i in range(1, n + 1) if i not in picked]
            ranked = [candidates[i - 1] for i in full][:settings.SEARCH_K]
            return ranked, {"mode": "llm", "model": settings.LLM_MODEL,
                            "partial" if len(picked) < n else "full_rank": True,
                            "before": before,
                            "after": [c["metadata"].get("filename", "") for c in ranked]}
        except Exception as e:
            logger.exception("LLM 重排失败，沿用 RRF 顺序")
            return candidates[:settings.SEARCH_K], {
                "mode": "fallback", "before": before,
                "after": before[:settings.SEARCH_K], "error": str(e)[:200]}

    async def _generate_with_llm(self, question: str, context: str,
                                 session_id: Optional[str], use_history: bool,
                                 results: List[Dict[str, Any]]):
        """调用 OpenAI 兼容接口生成回答，失败时回退抽取式。返回 (answer, 生成细节)"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE,
            )

            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            n_history = 0
            if use_history and session_id and session_id in self.sessions:
                for msg in self.sessions[session_id]["messages"][-HISTORY_ROUNDS:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                    n_history += 1
            user_prompt = f"参考资料：\n{context or '（无检索结果）'}\n\n问题：{question}"
            messages.append({"role": "user", "content": user_prompt})

            resp = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.2,
            )
            detail = {
                "mode": "llm",
                "model": settings.LLM_MODEL,
                "base_url": settings.OPENAI_API_BASE,
                "history_messages_used": n_history,
                "prompt_chars": sum(len(m["content"]) for m in messages),
                "prompt_preview": user_prompt[:500],
            }
            answer = resp.choices[0].message.content
            return (answer or self._extractive_answer(question, results)), detail
        except Exception as e:
            logger.exception("LLM 调用失败，回退抽取式回答")
            return (self._extractive_answer(question, results),
                    {"mode": "extractive_fallback", "error": str(e)[:300]})

    def _extractive_answer(self, question: str, results: List[Dict[str, Any]]) -> str:
        if not results:
            return "知识库中未找到与该问题相关的内容。请先上传文档，或配置 OPENAI_API_KEY 以启用自由回答。"
        parts = [f"根据知识库检索到 {len(results)} 条相关资料（未配置 LLM，以下为抽取式回答）：\n"]
        for i, r in enumerate(results):
            fn = r["metadata"].get("filename", "未知文档")
            parts.append(f"[资料{i + 1}]（来源：{fn}，相似度 {r['score']:.2f}）\n{r['content']}\n")
        return "\n".join(parts)

    # ---------- 会话管理 ----------

    async def get_session_history(self, session_id: str) -> Optional[Dict]:
        return self.sessions.get(session_id)

    async def get_all_sessions(self) -> List[Dict]:
        return list(self.sessions.values())

    async def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions()
            return True
        return False

    async def clear_all_sessions(self) -> int:
        n = len(self.sessions)
        self.sessions = {}
        self._save_sessions()
        return n


qa_service = QAService()
