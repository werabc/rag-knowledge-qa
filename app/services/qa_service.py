"""
最小可用问答服务：检索 → 上下文构建 → 生成（LLM可选/抽取式回退）+ 会话记忆
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import settings
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

        # 1. 检索
        t0 = time.perf_counter()
        results = await vector_store.search_similar(question, k=settings.SEARCH_K)
        _step("retrieval", t0, query=question, k=settings.SEARCH_K, hits=[
            {
                "rank": i + 1,
                "filename": r["metadata"].get("filename", ""),
                "doc_id": r["metadata"].get("doc_id", ""),
                "score": round(r["score"], 4),
                "preview": r["content"][:80],
            }
            for i, r in enumerate(results)
        ])

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

        confidence = max((r["score"] for r in results), default=0.0)

        return {
            "answer": answer,
            "sources": [
                {
                    "content": r["content"],
                    "score": r["score"],
                    "filename": r["metadata"].get("filename", ""),
                    "doc_id": r["metadata"].get("doc_id", ""),
                }
                for r in results
            ],
            "confidence": round(confidence, 4),
            "session_id": sid,
            "trace": trace,
        }

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
