"""
L3 工具调用 Agent：ReAct 循环（thought → tool → observation）
协议用 JSON-in-text 而非 function-calling API，兼容任意 OpenAI 兼容模型。
决策权在 LLM：查什么、查几次、何时收口由模型自己定。
"""

import json
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.qa_service import qa_service, HISTORY_ROUNDS

logger = logging.getLogger(__name__)

AGENT_SYSTEM = """你是企业知识库 Agent，通过多步工具调用来回答问题。可用工具：
- kb_search: 检索知识库，args {"query": "检索词"}。可以多次调用、每次换不同检索词。
- kb_stats: 查看知识库文档统计，args {}
- session_history: 回看当前对话最近的历史消息，args {}

每一轮只输出一个 JSON 对象，不要其他文字。两种形式二选一：
{"thought": "当前判断", "tool": "工具名", "args": {}}
{"thought": "已掌握信息的总结", "final": "给用户的完整回答"}

规则：回答必须基于工具返回的资料；复合问题先分别检索再汇总；资料不足时明确说不知道。"""

FORCE_FINAL = "已达到最大步数。请基于目前所有观察，直接只输出一个 final JSON 对象。"


class AgentService:
    async def run(self, question: str, session_id: Optional[str] = None,
                  use_history: bool = True) -> Dict[str, Any]:
        t_total = time.perf_counter()
        turns: List[Dict[str, Any]] = []
        scratch: List[Dict[str, str]] = []   # ReAct 中间消息（assistant 动作 + 观察）
        gathered: Dict[str, Dict[str, Any]] = {}  # chunk_key -> passage，去重收集
        sid = session_id or str(uuid.uuid4())
        answer = ""

        for step_i in range(1, settings.AGENT_MAX_STEPS + 1):
            t0 = time.perf_counter()
            raw = await qa_service._llm_chat(
                self._messages(question, sid, use_history, scratch), temperature=0.1)
            action = self._parse_action(raw)
            ms = round((time.perf_counter() - t0) * 1000, 1)

            if action is None:
                # 模型没按协议输出：把原文当最终回答兜底
                answer = raw.strip() or "（Agent 无输出）"
                turns.append({"turn": step_i, "ms": ms, "mode": "protocol_fallback",
                              "raw": raw[:300]})
                break

            if "final" in action:
                answer = str(action["final"])
                turns.append({"turn": step_i, "ms": ms, "mode": "final",
                              "thought": action.get("thought", "")})
                break

            tool = action.get("tool", "")
            args = action.get("args") or {}
            observation, passages = await self._call_tool(tool, args, sid)
            for p in passages:
                gathered[p["key"]] = p
            turns.append({"turn": step_i, "ms": ms, "mode": "tool",
                          "thought": action.get("thought", ""), "tool": tool,
                          "args": args, "observation": observation[:600]})
            scratch.append({"role": "assistant", "content": json.dumps(
                {"thought": action.get("thought", ""), "tool": tool, "args": args},
                ensure_ascii=False)})
            scratch.append({"role": "user", "content": f"观察: {observation}"})
        else:
            # 步数耗尽仍无 final：强制收口一次
            t0 = time.perf_counter()
            scratch.append({"role": "user", "content": FORCE_FINAL})
            raw = await qa_service._llm_chat(
                self._messages(question, sid, use_history, scratch), temperature=0.1)
            action = self._parse_action(raw)
            answer = str(action.get("final") or action.get("thought") or raw) if action \
                else raw.strip()
            turns.append({"turn": settings.AGENT_MAX_STEPS + 1,
                          "ms": round((time.perf_counter() - t0) * 1000, 1),
                          "mode": "forced_final", "thought": "步数耗尽强制收口"})

        # 写入会话记忆（与 L1 问答共用同一份短期记忆）
        qa_service._append_message(sid, question, answer, [])
        qa_service.sessions[sid]["messages"][-1]["agent_turns"] = turns
        qa_service._save_sessions()

        passages_out = [
            {"content": p["content"], "filename": p["filename"],
             "score": p["rrf"], "vec_score": p["vec_score"],
             "bm25_score": p["bm25_score"], "doc_id": p["doc_id"]}
            for p in sorted(gathered.values(), key=lambda x: -x["rrf"])
        ]
        confidence = max((p["vec_score"] for p in gathered.values()), default=0.0)
        trace = [
            {"step": "agent", "ms": round((time.perf_counter() - t_total) * 1000, 1),
             "detail": {"max_steps": settings.AGENT_MAX_STEPS, "turns": turns,
                        "model": settings.LLM_MODEL}},
            {"step": "memory", "ms": 0.0,
             "detail": {"session_id": sid,
                        "total_messages": len(qa_service.sessions[sid]["messages"])}},
        ]
        return {"answer": answer, "sources": passages_out,
                "confidence": round(confidence, 4), "session_id": sid, "trace": trace}

    def _messages(self, question: str, sid: str, use_history: bool,
                  scratch: List[Dict[str, str]]) -> List[Dict[str, str]]:
        msgs = [{"role": "system", "content": AGENT_SYSTEM}]
        if use_history and sid in qa_service.sessions:
            for m in qa_service.sessions[sid]["messages"][-HISTORY_ROUNDS:]:
                msgs.append({"role": m["role"], "content": m["content"][:500]})
        msgs.append({"role": "user", "content": f"问题：{question}"})
        msgs.extend(scratch)
        return msgs

    @staticmethod
    def _parse_action(raw: str) -> Optional[Dict[str, Any]]:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
        return obj if isinstance(obj, dict) and ("final" in obj or "tool" in obj) else None

    async def _call_tool(self, tool: str, args: Dict[str, Any], sid: str):
        """执行工具，返回 (给LLM看的观察文本, 结构化passages供sources)"""
        if tool == "kb_search":
            query = str(args.get("query", "")).strip()
            if not query:
                return "错误：kb_search 需要 args.query", []
            results, _ = await qa_service.hybrid_search(query)
            lines, out = [], []
            for i, r in enumerate(results, 1):
                fn = r["metadata"].get("filename", "")
                meta = r["metadata"]
                key = f"{meta.get('doc_id')}_chunk_{meta.get('chunk_index')}"
                out.append({"key": key, "content": r["content"], "filename": fn,
                            "doc_id": meta.get("doc_id", ""),
                            "rrf": r["rrf"], "vec_score": r["vec_score"],
                            "bm25_score": r["bm25_score"]})
                lines.append(f"[{i}] ({fn} 向量{r['vec_score']:.2f}/BM25 {r['bm25_score']:.2f}) {r['content'][:300]}")
            obs = f"检索「{query}」命中 {len(results)} 条：\n" + "\n".join(lines) \
                if results else f"检索「{query}」无命中"
            return obs, out

        if tool == "kb_stats":
            from app.services.document_service import document_service
            stats = await document_service.get_document_stats()
            return (f"知识库统计：文档 {stats.total_documents} 篇，分块 {stats.total_chunks} 个，"
                    f"类型分布 {stats.file_types}"), []

        if tool == "session_history":
            msgs = qa_service.sessions.get(sid, {}).get("messages", [])[-6:]
            if not msgs:
                return "当前会话暂无历史消息", []
            text = "\n".join(
                f"{'用户' if m['role'] == 'user' else '助手'}: {m['content'][:200]}"
                for m in msgs)
            return f"最近对话：\n{text}", []

        return f"错误：未知工具 {tool}，可用 kb_search/kb_stats/session_history", []


agent_service = AgentService()
