# 6B-4 Conversation-bound Recent Review Identity 实施计划

> 只执行 RQ-068。完成本计划后停在 6B-4，不进入 6B-5。

## Task 1：冻结 pure domain、fingerprint 与 Service 合同

### 输出

- `ConversationRecentReviewRequest`：只含 count/queue/focus；
- schema 2.0 command、pending intent、binding、private execution target；
- Review Task 1.0/2.0 条件形状和 View 最小投影；
- identity-aware fingerprint；
- Service 的 `create_conversation_review()`。

### 红灯/绿灯

先写测试证明：body 不能含 identity；2.0 缺任一 binding/target 失败；1.0 带 binding 失败；更换任一
trusted tuple 字段会改 fingerprint；公共 View 不含 PUUID/subject/relationship；Fake Repository 的
not-found/conflict/capacity 映射安全。再写最小实现并跑聚焦测试。

## Task 2：增加 reversible Alembic 0004 与 ORM metadata

### 输出

- `review_tasks` 四个 nullable identity columns；
- schema 1.0 all-null / 2.0 all-present CHECK；
- composite FK → Conversation identity；
- identity lookup indexes；
- immutable task identity trigger；
- downgrade 只移除本批对象，旧数据/表仍可恢复。

### 红灯/绿灯

真实 PostgreSQL 断言 constraint/index/trigger 名称、1.0 insert 成功、2.0 partial tuple 失败、cross tuple
失败、direct SQL rebind 失败、upgrade→downgrade 0003→re-upgrade 和 `alembic check`。本机无 PostgreSQL
只允许明确 skip。

## Task 3：实现 PostgreSQL 原子 Conversation binding

### 输出

- `create_conversation_bound_or_replay()` 单事务；
- relationship→Conversation 一致锁顺序；
- private PUUID/routing/alias target 装配；
- create/get/claim/replay 都能映射 2.0，legacy helper 继续映射 1.0。

### 红灯/绿灯

覆盖 owner isolation、active-only、same-key replay、cross-Conversation conflict、capacity、rollback、
alias rename 保持 subject、创建后 archive 的 late claim、create-vs-hide/archive 串行最终态、identity
trigger。同步已有直接调用 `_record_to_task(record)` 的 legacy 测试。

## Task 4：实现 trusted-PUUID Summary/Application/Executor

### 输出

- `build_player_summary_by_puuid()` / `RiotPlayerSummaryBuilder.build_by_puuid()`；
- `RecentReviewApplicationService.review_by_puuid()`，复用 validate/render/compiler/runtime/receipt；
- Executor 1.0/2.0 显式分支。

### 红灯/绿灯

Fake Riot client 记录调用：2.0 的 Account-V1 必须为 0，Match-V5 正常；alias 仅影响显示；target 或
fingerprint 被篡改在 Runtime 前失败；1.0 既有测试保持全绿；existing Runtime/Harness offline vertical
通过。

## Task 5：接 FastAPI、composition、package smoke 与 CI

### 输出

- `POST /conversations/{conversation_id}/reviews/recent`；
- strict 202 response 携带 `conversation_id`，无 PUUID/subject/relationship；
- composed API 绑定同一 ReviewTaskService；
- Worker composition 无第二套 Worker；
- package smoke 覆盖 Link→Conversation→v2 Task→claim/safe terminal，external calls=0；
- 新 PostgreSQL 测试加入 blocking job。

### 红灯/绿灯

API create/replay/404/409/422/503、wrong owner、OpenAPI/import no-I/O；Linux smoke 和旧 endpoint 兼容。

## Task 6：教学、状态、完整门禁与公共闭环

### 输出

- 6B-4 walkthrough 覆盖八维 evidence；
- coverage `planned → complete`；
- canonical、路线、能力矩阵、决策/历史/活动计划一致；
- 只准备 6B-5，绝不实现。

### 验证顺序

1. 新增 focused tests；
2. 相邻 task/conversation/player/product/API/worker/package tests；
3. 完整 pytest；
4. 两套 RAG 质量门、Harness dry-run、compileall；
5. SDK boundary、tracked Secret/run-data、YAML、governance、`git diff --check`；
6. 独立 cached diff、提交、推送；
7. 等待 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 全绿；
8. 关闭 6B-4 并停止。

## 固定失败边界

- 测试/CI 不读真实 Key，不调用 Riot/Provider；
- 不实现 Memory、assistant Message、Auth/RSO、前端/SSE、LangGraph/Multi-Agent/SDK；
- 不用 SQLite 替代 PostgreSQL 语义证据；
- 任一公共 job 失败只做根因最小修复，不把失败 SHA 写成完成证据。
