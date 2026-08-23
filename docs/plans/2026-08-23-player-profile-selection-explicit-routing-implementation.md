# 8E Batch B：玩家档案选择与显式 Riot 路由实施计划

## Task 1：冻结合同红灯

- 输出：profile domain/API DTO、service/API/PostgreSQL 预期与 routing contract tests。
- 验证：新测试因缺少模型、方法、endpoint、required region 或 routed builder 明确失败。

## Task 2：实现 profile query

- 输出：`PlayerRepository.list_profiles`、PostgreSQL latest-success projection、
  `PlayerLinkService.list_profiles` 与 `GET /player-profiles`。
- 验证：pure/service/API/PostgreSQL tests 证明 owner isolation、success-only、dedupe、hidden
  exclusion 和 PUUID-free response。

## Task 3：实现 selection DTO

- 输出：Conversation 请求以 `player_profile_id` 为 canonical 字段，旧
  `relationship_id` 作为严格兼容输入别名。
- 验证：新字段成功、旧字段兼容、双字段/跨 owner/未知 ID 安全拒绝。

## Task 4：移除 ambient region

- 输出：legacy request required region、Task fingerprint/payload region、Application/Executor
  region propagation、四地区 `RoutedRiotPlayerSummaryBuilder`、Worker settings 删除环境地区。
- 验证：missing/CN 422、不同 region fingerprint 不同、legacy/conversation 走精确 client、
  `RIOT_REGION` 不能影响请求。

## Task 5：比例回归与持久证据

- 输出：聚焦/相邻/完整 pytest、真实 PostgreSQL、compile/RAG/Harness/security/governance/diff
  门；8E Batch B 八维 walkthrough、coverage/roadmap/canonical/active-plan 同步。
- 验证：本地门全绿，工作区只包含本批文件。

## Task 6：独立公共闭环

- 输出：一个独立 implementation/evidence commit，push `main`，记录 exact SHA 和 Actions run。
- 验证：`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 同 SHA 全绿；公共闭环前
  不进入前端 Batch D。
