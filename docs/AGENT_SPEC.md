# Agent 开发分级规范（本项目定版）

> 目的：给"RAG 问答"到"Agent"划一条可执行、可验收的升级路线。
> 每一级回答三个问题：**新增什么机制、判定标准是什么、本项目落在哪个文件**。

## 分级总览

| 级别 | 名称 | 核心机制 | 决策者 | 本项目状态 |
|---|---|---|---|---|
| L1 | 固定流水线 RAG | 检索→拼上下文→生成，一条路走到底 | 代码写死 | ✅ `qa_service.query()`（v1.0 前） |
| L2 | 检索增强 | 查询改写、混合召回+RRF、重排 | 代码写死，但环节可开关 | ✅ `1c4eebc`（rewrite/rerank/reindex） |
| L3 | 工具调用 Agent | LLM 自主决定「查什么、查几次、够不够」，ReAct 循环 | **LLM** | ✅ `agent_service.py` + `/api/chat/agent`（`c2bb7b2`，实测复合问题自主规划 2 次 kb_search） |
| L4 | 记忆分层 | 短期会话记忆之外，跨会话长期事实记忆（抽取→存储→注入） | LLM 抽取，规则召回 | ✅ `memory_service.py` + `/api/chat/memories`（`0b2eac9`，实测 use_history=false 仍认出用户身份） |
| L5 | 评估与自省 | golden set 量化检索质量（hit@k/MRR），迭代有基线 | 评估脚本 | ✅ `scripts/evaluate_retrieval.py`（`5710b70`，11 条金标双通道基线 hit@1/hit@4/MRR 全 1.0） |

## L1 固定流水线（已达）

```
question → retrieve(top-k) → context concat → LLM → answer
```
- 判定：能答对单轮、资料内的事实题。
- 缺陷：追问带指代就失效；一次检索定生死；问句拆开也答不了（需要多次检索的复合问题）。

## L2 检索增强（已达）

在流水线里加可开关的环节，**流程仍由代码固定**，LLM 不做决策：
- 查询改写（指代消解）：`QUERY_REWRITE`
- 双路召回 + RRF 融合：`HYBRID_BM25`
- 召回池扩大 + LLM listwise 重排：`LLM_RERANK` / `RERANK_CANDIDATES`
- 判定：带历史的追问「那它的…」能检索到正确文档；重排能纠正 RRF 错序。

## L3 工具调用 Agent（本级的分水岭）

**控制权从代码交给 LLM**：LLM 拿到工具清单，自己决定调用哪个、传什么参数、要不要继续。

```
loop ≤ AGENT_MAX_STEPS:
    LLM(thought + 动作) → 解析 JSON → 执行工具 → observation 回填上下文
    直到 LLM 给出 final answer
```
- 本项目工具集：`kb_search`（复用 L2 全链路检索）、`kb_stats`（库盘点）、`session_history`（回看对话）。
- 协议：不依赖 function-calling API（LongCat 兼容性未知），用 **JSON-in-text ReAct**——system prompt 规定只输出 `{"thought":…,"tool":…,"args":…}` 或 `{"thought":…,"final":…}`，解析失败按 final 兜底。
- 判定标准：
  1. 复合问题（需要两次不同检索）能拆步完成，如「对比朱雀和星辰编辑器的上线时间」；
  2. trace 里能看到完整 thought→tool→observation 链；
  3. 步数上限、解析失败都有兜底，不死循环。

## L4 记忆分层

| 记忆类型 | 载体 | 生命周期 | 本项目 |
|---|---|---|---|
| 短期（会话内） | `sessions.json` 消息 + 最近6条进 prompt | 单会话 | 已有 |
| 长期（跨会话） | `longterm.json` 原子事实 | 永久，可查可删 | L4 新增 |
| 工作记忆 | 单次请求的 trace | 请求内 | 已有 |

- 机制：每轮问答后异步让 LLM 抽取「关于用户的稳定事实」（偏好、角色、项目背景），去重落盘；新问答时把最相关的事实注入 system prompt。
- 判定：换一个全新 session_id 提问，系统仍知道你之前说过的事实。

## L5 评估与自省

没有量化基线，前面所有调参都是玄学。
- golden set：问题 → 期望命中文档；覆盖中文直查、英文、关键词、语义改写四类。
- 指标：**hit@1**（第一名就对）、**hit@k**（前k有对）、**MRR**（对的排多前的调和平均）。
- 判定：一条命令跑出报告；改动检索链路后重跑，分数变化可解释。

## 边界（不做的级别）

- L6 自主规划/多 Agent 协作、L7 自我改进（自动改 prompt/权重）：对面试演示项目收益低、复杂度高，本规范明确**不做**，防止过度工程。
