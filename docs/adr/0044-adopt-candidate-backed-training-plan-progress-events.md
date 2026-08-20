# ADR-0044：采用 Candidate 驱动的 Training Plan 与 Artifact 进度事件

- 状态：Accepted（6B-7 设计批）
- 日期：2026-08-21
- 范围：`6B-7-training-plan-progress`
- 上游：ADR-0039、ADR-0042、ADR-0043
- 需求：RQ-071

## 背景

6B-5 已建立 Memory Candidate 与事务内 materializer，6B-6 已把 Preference、Profile、
Review Memory 接到真实 PostgreSQL target。长期 Coach 还缺少两个不同概念：用户确认过的
训练计划，以及能够证明“某个允许列表指标在某次完整复盘中测得多少”的进度事件。

Plan 不是一句模型建议，Progress 也不是主观总结。若把二者继续塞进通用 Review Memory，
数据库无法证明一个关系最多一个 active Plan、Progress 指标属于该 Plan，或数值确实来自完整
Artifact；若直接让模型更新一个 progress JSON，又会覆盖历史并把相关性误写成因果。

## 决策

### 1. 使用两张独立业务表

新增 `training_plans` 与 `training_progress_events`。Plan 保存 owner/Conversation/relationship/
subject/self identity、版本、状态、严格 payload、source Candidate 与 supersede 链。Progress 保存
Plan identity、metric key、有限数值、测量时间、source task/run/final-Artifact digest、source
Candidate、状态和可选 supersedes event。

Plan 的公开生命周期为 `active | completed | abandoned | superseded`。待确认的草稿继续由 pending
Candidate 表示；只有用户 `accept` 的 Candidate 才能在同一事务中物化为 active Plan。这样不会创建
一条绕过 Candidate gate 的第二写路径。

### 2. Plan 必须 self-only 且一次只有一个 active

Plan Candidate 必须是 `owner_player + training_plan + set + user_structured_input`，并由 gate 标记
`requires_confirmation=true`。materializer 再要求用户接受事务、active self relationship 和严格
payload。数据库 composite FK/CHECK 与 partial unique index 同时证明：每个 owner relationship 最多
一个 active Plan，observed relationship 永远不能拥有 Plan/Progress。

新的 active Plan 可以显式 supersede 当前 active Plan；expected-version 不匹配时 Candidate 保持
pending，并返回安全 version conflict。完成或放弃仍必须通过新的用户确认 Plan Candidate，不能用
目标表 PATCH 绕过 provenance。

### 3. Plan payload 冻结 metric allowlist

V1 Plan payload 包含有界 `title`、`objective` 和 1—8 个去重 metric specification。每个 metric 固定：

- `metric_key`：安全标识符；
- `direction`：`increase | decrease | maintain`；
- `unit`：`count | ratio | percent | seconds | score`；
- 可选有限 `baseline`/`target` 与非负 `stable_tolerance`。

Progress 只能引用 active Plan 已列出的 metric，不能由客户端或模型临时发明新指标。

### 4. Progress 必须绑定完整 terminal Artifact

Progress Candidate 仅允许 `owner_player + training_progress + append + deterministic_run_fact`，必须同时
带 `source_task_id`、`source_run_id` 和 `source_artifact_sha256`。materializer 在 Repository 拥有的同一
PostgreSQL Session 中验证 Review Task：身份 tuple 匹配、`status=succeeded`、publication 为
`published|degraded`、`report_available=true`、final Artifact kind/digest 精确匹配。缺少或不完整证据
一律 fail closed，Candidate 保持 pending。

### 5. Progress 是不可变事件；纠错追加 superseding event

正常测量会新增 active event，不覆盖之前测量。纠错必须提供 `supersedes_progress_id`，锁定同 owner/
Plan/metric 的 active event，将旧 event 标为 `superseded`，再插入新 event。目标数值、来源身份与 payload
不可原地修改；source Candidate 全局唯一，避免 replay 重复写入。

### 6. 趋势只做确定性比较

查询层按 `observed_at, created_at, progress_id` 稳定排序。相同 metric 最近两个 active event 通过纯函数
比较，并结合 Plan 的 direction/tolerance 输出 `improving | declining | stable | insufficient_data`。
响应只描述数值变化和样本数，禁止输出“因为心态”“已经养成习惯”或任何心理/因果判断。

### 7. API 与范围

新增 owner-scoped 只读 API：

```text
GET /memory/players/{relationship_id}/training-plan
GET /memory/players/{relationship_id}/training-progress
```

写入继续复用 Candidate create/accept endpoint；不增加 Plan/Progress PATCH。6B-8 Context、typed assistant
terminal，6B-9 lifecycle/export，以及 Auth/RSO、SSE、前端、Redis/向量库、新 SDK 和真实外部调用不在本批。

## 备选方案

- **复用万能 Review Memory JSON**：拒绝，Plan/metric/Artifact/纠错不变量无法由数据库证明。
- **直接提供 Plan/Progress CRUD**：拒绝，会绕过已经公共闭环的 Candidate provenance/write gate。
- **引入事件溯源框架**：拒绝；两张表和追加式 Progress 已覆盖当前 Bad Case，新基础设施没有收益证据。

## 后果与重新评估条件

正面结果是权限、计划唯一性、Artifact 完整性、纠错和趋势语义都可独立测试；代价是 PostgreSQL schema、
trigger 和并发测试更多。只有真实产品需要同一 relationship 多 active Plan、非标 metric、跨 Plan 聚合，
或查询性能出现可重复 Bad Case 时，才通过新 ADR 重评估。
