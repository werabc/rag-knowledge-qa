# Agent 开发分级规范（本项目定版）

> 目的：给"RAG 问答"到"Agent"划一条可执行、可验收的升级路线。
> 每一级回答三个问题：**新增什么机制、判定标准是什么、本项目落在哪个文件**。

## 分级总览

| 级别 | 名称 | 核心机制 | 决策者 | 本项目状态 |
|---|---|---|---|---|
| L1 | 固定流水线 RAG | 检索→拼上下文→生成，一条路走到底 | 代码写死 | ✅ `qa_service.query()`（v1.0 前） |
| L2 | 检索增强 | 查询改写、混合召回+RRF、重排 | 代码写死，但环节可开关 | ✅ `1c4eebc`（rewrite/rerank/reindex） |
| L3 | 工具调用 Agent | LLM 自主决定「查什么、查几次、够不够」，ReAct 循环 | **LLM** | ✅ `agent_service.py` + `/api/v1/chat/agent`（`c2bb7b2`，实测复合问题自主规划 2 次 kb_search） |
| L4 | 记忆分层 | 短期会话记忆之外，跨会话长期事实记忆（抽取→存储→注入） | LLM 抽取，规则召回 | ✅ `memory_service.py` + `/api/v1/chat/memories`（`0b2eac9`，实测 use_history=false 仍认出用户身份） |
| L5 | 评估与自省 | golden set 量化检索质量（hit@k/MRR），迭代有基线 | 评估脚本 | ✅ `scripts/evaluate_retrieval.py`（29 条六类金标 + 拒答指标 + `--strict` 回归门禁，v1.2 深化） |

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
- 召回池扩大 + 重排：`RERANK_MODE`（ce=本地 cross-encoder / llm=LLM listwise / off）/ `RERANK_CANDIDATES`
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
- golden set：**29 条六类**——直查 / 同义改写 / 对抗（跨文档近似句抢位）/ 多跳（expect 列表任一命中）/ 扫描件 OCR / 不可回答（期望拒答）。
- 指标：**hit@1**（第一名就对）、**hit@k**（前k有对）、**MRR**（对的排多前的调和平均）、**refusal_accuracy**（不可回答题按拒答词典正则判定）。
- 判定：一条命令跑出报告；改动检索链路后重跑，分数变化可解释。

## 工程化基座（v1.2）

级别之外的三条「不退化」防线，全部一条命令可验收：

| 机制 | 端点/工具 | 验收方式 |
|---|---|---|
| REST 规范 | 统一 `/api/v1` 前缀；错误契约 `{"error":{code,message,detail}}`；分页信封 `{items,total,page,size}`；状态码语义（204 删除/409 冲突/413 超限） | `scripts/api_contract_test.py` 26 项矩阵全绿，含 openapi 路径扫描 |
| SSE 流式 | `POST /api/v1/chat/stream`：`step/token/citation/done/error` 五事件；`/query` 是消费同一生成器的薄壳（两端口径永不漂移） | 契约测试断言事件时序；curl -N 看首字节与逐帧；面板打字机+trace 实时点亮 |
| 回归门禁 | `eval/baseline.json` + `evaluate_retrieval.py --strict`：逐叶子对比基线，任一核心指标下降即 exit 1 | 实测：关掉重排重启 → strict 点名 hit@1 掉点等三项拦截 |
| 数据入口 | PyMuPDF 逐页提取+按页切块（`page_num` 元数据）；无文本层扫描页 → rapidocr 中文 OCR（`ocr=true`） | 零文本层两页中文扫描 PDF 实测：入库→问答答对事实，来源带「第N页·OCR·被引用」徽标；金标 ocr 类 3 条入门禁集 |

- 设计原则：**门禁拦的是「同一配置下能力退化」**，配置变更（开/关重排）须显式 `--update-baseline` 并说明理由，防默认漂移。
- 评估依赖运行中的服务与固定语料：golden set 与知识库文档是一对整体，增删文档后要同步金标（v1.2 的 ocr 类即随 scan_xuanhe.pdf 入库而加）。

## 边界（不做的级别）

- L6 自主规划/多 Agent 协作、L7 自我改进（自动改 prompt/权重）：对面试演示项目收益低、复杂度高，本规范明确**不做**，防止过度工程。
