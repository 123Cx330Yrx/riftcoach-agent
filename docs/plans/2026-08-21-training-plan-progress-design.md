# 6B-7 Training Plan / Progress 设计稿

## 1. 初学者问题定义

训练建议只有在用户确认后才应成为长期计划；一次复盘里的数字只有能追溯到完整 Run/Artifact，才应成为
进度。Plan 回答“要练什么、用什么指标判断”，Progress 回答“哪一次可靠复盘测到了什么”。趋势只是两个
或多个测量事件的确定性比较，不代表因果、心理或习惯判断。

## 2. 数据与控制流

```text
用户结构化 Plan proposal
→ pending Training Plan Candidate（requires_confirmation）
→ 用户 accept
→ 同一事务锁 Candidate/relationship/active Plan
→ supersede 旧 Plan（若显式更新）并写 active Plan

完整 Conversation-bound Review Task + final Artifact
→ deterministic Training Progress Candidate
→ 用户 accept（当前统一公开 accept 入口）
→ 同一事务验证 task/run/publication/final Artifact digest
→ 校验 active Plan metric allowlist
→ append immutable Progress event / supersede 被纠错 event
→ owner-scoped query + pure deterministic trend comparison
```

所有 SQL 都在短事务中；Riot、Provider、模型、文件读取和网络调用都不在 materializer 内。

## 3. 核心合同

Plan payload 使用严格 envelope：

```json
{
  "value": {
    "action": "activate",
    "title": "Reduce early deaths",
    "objective": "Review positioning before minute 15",
    "metrics": [{
      "metric_key": "deaths_before_15",
      "direction": "decrease",
      "unit": "count",
      "baseline": 2.0,
      "target": 1.0,
      "stable_tolerance": 0.0
    }]
  },
  "expected_version": null
}
```

后续 `complete`/`abandon` action 只引用当前 active Plan 并带 expected version。替换计划仍用 `activate`，
会把旧 active 置为 superseded。pending Candidate 是唯一草稿，不另建可绕过 gate 的 draft CRUD。

Progress payload：

```json
{
  "value": {
    "plan_id": "00000000-0000-0000-0000-000000000001",
    "metric_key": "deaths_before_15",
    "metric_value": 1.0,
    "observed_at": "2026-08-21T12:00:00Z",
    "supersedes_progress_id": null
  }
}
```

source task/run/artifact 放在 Candidate 的强类型 provenance 字段中，不复制到自由 JSON。

## 4. 数据库与并发不变量

- composite FK 把 Plan/Progress 固定到 Candidate 与 owner relationship identity；
- CHECK 强制 Plan/Progress 只能是 `self`；
- partial unique 保证每个 relationship 一个 active Plan；
- advisory lock 串行首次 Plan 创建和 active Plan 替换；
- Progress correction 锁被纠正 event，旧 event 只能 active→superseded；
- trigger 阻止 payload、身份、版本、Artifact provenance 原地修改；
- source Candidate UNIQUE 保证 materialization exactly-once；
- 真实 PostgreSQL CI 证明 migration、FK/CHECK/trigger、并发与回滚，SQLite 不替代。

## 5. 查询和趋势

Plan 查询返回当前 active（或安全 not-found）及 bounded history。Progress 查询可按 metric 过滤，默认返回
active 事件并附每个 metric 的趋势。比较方向由 Plan metric contract 决定：目标 decrease 时数值下降为
improving，increase 时上升为 improving，maintain 在 tolerance 内为 stable。少于两个样本时只返回
`insufficient_data`。

## 6. 错误、安全与边界

公共错误只使用 allowlist：scope not found、plan not found、payload invalid、artifact incomplete、version
conflict、service unavailable。响应不暴露 PUUID、Artifact 路径/正文、Candidate payload、SQL 或原始异常。
observed、跨 owner、非 terminal/rejected publication、digest mismatch、未知 metric 和非有限数值全部拒绝。

## 7. 验证层次

1. pure models/trend 红灯与绿灯；
2. materializer/Fake writer 合同；
3. ORM/Alembic 离线和真实 PostgreSQL migration；
4. Repository 首写、替换、终态、Artifact、纠错、并发/回滚；
5. owner-scoped Service/API/composition/package no-I/O；
6. 完整 pytest、RAG、Harness、compile、安全/治理/diff；
7. 八维 walkthrough、独立提交与 exact-SHA 三 job。

## 8. 本批不做

6B-8 Context/assistant terminal、6B-9 lifecycle/export/exit，正式 Auth/RSO、RLS、SSE、前端、向量检索、
LangGraph、Multi-Agent、新 SDK，以及真实 Riot/Provider 调用。
