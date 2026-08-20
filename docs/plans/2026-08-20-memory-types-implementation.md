# 6B-6 Preferences / Profile / Review Memory 实施计划

## 目标

在不改变阶段 0—8、6B-5 Candidate 状态机和 PostgreSQL 唯一真源的前提下，
实现三类 typed target、真实 materializer、版本冲突保护、owner-scoped 查询与
公共 PostgreSQL 证据。

## Task 1：pure domain contract（红灯→绿灯）

- 新建 typed target models 和严格 payload schemas；
- 新建 `MemoryWriteEnvelope`，解析 `value + expected_version`；
- 冻结 key/scope/role/operation allowlist；
- 增加安全错误码：payload invalid、role forbidden、version conflict；
- 测试 extra 字段、bool 冒充 int、未知 key、越界 payload、observed 越权和首写/更新 envelope。

## Task 2：materializer pure contract

- 实现三个 materializer 的 typed 解析和 reference 合同；
- Fake `MaterializationSession` 证明不 commit/rollback、不做外部 I/O；
- 先写失败测试：错误 scope、错误 role、未知 key、source candidate mismatch、版本冲突；
- 证明 materializer 输出 target kind/version 与 Candidate kind 一致。

## Task 3：ORM 与 Alembic migration

- 新增 `MemoryPreferenceRecord`、`PlayerProfileRecord`、`ReviewMemoryRecord`；
- 为每张表加入 source candidate FK/UNIQUE、owner/relationship composite FK、status/version/payload CHECK；
- 加 partial unique active index、scope/key/version index、supersedes self-FK；
- 加 immutable target trigger，只允许 active→superseded/retired；
- migration 必须可逆，并通过 `alembic check`。

## Task 4：typed target Repository

- 在同一 Session 中取得 PostgreSQL transaction advisory lock；
- 锁定 active 行，校验 expected version；
- supersede 旧行并插入新版本；
- 对 owner-global Preference 正确忽略 Conversation subject 作为业务作用域，但保留 Candidate provenance；
- 对 Profile/Review 保持 owner + relationship + subject + role 隔离；
- source candidate UNIQUE/replay 和并发两个 accept 只允许一个 materializer 成功；
- 把版本冲突转成安全的 `MemoryTargetVersionConflict`，让 Candidate 保持 pending。

## Task 5：注册到 6B-5 composition

- 在生产 composition root 注册三类真实 materializer；
- empty registry 的旧 fail-closed 测试改为“未配置 registry 的显式诊断”，不允许生产 composition 静默空配；
- 维持 Candidate→target→accepted 的同事务顺序；
- 不把 target payload 或底层 SQL 泄露到 HTTP、Trace 或日志。

## Task 6：owner-scoped query service/API

- 新增 Preference/Profile/Review active/history query ports；
- 校验 trusted ActorContext 与 relationship owner；
- 增加三个 GET 路径和 bounded `include_history`；
- 不添加 target PATCH；更正必须重新创建 Candidate 并带 expected version；
- 测试跨 owner、跨 subject、observed Profile、hidden relationship 和 history 上限。

## Task 7：公共验证与教学收尾

- walkthrough 覆盖问题/原理、设计/实现、代码地图、数据/控制流、验证、runbook、失败/安全边界、面试表述；
- focused tests、完整 pytest、compileall、RAG/Harness、secret/tracked-data、YAML、governance、diff check；
- 本机缺少 PostgreSQL/Docker 的测试必须明确 skip；真实 migration/FK/partial unique/trigger/advisory lock/
  concurrency 由 blocking CI 证明；
- packaging smoke 保持 `external_riot_provider_calls=0`；
- 提交实现 SHA，等待 `pytest`、`postgres-migrations`、`packaging-smoke` exact-SHA 全绿；
- 公共闭环后单独状态收尾，coverage 八维置 complete，只交接 6B-7 prepared/waiting authorization。

## 验收矩阵

| 维度 | 必须证明 |
|---|---|
| 类型/权限 | self/observed、scope、key、operation、payload strictness |
| 版本 | 首写、supersede、expected-version 冲突、历史可查 |
| 事务 | target 写入与 Candidate accepted 同 commit；失败全 rollback |
| 幂等/并发 | source candidate replay 不重复；同 key 双 writer 只有一个 active |
| 数据库 | migration 可逆、FK、CHECK、partial unique、immutable trigger |
| API | owner-scoped active/history、safe 404、bounded response、无 PATCH 绕过 |
| 安全 | 无 PUUID/body/provenance/异常泄露；外部 I/O 为 0 |
| 教学 | 八维 evidence 和可准确面试表述 |

## 当前停止点

本文件完成只代表设计与实施顺序冻结。直到实现、测试、提交和 exact-SHA 三 job 全绿，
canonical 仍为 `6B-6 / in_progress`，coverage 仍为 `planned`，不得进入 6B-7。
