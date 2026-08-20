# 6B-8 Memory-aware Context / Typed Conversation Turns Implementation Plan

**Goal:** 在不复制 AgentRuntime/Harness、不提高 Skill ceiling 的前提下，让 Conversation-bound Review 使用
bounded legal Message/Memory Context，并只把可信 terminal output 持久化为 typed conversation turn。

**Architecture:** 服务器 Task binding 进入 Runtime request；PostgreSQL selector 产出严格 snapshot；
run-scoped decorator 将记录作为 data-only whole sections 交给现有 ContextBuilder；body-free manifest 写入
run data plane；SQL terminal writer 重新验证 Task/final Artifact 后追加 assistant Message。legacy 1.0 保持原行为。

**Tech stack:** Python 3.11、Pydantic v2、SQLAlchemy 2、Alembic/PostgreSQL 17、现有 Runtime/Harness、pytest。

## Task 1：pure binding、snapshot、manifest 与选择合同

**Create:** `app/memory/context_models.py`, `app/memory/context_selector.py`, focused tests.

1. 先写 binding identity、record kind/ref、self/observed legal shape、stable priority、count bounds、body-free
   manifest 和 canonical digest 红灯。
2. 写 whole-record selection 红灯：同类稳定 tie-break、Message chronological restoration、少预算整项省略、
   omission reason、调用方 ceiling 不得抬高。
3. 实现无 I/O 模型/纯 selector，聚焦转绿。

## Task 2：PostgreSQL legal snapshot repository

**Create:** `app/persistence/memory_context_repository.py`, PostgreSQL tests.

1. 红灯覆盖两 owner/两 Conversation/同 subject 隔离、active relationship、hidden Message、active-only typed
   records、self/observed 差异、Plan/Progress allowlist 与硬数量上限。
2. 实现单个只读短事务和稳定 SQL order；不持锁进入 Context/Provider。
3. 本机无 PostgreSQL 明确 skip；文件加入 blocking job。

## Task 3：Context decorator 与 private manifest store

**Create:** `app/agent/memory_context.py`, `app/memory/context_manifest_store.py`; modify minimal Context/Runtime seams.

1. 红灯证明所有 Memory sections 为 user/data-only，注入文本不能变 system/tool/budget，基础必需 facts 仍优先，
   manifest selected/omitted 与 ContextBundle 一致。
2. 给 `ContextBuilderV1.build()` 增加 internal-only additional data sections 参数或等价窄 seam；默认 null 时逐字段
   parity，Prompt Program identity 不变。
3. 实现规范 JSON、原子文件写、replay/tamper/path/size failure；Runtime request binding null 时不创建 manifest。

## Task 4：Runtime/Application trusted binding vertical

**Modify:** Runtime models/runtime、Recent Review compiler/service、Task executor and tests.

1. `RuntimeRunRequest` 增加可选 `MemoryContextBinding`；run_id/tuple strict。
2. schema 2.0 Executor 把既有 binding 传给 `review_by_puuid()`；Compiler 写入 Runtime request；legacy schema 1.0
   继续 binding null，旧 test doubles 明确适配。
3. Runtime 只在 binding 存在时要求 memory-aware builder；selector/manifest 失败映射既有 `context_build_failed`，
   Provider 调用保持 0。

## Task 5：terminal Assistant turn 与 typed Candidate seam

**Modify/Create:** Conversation models/records/repository，migration 0008，terminal turn projector/writer/tests.

1. 红灯冻结 terminal turn/proposal strict contract、assistant content digest、source task/run/artifact、publication。
2. 0008 增加 assistant source-run partial unique 与必要 trigger；upgrade/downgrade/re-upgrade、metadata head 全证。
3. Writer 要求 Task succeeded、published/degraded、report available、final Artifact/binding 精确匹配；Conversation
   active；同 run 同 digest replay，不同 digest conflict；并发只写一条。
4. 显式 proposal 通过 Candidate gate 并保持 pending；当前 Recent Review projector 提供空 tuple，不解析报告正文。
5. Worker 在 SQL task succeed 后调用幂等 terminal projector；失败显式记录安全结果，不把 rejected/draft 写入。

## Task 6：production composition、package 与 durable evidence

1. Worker composition 注入真实 selector/manifest store/terminal writer；构造 no-I/O，API 不读取 Key/正文。
2. package smoke schema 1.5 用 Fake Riot/Provider 走 Conversation message→schema 2.0 Review→Memory Context
   manifest；Review 故意安全失败，因此只证明合法 selector、body-free manifest 和零 terminal Assistant，
   外部调用仍为 0。成功 terminal Assistant 与 typed Candidate 由真实 PostgreSQL writer 测试单独证明。
3. 新增 `docs/learning/6b-8-memory-aware-context-typed-turns-walkthrough.md`，补八维 evidence；公共 CI 前
   coverage 保持 planned。
4. 跑聚焦、相邻、完整 pytest、RAG development/holdout、Harness dry-run、compileall、SDK/Secret/tracked
   data、YAML、governance、diff。
5. 独立提交/推送实现并等待 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 全绿；单独状态收尾
   后按 RQ-071 进入 6B-9。

## 验收矩阵

| 维度 | 必须证明 |
|---|---|
| identity | binding 全由 schema 2.0 Task 派生；legacy null；不能客户端覆盖 |
| selection | active/visible/owner-scoped；稳定顺序、固定上限、整记录省略 |
| role | observed 不见 Profile/Plan/Progress；self 可见 allowlisted active data |
| trust/budget | 所有 Memory data-only；同一 ContextSizer；caller 不能提高 ceiling |
| manifest | body-free ID/version/digest/count/reason；安全原子 replay/tamper |
| terminal | succeeded + published/degraded + final Artifact + binding；rejected/failed 零写入 |
| candidate | 只有显式 typed proposal；仍过 Gate、默认 pending；不从 report 猜测 |
| evidence | 真 PostgreSQL、Linux package、八维 walkthrough、exact-SHA 三 job |

## 本批不做

开放域聊天 Skill、Prompt Program output schema 变更、向量检索、6B-9 lifecycle/export、正式 Auth/RSO/RLS、
SSE/前端、MCP、Multi-Agent、新 SDK、真实 Riot/Provider 调用。
