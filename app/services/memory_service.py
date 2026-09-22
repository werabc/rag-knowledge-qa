"""
L4 长期记忆：跨会话的原子事实库
每轮问答后异步用 LLM 抽取「关于用户/项目的稳定事实」→ data/longterm.json；
新问答时按词重叠召回最相关事实注入 system prompt。
与短期会话记忆（sessions.json，会话内）分层互补。
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List

from app.config import settings
from app.services.bm25_index import _tokenize

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = (
    "从下面这轮对话中抽取关于用户的稳定事实（身份、职责、偏好、项目背景），"
    "每条一句话、自包含、可独立理解。只输出 JSON 字符串数组，没有可抽取事实则输出 []。\n\n"
    "用户：{question}\n助手：{answer}\n\nJSON："
)

MAX_FACTS = 200


class MemoryService:
    def __init__(self):
        self.facts: List[Dict[str, Any]] = []
        self._store_file = os.path.join(settings.DOCUMENT_STORAGE_PATH, "longterm.json")
        self._load()

    # ---------- 存储 ----------

    def _load(self):
        try:
            if os.path.exists(self._store_file):
                with open(self._store_file, "r", encoding="utf-8") as f:
                    self.facts = json.load(f)
        except Exception:
            logger.exception("加载长期记忆失败，从空开始")
            self.facts = []

    def _save(self):
        try:
            os.makedirs(settings.DOCUMENT_STORAGE_PATH, exist_ok=True)
            tmp = self._store_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.facts, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self._store_file)
        except Exception:
            logger.exception("保存长期记忆失败")

    # ---------- 写入 ----------

    def add_fact(self, fact: str, source: str = "manual") -> Dict[str, Any]:
        fact = fact.strip()
        if not fact:
            return None
        norm = fact.lower().replace(" ", "")
        if any(x["fact"].lower().replace(" ", "") == norm for x in self.facts):
            return None  # 去重
        item = {"id": str(uuid.uuid4()), "fact": fact, "source": source,
                "created_at": datetime.now().isoformat()}
        self.facts.append(item)
        if len(self.facts) > MAX_FACTS:
            self.facts = self.facts[-MAX_FACTS:]
        self._save()
        return item

    async def extract_and_store(self, question: str, answer: str, session_id: str):
        """问答结束后调用：LLM 抽取原子事实入库（失败静默，不影响主流程）"""
        if not (settings.LONGTERM_MEMORY and settings.OPENAI_API_KEY):
            return
        try:
            from app.services.qa_service import qa_service
            raw = await qa_service._llm_chat(
                [{"role": "user", "content": EXTRACT_PROMPT.format(
                    question=question[:500], answer=answer[:500])}], temperature=0.0)
            import re
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            items = json.loads(m.group(0)) if m else []
            for fact in items if isinstance(items, list) else []:
                if isinstance(fact, str) and 5 < len(fact) <= 120:
                    self.add_fact(fact, source=f"session:{session_id[:8]}")
        except Exception:
            logger.exception("长期记忆抽取失败（忽略）")

    def spawn_extraction(self, question: str, answer: str, session_id: str):
        """后台执行抽取，不阻塞响应"""
        try:
            asyncio.get_running_loop().create_task(
                self.extract_and_store(question, answer, session_id))
        except RuntimeError:
            pass

    # ---------- 召回与注入 ----------

    def recall(self, query: str, n: int = 5) -> List[Dict[str, Any]]:
        """词重叠打分召回（事实库小，够用；避免再调一次 LLM/embedding）"""
        qtok = set(_tokenize(query))
        if not qtok:
            return []
        scored = []
        for item in self.facts:
            ftok = set(_tokenize(item["fact"]))
            overlap = len(qtok & ftok)
            if overlap:
                scored.append((overlap / (len(ftok) ** 0.5 + 1e-6), item))
        scored.sort(key=lambda x: -x[0])
        return [item for _, item in scored[:n]]

    def context_block(self, query: str) -> str:
        hits = self.recall(query)
        if not hits:
            return ""
        return ("\n\n【长期记忆】跨会话已知事实（可信，可直接使用）：\n"
                + "\n".join(f"- {h['fact']}" for h in hits))

    # ---------- 管理 ----------

    def list_facts(self) -> List[Dict[str, Any]]:
        return list(self.facts)

    def delete_fact(self, fact_id: str) -> bool:
        before = len(self.facts)
        self.facts = [f for f in self.facts if f["id"] != fact_id]
        if len(self.facts) != before:
            self._save()
            return True
        return False

    def clear(self) -> int:
        n = len(self.facts)
        self.facts = []
        self._save()
        return n


memory_service = MemoryService()
