# DeepSeek 领域 held-out 生产装配实施计划

## 目标

在零外部调用下修正未执行 held-out 的注入准入语义，冻结独立输入计划，接入
oracle-blind 生产案例 Executor 与真实门 CLI，并通过 exact-SHA 公开 CI。

## Task 1：冻结正确的 held-out 与输入计划合同

- 将 held-out 升至 1.1.0，三个案例都要求安全端到端成功；保留 ID、顺序和 4-call/
  4000-token 上限。
- 新增严格 input-plan model/loader 和冻结 JSON Artifact。
- 修改 `DomainCaseExecutor` 为 `execute(case_id, provider)`，不向执行器传 oracle。
- 测试：Dataset 生命周期、计划 bytes/hash/路径/order/fixture 漂移和 oracle 隔离。

## Task 2：实现生产案例 Executor

- 复用真实 Catalog/Router/Boundary/ContextBuilder、AgentLoop、local RAG、Secure
  Evaluation 1.1、ReviewHarness 和 typed output。
- 为 `SkillReviewExecutor` 增加默认行为不变的 `max_revisions` 受控注入点，本实验固定 0。
- 从 Agent/Artifact 生成白名单语义观测和 provenance，不上报资源。
- 测试：三场安全路径、user/knowledge marker、引用、事实、Agent failure 和零修订。

## Task 3：实现真实门 CLI 装配

- 顺序固定为 no-I/O preflight/计划核对 -> output reservation -> env/Provider -> Executor
  -> coordinator -> immutable commit。
- 解耦协议证据与未使用领域 Dataset SHA，同时保留协议 bytes/provider/model/resources 门。
- 测试：preflight/plan/output 失败均在 env/provider 前，重复输出、错误配置、脱敏结果。

## Task 4：验证并公开

- 聚焦测试、相邻纵向回归、完整 pytest、两套 RAG、compileall、Harness dry-run、秘密/
  run-data/SDK 边界、governance、stale phrase 和 diff check。
- 更新 canonical state、活动计划、路线修订、能力矩阵和决策记录。
- 提交、推送并验证精确 SHA 的公开 GitHub Actions。
- 本计划不运行真实 Provider 或 held-out。
