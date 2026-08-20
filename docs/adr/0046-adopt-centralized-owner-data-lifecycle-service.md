# ADR-0046：采用集中式 owner data lifecycle service 与 SQL deletion marker

- 状态：Accepted（6B-9 设计批）
- 日期：2026-08-21
- 范围：`6B-9-lifecycle-export-exit-review`
- 上游：ADR-0039、ADR-0040 至 ADR-0045
- 需求：RQ-071

## 背景

6B-1 至 6B-8 已形成 Player Relationship、Conversation/Message、Candidate、typed Memory、Plan/Progress、
Memory-aware Context 和 terminal Assistant。数据分散在多张相互引用的表中；若每个 Repository 各自实现
删除，容易出现 Conversation 已隐藏但 derived Memory 仍可查询、跨 owner 误删、清理失败后正文重新暴露，
或为删除 relationship 破坏仍被 Task 引用的全局 Player Subject。

6A 已证明 terminal Task 的 hidden-before-cleanup，但它只处理单个 task/run。6B-9 需要面向 owner 私有数据的
统一导出、三种明确删除范围、injected-clock retention、bounded purge 和可幂等补偿，同时不把正式 Auth、
RSO、SSE、前端、备份恢复或阶段 8 取消/lease 偷渡进来。

## 决策

### 1. 一个 application service 编排，PostgreSQL 是可见性真源

新增 `OwnerDataLifecycleService`，只接受 trusted `owner_id` 与严格 typed command。Repository 在一个短事务中
锁定目标 Conversation/Relationship，先把全部选中 SQL row 置为不可见并创建 body-free deletion marker；
事务提交后才执行可选文件清理。文件清理失败只把 marker 保持 `cleanup_pending`，重试不能恢复正文。

### 2. 删除范围严格区分

- `conversation_only`：隐藏 Conversation 与 Message；保留 Candidate/长期 Memory/Plan/Progress；
- `conversation_and_derived_memory`：在前者基础上隐藏来源 Conversation 的 Candidate、typed target、Plan/Progress；
- `relationship_private_data`：隐藏 owner-player 的全部 Conversation、Message、player-scoped Candidate/Memory/
  Plan/Progress，并隐藏 relationship；owner-global Preference 不因某个 relationship 删除而消失。

Task/Run/Artifact 保持既有独立生命周期；Player Subject/alias 是跨 owner 稳定身份，不在本批物理删除。

### 3. 使用统一 `hidden_at` 与 deletion marker，不扩张业务状态枚举

Candidate、typed Memory、Plan 和 Progress 增加 nullable `hidden_at`；现有 pending/accepted、active/superseded 等
业务状态保持原意。所有 query、Context selector 和 materialization source lookup 都排除 hidden row。
`owner_data_deletions` 只保存 marker ID、owner、scope、target IDs、安全状态/原因、计数和 timestamps，不保存
Message/Memory/报告正文、PUUID、Prompt 或异常。

### 4. Export 是有界、版本化、owner-scoped snapshot

导出由单个只读事务产生 schema 1.0 snapshot，包含 visible relationship label、Conversation/Message、Candidate
decision、typed Memory/Plan/Progress 与 body-free Task/Artifact references。保留 supersede/provenance 链，但不
导出 PUUID、Key、Prompt、Provider/Tool body、内部异常或 Artifact 正文。每类记录有显式上限；超过上限安全
失败，不返回悄悄截断的“完整导出”。

### 5. Retention 先隐藏，purge 再按 FK 顺序物理清理

injected-clock retention 用固定策略与 bounded batch：Message 90 天、pending Candidate 到 expires_at、rejected/
expired Candidate 决定后 30 天、superseded typed records 90 天、Review Memory 365 天、completed/abandoned
Plan/Progress 365 天。第一阶段只改变可见性并写 marker；purge 只处理已隐藏且过安全等待期的数据，按
Progress→Plan→typed Memory→Candidate→Message 顺序删除。仍被 Task/保留引用阻塞时保留 marker 等待重试。

## 备选方案

### 每个 Repository 各自增加 delete/export

改动分散但无法保证跨表范围、提交顺序和补偿一致，容易形成部分删除。拒绝。

### 只建立 tombstone join，不给业务表加 `hidden_at`

迁移较少，但所有查询都必须正确做 scope join，active partial unique 也仍会把已删除记录视为 active，导致用户
无法重新建立同 key Memory/Plan。拒绝。

### 数据库级 cascade hard delete

实现简单，却会把 Task/Artifact 独立生命周期、审计链和跨 owner Player Subject 一并耦合，清理失败也没有
hidden-before-cleanup 边界。拒绝。

## 后果

优点是删除可见性、导出范围、retention 和补偿只有一个权威编排点；代价是 migration 0009、所有读取路径的
hidden filter、跨表真库测试和更长的 purge 顺序。SQL marker 与文件清理不是跨介质原子事务，因此只保证先
隐藏、后清理和幂等补偿，不声称分布式事务。正式身份验证、RLS、备份恢复、法务级合规与生产 SLA 继续 deferred。
