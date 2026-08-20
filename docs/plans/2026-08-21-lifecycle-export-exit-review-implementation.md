# 6B-9 Lifecycle / Export / Exit Review Implementation Plan

## Task 1：pure contracts 红灯

- 新增 export snapshot、delete command/result、marker、retention decision 与 purge summary strict models；
- 测试三 scope shape、owner/UUID、timezone、record/byte upper bound、body-free safe code；
- 不接数据库/API。

## Task 2：0009 与 ORM 红灯

- 给 Candidate/typed Memory/Plan/Progress 增加 `hidden_at`；
- 新增 `owner_data_deletions` 与 scope/status/timestamp/check/index；
- 更新 active partial unique、metadata head、upgrade/downgrade/constraint 测试；
- 不改变既有业务 status 枚举。

## Task 3：owner export repository/service

- 在一个只读事务按 owner 收集 visible relationship/conversation/message/candidate/target/training/task refs；
- 投影版本化安全 DTO，保留 decision/supersede/provenance，排除 PUUID/Prompt/Provider/Tool/异常/Artifact body；
- 每类超限 fail closed；两 owner/同 PUUID 真库隔离测试。

## Task 4：三 scope visibility transaction

- 锁 target，服务器派生 identity；
- 同事务按 scope 更新 Conversation/Message/Candidate/typed targets/Plan/Progress/Relationship hidden_at 并插 marker；
- query、selector、accept/materializer 全部排除 hidden；
- replay/concurrency/rollback/跨 owner/另 Conversation 测试。

## Task 5：cleanup compensation、retention 与 purge

- Service 在 SQL commit 后调用 CleanupPort；失败保留 body-free pending marker，retry success 置 complete；
- injected-clock retention 按 90/30/90/365/365 日策略 bounded hide；
- purge 按 Progress→Plan→typed targets→Candidate→Message 删除过等待期 hidden row，FK 阻塞保留 marker；
- 不 sleep、不删除 Task/Artifact/Player Subject。

## Task 6：薄 API、composition 与 package 1.6

- `GET /owner-data/export`；
- `POST /owner-data/deletions`；
- `POST /owner-data/deletions/{marker_id}/retry`（仅 pending）；
- ActorContext 唯一提供 owner，错误 body-safe；
- package 先导出并证明 1 Conversation/Message/Preference/Plan，再 `conversation_only`，证明 Message 不可见但
  Preference/Plan 仍可见，external Riot/Provider calls 为 0。

## Task 7：八维 evidence、exit matrix 与门禁

- walkthrough 覆盖问题/原理、设计/实现、代码地图、流、验证、runbook、失败安全边界、面试表述；
- exit matrix 复核 6B-1 至 6B-9、两 owner/同 PUUID、claimed/observed、无 verified creation、Context/terminal；
- 聚焦、相邻、全量 pytest、RAG 两套、Harness dry-run、compileall、SDK/Secret/tracked-data、YAML、pip、
  governance、diff；
- 独立提交/推送并等待 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 三 job。

## 明确 deferred

正式 Auth/RSO/HTTPS、RLS、SSE/前端、异步大导出、备份副本擦除、阶段 7 MCP、阶段 8 cancellation/recovery/
Multi-Agent、新数据库/队列/向量库和真实 Riot/Provider 调用不在 6B-9。
